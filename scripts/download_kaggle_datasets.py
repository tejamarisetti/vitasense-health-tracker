"""
Automated Dataset Download Pipeline for VitaSense AI
PRD Sections 23-25 Compliance
Features:
- Manifest-driven (configs/datasets.yaml)
- Explicit status gating ('approved' only)
- Dry-run and list modes
- SHA-256 checksum calculation & verification
- Automatic exponential-backoff retries for network resilience
- Non-leaking credential detection via ~/.kaggle/access_token
"""

import os
import sys
import re
import time
import argparse
import hashlib
import subprocess
from pathlib import Path
import yaml
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "datasets.yaml"
METADATA_DIR = ROOT / "data" / "metadata"


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file efficiently."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def setup_kaggle_credentials() -> bool:
    """Safely configure Kaggle credentials without leaking secrets."""
    kaggle_home = Path.home() / ".kaggle"
    kaggle_json = kaggle_home / "kaggle.json"
    access_token = kaggle_home / "access_token"

    if "KAGGLE_API_TOKEN" in os.environ and os.environ["KAGGLE_API_TOKEN"].strip():
        return True
    if access_token.exists():
        token = access_token.read_text().strip()
        os.environ["KAGGLE_API_TOKEN"] = token
        return True
    if kaggle_json.exists():
        return True

    return False


def run_with_retry(cmd: list, max_retries: int = 3, backoff_factor: int = 2):
    """Execute subprocess command with exponential backoff retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return res
        except subprocess.CalledProcessError as exc:
            if attempt == max_retries:
                raise exc
            sleep_sec = backoff_factor ** attempt
            print(f"  [RETRY] Command failed (attempt {attempt}/{max_retries}). Retrying in {sleep_sec}s...")
            time.sleep(sleep_sec)


def process_dataset(item: dict, dry_run: bool = False, verify_checksums: bool = False):
    name = item.get("id", "unnamed")
    status = item.get("status", "proposed")
    enabled = item.get("enabled", False)
    licence_reviewed = item.get("licence_reviewed", False)
    source = item.get("source", "")
    dest = ROOT / item.get("destination", "data/raw/unknown")
    expected_file = item.get("expected_file", "")
    expected_hash = item.get("sha256", "")

    # Status check
    if status != "approved" or not enabled or not licence_reviewed:
        print(f"[SKIP] {name}: status='{status}', enabled={enabled}, licence_reviewed={licence_reviewed}")
        return

    dest.mkdir(parents=True, exist_ok=True)
    target_path = dest / expected_file if expected_file else None

    # Check existence
    exists = target_path.exists() if target_path else (len(list(dest.glob("*.csv"))) > 0)

    if dry_run or verify_checksums:
        if not exists:
            print(f"[DRY-RUN] {name}: NOT downloaded (target path {dest} not found).")
            return

        if target_path and target_path.exists():
            computed = compute_sha256(target_path)
            if expected_hash:
                match = (computed.lower() == expected_hash.lower())
                print(f"[VERIFY] {name}: SHA-256 {'MATCH' if match else 'MISMATCH'}")
                if not match:
                    print(f"  Expected: {expected_hash}\n  Actual:   {computed}")
            else:
                print(f"[VERIFY] {name}: SHA-256={computed} (no expected hash in manifest)")
        else:
            print(f"[VERIFY] {name}: present at {dest}")
        return

    if exists:
        print(f"[EXISTS] {name}: already downloaded at {dest}")
        if target_path and target_path.exists() and expected_hash:
            computed = compute_sha256(target_path)
            if computed.lower() != expected_hash.lower():
                print(f"  [WARN] Checksum mismatch for {target_path.name}! Re-download suggested.")
        return

    # Real Download Execution
    if source == "ucimlrepo":
        uci_id = item.get("uci_id", 45)
        print(f"[DOWNLOAD] Fetching UCI dataset ID {uci_id} ({name})...")
        try:
            from ucimlrepo import fetch_ucirepo
            dataset = fetch_ucirepo(id=uci_id)
            df = pd.concat([dataset.data.features, dataset.data.targets], axis=1)
            out_file = target_path if target_path else dest / f"{name}.csv"
            df.to_csv(out_file, index=False)
            h = compute_sha256(out_file)
            print(f"[OK] {name} saved: {df.shape}, SHA-256: {h}")
        except Exception as e:
            print(f"[FAIL] Error downloading UCI {name}: {e}")

    elif source == "kaggle":
        slug = item.get("dataset_slug", "")
        if not setup_kaggle_credentials():
            print(f"[FAIL] {name}: Kaggle credentials not found in ~/.kaggle")
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", slug):
            print(f"[FAIL] {name}: invalid Kaggle slug {slug!r}")
            return

        print(f"[DOWNLOAD] Downloading Kaggle dataset {slug} to {dest}...")
        cmd = [sys.executable, "-m", "kaggle", "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"]
        try:
            run_with_retry(cmd)
            print(f"[OK] Successfully downloaded {name} ({slug}).")
            if target_path and target_path.exists():
                h = compute_sha256(target_path)
                print(f"  SHA-256 ({target_path.name}): {h}")
        except Exception as e:
            print(f"[FAIL] Error downloading Kaggle {name}: {e}")
    else:
        print(f"[SKIP] Source '{source}' requires manual approval or custom driver.")


def main():
    parser = argparse.ArgumentParser(description="VitaSense AI Automated Dataset Downloader")
    parser.add_argument("--list", action="store_true", help="List all datasets and status from manifest")
    parser.add_argument("--dry-run", action="store_true", help="Perform pre-flight checks without downloading")
    parser.add_argument("--verify-checksums", action="store_true", help="Verify SHA-256 checksums of local files")
    args = parser.parse_args()

    if not MANIFEST.exists():
        raise SystemExit(f"Missing manifest: {MANIFEST}")

    config = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    datasets = config.get("datasets", [])

    if args.list:
        print(f"\nVitaSense AI Dataset Manifest ({len(datasets)} entries):")
        print(f"{'ID':<34} {'STATUS':<10} {'SOURCE':<12} {'LICENCE REVIEWED'}")
        print("-" * 75)
        for d in datasets:
            lr = "YES" if d.get("licence_reviewed") else "NO"
            print(f"{d.get('id', ''):<34} {d.get('status', ''):<10} {str(d.get('source', '')):<12} {lr}")
        print()
        return

    print(f"VitaSense AI Downloader — Processing {len(datasets)} dataset manifest entries...")
    for item in datasets:
        process_dataset(item, dry_run=args.dry_run, verify_checksums=args.verify_checksums)


if __name__ == "__main__":
    main()
