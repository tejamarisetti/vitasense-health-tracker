"""
Evaluate Tau Sensitivity Grid across all 15 PPG-DaLiA subjects.
Evaluates:
- Tau floor in {100, 110, 120} bpm
- k multiplier in {2.0, 2.5, 3.0}
- Fixed: theta_rest = 0.05 g, T_persist = 30.0 s
Report: event minutes first, counts second (in parentheses).
No algorithm results.
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd

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
ALL_SUBJECTS = [f"S{i}" for i in range(1, 16)]
FLOORS = [100.0, 110.0, 120.0]
K_VALS = [2.0, 2.5, 3.0]


def run_tau_sensitivity():
    cols = [(fl, k) for fl in FLOORS for k in K_VALS]
    col_names = [f"fl={int(fl)}, k={k}" for fl, k in cols]
    grid_results = {key: {} for key in cols}

    for s in ALL_SUBJECTS:
        pkl_path = DATA_DIR / s / f"{s}.pkl"
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

        is_rest_act = np.isin(act_aligned, list(RESTING_ACTIVITY_CODES))
        is_still = (enmo_10s <= 0.05)
        rest_mask = is_rest_act & is_still

        for fl, k in cols:
            tau_i = max(fl, mu_rest + k * sd_rest)
            is_tachy = (labels > tau_i)
            joint = is_tachy & rest_mask
            evs = find_continuous_events(joint, step_sec=2.0, min_duration_sec=30.0)
            tot_min = float(sum(e[2] for e in evs) / 60.0)
            grid_results[(fl, k)][s] = (tot_min, len(evs))
        del data

    print("\n" + "=" * 115)
    print("TABLE: TAU SENSITIVITY GRID (All 15 Subjects, theta=0.05g, T_persist=30s)")
    print("Primary Metric: Event Minutes | Secondary Metric: Event Count in parentheses")
    print("=" * 115)

    rows = []
    for s in ALL_SUBJECTS:
        r = {"Subject": s}
        for (fl, k), cname in zip(cols, col_names):
            m, c = grid_results[(fl, k)][s]
            r[cname] = f"{m:5.1f}m ({c:2d})"
        rows.append(r)

    tot_row = {"Subject": "TOTAL"}
    for (fl, k), cname in zip(cols, col_names):
        tot_m = sum(grid_results[(fl, k)][s][0] for s in ALL_SUBJECTS)
        tot_c = sum(grid_results[(fl, k)][s][1] for s in ALL_SUBJECTS)
        tot_row[cname] = f"{tot_m:5.1f}m ({tot_c:2d})"
    rows.append(tot_row)

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print("=" * 115)


if __name__ == "__main__":
    run_tau_sensitivity()
