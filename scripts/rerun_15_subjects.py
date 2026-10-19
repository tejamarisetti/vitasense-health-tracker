"""
Re-run Script for All 15 PPG-DaLiA Subjects
VitaSense AI - Labelled: 'all 15 subjects, clean baseline, no tuning'

Performs:
1. Event prevalence computation under Amendment 1 across S1..S15.
2. Clean PPG baseline estimation across S1..S15 (per-subject and per-activity with bootstrap CIs).
3. Outlier and signal quality report for newly added subjects S6..S9 using plain descriptive language.
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.stats as stats

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.estimators.ppg_hr_estimator import WristPPGHREstimator
from vitasense.quality.event_prevalence import compute_subject_prevalence

DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
ALL_SUBJECTS = [f"S{i}" for i in range(1, 16)]
NEW_SUBJECTS = ["S6", "S7", "S8", "S9"]

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

def find_events(condition_series, dt=2.0, min_duration=30.0):
    min_windows = int(np.ceil(min_duration / dt))
    events = []
    in_event = False
    start_idx = 0
    
    for i, val in enumerate(condition_series):
        if val and not in_event:
            in_event = True
            start_idx = i
        elif not val and in_event:
            in_event = False
            duration = (i - start_idx) * dt
            if (i - start_idx) >= min_windows:
                events.append((start_idx, i - 1, duration))
    if in_event:
        duration = (len(condition_series) - start_idx) * dt
        if (len(condition_series) - start_idx) >= min_windows:
            events.append((start_idx, len(condition_series) - 1, duration))
    return events

def run_all_15():
    missing = [s for s in ALL_SUBJECTS if not (DATA_DIR / s / f"{s}.pkl").exists()]
    if missing:
        print(f"ERROR: Cannot run all 15 subjects. Missing subjects: {missing}")
        print("Please run verify_and_extract_dalia.py first.")
        sys.exit(1)

    print("======================================================================")
    print("ALL 15 SUBJECTS: CLEAN BASELINE & EVENT PREVALENCE (NO TUNING)")
    print("======================================================================\n")

    # 1. Event Prevalence (CANONICAL UNIFIED IMPLEMENTATION via vitasense.quality.event_prevalence)
    # Note: Prior inline calculation with /64 ENMO bug is superseded.
    print("Table 1: Ground Truth Event Prevalence under Amendment 1 (all 15 subjects, clean baseline, no tuning)")
    prevalence_records = []
    
    for subj_id in ALL_SUBJECTS:
        with open(DATA_DIR / subj_id / f"{subj_id}.pkl", "rb") as f:
            data = pickle.load(f, encoding="latin1")
            
        res = compute_subject_prevalence(data=data, subject_id=subj_id)
        prevalence_records.append(res)
        
    prev_df = pd.DataFrame(prevalence_records)
    print(prev_df[["subject", "total_min", "resting_min", "pct_resting", "uncontext_events", "amend1_events", "event_time_min"]].to_string(index=False))
    print("-" * 75)
    print(f"TOTAL: Total Time={prev_df['total_min'].sum():.1f} min | Resting Time={prev_df['resting_min'].sum():.1f} min ({prev_df['resting_min'].sum()/prev_df['total_min'].sum()*100:.1f}%) | Amend1 Events={prev_df['amend1_events'].sum()} ({prev_df['event_time_min'].sum():.1f} min)")

    # 2. PPG Estimator Clean Baseline
    print("\n--- 2. Clean Wrist-PPG Baseline Across All 15 Subjects ---")
    estimator = WristPPGHREstimator(fs_ppg=64.0, window_sec=8.0, step_sec=2.0)
    all_rows = []
    subj_summary = []
    
    for subj_id in ALL_SUBJECTS:
        with open(DATA_DIR / subj_id / f"{subj_id}.pkl", "rb") as f:
            data = pickle.load(f, encoding="latin1")
        bvp = data["signal"]["wrist"]["BVP"].flatten()
        labels = data["label"].flatten()
        activity = data["activity"].flatten()
        n_windows = len(labels)
        
        estimates = estimator.estimate_stream(bvp, total_windows=n_windows)
        
        preds = []
        refs = []
        for i in range(min(len(estimates), n_windows)):
            est = estimates[i]
            ref = labels[i]
            t_sec = i * 2.0
            act_idx = min(len(activity) - 1, int(round((t_sec + 4.0) * 4.0)))
            act_code = int(round(activity[act_idx]))
            
            p_val = float(est.hr_bpm) if est.hr_bpm is not None else np.nan
            r_val = float(ref) if ref is not None else np.nan
            preds.append(p_val)
            refs.append(r_val)
            all_rows.append({
                "subject_id": subj_id,
                "activity_code": act_code,
                "hr_pred": p_val,
                "hr_ref": r_val,
                "is_valid": est.is_valid,
            })
            
        preds = np.array(preds, dtype=float)
        refs = np.array(refs, dtype=float)
        valid_mask = ~np.isnan(preds) & ~np.isnan(refs)
        
        mae = np.mean(np.abs(preds[valid_mask] - refs[valid_mask]))
        med = np.median(np.abs(preds[valid_mask] - refs[valid_mask]))
        corr = stats.pearsonr(preds[valid_mask], refs[valid_mask])[0]
        cov = np.mean(valid_mask) * 100.0
        
        subj_summary.append({
            "subject": subj_id,
            "duration_min": n_windows * 2.0 / 60.0,
            "windows": n_windows,
            "mae_bpm": mae,
            "median_bpm": med,
            "pearson_r": corr,
            "coverage_pct": cov,
        })
        
    sub_df = pd.DataFrame(subj_summary)
    print("\nTable 2: Per-Subject Clean Baseline (all 15 subjects, clean baseline, no tuning):")
    print(sub_df.to_string(index=False))
    
    pooled_valid = pd.DataFrame(all_rows).dropna(subset=["hr_pred", "hr_ref"])
    pooled_mae = np.mean(np.abs(pooled_valid["hr_pred"] - pooled_valid["hr_ref"]))
    pooled_med = np.median(np.abs(pooled_valid["hr_pred"] - pooled_valid["hr_ref"]))
    pooled_corr = stats.pearsonr(pooled_valid["hr_pred"], pooled_valid["hr_ref"])[0]
    print("-" * 75)
    print(f"POOLED (15 Subjects, {len(pooled_valid)} windows): MAE={pooled_mae:.2f} bpm | Median={pooled_med:.2f} bpm | Pearson r={pooled_corr:.4f}")

    # Bootstrap per-activity table across 15 subjects
    print("\nTable 3: Pooled Per-Activity Performance with 95% Bootstrap CIs over Subjects (all 15 subjects, clean baseline, no tuning):")
    # Resample over subjects (1000 iterations)
    rng = np.random.default_rng(42)
    activity_results = []
    
    for act_code, act_name in ACTIVITY_MAP.items():
        act_data = pooled_valid[pooled_valid["activity_code"] == act_code]
        if len(act_data) == 0:
            continue
            
        point_mae = np.mean(np.abs(act_data["hr_pred"] - act_data["hr_ref"]))
        point_med = np.median(np.abs(act_data["hr_pred"] - act_data["hr_ref"]))
        point_corr = stats.pearsonr(act_data["hr_pred"], act_data["hr_ref"])[0] if np.std(act_data["hr_pred"]) > 0 and np.std(act_data["hr_ref"]) > 0 else np.nan
        
        boot_maes = []
        boot_meds = []
        for _ in range(1000):
            sampled_subjs = rng.choice(ALL_SUBJECTS, size=len(ALL_SUBJECTS), replace=True)
            sampled_df = pooled_valid[(pooled_valid["activity_code"] == act_code) & (pooled_valid["subject_id"].isin(sampled_subjs))]
            if len(sampled_df) > 0:
                boot_maes.append(np.mean(np.abs(sampled_df["hr_pred"] - sampled_df["hr_ref"])))
                boot_meds.append(np.median(np.abs(sampled_df["hr_pred"] - sampled_df["hr_ref"])))
                
        mae_ci = [np.percentile(boot_maes, 2.5), np.percentile(boot_maes, 97.5)] if boot_maes else [np.nan, np.nan]
        med_ci = [np.percentile(boot_meds, 2.5), np.percentile(boot_meds, 97.5)] if boot_meds else [np.nan, np.nan]
        
        activity_results.append({
            "activity": act_name,
            "windows": len(act_data),
            "mae_bpm": f"{point_mae:.2f} [{mae_ci[0]:.2f}, {mae_ci[1]:.2f}]",
            "median_bpm": f"{point_med:.2f} [{med_ci[0]:.2f}, {med_ci[1]:.2f}]",
            "pearson_r": f"{point_corr:.4f}",
        })
    print(pd.DataFrame(activity_results).to_string(index=False))

    # 3. Newly Added Subjects Report (S6-S9)
    print("\n--- 3. Plain-Language Outlier Check for S6 to S9 (all 15 subjects, clean baseline, no tuning) ---")
    for s in NEW_SUBJECTS:
        with open(DATA_DIR / s / f"{s}.pkl", "rb") as f:
            d = pickle.load(f, encoding="latin1")
        rp = d["rpeaks"].flatten()
        lbl = d["label"].flatten()
        act = d["activity"].flatten()
        
        rr_sec = np.diff(rp) / 700.0
        rr_bpm = 60.0 / rr_sec
        
        frac_lt_35 = np.mean(rr_bpm < 35.0) * 100.0
        frac_gt_200 = np.mean(rr_bpm > 200.0) * 100.0
        
        # Baseline resting HR
        n_win = len(lbl)
        act_at_lbl = [int(round(act[min(len(act)-1, int(round((i*2.0+4.0)*4.0)))])) for i in range(n_win)]
        act_at_lbl = np.array(act_at_lbl)
        base_mask = (act_at_lbl == 1)
        
        rest_hr = lbl[base_mask]
        mu_r = np.mean(rest_hr)
        sd_r = np.std(rest_hr, ddof=1)
        
        # Rpeak vs label MAE
        # HR from R-peaks in 8s windows:
        hr_rp = []
        for i in range(n_win):
            t_s = i * 2.0 * 700.0
            t_e = t_s + 8.0 * 700.0
            p_win = rp[(rp >= t_s) & (rp < t_e)]
            if len(p_win) > 1:
                hr_rp.append((len(p_win) - 1) * 60.0 / ((p_win[-1] - p_win[0]) / 700.0))
            else:
                hr_rp.append(np.nan)
        hr_rp = np.array(hr_rp)
        val = ~np.isnan(hr_rp) & ~np.isnan(lbl)
        rp_mae = np.mean(np.abs(hr_rp[val] - lbl[val]))
        rp_corr = stats.pearsonr(hr_rp[val], lbl[val])[0]
        
        print(f"\nSubject {s}:")
        print(f"  Questionnaire: {d.get('questionnaire', 'None')}")
        print(f"  Duration: {n_win*2/60:.1f} min ({n_win} windows) | R-peaks: {len(rp)}")
        print(f"  Resting HR (BASELINE): Mean={mu_r:.2f} bpm, SD={sd_r:.2f} bpm, Min={np.min(rest_hr):.2f}, Max={np.max(rest_hr):.2f} bpm")
        print(f"  Threshold tau_i: {max(100.0, mu_r + 2.5*sd_r):.2f} bpm")
        print(f"  RR Intervals: Mean={np.mean(rr_sec):.4f}s, Implied HR Median={np.median(rr_bpm):.1f} bpm")
        print(f"  RR Outliers: HR < 35 bpm = {frac_lt_35:.3f}%, HR > 200 bpm = {frac_gt_200:.3f}%")
        print(f"  R-peak vs Reference Label Agreement: MAE={rp_mae:.3f} bpm, Pearson r={rp_corr:.4f}")

if __name__ == "__main__":
    run_all_15()
