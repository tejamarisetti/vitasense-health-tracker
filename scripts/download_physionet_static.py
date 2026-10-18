"""
PhysioNet Static File Downloader and Verifier (4 Workers, Honest User-Agent)
VitaSense AI - PRD Section 23 & User Instructions

- Concurrency: 4 workers
- User-Agent: Honest academic identifier (no spoofing)
- Resumable: Validates existing files against SHA256SUMS.txt; only downloads missing/corrupt files
- Verifies every single file against official SHA256SUMS.txt
"""

import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
DEST_DIR = ROOT / "data" / "raw" / "physionet_wearable"
SUMS_FILE = DEST_DIR / "SHA256SUMS.txt"
HONEST_USER_AGENT = "VitaSenseAI-Research/1.0"

thread_local = threading.local()


def get_session():
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=5)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": HONEST_USER_AGENT})
        thread_local.session = session
    return thread_local.session


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(512 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def download_and_verify_single(entry: Tuple[str, str], max_retries: int = 3) -> Tuple[str, bool, str, int]:
    expected_sha, rel_path = entry
    dest_path = DEST_DIR / rel_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # If file exists and matches hash, skip download (resumable)
    if dest_path.exists():
        try:
            current_sha = compute_sha256(dest_path)
            if current_sha == expected_sha:
                return rel_path, True, "already_verified", dest_path.stat().st_size
            else:
                # File exists but hash does not match (partial/corrupted) -> remove and redownload
                dest_path.unlink()
        except Exception:
            pass

    url_path = rel_path.replace("\\", "/")
    file_url = BASE_URL + url_path
    session = get_session()

    for attempt in range(1, max_retries + 1):
        try:
            # Stream download to avoid memory spikes on large files like the 34MB notebook
            temp_file = dest_path.with_suffix(dest_path.suffix + ".downloading")
            with session.get(file_url, stream=True, timeout=90) as resp:
                resp.raise_for_status()
                with open(temp_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            f.write(chunk)

            calculated_sha = compute_sha256(temp_file)
            if calculated_sha != expected_sha:
                if temp_file.exists():
                    temp_file.unlink()
                if attempt == max_retries:
                    return rel_path, False, f"hash_mismatch: got {calculated_sha} expected {expected_sha}", 0
                time.sleep(2 ** attempt)
                continue

            temp_file.replace(dest_path)
            return rel_path, True, "downloaded_and_verified", dest_path.stat().st_size

        except Exception as e:
            temp_file = dest_path.with_suffix(dest_path.suffix + ".downloading")
            if temp_file.exists():
                temp_file.unlink()
            if attempt == max_retries:
                return rel_path, False, str(e), 0
            time.sleep(2 ** attempt)

    return rel_path, False, "unknown_error", 0


def run_physionet_download(max_workers: int = 4) -> Dict[str, Any]:
    if not SUMS_FILE.exists():
        raise FileNotFoundError(f"Missing {SUMS_FILE}")

    with open(SUMS_FILE, "r", encoding="utf-8") as f:
        entries = [line.strip().split(maxsplit=1) for line in f if line.strip()]

    print("=" * 70, flush=True)
    print("PhysioNet Wearable Device Dataset 1.0.1 - Static Download & Verification", flush=True)
    print(f"Workers: {max_workers} | User-Agent: {HONEST_USER_AGENT}", flush=True)
    print(f"Catalog entries: {len(entries)} files from {SUMS_FILE.name}", flush=True)
    print("=" * 70, flush=True)

    start_time = time.time()
    completed = 0
    failed: List[Tuple[str, str]] = []
    total_bytes = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_and_verify_single, (sha, path)): path for sha, path in entries}

        for future in as_completed(futures):
            rel_path, success, msg, size = future.result()
            completed += 1
            if success:
                total_bytes += size
            else:
                failed.append((rel_path, msg))

            if completed % 50 == 0 or completed == len(entries):
                elapsed = time.time() - start_time
                mb = total_bytes / (1024 * 1024)
                print(f"  [{completed}/{len(entries)}] Verified: {mb:.2f} MB in {elapsed:.1f}s", flush=True)

    # Final tally across all files on disk
    all_files_on_disk = [f for f in DEST_DIR.rglob("*") if f.is_file() and f.name != "SHA256SUMS.txt"]
    total_disk_bytes = sum(f.stat().st_size for f in all_files_on_disk)

    report = {
        "dataset": "physionet_wearable_stress_exercise",
        "total_catalog_files": len(entries),
        "verified_passing_files": completed - len(failed),
        "failed_files": failed,
        "total_files_on_disk": len(all_files_on_disk),
        "total_size_mb": total_disk_bytes / (1024 * 1024),
        "elapsed_sec": time.time() - start_time,
        "status": "COMPLETE-VERIFIED" if len(failed) == 0 and len(all_files_on_disk) == len(entries) else "PARTIAL",
    }

    print("\n" + "=" * 70, flush=True)
    print(f"Status:                 {report['status']}", flush=True)
    print(f"Total catalog files:    {report['total_catalog_files']}", flush=True)
    print(f"Passing SHA256SUMS.txt: {report['verified_passing_files']}", flush=True)
    print(f"Failed / Incomplete:    {len(failed)}", flush=True)
    print(f"Total size on disk:     {report['total_size_mb']:.2f} MB", flush=True)
    print("=" * 70, flush=True)

    return report


if __name__ == "__main__":
    run_physionet_download(max_workers=4)
