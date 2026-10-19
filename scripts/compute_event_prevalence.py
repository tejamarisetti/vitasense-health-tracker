"""
Compute Ground Truth Alert Event Prevalence under Amendment 1
VitaSense AI - Protocol Section 3.1 & Amendment 1
Unified Canonical Implementation across all 15 PPG-DaLiA subjects.

Uses vitasense.quality.event_prevalence for standard, test-verified metrics.
"""

import sys
import pickle
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.quality.event_prevalence import compute_subject_prevalence

DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
ALL_SUBJECTS = [f"S{i}" for i in range(1, 16)]


def main():
    print("=" * 86)
    print("PPG-DaLiA GROUND-TRUTH EVENT PREVALENCE (Amendment 1: Canonical Unified Implementation)")
    print("=" * 86)

    records = []
    for subj_id in ALL_SUBJECTS:
        pkl_path = DATA_DIR / subj_id / f"{subj_id}.pkl"
        if not pkl_path.exists():
            print(f"Error: Missing {pkl_path}")
            sys.exit(1)
        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")
        res = compute_subject_prevalence(data=data, subject_id=subj_id)
        records.append(res)

    df = pd.DataFrame(records)
    print(f"{'Subject':<8s} {'Total Min':<10s} {'Rest (min)':<11s} {'Rest (%)':<9s} {'tau_i':<8s} {'Events':<8s} {'Event Min':<10s} {'Unctxt Events':<14s}")
    print("-" * 86)
    for _, r in df.iterrows():
        print(f"{r['subject']:<8s} {r['total_min']:>8.1f}m  {r['resting_min']:>9.1f}m  {r['pct_resting']:>7.1f}%  {r['tau_i']:>6.1f}  {r['amend1_events']:>6d}  {r['event_time_min']:>8.1f}m  {r['uncontext_events']:>10d}")
    print("-" * 86)
    total_rec_min = df["total_min"].sum()
    total_rest_min = df["resting_min"].sum()
    total_events = df["amend1_events"].sum()
    total_event_min = df["event_time_min"].sum()
    total_raw_events = df["uncontext_events"].sum()

    print(f"{'TOTAL':<8s} {total_rec_min:>8.1f}m  {total_rest_min:>9.1f}m  {(total_rest_min/total_rec_min)*100:>7.1f}%  {'--':>6s}  {total_events:>6d}  {total_event_min:>8.1f}m  {total_raw_events:>10d}")
    print("=" * 86)


if __name__ == "__main__":
    main()
