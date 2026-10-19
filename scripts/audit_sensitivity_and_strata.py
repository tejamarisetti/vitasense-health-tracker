"""
Script to compute:
1. Arms 1 and 2 Grid Sensitivity Tables across all 15 subjects (Condition 0).
2. Arms 1 and 2 Jump-Size Stratification (<30 bpm, 30-50 bpm, >50 bpm).
3. Detailed breakdown of S8 episodes, peaks, and thresholds.
"""

import sys
import pickle
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.benchmarks.alert_emitter import StandardAlertEmitter
from vitasense.benchmarks.alerting_arms import Arm1FixedThreshold, Arm2PersonalBaselineShrinkage
from vitasense.benchmarks.scoring import score_alert_stream

CACHE_DIR = ROOT / "data" / "processed"
with open(CACHE_DIR / "benchmark_ground_truth.pkl", "rb") as f:
    ground_truth = pickle.load(f)

all_sids = [f"S{i}" for i in range(1, 16)]
subjects_data = {}
calib_hrs = []
for sid in all_sids:
    cache = np.load(CACHE_DIR / f"{sid}_ppg_cache.npz")
    hr_ppg = cache["hr_ppg"]
    enmo_10s = cache["enmo_10s"]
    valid = cache["is_valid"]
    gt = ground_truth[sid]
    hr_eval = hr_ppg + gt["delta_hr"]
    subjects_data[sid] = {
        "hr_ppg": hr_ppg,
        "hr_eval": hr_eval,
        "enmo_10s": enmo_10s,
        "is_valid": valid,
        "injected_episodes": gt["injected_episodes"],
        "natural_events": gt["natural_events"],
        "step_sec": 2.0,
    }
    rest_mask = (enmo_10s <= 0.05) & valid & np.isfinite(hr_ppg)
    calib_hrs.append(hr_ppg[rest_mask])

mu_pop = float(np.mean(np.concatenate(calib_hrs)))
sigma_pop = float(np.std(np.concatenate(calib_hrs), ddof=1))


def run_arm1_sensitivity():
    print("\n" + "=" * 80)
    print("ARM 1 GRID SENSITIVITY TABLE (All 15 Subjects, No Faults, R=60s)")
    print("=" * 80)
    print(f"{'tau_pop (bpm)':<14} {'P (s)':<8} {'Pooled Rec %':>14} {'Clean FA/hr':>13} {'Median Delay':>14}")
    print("-" * 80)

    for tau in [100.0, 110.0, 120.0, 125.0, 130.0]:
        arm = Arm1FixedThreshold(tau_pop=tau)
        for p in [10.0, 20.0, 30.0]:
            emitter = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=60.0)
            tp_total = 0
            ep_total = 0
            fa_total = 0
            hours_total = 0.0
            delays = []

            for sid in all_sids:
                d = subjects_data[sid]
                out = arm.predict(d["hr_eval"], emitter=emitter)
                res = score_alert_stream(out.alert_mask, d["injected_episodes"], d["natural_events"])
                tp_total += res.event_scoring.true_positives
                ep_total += res.event_scoring.n_injected_episodes
                fa_total += res.alert_rate.false_alerts
                hours_total += res.alert_rate.non_event_hours
                delays.extend(res.event_scoring.delays_sec)

            rec = (tp_total / ep_total * 100.0) if ep_total > 0 else 0.0
            fa_hr = (fa_total / hours_total) if hours_total > 0 else 0.0
            med_del = float(np.median(delays)) if delays else 0.0
            print(f"{tau:<14.0f} {p:<8.0f} {rec:>13.1f}% {fa_hr:>13.2f} {med_del:>13.1f}s")


def run_arm2_sensitivity():
    print("\n" + "=" * 90)
    print("ARM 2 GRID SENSITIVITY TABLE (All 15 Subjects, No Faults, R=60s)")
    print("=" * 90)
    print(f"{'k':<6} {'kappa (h)':<10} {'P (s)':<8} {'Pooled Rec %':>14} {'Clean FA/hr':>13} {'Median Delay':>14}")
    print("-" * 90)

    for k in [2.0, 2.5, 3.0, 3.5, 4.0]:
        for kappa in [0.5, 1.0, 2.0]:
            arm = Arm2PersonalBaselineShrinkage(k=k, kappa_hours=kappa, mu_pop=mu_pop, sigma_pop=sigma_pop)
            for p in [10.0, 20.0, 30.0]:
                emitter = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=60.0)
                tp_total = 0
                ep_total = 0
                fa_total = 0
                hours_total = 0.0
                delays = []

                for sid in all_sids:
                    d = subjects_data[sid]
                    out = arm.predict(d["hr_eval"], d["enmo_10s"], emitter=emitter)
                    res = score_alert_stream(out.alert_mask, d["injected_episodes"], d["natural_events"])
                    tp_total += res.event_scoring.true_positives
                    ep_total += res.event_scoring.n_injected_episodes
                    fa_total += res.alert_rate.false_alerts
                    hours_total += res.alert_rate.non_event_hours
                    delays.extend(res.event_scoring.delays_sec)

                rec = (tp_total / ep_total * 100.0) if ep_total > 0 else 0.0
                fa_hr = (fa_total / hours_total) if hours_total > 0 else 0.0
                med_del = float(np.median(delays)) if delays else 0.0
                print(f"{k:<6.1f} {kappa:<10.1f} {p:<8.0f} {rec:>13.1f}% {fa_hr:>13.2f} {med_del:>13.1f}s")


def run_jump_size_stratification():
    print("\n" + "=" * 90)
    print("JUMP-SIZE STRATIFICATION (Protocol Amendment 3 Section 8.2)")
    print("=" * 90)

    # Collect all 112 episodes with physiological jump size = peak_hr - mu_i_rest
    # Load synthetic injection audit csv if available
    audit_file = ROOT / "docs" / "synthetic_injection_audit.csv"
    import csv
    with open(audit_file, "r") as f:
        reader = csv.DictReader(f)
        episodes_audit = list(reader)

    # LOSO evaluated predictions for Arm 1 and Arm 2
    from scripts.run_arms_1_2_benchmark import run_benchmark
    _, results_arm1, sel1, results_arm2, sel2 = run_benchmark()

    # Stratify by jump size
    strata = {
        "Small Jump (< 30 bpm)": [],
        "Moderate Jump (30 - 50 bpm)": [],
        "Large Jump (> 50 bpm)": [],
    }

    for row in episodes_audit:
        sid = row["subject"]
        ep_id = int(row["episode_id"])
        jump_size = float(row["jump_size_bpm"])
        if jump_size < 30.0:
            st = "Small Jump (< 30 bpm)"
        elif jump_size <= 50.0:
            st = "Moderate Jump (30 - 50 bpm)"
        else:
            st = "Large Jump (> 50 bpm)"

        # Check detection in Arm 1 and Arm 2
        det1 = ep_id in results_arm1[sid].event_scoring.detected_episode_ids
        det2 = ep_id in results_arm2[sid].event_scoring.detected_episode_ids

        # Delay
        delay1 = None
        if det1:
            idx = results_arm1[sid].event_scoring.detected_episode_ids.index(ep_id)
            delay1 = results_arm1[sid].event_scoring.delays_sec[idx]

        delay2 = None
        if det2:
            idx = results_arm2[sid].event_scoring.detected_episode_ids.index(ep_id)
            delay2 = results_arm2[sid].event_scoring.delays_sec[idx]

        strata[st].append({
            "sid": sid,
            "ep_id": ep_id,
            "jump": jump_size,
            "det1": det1,
            "delay1": delay1,
            "det2": det2,
            "delay2": delay2,
        })

    print(f"{'Stratum':<28} {'N_ep':>6} {'Arm 1 Rec %':>13} {'Arm 1 MedDelay':>16} {'Arm 2 Rec %':>13} {'Arm 2 MedDelay':>16}")
    print("-" * 95)
    for st_name, eps in strata.items():
        n_ep = len(eps)
        tp1 = sum(1 for e in eps if e["det1"])
        tp2 = sum(1 for e in eps if e["det2"])
        rec1 = (tp1 / n_ep * 100.0) if n_ep > 0 else 0.0
        rec2 = (tp2 / n_ep * 100.0) if n_ep > 0 else 0.0
        delays1 = [e["delay1"] for e in eps if e["delay1"] is not None]
        delays2 = [e["delay2"] for e in eps if e["delay2"] is not None]
        med_del1 = f"{np.median(delays1):.1f}s" if delays1 else "N/A"
        med_del2 = f"{np.median(delays2):.1f}s" if delays2 else "N/A"
        print(f"{st_name:<28} {n_ep:>6} {rec1:>12.1f}% {med_del1:>16} {rec2:>12.1f}% {med_del2:>16}")


def audit_s8():
    print("\n" + "=" * 95)
    print("SUBJECT S8 DETAILED EPISODE & THRESHOLD AUDIT")
    print("=" * 95)

    import csv
    with open(ROOT / "docs" / "synthetic_injection_audit.csv", "r") as f:
        reader = csv.DictReader(f)
        s8_audit = [r for r in reader if r["subject"] == "S8"]

    from scripts.run_arms_1_2_benchmark import run_benchmark
    _, results_arm1, sel1, results_arm2, sel2 = run_benchmark()

    res1 = results_arm1["S8"]
    res2 = results_arm2["S8"]

    d8 = subjects_data["S8"]
    # Re-predict Arm 2 to get the threshold_series
    arm2 = Arm2PersonalBaselineShrinkage(
        k=sel2["S8"][0],
        kappa_hours=sel2["S8"][1],
        mu_pop=mu_pop,
        sigma_pop=sigma_pop,
    )
    em2 = StandardAlertEmitter(p_persist_sec=sel2["S8"][2], r_refractory_sec=60.0)
    out2 = arm2.predict(d8["hr_eval"], d8["enmo_10s"], emitter=em2)

    print(f"S8 Selected: Arm 1 (tau={sel1['S8'][0]:.0f}, P={sel1['S8'][1]:.0f}s) | Arm 2 (k={sel2['S8'][0]:.1f}, kap={sel2['S8'][1]:.1f}h, P={sel2['S8'][2]:.0f}s)")
    print(f"S8 Personal resting mean: {s8_audit[0]['resting_mean']} bpm")
    print("-" * 95)
    print(f"{'Ep#':<4} {'Start':>7} {'Dur':>5} {'Peak HR':>9} {'Req Peak':>9} {'Jump':>7} {'Arm1 Thresh':>12} {'Arm1 Det':>9} {'Arm2 Thresh':>12} {'Arm2 Det':>9}")
    print("-" * 95)

    for r in s8_audit:
        ep_id = int(r["episode_id"])
        ep = d8["injected_episodes"][ep_id - 1]
        t_start = float(ep["start_sec"])
        dur = float(ep["end_sec"]) - t_start
        peak_hr = float(r["actual_peak_hr"])
        req_peak = float(r["requested_peak_hr"])
        jump = float(r["jump_size_bpm"])

        w_start = int(t_start / 2.0)
        w_end = int(float(ep["end_sec"]) / 2.0)
        a1_thresh = 100.0
        a2_thresh = float(np.mean(out2.threshold_series[w_start:w_end+1]))

        # Check continuous run length above thresholds
        hr_seg = d8["hr_eval"][w_start:w_end+1]
        above_a1 = (hr_seg > a1_thresh) & np.isfinite(hr_seg)
        above_a2 = (hr_seg > out2.threshold_series[w_start:w_end+1]) & np.isfinite(hr_seg)

        def max_run(arr):
            m, c = 0, 0
            for v in arr:
                c = c + 1 if v else 0
                if c > m: m = c
            return m * 2

        max_r1 = max_run(above_a1)
        max_r2 = max_run(above_a2)

        det1 = "YES" if ep_id in res1.event_scoring.detected_episode_ids else "NO (MISS)"
        det2 = "YES" if ep_id in res2.event_scoring.detected_episode_ids else "NO (MISS)"

        print(f"#{ep_id:<3} {t_start:>6.0f}s {dur:>4.0f}s {peak_hr:>8.1f} {req_peak:>8.1f} {jump:>6.1f} {a1_thresh:>11.1f} {det1:>9} (max_run={max_r1}s/P30) {a2_thresh:>11.1f} {det2:>9} (max_run={max_r2}s/P10)")





if __name__ == "__main__":
    audit_s8()

