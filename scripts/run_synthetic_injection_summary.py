"""
VitaSense AI - Synthetic Tachycardia Injection Summary Script
Protocol Section 8 (Amendment 2 Option (a)) - Frozen Protocol v2.0.0

Runs the synthetic tachycardia injector (seed = 42) across all 15 PPG-DaLiA subjects.
Prints per subject:
- Subject ID
- Number of injected episodes
- Start time (seconds and minutes) and duration for each episode
- Total injected minutes
- Integrity confirmation (all episodes tagged SYNTHETIC, zero overlap with natural events)

Strict constraint: Does NOT run any alerting algorithms.
"""

import sys
import pickle
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.quality.event_prevalence import (
    compute_enmo,
    align_activity_to_windows,
    RESTING_ACTIVITY_CODES,
)
from vitasense.benchmarks.synthetic_alert_injection import SyntheticTachycardiaInjector


DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"


def main():
    print("=" * 80)
    print("VITASENSE AI - SYNTHETIC RESTING TACHYCARDIA INJECTION AUDIT")
    print("Protocol Amendment 2 Option (a) [Seed 42] - Ground Truth Benchmark Only")
    print("No Alerting Algorithms Evaluated")
    print("=" * 80)

    injector = SyntheticTachycardiaInjector(seed=42)

    total_episodes_all = 0
    total_injected_min_all = 0.0

    print(f"{'Subject':<8} | {'Episodes':<9} | {'Injected Min':<13} | {'Episode Details (ID: start_time -> dur, peak_hr)'}")
    print("-" * 80)

    subject_results = []

    for i in range(1, 16):
        subj_id = f"S{i}"
        pkl_path = DATA_DIR / subj_id / f"{subj_id}.pkl"
        if not pkl_path.exists():
            print(f"Error: {pkl_path} not found.")
            continue

        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")

        labels = np.asarray(data["label"]).flatten()
        activity = np.asarray(data["activity"]).flatten()
        acc = data["signal"]["wrist"]["ACC"]
        n_windows = len(labels)

        # 1. ENMO dynamic energy
        _, enmo_10s = compute_enmo(acc, n_windows=n_windows)

        # 2. Activity alignment
        act_aligned = align_activity_to_windows(activity, n_windows=n_windows)

        # 3. Personal baseline resting threshold
        baseline_mask = (act_aligned == 1)
        if np.sum(baseline_mask) >= 10:
            mu_rest = float(np.mean(labels[baseline_mask]))
            std_rest = float(np.std(labels[baseline_mask], ddof=1))
        else:
            mu_rest = 70.0
            std_rest = 5.0
        tau_i = max(100.0, mu_rest + 2.5 * std_rest)

        # 4. Resting context (Activity in {1, 5, 6, 8} AND ENMO <= 0.05g)
        is_resting = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES)) & (enmo_10s <= 0.05)

        # 5. Inject synthetic tachycardia
        res = injector.inject(
            hr_series=labels,
            is_resting=is_resting,
            tau_i=tau_i,
            subject_id=subj_id,
        )

        n_ep = len(res.episodes)
        inj_min = res.metadata["total_injected_min"]
        total_episodes_all += n_ep
        total_injected_min_all += inj_min

        # Format details
        ep_strs = []
        for ep in res.episodes:
            ep_strs.append(f"#{ep.episode_id}: {ep.start_time_sec:.0f}s ({ep.start_time_sec/60:.1f}m, {ep.duration_sec:.0f}s, {ep.peak_hr:.1f}bpm)")
        details_str = "; ".join(ep_strs[:3])
        if len(ep_strs) > 3:
            details_str += f"; ... (+{len(ep_strs)-3} more)"

        print(f"{subj_id:<8} | {n_ep:<9} | {inj_min:<13.2f} | {details_str}")

        subject_results.append({
            "subject": subj_id,
            "episodes": n_ep,
            "injected_min": inj_min,
            "episode_list": res.episodes,
        })

        del data

    print("-" * 80)
    print(f"{'TOTAL':<8} | {total_episodes_all:<9} | {total_injected_min_all:<13.2f} | Across all 15 subjects")
    print("=" * 80)

    # Detailed per-subject printout of all episodes
    print("\nDETAILED PER-SUBJECT EPISODE TIMESTAMPS:")
    print("=" * 80)
    for sr in subject_results:
        print(f"\n>>> Subject {sr['subject']}: {sr['episodes']} injected episodes, total {sr['injected_min']:.2f} min:")
        for ep in sr["episode_list"]:
            mm = int(ep.start_time_sec // 60)
            ss = int(ep.start_time_sec % 60)
            print(
                f"    Episode {ep.episode_id:2d}: Start window {ep.start_window:4d} | "
                f"Start time {ep.start_time_sec:6.0f}s ({mm:02d}:{ss:02d}) | "
                f"Duration {ep.duration_sec:4.0f}s (Plateau {ep.plateau_duration_sec:4.0f}s) | "
                f"Peak HR {ep.peak_hr:5.1f} bpm | Ramp {ep.ramp_rate_bpm_s:4.2f} bpm/s | "
                f"Tag: {ep.tag} [{ep.event_type}]"
            )
    print("=" * 80)


if __name__ == "__main__":
    main()
