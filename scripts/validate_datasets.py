"""
Dataset Schema and Data-Quality Validation for VitaSense AI
PRD Section 26 (Requirements 35-37)
"""

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
METADATA_DIR = ROOT / "data" / "metadata"


def validate_csv(path: Path, target_col: str = None):
    df = pd.read_csv(path)
    report = {
        "file": str(path.relative_to(ROOT)),
        "row_count": int(len(df)),
        "col_count": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_counts": {col: int(cnt) for col, cnt in df.isnull().sum().items() if cnt > 0},
        "duplicate_rows": int(df.duplicated().sum()),
        "summary": {}
    }

    if target_col and target_col in df.columns:
        report["target_distribution"] = {str(k): int(v) for k, v in df[target_col].value_counts().items()}

    return report


def main():
    print("VitaSense AI - Running Dataset Validation...")
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    datasets = [
        (DATA_RAW / "uci_heart_disease" / "uci_heart_disease.csv", "num", "uci_heart_disease_validation.json"),
        (DATA_RAW / "kaggle_heart_disease" / "heart.csv", "target", "kaggle_heart_disease_validation.json")
    ]

    for p, target, out_name in datasets:
        if not p.exists():
            print(f"[MISSING] {p}")
            continue

        rep = validate_csv(p, target)
        out_file = METADATA_DIR / out_name
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)

        print(f"[VALIDATED] {rep['file']}: {rep['row_count']} rows, {rep['col_count']} columns, duplicates: {rep['duplicate_rows']}")


if __name__ == "__main__":
    main()
