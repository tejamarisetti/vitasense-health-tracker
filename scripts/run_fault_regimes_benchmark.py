"""
VitaSense AI - Comprehensive Fault Regimes Benchmark Runner (Regime A, Regime B, No-Fault, F7)
Protocol Amendment 3 Section 5 & Amendment 4

Evaluates:
- Arm 1: Fixed Threshold (tau_pop in {100, 110, 120, 125, 130} bpm, P in {10, 20, 30}s, R = 60s)
- Arm 2: Personal Baseline with Shrinkage (k in {2.0, 2.5, 3.0, 3.5, 4.0}, kappa in {0.5, 1.0, 2.0}h, P in {10, 20, 30}s, R = 60s)
- Arm 3a: Kinematic Motion Gate Only (theta_rest in {0.03, 0.05, 0.08}g, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)
- Arm 3b: Multi-Attribute Trust Score Gate (theta_trust in {0.60, 0.70, 0.80}, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)
- Arm 3b-noMotion: Trust Gate Without Motion (theta_trust in {0.60, 0.70, 0.80}, P in {10, 20, 30}s, R = 60s, on Arm 2 baseline)

Conditions:
1. Condition 0: No-Fault Clean Background
2. Regime A: Low Fault-Duty (~10% total faulted background time, seed 42)
3. Regime B: Nominal Fault-Duty (~25-30% total faulted background time, seed 42)
4. F7: High-Motion Optical BVP Noise (+5 dB SNR before Step 3a estimator)

Statistical Evaluation:
- Pre-specified paired comparison: Arm 3b vs Arm 3a per-subject FA/hr difference
- Two-sided Wilcoxon signed-rank test (alpha = 0.05)
- Hodges-Lehmann median difference estimator
- 95% subject-bootstrap confidence interval (10,000 resamples)
"""

import sys
import pickle
import numpy as np
import scipy.stats as stats
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

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
from vitasense.benchmarks.fault_schedule import apply_fault_schedule, FaultRegime
from vitasense.quality.trust_score import RuleBasedTrustScorer


CACHE_DIR = ROOT / "data" / "processed"


def recompute_trust_scores_for_stream(
    hr_stream: np.ndarray,
    enmo_10s: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes S_trust and S_trust_nomot across all windows of an evaluated HR stream.
    Penalizes missing gaps (F1), stale flatlines (F2), and rate-of-change spikes (F4).
    """
    n_windows = len(hr_stream)
    scorer = RuleBasedTrustScorer(abstention_threshold=0.70)
    s_trust = np.zeros(n_windows, dtype=np.float64)
    s_trust_nomot = np.zeros(n_windows, dtype=np.float64)

    for i in range(n_windows):
        hr_win = hr_stream[max(0, i - 14) : i + 1]
        res = scorer.evaluate_window(hr_win)

        enmo_val = float(enmo_10s[i])
        if enmo_val <= scorer.rest_motion_threshold_g:
            mot_score = 1.0
        elif enmo_val >= scorer.severe_motion_threshold_g:
            mot_score = 0.20
        else:
            norm_m = (enmo_val - scorer.rest_motion_threshold_g) / (
                scorer.severe_motion_threshold_g - scorer.rest_motion_threshold_g
            )
            mot_score = float(1.0 - 0.60 * norm_m)

        g, st, ph = res.sub_scores["gap"], res.sub_scores["stale"], res.sub_scores["phys"]
        if g == 0.0 or st == 0.0 or ph == 0.0:
            tr = 0.0
            tr_nomot = 0.0
        else:
            tr = float(np.clip(g * st * ph * mot_score, 0.0, 1.0))
            tr_nomot = float(np.clip(g * st * ph, 0.0, 1.0))

        s_trust[i] = tr
        s_trust_nomot[i] = tr_nomot

    return s_trust, s_trust_nomot


def load_raw_subject_data():
    gt_file = CACHE_DIR / "benchmark_ground_truth.pkl"
    if not gt_file.exists():
        raise FileNotFoundError(f"Missing {gt_file}.")

    with open(gt_file, "rb") as f:
        ground_truth = pickle.load(f)

    subjects_raw = {}
    for sid in [f"S{i}" for i in range(1, 16)]:
        cache_path = CACHE_DIR / f"{sid}_ppg_cache.npz"
        cache = np.load(cache_path)
        hr_ppg = cache["hr_ppg"]
        enmo_10s = cache["enmo_10s"]
        is_valid = cache["is_valid"]

        gt = ground_truth[sid]
        delta_hr = gt["delta_hr"]
        hr_eval = hr_ppg + delta_hr

        subjects_raw[sid] = {
            "hr_ppg": hr_ppg,
            "hr_eval": hr_eval,
            "enmo_10s": enmo_10s,
            "is_valid": is_valid,
            "injected_episodes": gt["injected_episodes"],
            "natural_events": gt["natural_events"],
            "step_sec": 2.0,
        }
    return subjects_raw


def build_regime_subject_dataset(regime: FaultRegime, seed: int = 42):
    subjects_raw = load_raw_subject_data()
    dataset = {}

    for sid, d in subjects_raw.items():
        if regime == FaultRegime.NO_FAULT:
            hr_stream = d["hr_eval"].copy()
            fault_types = np.full(len(hr_stream), "F0_CLEAN", dtype="<U12")
        else:
            sched = apply_fault_schedule(
                hr_eval=d["hr_eval"],
                injected_episodes=d["injected_episodes"],
                regime=regime,
                seed=seed,
                step_sec=d["step_sec"],
            )
            hr_stream = sched.hr_faulted
            fault_types = sched.fault_types

        s_trust, s_trust_nomot = recompute_trust_scores_for_stream(hr_stream, d["enmo_10s"])

        dataset[sid] = {
            "hr_ppg": d["hr_ppg"],
            "hr_eval": hr_stream,
            "enmo_10s": d["enmo_10s"],
            "s_trust": s_trust,
            "s_trust_nomot": s_trust_nomot,
            "is_valid": np.isfinite(hr_stream),
            "injected_episodes": d["injected_episodes"],
            "natural_events": d["natural_events"],
            "fault_types": fault_types,
            "step_sec": d["step_sec"],
        }

    return dataset


def build_f7_subject_dataset():
    gt_file = CACHE_DIR / "benchmark_ground_truth.pkl"
    with open(gt_file, "rb") as f:
        ground_truth = pickle.load(f)

    dataset = {}
    for sid in [f"S{i}" for i in range(1, 16)]:
        f7_cache_path = CACHE_DIR / f"{sid}_f7_ppg_cache.npz"
        if not f7_cache_path.exists():
            raise FileNotFoundError(f"Missing F7 cache for {sid}: {f7_cache_path}")
        cache = np.load(f7_cache_path)
        hr_ppg = cache["hr_ppg"]
        enmo_10s = cache["enmo_10s"]
        s_trust = cache["s_trust"]
        s_trust_nomot = cache["s_trust_no_motion"]

        gt = ground_truth[sid]
        delta_hr = gt["delta_hr"]
        hr_eval = hr_ppg + delta_hr

        dataset[sid] = {
            "hr_ppg": hr_ppg,
            "hr_eval": hr_eval,
            "enmo_10s": enmo_10s,
            "s_trust": s_trust,
            "s_trust_nomot": s_trust_nomot,
            "is_valid": np.isfinite(hr_eval),
            "injected_episodes": gt["injected_episodes"],
            "natural_events": gt["natural_events"],
            "fault_types": np.full(len(hr_eval), "F7_BVP_NOISE", dtype="<U12"),
            "step_sec": 2.0,
        }
    return dataset


def compute_pop_priors(train_sids: List[str], dataset: Dict[str, Any], theta_rest: float = 0.05):
    calib_hrs = []
    for sid in train_sids:
        d = dataset[sid]
        hr = d["hr_ppg"]
        enmo = d["enmo_10s"]
        valid = d["is_valid"]
        rest_mask = (enmo <= theta_rest) & valid & np.isfinite(hr)
        if np.any(rest_mask):
            calib_hrs.append(hr[rest_mask])

    if calib_hrs:
        pooled = np.concatenate(calib_hrs)
        mu_pop = float(np.mean(pooled))
        sigma_pop = float(np.std(pooled, ddof=1))
    else:
        mu_pop, sigma_pop = 75.0, 10.0
    return mu_pop, sigma_pop


# --- Precomputed Scoring Cache for Hyperparameter Tuning ---

@dataclass
class FastSubjectScoringCache:
    sid: str
    n_windows: int
    ep_slices: List[np.ndarray]   # Boolean masks for each injected episode
    n_episodes: int
    is_non_event: np.ndarray     # Boolean mask of non-event windows
    non_event_hours: float


def build_fast_scoring_caches(dataset: Dict[str, Any]) -> Dict[str, FastSubjectScoringCache]:
    caches = {}
    for sid, d in dataset.items():
        n_windows = len(d["hr_eval"])
        step_sec = d["step_sec"]
        timestamps = np.arange(n_windows, dtype=np.float64) * step_sec

        # Injected episode masks
        ep_slices = []
        is_inj = np.zeros(n_windows, dtype=bool)
        for ep in d["injected_episodes"]:
            s = float(ep.start_time_sec if hasattr(ep, "start_time_sec") else ep["start_sec"])
            e = float(ep.end_time_sec if hasattr(ep, "end_time_sec") else ep["end_sec"])
            m = (timestamps >= s) & (timestamps <= e)
            ep_slices.append(m)
            is_inj |= m

        # Natural event masks (+- 30s)
        is_nat = np.zeros(n_windows, dtype=bool)
        for ev in d["natural_events"]:
            s = float(ev.start_time_sec if hasattr(ev, "start_time_sec") else ev["start_sec"])
            e = float(ev.end_time_sec if hasattr(ev, "end_time_sec") else ev["end_sec"])
            is_nat |= (timestamps >= s - 30.0) & (timestamps <= e + 30.0)

        is_non_event = (~is_inj) & (~is_nat)
        non_event_hours = float(np.sum(is_non_event) * step_sec / 3600.0)

        caches[sid] = FastSubjectScoringCache(
            sid=sid,
            n_windows=n_windows,
            ep_slices=ep_slices,
            n_episodes=len(ep_slices),
            is_non_event=is_non_event,
            non_event_hours=non_event_hours,
        )
    return caches


def fast_eval_mask(m: np.ndarray, cache: FastSubjectScoringCache) -> Tuple[int, int]:
    """Returns (tp_count, fa_count) on subject."""
    tp = sum(1 for ep_m in cache.ep_slices if np.any(m & ep_m))
    fa = int(np.sum(m & cache.is_non_event))
    return tp, fa


# --- LOSO Parameter Tuning Functions (Amendment 4 Selection Rule) ---

def tune_arm1(train_sids: List[str], dataset: Dict[str, Any], caches: Dict[str, FastSubjectScoringCache]):
    tau_grid = [100.0, 110.0, 120.0, 125.0, 130.0]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    raw_conds = {}
    for tau in tau_grid:
        arm = Arm1FixedThreshold(tau_pop=tau)
        raw_conds[tau] = {sid: arm.predict(dataset[sid]["hr_eval"]).raw_alert_mask for sid in train_sids}

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for tau in tau_grid:
        for p in p_grid:
            em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
            tp, fa = 0, 0
            for sid in train_sids:
                m = em.emit(raw_conds[tau][sid])
                t, f = fast_eval_mask(m, caches[sid])
                tp += t
                fa += f

            rec = tp / tot_ep if tot_ep > 0 else 0.0
            fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
            cands.append({"params": (tau, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm2(train_sids: List[str], dataset: Dict[str, Any], caches: Dict[str, FastSubjectScoringCache], mu_pop: float, sigma_pop: float):
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
                d = dataset[sid]
                tau_ser = compute_causal_baseline_threshold(
                    hr_arr=d["hr_eval"],
                    enmo_arr=d["enmo_10s"],
                    k=k,
                    kappa_hours=kap,
                    mu_pop=mu_pop,
                    sigma_pop=sigma_pop,
                )
                raw_conds[pair][sid] = (d["hr_eval"] > tau_ser) & np.isfinite(d["hr_eval"])

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for p in p_grid:
                em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                tp, fa = 0, 0
                for sid in train_sids:
                    m = em.emit(raw_conds[pair][sid])
                    t, f = fast_eval_mask(m, caches[sid])
                    tp += t
                    fa += f

                rec = tp / tot_ep if tot_ep > 0 else 0.0
                fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
                cands.append({"params": (k, kap, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], raw_conds, best


def tune_arm3a(train_sids: List[str], dataset: Dict[str, Any], caches: Dict[str, FastSubjectScoringCache], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.03, 0.05, 0.08]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, fa = 0, 0
                    for sid in train_sids:
                        d = dataset[sid]
                        raw = raw_conds_a2[pair][sid] & (d["enmo_10s"] <= th)
                        m = em.emit(raw)
                        t, f = fast_eval_mask(m, caches[sid])
                        tp += t
                        fa += f

                    rec = tp / tot_ep if tot_ep > 0 else 0.0
                    fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm3b(train_sids: List[str], dataset: Dict[str, Any], caches: Dict[str, FastSubjectScoringCache], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.60, 0.70, 0.80]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, fa = 0, 0
                    for sid in train_sids:
                        d = dataset[sid]
                        raw = raw_conds_a2[pair][sid] & (d["s_trust"] >= th)
                        m = em.emit(raw)
                        t, f = fast_eval_mask(m, caches[sid])
                        tp += t
                        fa += f

                    rec = tp / tot_ep if tot_ep > 0 else 0.0
                    fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def tune_arm3b_nomotion(train_sids: List[str], dataset: Dict[str, Any], caches: Dict[str, FastSubjectScoringCache], raw_conds_a2: Dict[Tuple[float, float], Dict[str, np.ndarray]]):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    th_grid = [0.60, 0.70, 0.80]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for th in th_grid:
                for p in p_grid:
                    em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                    tp, fa = 0, 0
                    for sid in train_sids:
                        d = dataset[sid]
                        raw = raw_conds_a2[pair][sid] & (d["s_trust_nomot"] >= th)
                        m = em.emit(raw)
                        t, f = fast_eval_mask(m, caches[sid])
                        tp += t
                        fa += f

                    rec = tp / tot_ep if tot_ep > 0 else 0.0
                    fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
                    cands.append({"params": (k, kap, th, p), "rec": rec, "fa_hr": fa_hr})

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


# --- Evaluation Engine ---

def evaluate_condition_loso(condition_name: str, dataset: Dict[str, Any]):
    all_sids = [f"S{i}" for i in range(1, 16)]
    caches = build_fast_scoring_caches(dataset)

    res_a1, sel_a1 = {}, {}
    res_a2, sel_a2 = {}, {}
    res_a3a, sel_a3a = {}, {}
    res_a3b, sel_a3b = {}, {}
    res_a3b_nomot, sel_a3b_nomot = {}, {}

    print(f"\n>>> Running LOSO Evaluation: {condition_name} ...", flush=True)

    for test_sid in all_sids:
        train_sids = [s for s in all_sids if s != test_sid]
        d_test = dataset[test_sid]
        mu_pop, sigma_pop = compute_pop_priors(train_sids, dataset)

        # 1. Arm 1
        p_a1, _ = tune_arm1(train_sids, dataset, caches)
        sel_a1[test_sid] = p_a1
        arm1 = Arm1FixedThreshold(tau_pop=p_a1[0])
        em1 = StandardAlertEmitter(p_persist_sec=p_a1[1], r_refractory_sec=60.0)
        out1 = arm1.predict(d_test["hr_eval"], emitter=em1)
        res_a1[test_sid] = score_alert_stream(
            out1.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )

        # 2. Arm 2
        p_a2, raw_conds_a2, _ = tune_arm2(train_sids, dataset, caches, mu_pop, sigma_pop)
        sel_a2[test_sid] = p_a2
        arm2 = Arm2PersonalBaselineShrinkage(k=p_a2[0], kappa_hours=p_a2[1], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em2 = StandardAlertEmitter(p_persist_sec=p_a2[2], r_refractory_sec=60.0)
        out2 = arm2.predict(d_test["hr_eval"], d_test["enmo_10s"], emitter=em2)
        res_a2[test_sid] = score_alert_stream(
            out2.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )

        # 3. Arm 3a
        p_a3a, _ = tune_arm3a(train_sids, dataset, caches, raw_conds_a2)
        sel_a3a[test_sid] = p_a3a
        arm3a = Arm3aKinematicGate(k=p_a3a[0], kappa_hours=p_a3a[1], theta_rest=p_a3a[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3a = StandardAlertEmitter(p_persist_sec=p_a3a[3], r_refractory_sec=60.0)
        out3a = arm3a.predict(d_test["hr_eval"], d_test["enmo_10s"], emitter=em3a)
        res_a3a[test_sid] = score_alert_stream(
            out3a.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )

        # 4. Arm 3b
        p_a3b, _ = tune_arm3b(train_sids, dataset, caches, raw_conds_a2)
        sel_a3b[test_sid] = p_a3b
        arm3b = Arm3bTrustScoreGate(k=p_a3b[0], kappa_hours=p_a3b[1], theta_trust=p_a3b[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3b = StandardAlertEmitter(p_persist_sec=p_a3b[3], r_refractory_sec=60.0)
        out3b = arm3b.predict(d_test["hr_eval"], d_test["enmo_10s"], d_test["s_trust"], emitter=em3b)
        res_a3b[test_sid] = score_alert_stream(
            out3b.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )

        # 5. Arm 3b-noMotion
        p_a3b_nm, _ = tune_arm3b_nomotion(train_sids, dataset, caches, raw_conds_a2)
        sel_a3b_nomot[test_sid] = p_a3b_nm
        arm3b_nm = Arm3bNoMotionGate(k=p_a3b_nm[0], kappa_hours=p_a3b_nm[1], theta_trust=p_a3b_nm[2], mu_pop=mu_pop, sigma_pop=sigma_pop)
        em3b_nm = StandardAlertEmitter(p_persist_sec=p_a3b_nm[3], r_refractory_sec=60.0)
        out3b_nm = arm3b_nm.predict(d_test["hr_eval"], d_test["enmo_10s"], d_test["s_trust_nomot"], emitter=em3b_nm)
        res_a3b_nomot[test_sid] = score_alert_stream(
            out3b_nm.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )
        print(f"  {test_sid} evaluated.", flush=True)

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
        "non_event_hours": non_event_h,
    }


def pool_fault_breakdown(sids: List[str], results: Dict[str, BenchmarkScoringResult], dataset: Dict[str, Any]):
    """Aggregates false alerts and hours per fault type across subjects."""
    all_fts = set()
    for s in sids:
        all_fts.update(dataset[s]["fault_types"])
    sorted_fts = sorted(list(all_fts))

    breakdown = {}
    for ft in sorted_fts:
        fa_count = 0
        hours = 0.0
        for s in sids:
            r = results[s]
            d = dataset[s]
            ft_mask = (d["fault_types"] == ft)
            # Find non-event windows
            is_inj = np.zeros(len(ft_mask), dtype=bool)
            for ep in d["injected_episodes"]:
                s_t = ep.start_time_sec if hasattr(ep, "start_time_sec") else ep["start_sec"]
                e_t = ep.end_time_sec if hasattr(ep, "end_time_sec") else ep["end_sec"]
                t = np.arange(len(ft_mask)) * 2.0
                is_inj |= (t >= s_t) & (t <= e_t)
            is_nat = np.zeros(len(ft_mask), dtype=bool)
            for ev in d["natural_events"]:
                s_t = ev.start_time_sec if hasattr(ev, "start_time_sec") else ev["start_sec"]
                e_t = ev.end_time_sec if hasattr(ev, "end_time_sec") else ev["end_sec"]
                t = np.arange(len(ft_mask)) * 2.0
                is_nat |= (t >= s_t - 30.0) & (t <= e_t + 30.0)
            non_ev = (~is_inj) & (~is_nat)
            active_ft = ft_mask & non_ev

            h_s = float(np.sum(active_ft) * 2.0 / 3600.0)
            hours += h_s
            # false alerts in this ft
            if r.alert_rate.fault_disaggregated_fa:
                fa_count += r.alert_rate.fault_disaggregated_fa.get(ft, 0)

        rate = (fa_count / hours) if hours > 0 else 0.0
        breakdown[ft] = {"fa": fa_count, "hours": hours, "rate": rate}
    return breakdown


# --- Pre-Specified Paired Statistical Comparison: Arm 3b vs Arm 3a ---

def compute_paired_comparison_3b_vs_3a(
    res_3b: Dict[str, BenchmarkScoringResult],
    res_3a: Dict[str, BenchmarkScoringResult],
    seed: int = 42,
    n_boot: int = 10000,
):
    """
    Computes per-subject FA/hr differences (3b minus 3a),
    two-sided Wilcoxon signed-rank test (alpha 0.05),
    Hodges-Lehmann estimator, and 95% subject-bootstrap CI.
    """
    sids = [f"S{i}" for i in range(1, 16)]
    fa_3b = np.array([res_3b[s].alert_rate.false_alerts_per_hour for s in sids], dtype=float)
    fa_3a = np.array([res_3a[s].alert_rate.false_alerts_per_hour for s in sids], dtype=float)
    diffs = fa_3b - fa_3a  # negative indicates Arm 3b has fewer false alarms than Arm 3a

    # Two-sided Wilcoxon signed-rank test
    # If all differences are zero, handle edge case gracefully
    non_zero = diffs[diffs != 0.0]
    if len(non_zero) > 0:
        w_res = stats.wilcoxon(diffs, zero_method="wilcox", alternative="two-sided")
        w_stat = float(w_res.statistic)
        p_val = float(w_res.pvalue)
    else:
        w_stat, p_val = 0.0, 1.0

    # Hodges-Lehmann estimate: median of all Walsh pairwise averages (d_i + d_j) / 2 for i <= j
    walsh_averages = []
    n = len(diffs)
    for i in range(n):
        for j in range(i, n):
            walsh_averages.append((diffs[i] + diffs[j]) / 2.0)
    hl_estimate = float(np.median(walsh_averages))

    # 95% Subject-Bootstrap CI (resampling the 15 subjects with replacement)
    rng = np.random.default_rng(seed)
    boot_means = np.zeros(n_boot, dtype=float)
    boot_hl = np.zeros(n_boot, dtype=float)

    for b in range(n_boot):
        sample_idx = rng.choice(n, size=n, replace=True)
        sample_diffs = diffs[sample_idx]
        boot_means[b] = np.mean(sample_diffs)

        # sample Walsh median
        sample_walsh = []
        for i in range(n):
            for j in range(i, n):
                sample_walsh.append((sample_diffs[i] + sample_diffs[j]) / 2.0)
        boot_hl[b] = np.median(sample_walsh)

    ci_mean_lo = float(np.percentile(boot_means, 2.5))
    ci_mean_hi = float(np.percentile(boot_means, 97.5))
    ci_hl_lo = float(np.percentile(boot_hl, 2.5))
    ci_hl_hi = float(np.percentile(boot_hl, 97.5))

    return {
        "sids": sids,
        "fa_3b": fa_3b,
        "fa_3a": fa_3a,
        "diffs": diffs,
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "w_stat": w_stat,
        "p_val": p_val,
        "hl_estimate": hl_estimate,
        "ci_mean": (ci_mean_lo, ci_mean_hi),
        "ci_hl": (ci_hl_lo, ci_hl_hi),
    }


def print_condition_strata_table(condition_name: str, condition_data: Dict[str, Any]):
    all_sids = [f"S{i}" for i in range(1, 16)]
    without_s5 = [s for s in all_sids if s != "S5"]
    stratum_s5_s6_s11 = ["S5", "S6", "S11"]

    print(f"\n{'='*155}")
    print(f"STRATA EVALUATION: {condition_name}")
    print(f"{'='*155}")

    header = (
        f"{'Stratum':<26} | "
        f"{'Arm 1 (Fixed)':<22} | "
        f"{'Arm 2 (Personal)':<22} | "
        f"{'Arm 3a (+Kinematic)':<22} | "
        f"{'Arm 3b (+Trust Score)':<22} | "
        f"{'Arm 3b-noMotion':<22}"
    )
    print(header)
    sub = (
        f"{'':<26} | "
        f"{'Rec%  Delay  FA/hr':<22} | "
        f"{'Rec%  Delay  FA/hr':<22} | "
        f"{'Rec%  Delay  FA/hr':<22} | "
        f"{'Rec%  Delay  FA/hr':<22} | "
        f"{'Rec%  Delay  FA/hr':<22}"
    )
    print(sub)
    print("-" * 155)

    for st_name, sids in [
        ("Pooled All-15", all_sids),
        ("Without S5 (14 subj)", without_s5),
        ("Stratum S5/S6/S11 (3 subj)", stratum_s5_s6_s11),
    ]:
        cols = []
        for arm_name in ["Arm 1", "Arm 2", "Arm 3a", "Arm 3b", "Arm 3b-noMotion"]:
            res_dict = condition_data[arm_name][0]
            p = pool_metrics(sids, res_dict)
            cols.append(f"{p['recall']:>5.1f}% {p['med_delay']:>4.0f}s {p['fa_per_hour']:>6.2f}")
        print(f"{st_name:<26} | " + " | ".join(cols))
    print("-" * 155)


def print_fault_disaggregated_table(condition_name: str, condition_data: Dict[str, Any], dataset: Dict[str, Any]):
    all_sids = [f"S{i}" for i in range(1, 16)]
    all_fts = sorted(list(set(dataset["S1"]["fault_types"])))

    print(f"\n--- DISAGGREGATED FA/HR PER FAULT TYPE: {condition_name} ---")
    header = (
        f"{'Fault Type':<14} | "
        f"{'Total Hours':<11} | "
        f"{'Arm 1 FA/hr':<14} | "
        f"{'Arm 2 FA/hr':<14} | "
        f"{'Arm 3a FA/hr':<14} | "
        f"{'Arm 3b FA/hr':<14} | "
        f"{'Arm 3b-noMot':<14}"
    )
    print(header)
    print("-" * 95)

    for ft in all_fts:
        cells = []
        tot_h = 0.0
        for arm_name in ["Arm 1", "Arm 2", "Arm 3a", "Arm 3b", "Arm 3b-noMotion"]:
            res_dict = condition_data[arm_name][0]
            fb = pool_fault_breakdown(all_sids, res_dict, dataset)
            tot_h = fb[ft]["hours"]
            cells.append(f"{fb[ft]['rate']:>6.2f} ({fb[ft]['fa']:>3} FA)")
        print(f"{ft:<14} | {tot_h:>8.2f}h   | " + " | ".join(f"{c:<14}" for c in cells))
    print("-" * 95)


def print_paired_stats(condition_name: str, stats_res: Dict[str, Any]):
    print(f"\n--- PRE-SPECIFIED PAIRED COMPARISON: Arm 3b vs Arm 3a ({condition_name}) ---")
    print(f"Per-Subject Differences (d_i = FA/hr_3b - FA/hr_3a):")
    for sid, fa_b, fa_a, d in zip(stats_res["sids"], stats_res["fa_3b"], stats_res["fa_3a"], stats_res["diffs"]):
        print(f"  {sid:<4}: Arm 3b={fa_b:>6.2f} FA/hr | Arm 3a={fa_a:>6.2f} FA/hr | Diff d_i={d:>+6.2f} FA/hr")

    print(f"\nStatistical Tests & Effect Size Estimates:")
    print(f"  - Mean Difference (3b - 3a):        {stats_res['mean_diff']:>+6.2f} FA/hr")
    print(f"  - Median Difference (3b - 3a):      {stats_res['median_diff']:>+6.2f} FA/hr")
    print(f"  - Hodges-Lehmann Median Difference:  {stats_res['hl_estimate']:>+6.2f} FA/hr")
    print(f"  - Wilcoxon Signed-Rank Test:        W = {stats_res['w_stat']:.1f}, p = {stats_res['p_val']:.4f} (alpha = 0.05)")
    print(f"  - 95% Bootstrap CI on Mean Diff:    [{stats_res['ci_mean'][0]:>+6.2f}, {stats_res['ci_mean'][1]:>+6.2f}] FA/hr")
    print(f"  - 95% Bootstrap CI on HL Median:    [{stats_res['ci_hl'][0]:>+6.2f}, {stats_res['ci_hl'][1]:>+6.2f}] FA/hr")
    sig_str = "Statistically Significant (p < 0.05)" if stats_res['p_val'] < 0.05 else "Not Statistically Significant (p >= 0.05)"
    print(f"  - Conclusion:                       {sig_str}")


def print_edge_of_grid_analysis(all_conditions_data: Dict[str, Dict[str, Any]]):
    all_sids = [f"S{i}" for i in range(1, 16)]
    print("\n" + "=" * 115)
    print("EDGE-OF-GRID HYPERPARAMETER SELECTIONS PER ARM")
    print("=" * 115)

    for cond_name, c_data in all_conditions_data.items():
        print(f"\nCondition: {cond_name}")
        for arm_name in ["Arm 1", "Arm 2", "Arm 3a", "Arm 3b", "Arm 3b-noMotion"]:
            sels = [c_data[arm_name][1][s] for s in all_sids]
            # Inspect values
            if arm_name == "Arm 1":
                taus = [p[0] for p in sels]
                ps = [p[1] for p in sels]
                print(f"  {arm_name:<16}: tau_pop in {sorted(list(set(taus)))}, P in {sorted(list(set(ps)))}")
            elif arm_name == "Arm 2":
                ks = [p[0] for p in sels]
                kaps = [p[1] for p in sels]
                ps = [p[2] for p in sels]
                print(f"  {arm_name:<16}: k in {sorted(list(set(ks)))}, kappa in {sorted(list(set(kaps)))}, P in {sorted(list(set(ps)))}")
            elif arm_name == "Arm 3a":
                ths = [p[2] for p in sels]
                ps = [p[3] for p in sels]
                print(f"  {arm_name:<16}: theta_rest in {sorted(list(set(ths)))}, P in {sorted(list(set(ps)))}")
            else:
                ths = [p[2] for p in sels]
                ps = [p[3] for p in sels]
                print(f"  {arm_name:<16}: theta_trust in {sorted(list(set(ths)))}, P in {sorted(list(set(ps)))}")


def run_full_benchmark_suite():
    print("Loading data and preparing datasets...")

    # 1. Condition 0: No-Fault
    data_nf = build_regime_subject_dataset(FaultRegime.NO_FAULT)
    res_nf = evaluate_condition_loso("Condition 0 (No-Fault Clean Background)", data_nf)

    # 2. Regime A: Low Fault-Duty (~10%)
    data_rega = build_regime_subject_dataset(FaultRegime.REGIME_A, seed=42)
    res_rega = evaluate_condition_loso("Regime A (Low Fault-Duty ~10%)", data_rega)

    # 3. Regime B: Nominal Fault-Duty (~25-30%)
    data_regb = build_regime_subject_dataset(FaultRegime.REGIME_B, seed=42)
    res_regb = evaluate_condition_loso("Regime B (Nominal Fault-Duty ~25-30%)", data_regb)

    # 4. F7: Optical BVP Noise
    data_f7 = build_f7_subject_dataset()
    res_f7 = evaluate_condition_loso("F7 (Optical BVP Noise, SNR = +5 dB)", data_f7)

    # Output tables
    print("\n" + "#" * 155)
    print("FINAL BENCHMARK EVALUATION RESULTS (Protocol Amendments 3 & 4)")
    print("#" * 155)

    for cond_name, c_data, d_set in [
        ("Condition 0 (No-Fault)", res_nf, data_nf),
        ("Regime A (Low Duty ~10%)", res_rega, data_rega),
        ("Regime B (Nominal Duty ~25-30%)", res_regb, data_regb),
        ("F7 (High-Motion Optical BVP Noise)", res_f7, data_f7),
    ]:
        print_condition_strata_table(cond_name, c_data)
        if cond_name != "F7 (High-Motion Optical BVP Noise)":
            print_fault_disaggregated_table(cond_name, c_data, d_set)

    # Paired comparisons
    stats_nf = compute_paired_comparison_3b_vs_3a(res_nf["Arm 3b"][0], res_nf["Arm 3a"][0])
    print_paired_stats("Condition 0: No-Fault", stats_nf)

    stats_rega = compute_paired_comparison_3b_vs_3a(res_rega["Arm 3b"][0], res_rega["Arm 3a"][0])
    print_paired_stats("Regime A: Low Fault-Duty (~10%)", stats_rega)

    stats_regb = compute_paired_comparison_3b_vs_3a(res_regb["Arm 3b"][0], res_regb["Arm 3a"][0])
    print_paired_stats("Regime B: Nominal Fault-Duty (~25-30%)", stats_regb)

    # Edge of grid
    all_conds = {
        "Condition 0 (No-Fault)": res_nf,
        "Regime A": res_rega,
        "Regime B": res_regb,
    }
    print_edge_of_grid_analysis(all_conds)


if __name__ == "__main__":
    run_full_benchmark_suite()
