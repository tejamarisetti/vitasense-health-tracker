"""
Evaluation Script: Clean Wrist-PPG Baseline Across All Intact Subjects
VitaSense AI - Component C Empirical Baseline (Interim: 11/15 Subjects)

Evaluates:
- All 11 intact subjects in PPG-DaLiA (S1-S5, S10-S15).
- Per-subject metrics: MAE, median error, coverage, correlation.
- Pooled per-activity metrics with bootstrap-over-subjects 95% Confidence Intervals (1,000 resamples).
- Labeled: 'interim, 11/15 subjects'. No parameter tuning.
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator

DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
SUBJECTS = ["S1", "S2", "S3", "S4", "S5", "S10", "S11", "S12", "S13", "S14", "S15"]

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


def process_all_subjects():
    estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
    all_subject_dfs = []
    subject_summaries = []

    for subj_id in SUBJECTS:
        pkl_path = DATA_DIR / subj_id / f"{subj_id}.pkl"
        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")

        bvp = data["signal"]["wrist"]["BVP"].flatten()
        label_ecg_hr = data["label"].flatten()
        activity = data["activity"].flatten()

        n_windows = len(label_ecg_hr)
        estimates = estimator.estimate_stream(bvp, total_windows=n_windows)

        records = []
        for i in range(min(len(estimates), n_windows)):
            est = estimates[i]
            ecg_ref = label_ecg_hr[i]
            t_sec = i * 2.0
            act_idx = min(len(activity) - 1, int(round((t_sec + 4.0) * 4.0)))
            act_code = int(round(activity[act_idx]))
            act_name = ACTIVITY_MAP.get(act_code, f"UNKNOWN_{act_code}")

            records.append({
                "subject_id": subj_id,
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
        all_subject_dfs.append(df)

        n_val = df["is_valid"].sum()
        cov = (n_val / n_windows) * 100.0
        mae = df["abs_error"].mean()
        med = df["abs_error"].median()
        valid_df = df.dropna(subset=["ppg_est_hr", "ecg_ref_hr"])
        corr = valid_df[["ppg_est_hr", "ecg_ref_hr"]].corr().iloc[0, 1] if len(valid_df) > 10 else np.nan

        subject_summaries.append({
            "subject": subj_id,
            "windows": n_windows,
            "coverage_pct": cov,
            "mae_bpm": mae,
            "median_err_bpm": med,
            "correlation": corr,
        })

    full_df = pd.concat(all_subject_dfs, ignore_index=True)
    subj_df = pd.DataFrame(subject_summaries)
    return full_df, subj_df


def compute_bootstrap_cis(full_df: pd.DataFrame, n_boot: int = 1000, seed: int = 42):
    """
    Computes 95% bootstrap confidence intervals by resampling SUBJECTS with replacement.
    """
    rng = np.random.default_rng(seed)
    unique_subjects = full_df["subject_id"].unique()
    n_subjects = len(unique_subjects)

    activity_codes = sorted(full_df["activity_code"].unique())
    activity_results = []

    # Map each subject's slice for fast indexing
    subj_slices = {s: full_df[full_df["subject_id"] == s] for s in unique_subjects}

    for act in activity_codes:
        act_name = ACTIVITY_MAP.get(act, str(act))
        sub_act = full_df[full_df["activity_code"] == act]
        total_w = len(sub_act)
        n_val = sub_act["is_valid"].sum()
        cov_pct = (n_val / total_w) * 100.0 if total_w > 0 else 0.0

        point_mae = sub_act["abs_error"].mean()
        point_median = sub_act["abs_error"].median()

        # Bootstrap over subjects
        boot_maes = []
        boot_medians = []

        for _ in range(n_boot):
            sampled_subjs = rng.choice(unique_subjects, size=n_subjects, replace=True)
            sampled_dfs = [subj_slices[s] for s in sampled_subjs]
            boot_df = pd.concat(sampled_dfs, ignore_index=True)
            boot_act = boot_df[boot_df["activity_code"] == act]

            if len(boot_act) > 0 and boot_act["is_valid"].sum() > 0:
                boot_maes.append(boot_act["abs_error"].mean())
                boot_medians.append(boot_act["abs_error"].median())

        mae_ci_low, mae_ci_high = np.percentile(boot_maes, [2.5, 97.5]) if boot_maes else (np.nan, np.nan)
        med_ci_low, med_ci_high = np.percentile(boot_medians, [2.5, 97.5]) if boot_medians else (np.nan, np.nan)

        activity_results.append({
            "activity_code": act,
            "activity_name": act_name,
            "windows": total_w,
            "coverage_pct": cov_pct,
            "mae_bpm": point_mae,
            "mae_ci_low": mae_ci_low,
            "mae_ci_high": mae_ci_high,
            "median_err_bpm": point_median,
            "med_ci_low": med_ci_low,
            "med_ci_high": med_ci_high,
        })

    return pd.DataFrame(activity_results)


def main():
    print("=" * 86)
    print("CLEAN WRIST-PPG BASELINE EVALUATION (interim, 11/15 subjects)")
    print("Documented Algorithm: 4th-order Bandpass [0.7, 3.5] Hz + 8s Window / 2s Shift Spectral FFT")
    print("=" * 86)

    full_df, subj_df = process_all_subjects()

    # Table 1: Per-Subject
    print("\nTABLE 1: PER-SUBJECT BASELINE PERFORMANCE (interim, 11/15 subjects)")
    print("-" * 86)
    print(f"{'Subject':<10s} {'Windows':<10s} {'Coverage':<12s} {'MAE (bpm)':<14s} {'Median (bpm)':<14s} {'Correlation':<12s}")
    print("-" * 86)
    for _, r in subj_df.iterrows():
        print(f"{r['subject']:<10s} {r['windows']:<10d} {r['coverage_pct']:>8.1f}%    {r['mae_bpm']:>10.2f}    {r['median_err_bpm']:>10.2f}    {r['correlation']:>10.4f}")
    print("-" * 86)
    pooled_mae = full_df["abs_error"].mean()
    pooled_med = full_df["abs_error"].median()
    pooled_cov = (full_df["is_valid"].sum() / len(full_df)) * 100.0
    valid_df = full_df.dropna(subset=["ppg_est_hr", "ecg_ref_hr"])
    pooled_corr = valid_df[["ppg_est_hr", "ecg_ref_hr"]].corr().iloc[0, 1]
    print(f"{'POOLED':<10s} {len(full_df):<10d} {pooled_cov:>8.1f}%    {pooled_mae:>10.2f}    {pooled_med:>10.2f}    {pooled_corr:>10.4f}")
    print("=" * 86)

    # Table 2: Pooled Per-Activity with Bootstrap-over-Subjects 95% CIs
    print("\nTABLE 2: POOLED PER-ACTIVITY PERFORMANCE (Bootstrap-over-Subjects 95% CIs, n=1000)")
    print("-" * 86)
    act_df = compute_bootstrap_cis(full_df, n_boot=1000, seed=42)
    print(f"{'Activity':<26s} {'Windows':<9s} {'Coverage':<10s} {'MAE (95% CI) bpm':<22s} {'Median (95% CI) bpm':<22s}")
    print("-" * 86)
    for _, r in act_df.iterrows():
        mae_str = f"{r['mae_bpm']:.2f} [{r['mae_ci_low']:.2f}, {r['mae_ci_high']:.2f}]"
        med_str = f"{r['median_err_bpm']:.2f} [{r['med_ci_low']:.2f}, {r['med_ci_high']:.2f}]"
        print(f"{r['activity_name']:<26s} {r['windows']:<9d} {r['coverage_pct']:>7.1f}%   {mae_str:<22s} {med_str:<22s}")
    print("=" * 86)


if __name__ == "__main__":
    main()
