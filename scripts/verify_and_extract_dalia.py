"""
Verification and Extraction Script for PPG-DaLiA Complete Archive
VitaSense AI - Data Ingestion Pipeline

Steps performed:
1. Verify existence and byte count of data/raw/ppg_dalia/ppg+dalia_full.zip.
2. Run zipfile.testzip() on outer archive.
3. Check and testzip() inner archive if nested (e.g. PPG_FieldStudy.zip).
4. Compute SHA-256 checksum and update configs/datasets.yaml.
5. Extract all 15 subjects (S1..S15) with standard zipfile module.
6. Load every S1.pkl..S15.pkl with pickle (encoding='latin1') and print:
   - Duration (min)
   - R-peaks count
   - Label array length
   - Truncation / integrity check
7. Clean up: delete old hand-extracted files and truncated archives.
"""

import os
import sys
import hashlib
import zipfile
import pickle
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia"
FULL_ZIP = DATA_DIR / "ppg+dalia_full.zip"
EXTRACT_DIR = DATA_DIR / "extracted" / "PPG_FieldStudy"
CONFIG_PATH = ROOT / "configs" / "datasets.yaml"

EXPECTED_INNER_BYTES = 2864337783

def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    if not FULL_ZIP.exists():
        print(f"FAILURE: File not found at {FULL_ZIP}")
        print(f"Current directory contents of {DATA_DIR}:")
        for item in DATA_DIR.iterdir():
            sz = item.stat().st_size if item.is_file() else "DIR"
            print(f"  - {item.name:25s} ({sz})")
        sys.exit(1)

    # 1. Check file size
    file_size = FULL_ZIP.stat().st_size
    print(f"Found {FULL_ZIP.name}: {file_size:,} bytes ({file_size / (1024**3):.3f} GB)")

    # 2. Test outer zip CRC
    print("Testing outer zip CRC via testzip()...")
    with zipfile.ZipFile(FULL_ZIP, "r") as outer_zf:
        bad_file = outer_zf.testzip()
        if bad_file:
            print(f"FAILURE: Corrupted file in outer archive: {bad_file}")
            sys.exit(1)
        print("Outer archive CRC check: PASS")
        outer_names = outer_zf.namelist()
        print(f"Outer archive contains {len(outer_names)} items:")
        for n in outer_names[:10]:
            print(f"  {n}")

    # 3. Compute SHA-256
    print("Computing SHA-256 of outer archive (may take ~15s)...")
    sha256_hash = compute_sha256(FULL_ZIP)
    print(f"SHA-256: {sha256_hash}")

    # 4. Clean old hand-extracted files and extract fresh
    import shutil
    print(f"Cleaning old hand-extracted files at {DATA_DIR / 'extracted'}...")
    shutil.rmtree(DATA_DIR / "extracted", ignore_errors=True)
    os.makedirs(DATA_DIR / "extracted", exist_ok=True)

    print(f"Extracting to {DATA_DIR / 'extracted'}...")
    with zipfile.ZipFile(FULL_ZIP, "r") as outer_zf:
        # Check if outer contains an inner zip
        inner_zips = [n for n in outer_names if n.endswith(".zip")]
        if inner_zips:
            inner_name = inner_zips[0]
            print(f"Found inner zip: {inner_name}. Extracting inner zip first...")
            outer_zf.extract(inner_name, DATA_DIR / "extracted")
            inner_path = DATA_DIR / "extracted" / inner_name
            print(f"Inner zip size: {inner_path.stat().st_size:,} bytes (expected ~{EXPECTED_INNER_BYTES:,})")
            print("Testing inner zip CRC via testzip()...")
            with zipfile.ZipFile(inner_path, "r") as inner_zf:
                bad_inner = inner_zf.testzip()
                if bad_inner:
                    print(f"FAILURE: Corrupted file in inner archive: {bad_inner}")
                    sys.exit(1)
                print("Inner archive CRC check: PASS")
                print("Extracting all files from inner zip...")
                inner_zf.extractall(DATA_DIR / "extracted")
            # Remove intermediate inner zip
            inner_path.unlink()
        else:
            print("Extracting directly from outer zip...")
            outer_zf.extractall(DATA_DIR / "extracted")

    # 5. Verify all 15 subjects
    print("\nVerifying all 15 subjects (S1..S15)...")
    all_subjects = [f"S{i}" for i in range(1, 16)]
    verified_data = {}

    for s in all_subjects:
        pkl_path = EXTRACT_DIR / s / f"{s}.pkl"
        if not pkl_path.exists():
            print(f"FAILURE: Missing {pkl_path}")
            sys.exit(1)
        
        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")
        
        rpeaks = data["rpeaks"].flatten()
        labels = data["label"].flatten()
        duration_min = (len(labels) * 2.0) / 60.0
        
        # Truncation / integrity check:
        wrist_bvp = data["signal"]["wrist"]["BVP"].flatten()
        chest_ecg = data["signal"]["chest"]["ECG"].flatten()
        
        # Check that signals span duration
        bvp_dur = len(wrist_bvp) / 64.0 / 60.0
        ecg_dur = len(chest_ecg) / 700.0 / 60.0
        
        is_truncated = abs(bvp_dur - duration_min) > 0.5 or abs(ecg_dur - duration_min) > 0.5
        status_str = "TRUNCATED!" if is_truncated else "OK (intact)"
        
        print(f"  {s:4s} | Duration: {duration_min:5.1f} min | R-peaks: {len(rpeaks):6d} | Labels: {len(labels):5d} | {status_str}")
        if is_truncated:
            print(f"FAILURE: Subject {s} failed truncation check!")
            sys.exit(1)
            
        verified_data[s] = {
            "duration_min": duration_min,
            "rpeaks": len(rpeaks),
            "labels": len(labels),
        }

    print("\nAll 15 subjects verified intact!")

    # 6. Update configs/datasets.yaml
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f)
        if "ppg_dalia" in cfg.get("datasets", {}):
            cfg["datasets"]["ppg_dalia"]["status"] = "COMPLETE-VERIFIED"
            cfg["datasets"]["ppg_dalia"]["sha256"] = sha256_hash
            cfg["datasets"]["ppg_dalia"]["archive_bytes"] = file_size
            cfg["datasets"]["ppg_dalia"]["subjects_verified"] = 15
            with open(CONFIG_PATH, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
            print("Updated configs/datasets.yaml with COMPLETE-VERIFIED status and SHA-256.")

    # 7. Clean up truncated archive and download artifact
    old_zip = DATA_DIR / "ppg+dalia.zip"
    old_download = DATA_DIR / "ppg+dalia.zip.download"
    if old_zip.exists():
        print(f"Removing old truncated archive: {old_zip.name}")
        old_zip.unlink()
    if old_download.exists():
        print(f"Removing incomplete download: {old_download.name}")
        old_download.unlink()

    print("\nStep 1 Complete: 15/15 subjects verified and extracted successfully.")

if __name__ == "__main__":
    main()
