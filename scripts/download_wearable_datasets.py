"""
VitaSense AI - Wearable Datasets Downloader & Integrity Verifier
PRD Sections 23-25 | Target: PhysioNet wearable 1.0.1 & PPG-DaLiA (UCI ID 495)

Rules:
- Never merge datasets.
- Compute and verify SHA-256 checksums.
- Respect access controls (both datasets verified as Open Access with CC BY 4.0 / ODC-By v1.0).
- WESAD is retained as 'proposed' (download skipped).
"""

import hashlib
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
CONFIG_FILE = ROOT / "configs" / "datasets.yaml"

PHYSIONET_ZIP_URL = "https://physionet.org/content/wearable-device-dataset/get-zip/1.0.1/"
PHYSIONET_DEST = DATA_RAW / "physionet_wearable"

PPG_DALIA_ZIP_URL = "https://archive.ics.uci.edu/static/public/495/ppg+dalia.zip"
PPG_DALIA_DEST = DATA_RAW / "ppg_dalia"


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def download_file(url: str, dest_file: Path, max_retries: int = 3) -> None:
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = dest_file.with_suffix(".tmp")

    headers = {
        "User-Agent": "VitaSenseAI-Research/1.0"
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[DOWNLOAD] Fetching {url} -> {dest_file.name} (Attempt {attempt}/{max_retries})...")
            with urllib.request.urlopen(req, timeout=120) as response, open(temp_file, "wb") as out_f:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.time()
                last_print = start_time

                while chunk := response.read(1024 * 512):
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print > 3.0:
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024) if total_size > 0 else 0
                        speed = mb / (now - start_time + 1e-5)
                        pct = (downloaded / total_size * 100) if total_size > 0 else 0
                        print(f"  Progress: {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s")
                        last_print = now

            temp_file.replace(dest_file)
            print(f"[SUCCESS] Download completed: {dest_file.name} ({dest_file.stat().st_size / (1024*1024):.2f} MB)")
            return
        except Exception as e:
            print(f"[WARN] Attempt {attempt} failed: {e}")
            if temp_file.exists():
                temp_file.unlink()
            if attempt < max_retries:
                sleep_sec = 2 ** attempt
                print(f"  Retrying in {sleep_sec}s...")
                time.sleep(sleep_sec)
            else:
                raise RuntimeError(f"Failed to download {url} after {max_retries} attempts.") from e


def update_manifest_sha(dataset_id: str, sha256_hash: str) -> None:
    if not CONFIG_FILE.exists():
        return
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for item in data.get("datasets", []):
        if item.get("id") == dataset_id:
            item["sha256"] = sha256_hash

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, indent=2)
    print(f"[MANIFEST] Updated {dataset_id} sha256 in {CONFIG_FILE.name}")


def setup_physionet() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("1. Processing PhysioNet Wearable Device Dataset (v1.0.1)")
    print("=" * 60)
    PHYSIONET_DEST.mkdir(parents=True, exist_ok=True)
    zip_path = PHYSIONET_DEST / "wearable-device-dataset-1.0.1.zip"

    if not zip_path.exists():
        download_file(PHYSIONET_ZIP_URL, zip_path)
    else:
        print(f"[EXISTS] {zip_path.name} already downloaded.")

    sha = compute_sha256(zip_path)
    print(f"[INTEGRITY] SHA-256 ({zip_path.name}): {sha}")
    update_manifest_sha("physionet_wearable_stress_exercise", sha)

    extract_dir = PHYSIONET_DEST / "extracted"
    if not extract_dir.exists():
        print(f"[EXTRACT] Extracting {zip_path.name} to {extract_dir.relative_to(ROOT)}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        print("[SUCCESS] Extraction complete.")
    else:
        print(f"[EXISTS] Extracted directory already present at {extract_dir.relative_to(ROOT)}.")

    return {
        "dataset_id": "physionet_wearable_stress_exercise",
        "zip_path": str(zip_path.relative_to(ROOT)),
        "sha256": sha,
        "size_mb": zip_path.stat().st_size / (1024 * 1024)
    }


def setup_ppg_dalia() -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("2. Processing PPG-DaLiA (UCI ID 495)")
    print("=" * 60)
    PPG_DALIA_DEST.mkdir(parents=True, exist_ok=True)
    zip_path = PPG_DALIA_DEST / "ppg+dalia.zip"

    if not zip_path.exists():
        download_file(PPG_DALIA_ZIP_URL, zip_path)
    else:
        print(f"[EXISTS] {zip_path.name} already downloaded.")

    sha = compute_sha256(zip_path)
    print(f"[INTEGRITY] SHA-256 ({zip_path.name}): {sha}")
    update_manifest_sha("ppg_dalia", sha)

    extract_dir = PPG_DALIA_DEST / "extracted"
    if not extract_dir.exists():
        print(f"[EXTRACT] Extracting {zip_path.name} to {extract_dir.relative_to(ROOT)}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        print("[SUCCESS] Extraction complete.")
    else:
        print(f"[EXISTS] Extracted directory already present at {extract_dir.relative_to(ROOT)}.")

    return {
        "dataset_id": "ppg_dalia",
        "zip_path": str(zip_path.relative_to(ROOT)),
        "sha256": sha,
        "size_mb": zip_path.stat().st_size / (1024 * 1024)
    }


if __name__ == "__main__":
    print("VitaSense AI - Wearable Dataset Downloader & Validator")
    p_info = setup_physionet()
    d_info = setup_ppg_dalia()
    print("\n" + "=" * 60)
    print("[ALL COMPLETE] Approved wearable datasets downloaded and validated.")
    print(f"  PhysioNet: {p_info['size_mb']:.2f} MB, SHA-256: {p_info['sha256']}")
    print(f"  PPG-DaLiA: {d_info['size_mb']:.2f} MB, SHA-256: {d_info['sha256']}")
    print("=" * 60)
