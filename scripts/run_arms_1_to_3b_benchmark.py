"""
VitaSense AI - Benchmark Runner for Arms 1, 2, 3a, 3b, and 3b-noMotion under LOSO Cross-Validation
Protocol Section 4 (Frozen v1.0.0) & Amendments 3 and 4

Evaluates:
- Arm 1: Fixed Threshold (tau_pop in {100, 110, 120, 125, 130} bpm, P in {10, 20, 30}s, R = 60s)
- Arm 2: Personal Baseline with Shrinkage (k in {2.0, 2.5, 3.0, 3.5, 4.0}, kappa in {0.5, 1.0, 2.0}h, P in {10, 20, 30}s, R = 60s)
- Arm 3a: Kinematic Motion Gate Only (theta_rest in {0.03, 0.05, 0.08}g, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)
- Arm 3b: Multi-Attribute Trust Score Gate (theta_trust in {0.60, 0.70, 0.80}, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)
- Arm 3b-noMotion: Trust Gate Without Motion (theta_trust in {0.60, 0.70, 0.80}, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)

LOSO Tuning Protocol:
- Full 15-subject Leave-One-Subject-Out cross-validation.
- Hyperparameter selection conducted strictly inside training folds (N-1 subjects) using Amendment 4 selection rule:
  Choose candidate achieving pooled training Recall >= 85% with minimum FA/hr; if none reaches 85%, maximize recall.
- Evaluated on test fold; reported per subject and pooled (All-15, Without-S5, and S5/S6/S11).
- Table labeled: "preliminary, Arms 1-3b-noMotion, no faults, Amendment 4".
"""

import sys
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.benchmarks.alert_emitter import StandardAlertEmitter
from vitasense.benchmarks.alerting_arms import (
    Arm1FixedThreshold,
    Arm2PersonalBaselineShrinkage,
    Arm3aKinematicGate,
    Arm3bTrustScoreGate,
    Arm3bNoMotionGate,
    compute_causal_baseline_threshold,
)
from vitasense.benchmarks.scoring import score_alert_stream, BenchmarkScoringResult


CACHE_DIR = ROOT / "data" / "processed"


def load_subject_data():
    """Loads all 15 subjects' PPG cache and ground-truth events."""
    gt_file = CACHE_DIR / "benchmark_ground_truth.pkl"
    if not gt_file.exists():
        raise FileNotFoundError(f"Missing {gt_file}.")

    with open(gt_file, "rb") as f:
        ground_truth = pickle.load(f)

    subjects_data = {}
    for sid in [f"S{i}" for i in range(1, 16)]:
        cache_path = CACHE_DIR / f"{sid}_ppg_cache.npz"
        cache = np.load(cache_path)
        hr_ppg = cache["hr_ppg"]
        enmo_10s = cache["enmo_10s"]
        s_trust = cache["s_trust"]
        s_trust_nomot = cache["s_trust_no_motion"]
        is_valid = cache["is_valid"]

        gt = ground_truth[sid]
        delta_hr = gt["delta_hr"]
        hr_eval = hr_ppg + delta_hr

        subjects_data[sid] = {
            "hr_ppg": hr_ppg,
            "hr_eval": hr_eval,
            "enmo_10s": enmo_10s,
            "s_trust": s_trust,
            "s_trust_nomot": s_trust_nomot,
            "is_valid": is_valid,
            "injected_episodes": gt["injected_episodes"],
            "natural_events": gt["natural_events"],
            "step_sec": 2.0,
        }

    return subjects_data


def compute_pop_priors(train_sids: List[str], subjects_data: Dict[str, Any], theta_rest: float = 0.05):
    calib_hrs = []
    for sid in train_sids:
        d = subjects_data[sid]
        hr = d["hr_ppg"]
        enmo = d["enmo_10s"]
        valid = d["is_valid"]
        rest_mask = (enmo <= theta_rest) & valid & np.isfinite(hr)
        calib_hrs.append(hr[rest_mask])

    pooled = np.concatenate(calib_hrs)
    mu_pop = float(np.mean(pooled))
    sigma_pop = float(np.std(pooled, ddof=1))
    return mu_pop, sigma_pop


def tune_arm1(train_sids: List[str], subjects_data: Dict[str, Any]):
    tau_grid = [100.0, 110.0, 120.0, 125.0, 130.0]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    raw_conds = {}
    for tau in tau_grid:
        arm = Arm1FixedThreshold(tau_pop=tau)
        raw_conds[tau] = {sid: arm.predict(subjects_data[sid]["hr_eval"]).raw_alert_mask for sid in train_sids}

    cands = []
    for tau in tau_grid:
        for p in p_grid:
            em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
            tp, ep, fa, nh = 0, 0, 0, 0.0
            for sid in train_sids:
                d = subjects_data[sid]
                m = em.emit(raw_conds[tau][sid])
                res = score_alert_stream(m, d["injected_episodes"], d["natural_events"])
                tp += res.event_scoring.true_positives
                ep += res.event_scoring.n_injected_episodes
                fa += res.alert_rate.false_alerts
                nh += res.alert_rate.non_event_hours

            rec = tp / ep if ep > 0 else 0.0
            fa_hr = fa / nh if nh > 0 else 0.0
            cands.append({"params": (tau, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm2(train_sids: List[str], subjects_data: Dict[str, Any], mu_pop: float, sigma_pop: float):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    raw_conds = {}
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            raw_conds[pair] = {}
            for sid in train_sids:
                d = subjects_data[sid]
                tau_ser = compute_causal_baseline_threshold(
                    hr_arr=d["hr_eval"],
                    enmo_arr=d["enmo_10s"],
                    k=k,
                    kappa_hours=kap,
                    mu_pop=mu_pop,
                    sigma_pop=sigma_pop,
                )
                raw_conds[pair][sid] = (d["hr_eval"] > tau_ser) & np.isfinite(d["hr_eval"])

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for p in p_grid:
                em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                tp, ep, fa, nh = 0, 0, 0, 0.0
                for sid in train_sids:
                    d = subjects_data[sid]
                    m = em.emit(raw_conds[pair][sid])
                    res = score_alert_stream(m, d["injected_episodes"], d["natural_events"])
                    tp += res.event_scoring.true_positives
                    ep += res.event_scoring.n_injected_episodes
                    fa += res.alert_rate.false_alerts
                    nh += res.alert_rate.non_event_hours

                rec = tp / ep if ep > 0 else 0.0
                fa_hr = fa / nh if nh > 0 else 0.0
                cands.append({"params": (k, kap, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], raw_conds, best


def tune_arm3a(train_sids: List[str], subjects_data: Dict[str, Any], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.03, 0.05, 0.08]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, ep, fa, nh = 0, 0, 0, 0.0
                    for sid in train_sids:
                        d = subjects_data[sid]
                        raw = raw_conds_a2[pair][sid] & (d["enmo_10s"] <= th)
                        m = em.emit(raw)
                        res = score_alert_stream(m, d["injected_episodes"], d["natural_events"])
                        tp += res.event_scoring.true_positives
                        ep += res.event_scoring.n_injected_episodes
                        fa += res.alert_rate.false_alerts
                        nh += res.alert_rate.non_event_hours

                    rec = tp / ep if ep > 0 else 0.0
                    fa_hr = fa / nh if nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm3b(train_sids: List[str], subjects_data: Dict[str, Any], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.60, 0.70, 0.80]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, ep, fa, nh = 0, 0, 0, 0.0
                    for sid in train_sids:
                        d = subjects_data[sid]
                        raw = raw_conds_a2[pair][sid] & (d["s_trust"] >= th)
                        m = em.emit(raw)
                        res = score_alert_stream(m, d["injected_episodes"], d["natural_events"])
                        tp += res.event_scoring.true_positives
                        ep += res.event_scoring.n_injected_episodes
                        fa += res.alert_rate.false_alerts
                        nh += res.alert_rate.non_event_hours

                    rec = tp / ep if ep > 0 else 0.0
                    fa_hr = fa / nh if nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm3b_nomotion(train_sids: List[str], subjects_data: Dict[str, Any], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.60, 0.70, 0.80]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, ep, fa, nh = 0, 0, 0, 0.0
                    for sid in train_sids:
                        d = subjects_data[sid]
                        raw = raw_conds_a2[pair][sid] & (d["s_trust_nomot"] >= th)
                        m = em.emit(raw)
                        res = score_alert_stream(m, d["injected_episodes"], d["natural_events"])
                        tp += res.event_scoring.true_positives
                        ep += res.event_scoring.n_injected_episodes
                        fa += res.alert_rate.false_alerts
                        nh += res.alert_rate.non_event_hours

                    rec = tp / ep if ep > 0 else 0.0
                    fa_hr = fa / nh if nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def run_all_arms_benchmark():
    subjects_data = load_subject_data()
    all_sids = [f"S{i}" for i in range(1, 16)]

    res_a1, sel_a1 = {}, {}
    res_a2, sel_a2 = {}, {}
    res_a3a, sel_a3a = {}, {}
    res_a3b, sel_a3b = {}, {}
    res_a3b_nomot, sel_a3b_nomot = {}, {}

    print("\nRunning LOSO Evaluation for Arms 1, 2, 3a, 3b, 3b-noMotion (Amendment 4)...")

    for test_sid in all_sids:
        train_sids = [s for s in all_sids if s != test_sid]
        d_test = subjects_data[test_sid]
        mu_pop, sigma_pop = compute_pop_priors(train_sids, subjects_data)

        # 1. Arm 1
        p_a1, _ = tune_arm1(train_sids, subjects_data)
        sel_a1[test_sid] = p_a1
        arm1 = Arm1FixedThreshold(tau_pop=p_a1[0])
        em1 = StandardAlertEmitter(p_persist_sec=p_a1[1], r_refractory_sec=60.0)
        out1 = arm1.predict(d_test["hr_eval"], emitter=em1)
        res_a1[test_sid] = score_alert_stream(out1.alert_mask, d_test["injected_episodes"], d_test["natural_events"], subject_id=test_sid)

        # 2. Arm 2
        p_a2, raw_conds_a2, _ = tune_arm2(train_sids, subjects_data, mu_pop, sigma_pop)
        sel_a2[test_sid] = p_a2
        arm2 = Arm2PersonalBaselineShrinkage(k=p_a2[0], kappa_hours=p_a2[1], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em2 = StandardAlertEmitter(p_persist_sec=p_a2[2], r_refractory_sec=60.0)
        out2 = arm2.predict(d_test["hr_eval"], d_test["enmo_10s"], emitter=em2)
        res_a2[test_sid] = score_alert_stream(out2.alert_mask, d_test["injected_episodes"], d_test["natural_events"], subject_id=test_sid)

        # 3. Arm 3a
        p_a3a, _ = tune_arm3a(train_sids, subjects_data, raw_conds_a2)
        sel_a3a[test_sid] = p_a3a
        arm3a = Arm3aKinematicGate(k=p_a3a[0], kappa_hours=p_a3a[1], theta_rest=p_a3a[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3a = StandardAlertEmitter(p_persist_sec=p_a3a[3], r_refractory_sec=60.0)
        out3a = arm3a.predict(d_test["hr_eval"], d_test["enmo_10s"], emitter=em3a)
        res_a3a[test_sid] = score_alert_stream(out3a.alert_mask, d_test["injected_episodes"], d_test["natural_events"], subject_id=test_sid)

        # 4. Arm 3b
        p_a3b, _ = tune_arm3b(train_sids, subjects_data, raw_conds_a2)
        sel_a3b[test_sid] = p_a3b
        arm3b = Arm3bTrustScoreGate(k=p_a3b[0], kappa_hours=p_a3b[1], theta_trust=p_a3b[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3b = StandardAlertEmitter(p_persist_sec=p_a3b[3], r_refractory_sec=60.0)
        out3b = arm3b.predict(d_test["hr_eval"], d_test["enmo_10s"], d_test["s_trust"], emitter=em3b)
        res_a3b[test_sid] = score_alert_stream(out3b.alert_mask, d_test["injected_episodes"], d_test["natural_events"], subject_id=test_sid)

        # 5. Arm 3b-noMotion
        p_a3b_nm, _ = tune_arm3b_nomotion(train_sids, subjects_data, raw_conds_a2)
        sel_a3b_nomot[test_sid] = p_a3b_nm
        arm3b_nm = Arm3bNoMotionGate(k=p_a3b_nm[0], kappa_hours=p_a3b_nm[1], theta_trust=p_a3b_nm[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3b_nm = StandardAlertEmitter(p_persist_sec=p_a3b_nm[3], r_refractory_sec=60.0)
        out3b_nm = arm3b_nm.predict(d_test["hr_eval"], d_test["enmo_10s"], d_test["s_trust_nomot"], emitter=em3b_nm)
        res_a3b_nomot[test_sid] = score_alert_stream(out3b_nm.alert_mask, d_test["injected_episodes"], d_test["natural_events"], subject_id=test_sid)

        print(
            f"  {test_sid} evaluated: "
            f"Arm 1 Rec={res_a1[test_sid].event_scoring.recall*100:.1f}%, FA/hr={res_a1[test_sid].alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 2 Rec={res_a2[test_sid].event_scoring.recall*100:.1f}%, FA/hr={res_a2[test_sid].alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 3a Rec={res_a3a[test_sid].event_scoring.recall*100:.1f}%, FA/hr={res_a3a[test_sid].alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 3b Rec={res_a3b[test_sid].event_scoring.recall*100:.1f}%, FA/hr={res_a3b[test_sid].alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 3b-noMot Rec={res_a3b_nomot[test_sid].event_scoring.recall*100:.1f}%, FA/hr={res_a3b_nomot[test_sid].alert_rate.false_alerts_per_hour:.2f}"
        )

    return {
        "Arm 1": (res_a1, sel_a1),
        "Arm 2": (res_a2, sel_a2),
        "Arm 3a": (res_a3a, sel_a3a),
        "Arm 3b": (res_a3b, sel_a3b),
        "Arm 3b-noMotion": (res_a3b_nomot, sel_a3b_nomot),
    }


def pool_metrics(sids: List[str], results: Dict[str, BenchmarkScoringResult]):
    n_episodes = sum(results[s].event_scoring.n_injected_episodes for s in sids)
    tp = sum(results[s].event_scoring.true_positives for s in sids)
    fn = sum(results[s].event_scoring.false_negatives for s in sids)
    recall = (tp / n_episodes * 100.0) if n_episodes > 0 else 0.0

    all_delays = []
    for s in sids:
        all_delays.extend(results[s].event_scoring.delays_sec)
    med_delay = float(np.median(all_delays)) if all_delays else 0.0

    false_alerts = sum(results[s].alert_rate.false_alerts for s in sids)
    natural_alerts = sum(results[s].alert_rate.natural_alerts for s in sids)
    non_event_h = sum(results[s].alert_rate.non_event_hours for s in sids)
    fa_per_hour = (false_alerts / non_event_h) if non_event_h > 0 else 0.0

    return {
        "n_episodes": n_episodes,
        "tp": tp,
        "fn": fn,
        "recall": recall,
        "med_delay": med_delay,
        "false_alerts": false_alerts,
        "natural_alerts": natural_alerts,
        "fa_per_hour": fa_per_hour,
    }


def print_comprehensive_tables(arms_data):
    all_sids = [f"S{i}" for i in range(1, 16)]
    without_s5 = [s for s in all_sids if s != "S5"]
    stratum_s5_s6_s11 = ["S5", "S6", "S11"]

    print("\n" + "=" * 165)
    print("TABLE: preliminary, Arms 1-3b-noMotion, no faults, Amendment 4")
    print("Protocol Section 4 & Amendments 3-4: LOSO Alerting Benchmark (Condition 0: Clean Background, R=60s Refractory Hold-off)")
    print("=" * 165)

    # 1. Headline Pooled Strata Comparison Table
    print("\n--- POOLED STRATA COMPARISON (Arms 1, 2, 3a, 3b, 3b-noMotion) ---")
    header_strata = (
        f"{'Stratum':<28} | "
        f"{'Arm 1 (Fixed)':<24} | "
        f"{'Arm 2 (Personal)':<24} | "
        f"{'Arm 3a (+Kinematic)':<24} | "
        f"{'Arm 3b (+Trust Score)':<24} | "
        f"{'Arm 3b-noMotion':<24}"
    )
    print(header_strata)
    sub_header = (
        f"{'':<28} | "
        f"{'Rec%   Delay  FA/hr  NatA':<24} | "
        f"{'Rec%   Delay  FA/hr  NatA':<24} | "
        f"{'Rec%   Delay  FA/hr  NatA':<24} | "
        f"{'Rec%   Delay  FA/hr  NatA':<24} | "
        f"{'Rec%   Delay  FA/hr  NatA':<24}"
    )
    print(sub_header)
    print("-" * 165)

    for st_name, sids in [
        ("POOLED: All 15 Subjects", all_sids),
        ("POOLED: Without S5 (14)", without_s5),
        ("STRATUM: S5/S6/S11 (3)", stratum_s5_s6_s11),
    ]:
        cols = []
        for arm_name in ["Arm 1", "Arm 2", "Arm 3a", "Arm 3b", "Arm 3b-noMotion"]:
            res_dict = arms_data[arm_name][0]
            p = pool_metrics(sids, res_dict)
            cols.append(f"{p['recall']:>5.1f}% {p['med_delay']:>4.0f}s {p['fa_per_hour']:>6.2f} {p['natural_alerts']:>4}")
        print(f"{st_name:<28} | " + " | ".join(cols))

    print("=" * 165)

    # 2. Detailed Per-Subject Results Table
    print("\n--- PER-SUBJECT DETAILED PERFORMANCE TABLE ---")
    header_subj = (
        f"{'Subject':<8} | "
        f"{'Arm 1 Rec% (FA/hr)':<20} | "
        f"{'Arm 2 Rec% (FA/hr)':<20} | "
        f"{'Arm 3a Rec% (FA/hr)':<20} | "
        f"{'Arm 3b Rec% (FA/hr)':<20} | "
        f"{'Arm 3b-noMot Rec% (FA/hr)':<26}"
    )
    print(header_subj)
    print("-" * 125)

    for sid in all_sids:
        cells = []
        for arm_name in ["Arm 1", "Arm 2", "Arm 3a", "Arm 3b", "Arm 3b-noMotion"]:
            r = arms_data[arm_name][0][sid]
            rec = r.event_scoring.recall * 100.0
            fa_hr = r.alert_rate.false_alerts_per_hour
            cells.append(f"{rec:>5.1f}% ({fa_hr:>5.2f})")
        print(f"{sid:<8} | " + " | ".join(f"{c:<20}" for c in cells[:4]) + f" | {cells[4]:<26}")

    print("-" * 125)

    # Print selected hyperparameters summary
    print("\n--- SELECTED HYPERPARAMETERS PER SUBJECT ---")
    for sid in all_sids:
        p1 = arms_data["Arm 1"][1][sid]
        p2 = arms_data["Arm 2"][1][sid]
        p3a = arms_data["Arm 3a"][1][sid]
        p3b = arms_data["Arm 3b"][1][sid]
        p3bnm = arms_data["Arm 3b-noMotion"][1][sid]
        print(
            f"{sid:<4}: "
            f"A1(tau={p1[0]:.0f},P={p1[1]:.0f}s) | "
            f"A2(k={p2[0]:.1f},kap={p2[1]:.1f}h,P={p2[2]:.0f}s) | "
            f"A3a(k={p3a[0]:.1f},kap={p3a[1]:.1f}h,th={p3a[2]:.2f}g,P={p3a[3]:.0f}s) | "
            f"A3b(th={p3b[2]:.2f},P={p3b[3]:.0f}s) | "
            f"A3b-noMot(th={p3bnm[2]:.2f},P={p3bnm[3]:.0f}s)"
        )


if __name__ == "__main__":
    arms_data = run_all_arms_benchmark()
    print_comprehensive_tables(arms_data)
