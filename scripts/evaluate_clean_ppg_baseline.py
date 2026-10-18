"""
Evaluation Script: Clean Wrist-PPG HR Estimator Baseline vs ECG Reference
VitaSense AI - Component C Empirical Baseline Evaluation

Evaluates:
- Real clean ambulatory data from PPG-DaLiA (S1).
- Per-activity breakdown (BASELINE, STAIRS, SOCCER, CYCLING, DRIVING, LUNCH, WALKING, WORKING).
- Computes: Mean Absolute Error (MAE), Median Absolute Error, Coverage (%).
- Honest reporting of optical PPG motion vulnerability during physical exercise.
"""

import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator

ROOT = Path(__file__).resolve().parents[1]
S1_PATH = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy" / "S1" / "S1.pkl"

ACTIVITY_MAP = {
    0: "NO_ACTIVITY (Transitions)",
    1: "BASELINE (Resting)",
    2: "STAIRS (Climbing)",
    3: "SOCCER (Table soccer)",
    4: "CYCLING (Outdoor)",
    5: "DRIVING (Car)",
    6: "LUNCH (Sitting/eating)",
    7: "WALKING (Walking)",
    8: "WORKING (Desk work)",
}


def evaluate_subject_clean_baseline(subject_pkl_path: Path):
    if not subject_pkl_path.exists():
        raise FileNotFoundError(f"Missing {subject_pkl_path}")

    print(f"Loading {subject_pkl_path.name}...")
    with open(subject_pkl_path, "rb") as f:
        s_data = pickle.load(f, encoding="latin1")

    bvp = s_data["signal"]["wrist"]["BVP"].flatten()  # 64 Hz
    label_ecg_hr = s_data["label"].flatten()          # Ground truth ECG HR every 2s
    activity_4hz = s_data["activity"].flatten()        # 4 Hz activity labels

    n_windows = len(label_ecg_hr)
    print(f"Total reference windows: {n_windows} (~{n_windows * 2.0 / 60:.1f} minutes)")

    estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
    print("Running spectral wrist-PPG estimation stream...")
    estimates = estimator.estimate_stream(bvp, total_windows=n_windows)

    records = []
    for i in range(min(len(estimates), n_windows)):
        est = estimates[i]
        ecg_ref = label_ecg_hr[i]
        t_sec = i * 2.0

        # Sample activity label at midpoint of 8-second window (t_sec + 4.0s)
        act_idx = min(len(activity_4hz) - 1, int(round((t_sec + 4.0) * 4.0)))
        act_code = int(round(activity_4hz[act_idx]))
        act_name = ACTIVITY_MAP.get(act_code, f"UNKNOWN_{act_code}")

        records.append({
            "window_idx": i,
            "timestamp_sec": t_sec,
            "activity_code": act_code,
            "activity_name": act_name,
            "ecg_ref_hr": ecg_ref,
            "ppg_est_hr": est.hr_bpm,
            "is_valid": est.is_valid,
            "spectral_sqi": est.spectral_sqi,
        })

    df = pd.DataFrame(records)
    df["abs_error"] = np.where(df["is_valid"], np.abs(df["ppg_est_hr"] - df["ecg_ref_hr"]), np.nan)

    # 1. Overall Metrics
    total_w = len(df)
    valid_w = df["is_valid"].sum()
    overall_cov = (valid_w / total_w) * 100.0
    overall_mae = df["abs_error"].mean()
    overall_median = df["abs_error"].median()
    overall_corr = df[["ppg_est_hr", "ecg_ref_hr"]].dropna().corr().iloc[0, 1]

    print("\n" + "=" * 78)
    print(f"CLEAN WRIST-PPG BASELINE EVALUATION: {s_data.get('subject', 'S1')}")
    print("=" * 78)
    print(f"Total Windows:      {total_w}")
    print(f"Coverage:           {overall_cov:.2f}% ({valid_w}/{total_w} windows valid)")
    print(f"Overall MAE:        {overall_mae:.2f} bpm")
    print(f"Overall Median Err: {overall_median:.2f} bpm")
    print(f"Correlation:        {overall_corr:.4f}")
    print("-" * 78)

    # 2. Per-Activity Breakdown
    print(f"{'Activity':<28s} {'Windows':<9s} {'Coverage':<10s} {'MAE (bpm)':<12s} {'Median (bpm)':<12s}")
    print("-" * 78)

    summary_rows = []
    for act_code in sorted(df["activity_code"].unique()):
        sub_df = df[df["activity_code"] == act_code]
        n_act = len(sub_df)
        n_val = sub_df["is_valid"].sum()
        cov = (n_val / n_act) * 100.0 if n_act > 0 else 0.0
        mae = sub_df["abs_error"].mean()
        med = sub_df["abs_error"].median()
        act_name = ACTIVITY_MAP.get(act_code, str(act_code))

        print(f"{act_name:<28s} {n_act:<9d} {cov:>7.1f}%   {mae:>10.2f}   {med:>10.2f}")
        summary_rows.append({
            "activity_code": act_code,
            "activity_name": act_name,
            "windows": n_act,
            "coverage_pct": cov,
            "mae_bpm": mae,
            "median_error_bpm": med,
        })

    print("=" * 78)
    return df, pd.DataFrame(summary_rows)


if __name__ == "__main__":
    evaluate_subject_clean_baseline(S1_PATH)
