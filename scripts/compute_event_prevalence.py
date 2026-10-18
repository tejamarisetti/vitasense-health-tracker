"""
Compute Ground Truth Alert Event Prevalence under Amendment 1
VitaSense AI - Protocol Section 3.1 & Amendment 1

Evaluates:
- All 11 intact subjects in PPG-DaLiA (S1-S5, S10-S15).
- Personal resting parameters mu_{i,rest} and sigma_{i,rest} during BASELINE (activity == 1).
- Personal threshold tau_i = max(100 bpm, mu_{i,rest} + 2.5 * sigma_{i,rest}).
- Rest/sedentary condition: activity in [1 (BASELINE), 5 (DRIVING), 6 (LUNCH), 8 (WORKING)]
  AND/OR 10s moving average of wrist ENMO <= 0.05g.
- Continuous persistence for >= 30 seconds (15 consecutive 2-second windows).
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"

SUBJECTS = ["S1", "S2", "S3", "S4", "S5", "S10", "S11", "S12", "S13", "S14", "S15"]
RESTING_ACTIVITIES = {1, 5, 6, 8}  # BASELINE, DRIVING, LUNCH, WORKING


def compute_prevalence_for_subject(subj_id: str):
    pkl_file = DATA_DIR / subj_id / f"{subj_id}.pkl"
    with open(pkl_file, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    label = data["label"].flatten()          # ECG HR @ 2s intervals
    activity = data["activity"].flatten()    # 4 Hz
    acc_wrist = data["signal"]["wrist"]["ACC"]  # 32 Hz, shape (N, 3)

    n_windows = len(label)
    total_duration_min = (n_windows * 2.0) / 60.0

    # Calculate ENMO for each 2s window
    # acc_wrist is 32 Hz -> 64 samples per 2s step
    acc_mag = np.linalg.norm(acc_wrist, axis=1)
    enmo_raw = np.maximum(0.0, acc_mag - 1.0)

    # Downsample ENMO to 2s window resolution
    samples_per_win = 64
    enmo_2s = []
    for i in range(n_windows):
        start = i * samples_per_win
        end = start + samples_per_win
        if start < len(enmo_raw):
            enmo_2s.append(np.mean(enmo_raw[start:end]))
        else:
            enmo_2s.append(0.0)
    enmo_2s = np.array(enmo_2s)

    # 10s moving average of ENMO (5 windows of 2s)
    enmo_10s = np.convolve(enmo_2s, np.ones(5) / 5.0, mode="same")

    # Activity code at midpoint of each window
    act_codes = []
    for i in range(n_windows):
        t_sec = i * 2.0 + 1.0
        act_idx = min(len(activity) - 1, int(round(t_sec * 4.0)))
        act_codes.append(int(round(activity[act_idx])))
    act_codes = np.array(act_codes)

    # 1. Personal baseline from BASELINE (activity == 1)
    baseline_mask = (act_codes == 1)
    if np.sum(baseline_mask) > 10:
        mu_rest = float(np.mean(label[baseline_mask]))
        sigma_rest = float(np.std(label[baseline_mask]))
    else:
        mu_rest = 70.0
        sigma_rest = 5.0

    tau_i = max(100.0, mu_rest + 2.5 * sigma_rest)

    # 2. Resting condition: activity in RESTING_ACTIVITIES AND enmo_10s <= 0.05g
    is_resting = np.isin(act_codes, list(RESTING_ACTIVITIES)) & (enmo_10s <= 0.05)
    total_rest_min = (np.sum(is_resting) * 2.0) / 60.0

    # 3. Candidate tachycardia: ECG HR > tau_i
    is_tachy = (label > tau_i)

    # Joint criterion
    joint_alert = is_resting & is_tachy

    # 4. Count episodes of duration >= 30 seconds (>= 15 consecutive 2s windows)
    # Find contiguous blocks of True
    min_consecutive_windows = 15  # 30s / 2s
    event_count = 0
    total_event_windows = 0

    in_event = False
    current_run = 0

    for val in joint_alert:
        if val:
            current_run += 1
        else:
            if current_run >= min_consecutive_windows:
                event_count += 1
                total_event_windows += current_run
            current_run = 0
    if current_run >= min_consecutive_windows:
        event_count += 1
        total_event_windows += current_run

    total_event_min = (total_event_windows * 2.0) / 60.0

    # Also compute if uncontextualized: how many episodes HR > tau_i regardless of rest?
    raw_event_count = 0
    raw_run = 0
    for val in is_tachy:
        if val:
            raw_run += 1
        else:
            if raw_run >= min_consecutive_windows:
                raw_event_count += 1
            raw_run = 0
    if raw_run >= min_consecutive_windows:
        raw_event_count += 1

    return {
        "subject": subj_id,
        "total_min": total_duration_min,
        "mu_rest": mu_rest,
        "sigma_rest": sigma_rest,
        "tau_i": tau_i,
        "resting_min": total_rest_min,
        "resting_pct": (total_rest_min / total_duration_min) * 100.0,
        "amendment1_events": event_count,
        "amendment1_event_min": total_event_min,
        "uncontextualized_tachy_events": raw_event_count,
    }


def main():
    print("=" * 86)
    print("PPG-DaLiA GROUND-TRUTH EVENT PREVALENCE (Amendment 1: Rest-Contextualized Tachycardia)")
    print("=" * 86)
    results = []
    for s in SUBJECTS:
        res = compute_prevalence_for_subject(s)
        results.append(res)

    df = pd.DataFrame(results)

    print(f"{'Subject':<8s} {'Total Min':<10s} {'Rest (min)':<11s} {'Rest (%)':<9s} {'tau_i':<8s} {'Events':<8s} {'Event Min':<10s} {'Unctxt Events':<14s}")
    print("-" * 86)
    for _, r in df.iterrows():
        print(f"{r['subject']:<8s} {r['total_min']:>8.1f}m  {r['resting_min']:>9.1f}m  {r['resting_pct']:>7.1f}%  {r['tau_i']:>6.1f}  {r['amendment1_events']:>6d}  {r['amendment1_event_min']:>8.1f}m  {r['uncontextualized_tachy_events']:>10d}")
    print("-" * 86)
    total_rec_min = df["total_min"].sum()
    total_rest_min = df["resting_min"].sum()
    total_events = df["amendment1_events"].sum()
    total_event_min = df["amendment1_event_min"].sum()
    total_raw_events = df["uncontextualized_tachy_events"].sum()

    print(f"{'TOTAL':<8s} {total_rec_min:>8.1f}m  {total_rest_min:>9.1f}m  {(total_rest_min/total_rec_min)*100:>7.1f}%  {'--':>6s}  {total_events:>6d}  {total_event_min:>8.1f}m  {total_raw_events:>10d}")
    print("=" * 86)

    print(f"\nSummary Analysis:")
    print(f"- Total Monitoring Time: {total_rec_min:.1f} minutes ({total_rec_min/60:.2f} hours)")
    print(f"- Total Resting Time:    {total_rest_min:.1f} minutes ({total_rest_min/60:.2f} hours, {(total_rest_min/total_rec_min)*100:.1f}%)")
    print(f"- Total Amendment 1 Resting Tachycardia Events: {total_events}")
    print(f"- Subjects with >= 1 event: {(df['amendment1_events'] > 0).sum()} / {len(df)}")
    print(f"- Total Uncontextualized Tachycardia Events (Exercise + Rest): {total_raw_events}")


if __name__ == "__main__":
    main()
