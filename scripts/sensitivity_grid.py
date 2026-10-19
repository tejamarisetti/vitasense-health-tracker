"""
Generate Prevalence Sensitivity Grid across all 15 PPG-DaLiA subjects.
Evaluates theta_rest in {0.03, 0.05, 0.10} g and T_persist in {15, 30, 60} s.
tau_i rule unchanged.
Primary quantity: Event Minutes.
Secondary quantity: Event Count (in parentheses).
No algorithm results.
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
THETA_GRID = [0.03, 0.05, 0.10]
TPERSIST_GRID = [15.0, 30.0, 60.0]


def main():
    print("\n" + "=" * 115)
    print("TABLE: EVENT PREVALENCE SENSITIVITY GRID (All 15 Subjects, Clean Baseline, No Tuning)")
    print("Primary Metric: Event Minutes | Secondary Metric: Event Count in parentheses")
    print("=" * 115)

    cols = [(th, int(tp)) for th in THETA_GRID for tp in TPERSIST_GRID]
    col_names = [f"th={th:.2f}g, T={tp}s" for th, tp in cols]

    grid_results = {key: {} for key in cols}

    for s in ALL_SUBJECTS:
        pkl_path = DATA_DIR / s / f"{s}.pkl"
        with open(pkl_path, "rb") as f:
            data = pickle.load(f, encoding="latin1")
            
        for th, tp in cols:
            res = compute_subject_prevalence(data, s, theta_rest=th, t_persist=float(tp))
            grid_results[(th, tp)][s] = (res["event_time_min"], res["amend1_events"])
        del data

    rows = []
    for s in ALL_SUBJECTS:
        r = {"Subject": s}
        for (th, tp), cname in zip(cols, col_names):
            m, c = grid_results[(th, tp)][s]
            r[cname] = f"{m:5.1f}m ({c:2d})"
        rows.append(r)

    # Total row
    tot_row = {"Subject": "TOTAL"}
    for (th, tp), cname in zip(cols, col_names):
        tot_m = sum(grid_results[(th, tp)][s][0] for s in ALL_SUBJECTS)
        tot_c = sum(grid_results[(th, tp)][s][1] for s in ALL_SUBJECTS)
        tot_row[cname] = f"{tot_m:5.1f}m ({tot_c:2d})"
    rows.append(tot_row)

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print("=" * 115)


if __name__ == "__main__":
    main()
