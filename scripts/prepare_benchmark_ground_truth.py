"""
VitaSense AI - Benchmark Ground Truth Generator
Generates and caches deterministic synthetic episodes (Amendment 3 T_gap=60s)
and natural Amendment 1 events for all 15 subjects into data/processed/benchmark_ground_truth.pkl
"""

import pickle
import numpy as np
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.quality.event_prevalence import (
    RESTING_ACTIVITY_CODES,
    align_activity_to_windows,
    find_continuous_events,
)
from vitasense.benchmarks.synthetic_alert_injection import SyntheticTachycardiaInjector
DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"
CACHE_DIR = ROOT / "data" / "processed"


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    injector = SyntheticTachycardiaInjector(seed=42)

    ground_truth = {}
    total_episodes = 0

    print("Generating benchmark ground truth for all 15 subjects...")

    for i in range(1, 16):
        sid = f"S{i}"
        pkl_path = DATA_DIR / sid / f"{sid}.pkl"
        if not pkl_path.exists():
            raise FileNotFoundError(f"Missing {pkl_path}")

        with open(pkl_path, "rb") as f:
            d = pickle.load(f, encoding="latin1")

        labels = np.asarray(d["label"]).flatten()
        activity = np.asarray(d["activity"]).flatten()
        n_windows = len(labels)

        # Load precomputed enmo_10s from cache
        cache_data = np.load(CACHE_DIR / f"{sid}_ppg_cache.npz")
        enmo_10s = cache_data["enmo_10s"]

        # Activity alignment and baseline resting threshold
        act_aligned = align_activity_to_windows(activity, n_windows)
        b_mask = (act_aligned == 1)
        if np.sum(b_mask) >= 10:
            mu_rest = float(np.mean(labels[b_mask]))
            std_rest = float(np.std(labels[b_mask], ddof=1))
        else:
            mu_rest = 70.0
            std_rest = 5.0
        tau_i = max(100.0, mu_rest + 2.5 * std_rest)
        is_resting = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES)) & (enmo_10s <= 0.05)

        # Compute Amendment 1 natural resting tachycardia events
        is_tachy = (labels > tau_i)
        joint_alert = is_resting & is_tachy
        nat_events = find_continuous_events(joint_alert, step_sec=2.0, min_duration_sec=30.0)

        # Inject synthetic tachycardia
        inj_res = injector.inject(labels, is_resting, tau_i, subject_id=sid)
        episodes = inj_res.episodes
        total_episodes += len(episodes)

        # Calculate exact delta_hr added
        delta_hr = np.where(inj_res.synthetic_mask, inj_res.hr_injected - labels, 0.0)

        # Store in dict
        ground_truth[sid] = {
            "n_windows": n_windows,
            "step_sec": 2.0,
            "tau_i_ref": tau_i,
            "mu_rest_ref": mu_rest,
            "std_rest_ref": std_rest,
            "delta_hr": delta_hr,
            "synthetic_mask": inj_res.synthetic_mask,
            "injected_episodes": [
                {
                    "episode_id": ep.episode_id,
                    "start_window": ep.start_window,
                    "end_window": ep.end_window,
                    "start_sec": ep.start_time_sec,
                    "end_sec": ep.end_time_sec,
                    "duration_sec": ep.duration_sec,
                    "plateau_duration_sec": ep.plateau_duration_sec,
                    "ramp_rate_bpm_s": ep.ramp_rate_bpm_s,
                    "peak_hr": ep.peak_hr,
                    "base_hr": ep.base_hr,
                }
                for ep in episodes
            ],
            "natural_events": [
                {
                    "start_window": ev[0],
                    "end_window": ev[1],
                    "start_sec": float(ev[0] * 2.0),
                    "end_sec": float(ev[1] * 2.0),
                    "duration_sec": float(ev[2]),
                }
                for ev in nat_events
            ],
        }

        print(f"  {sid}: {len(episodes)} injected episodes, {len(nat_events)} natural events")

    print(f"Cohort Total: {total_episodes} injected episodes (expected 112).")
    assert total_episodes == 112, f"Expected 112 episodes, got {total_episodes}"

    out_file = CACHE_DIR / "benchmark_ground_truth.pkl"
    with open(out_file, "wb") as f:
        pickle.dump(ground_truth, f)
    print(f"Saved ground truth cache to {out_file}")


if __name__ == "__main__":
    main()
