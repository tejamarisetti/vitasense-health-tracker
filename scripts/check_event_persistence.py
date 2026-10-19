"""
Persistence check for surviving Amendment 1 events on S5, S6, and S11.
Verifies:
- start window, end window, duration in seconds.
- combined condition (HR > tau AND activity in {1, 5, 6, 8} AND ENMO_10s <= 0.05g) holds for EVERY single window.
- confirms events never span a gap (strictly contiguous True windows).
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
    find_continuous_events,
    RESTING_ACTIVITY_CODES,
)

DATA_DIR = ROOT / "data" / "raw" / "ppg_dalia" / "extracted" / "PPG_FieldStudy"


def audit_persistence(subj_id: str):
    pkl_path = DATA_DIR / subj_id / f"{subj_id}.pkl"
    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    labels = np.asarray(data["label"]).flatten()
    activity = np.asarray(data["activity"]).flatten()
    acc = data["signal"]["wrist"]["ACC"]
    n_windows = len(labels)

    _, enmo_10s = compute_enmo(acc, n_windows=n_windows)
    act_aligned = align_activity_to_windows(activity, n_windows=n_windows)

    base_mask = (act_aligned == 1)
    mu_rest = float(np.mean(labels[base_mask]))
    sd_rest = float(np.std(labels[base_mask], ddof=1))
    tau_i = max(100.0, mu_rest + 2.5 * sd_rest)

    is_tachy = (labels > tau_i)
    is_rest_act = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES))
    is_still = (enmo_10s <= 0.05)
    joint_condition = is_tachy & is_rest_act & is_still

    events = find_continuous_events(joint_condition, step_sec=2.0, min_duration_sec=30.0)

    print("=" * 95)
    print(f"PERSISTENCE AUDIT: SUBJECT {subj_id} (tau_i = {tau_i:.2f} bpm, total events = {len(events)})")
    print("=" * 95)

    all_passed = True
    no_gaps = True

    for idx, (s, e, dur_sec) in enumerate(events):
        win_range = range(s, e + 1)
        sub_cond = joint_condition[s : e + 1]
        
        # Check that EVERY window in the interval is True
        all_true = bool(np.all(sub_cond))
        n_true = int(np.sum(sub_cond))
        expected_len = e - s + 1
        has_gap = (n_true != expected_len)

        if not all_true or has_gap:
            all_passed = False
            no_gaps = False

        min_hr = np.min(labels[s : e + 1])
        max_hr = np.max(labels[s : e + 1])
        acts = set(act_aligned[s : e + 1])
        max_enmo = np.max(enmo_10s[s : e + 1])

        t_start_s = s * 2.0
        t_end_s = (e + 1) * 2.0

        status_str = "VALID (100% windows match, no gap)" if (all_true and not has_gap) else "INVALID!"
        print(
            f"Event #{idx+1:02d}: Start Win={s:4d}..End={e:4d} | "
            f"Time={t_start_s:6.1f}s..{t_end_s:6.1f}s | "
            f"Dur={dur_sec:4.0f}s ({expected_len:2d} win) | "
            f"HR=[{min_hr:5.1f}..{max_hr:5.1f}] | "
            f"Act={acts} | "
            f"Max ENMO={max_enmo:.4f}g | {status_str}"
        )

    print("-" * 95)
    print(f"Summary for {subj_id}: All windows verified True = {all_passed} | Contiguous without gaps = {no_gaps}\n")
    return all_passed and no_gaps


def main():
    for s in ["S5", "S6", "S11"]:
        ok = audit_persistence(s)
        if not ok:
            print(f"FAILURE on {s}")
            sys.exit(1)
    print("ALL PERSISTENCE CHECKS PASSED: Combined condition holds for 100% of windows with 0 gaps.")


if __name__ == "__main__":
    main()
