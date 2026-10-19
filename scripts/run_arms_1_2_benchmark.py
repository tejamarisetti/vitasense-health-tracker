"""
VitaSense AI - Benchmark Runner for Arms 1 and 2 under LOSO Cross-Validation
Protocol Section 4 (Frozen v1.0.0) & Amendments 3 and 4

Evaluates:
- Arm 1: Fixed Threshold (tau_pop in {100, 110, 120, 125, 130} bpm, P in {10, 20, 30}s, R = 60s)
- Arm 2: Personal Baseline with Shrinkage (k in {2.0, 2.5, 3.0, 3.5, 4.0}, kappa in {0.5, 1.0, 2.0}h, P in {10, 20, 30}s, R = 60s)

LOSO Tuning Protocol (Amendment 4):
- Full 15-subject Leave-One-Subject-Out cross-validation.
- Hyperparameter selection (tau, P) and (k, kappa, P) is conducted strictly inside the training folds (N-1 subjects).
- Selection rule: Choose candidate achieving pooled training Recall >= 85% with minimum FA/hr;
  if none achieves 85%, maximize recall (Amendment 4 Section 2).
- Evaluated on test fold; reported per subject and pooled (All-15, Without-S5, and S5/S6/S11).
- Labeled: "preliminary, Arms 1-2, no faults, Amendment 4".
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
)
from vitasense.benchmarks.scoring import score_alert_stream, BenchmarkScoringResult


CACHE_DIR = ROOT / "data" / "processed"


def load_subject_data():
    """Loads all 15 subjects' PPG cache and ground-truth events."""
    gt_file = CACHE_DIR / "benchmark_ground_truth.pkl"
    if not gt_file.exists():
        raise FileNotFoundError(f"Missing {gt_file}. Run scripts/prepare_benchmark_ground_truth.py first.")

    with open(gt_file, "rb") as f:
        ground_truth = pickle.load(f)

    subjects_data = {}
    for sid in [f"S{i}" for i in range(1, 16)]:
        cache_path = CACHE_DIR / f"{sid}_ppg_cache.npz"
        if not cache_path.exists():
            raise FileNotFoundError(f"Missing {cache_path}")

        cache = np.load(cache_path)
        hr_ppg = cache["hr_ppg"]
        enmo_10s = cache["enmo_10s"]
        is_valid = cache["is_valid"]

        gt = ground_truth[sid]
        delta_hr = gt["delta_hr"]

        # Superimpose synthetic tachycardia onto wrist-PPG estimate (Amendment 3 Section 4.2)
        hr_eval = hr_ppg + delta_hr

        subjects_data[sid] = {
            "hr_ppg": hr_ppg,
            "hr_eval": hr_eval,
            "enmo_10s": enmo_10s,
            "is_valid": is_valid,
            "injected_episodes": gt["injected_episodes"],
            "natural_events": gt["natural_events"],
            "step_sec": 2.0,
        }

    return subjects_data


def compute_pop_priors(train_sids: List[str], subjects_data: Dict[str, Any], theta_rest: float = 0.05):
    """
    Computes population resting mean and standard deviation from deployment-available
    calibration windows in the training folds (Amendment 3 Section 6.3).
    """
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


def tune_arm1(train_sids: List[str], subjects_data: Dict[str, Any]) -> Tuple[Tuple[float, float], Dict[str, Any]]:
    """
    Tunes Arm 1 (tau_pop in {100, 110, 120, 125, 130} bpm, P in {10, 20, 30}s, R=60s)
    strictly inside training folds per Amendment 4.
    """
    tau_grid = [100.0, 110.0, 120.0, 125.0, 130.0]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0
    step_sec = 2.0

    # Precompute raw conditions for each tau across training subjects
    raw_conditions: Dict[float, Dict[str, np.ndarray]] = {}
    for tau in tau_grid:
        raw_conditions[tau] = {}
        arm = Arm1FixedThreshold(tau_pop=tau)
        for sid in train_sids:
            d = subjects_data[sid]
            out = arm.predict(d["hr_eval"])
            raw_conditions[tau][sid] = out.raw_alert_mask

    candidate_results = []

    for tau in tau_grid:
        for p in p_grid:
            emitter = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec, step_sec=step_sec)
            total_tp = 0
            total_episodes = 0
            total_fa = 0
            total_non_event_h = 0.0

            for sid in train_sids:
                d = subjects_data[sid]
                raw_mask = raw_conditions[tau][sid]
                alert_mask = emitter.emit(raw_mask)
                res = score_alert_stream(
                    alert_mask=alert_mask,
                    injected_episodes=d["injected_episodes"],
                    natural_events=d["natural_events"],
                    step_sec=d["step_sec"],
                    subject_id=sid,
                )
                total_tp += res.event_scoring.true_positives
                total_episodes += res.event_scoring.n_injected_episodes
                total_fa += res.alert_rate.false_alerts
                total_non_event_h += res.alert_rate.non_event_hours

            recall = total_tp / total_episodes if total_episodes > 0 else 0.0
            fa_per_hour = total_fa / total_non_event_h if total_non_event_h > 0 else 0.0

            candidate_results.append({
                "params": (tau, p),
                "tau_pop": tau,
                "p_persist": p,
                "recall": recall,
                "fa_per_hour": fa_per_hour,
            })

    # Selection Rule (Amendment 4 Section 2):
    # Recall >= 0.85 with lowest FA/hr (tie-break higher recall); else max recall (tie-break lowest FA/hr)
    valid_candidates = [c for c in candidate_results if c["recall"] >= 0.85]
    if valid_candidates:
        best = min(valid_candidates, key=lambda c: (c["fa_per_hour"], -c["recall"]))
    else:
        best = max(candidate_results, key=lambda c: (c["recall"], c["fa_per_hour"]))

    return best["params"], best


def tune_arm2(
    train_sids: List[str],
    subjects_data: Dict[str, Any],
    mu_pop: float,
    sigma_pop: float,
) -> Tuple[Tuple[float, float, float], Dict[str, Any]]:
    """
    Tunes Arm 2 (k in {2.0, 2.5, 3.0, 3.5, 4.0}, kappa in {0.5, 1.0, 2.0}h, P in {10, 20, 30}s, R=60s)
    strictly inside training folds per Amendment 4.
    """
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kappa_grid = [0.5, 1.0, 2.0]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0
    step_sec = 2.0

    # Precompute raw conditions for each (k, kappa) across training subjects
    raw_conditions: Dict[Tuple[float, float], Dict[str, np.ndarray]] = {}
    for k in k_grid:
        for kappa in kappa_grid:
            pair = (k, kappa)
            raw_conditions[pair] = {}
            arm = Arm2PersonalBaselineShrinkage(
                k=k,
                kappa_hours=kappa,
                mu_pop=mu_pop,
                sigma_pop=sigma_pop,
            )
            for sid in train_sids:
                d = subjects_data[sid]
                out = arm.predict(d["hr_eval"], d["enmo_10s"])
                raw_conditions[pair][sid] = out.raw_alert_mask

    candidate_results = []

    for k in k_grid:
        for kappa in kappa_grid:
            pair = (k, kappa)
            for p in p_grid:
                emitter = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec, step_sec=step_sec)
                total_tp = 0
                total_episodes = 0
                total_fa = 0
                total_non_event_h = 0.0

                for sid in train_sids:
                    d = subjects_data[sid]
                    raw_mask = raw_conditions[pair][sid]
                    alert_mask = emitter.emit(raw_mask)
                    res = score_alert_stream(
                        alert_mask=alert_mask,
                        injected_episodes=d["injected_episodes"],
                        natural_events=d["natural_events"],
                        step_sec=d["step_sec"],
                        subject_id=sid,
                    )
                    total_tp += res.event_scoring.true_positives
                    total_episodes += res.event_scoring.n_injected_episodes
                    total_fa += res.alert_rate.false_alerts
                    total_non_event_h += res.alert_rate.non_event_hours

                recall = total_tp / total_episodes if total_episodes > 0 else 0.0
                fa_per_hour = total_fa / total_non_event_h if total_non_event_h > 0 else 0.0

                candidate_results.append({
                    "params": (k, kappa, p),
                    "k": k,
                    "kappa": kappa,
                    "p_persist": p,
                    "recall": recall,
                    "fa_per_hour": fa_per_hour,
                })

    valid_candidates = [c for c in candidate_results if c["recall"] >= 0.85]
    if valid_candidates:
        best = min(valid_candidates, key=lambda c: (c["fa_per_hour"], -c["recall"]))
    else:
        best = max(candidate_results, key=lambda c: (c["recall"], c["fa_per_hour"]))

    return best["params"], best


def run_benchmark():
    subjects_data = load_subject_data()
    all_sids = [f"S{i}" for i in range(1, 16)]

    results_arm1: Dict[str, BenchmarkScoringResult] = {}
    selected_arm1: Dict[str, Tuple[float, float]] = {}

    results_arm2: Dict[str, BenchmarkScoringResult] = {}
    selected_arm2: Dict[str, Tuple[float, float, float]] = {}

    print("\nRunning LOSO Cross-Validation across 15 subjects (Amendment 4)...")

    for test_sid in all_sids:
        train_sids = [s for s in all_sids if s != test_sid]

        # 1. Arm 1 Tuning & Evaluation
        (best_tau, best_p1), a1_tune = tune_arm1(train_sids, subjects_data)
        selected_arm1[test_sid] = (best_tau, best_p1)

        emitter1 = StandardAlertEmitter(p_persist_sec=best_p1, r_refractory_sec=60.0, step_sec=2.0)
        arm1 = Arm1FixedThreshold(tau_pop=best_tau)
        d_test = subjects_data[test_sid]
        out1 = arm1.predict(d_test["hr_eval"], emitter=emitter1)
        res1 = score_alert_stream(
            alert_mask=out1.alert_mask,
            injected_episodes=d_test["injected_episodes"],
            natural_events=d_test["natural_events"],
            step_sec=d_test["step_sec"],
            subject_id=test_sid,
        )
        results_arm1[test_sid] = res1

        # 2. Arm 2 Tuning & Evaluation
        mu_pop, sigma_pop = compute_pop_priors(train_sids, subjects_data)
        (best_k, best_kappa, best_p2), a2_tune = tune_arm2(train_sids, subjects_data, mu_pop, sigma_pop)
        selected_arm2[test_sid] = (best_k, best_kappa, best_p2)

        emitter2 = StandardAlertEmitter(p_persist_sec=best_p2, r_refractory_sec=60.0, step_sec=2.0)
        arm2 = Arm2PersonalBaselineShrinkage(
            k=best_k,
            kappa_hours=best_kappa,
            mu_pop=mu_pop,
            sigma_pop=sigma_pop,
        )
        out2 = arm2.predict(d_test["hr_eval"], d_test["enmo_10s"], emitter=emitter2)
        res2 = score_alert_stream(
            alert_mask=out2.alert_mask,
            injected_episodes=d_test["injected_episodes"],
            natural_events=d_test["natural_events"],
            step_sec=d_test["step_sec"],
            subject_id=test_sid,
        )
        results_arm2[test_sid] = res2

        print(
            f"  {test_sid} evaluated: "
            f"Arm 1 (tau={best_tau:.0f}, P={best_p1:.0f}s) -> Rec={res1.event_scoring.recall*100:.1f}%, FA/hr={res1.alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 2 (k={best_k:.1f}, kap={best_kappa:.1f}h, P={best_p2:.0f}s) -> Rec={res2.event_scoring.recall*100:.1f}%, FA/hr={res2.alert_rate.false_alerts_per_hour:.2f}"
        )

    return subjects_data, results_arm1, selected_arm1, results_arm2, selected_arm2


def pool_metrics(sids: List[str], results: Dict[str, BenchmarkScoringResult]):
    """Aggregates metrics across specified subject subset."""
    n_episodes = sum(results[s].event_scoring.n_injected_episodes for s in sids)
    tp = sum(results[s].event_scoring.true_positives for s in sids)
    fn = sum(results[s].event_scoring.false_negatives for s in sids)
    recall = (tp / n_episodes * 100.0) if n_episodes > 0 else 0.0

    all_delays = []
    for s in sids:
        all_delays.extend(results[s].event_scoring.delays_sec)
    mean_delay = float(np.mean(all_delays)) if all_delays else 0.0
    med_delay = float(np.median(all_delays)) if all_delays else 0.0

    false_alerts = sum(results[s].alert_rate.false_alerts for s in sids)
    natural_alerts = sum(results[s].alert_rate.natural_alerts for s in sids)
    total_alerts = sum(results[s].alert_rate.total_alerts for s in sids)
    non_event_h = sum(results[s].alert_rate.non_event_hours for s in sids)
    fa_per_hour = (false_alerts / non_event_h) if non_event_h > 0 else 0.0

    return {
        "n_episodes": n_episodes,
        "tp": tp,
        "fn": fn,
        "recall": recall,
        "mean_delay": mean_delay,
        "med_delay": med_delay,
        "false_alerts": false_alerts,
        "natural_alerts": natural_alerts,
        "total_alerts": total_alerts,
        "non_event_h": non_event_h,
        "fa_per_hour": fa_per_hour,
    }


def format_table(results_arm1, sel1, results_arm2, sel2):
    all_sids = [f"S{i}" for i in range(1, 16)]
    without_s5 = [s for s in all_sids if s != "S5"]
    stratum_s5_s6_s11 = ["S5", "S6", "S11"]

    print("\n" + "=" * 140)
    print("TABLE: preliminary, Arms 1-2, no faults, Amendment 4")
    print("Protocol Section 4 & Amendment 4: LOSO Alerting Benchmark (Condition 0: Clean Background, R=60s Refractory Hold-off)")
    print("=" * 140)

    header = (
        f"{'Subject':<8} | "
        f"{'Arm 1 Selected':<18} {'Rec %':>7} {'Delay(TP)':>9} {'FA/hr':>8} {'FA':>5} {'NatA':>5} | "
        f"{'Arm 2 Selected (k, kappa)':<26} {'Rec %':>7} {'Delay(TP)':>9} {'FA/hr':>8} {'FA':>5} {'NatA':>5}"
    )
    print(header)
    print("-" * 140)

    for sid in all_sids:
        r1 = results_arm1[sid]
        r2 = results_arm2[sid]

        r1_rec = r1.event_scoring.recall * 100.0
        r1_delay = f"{r1.event_scoring.median_delay_sec:.1f}s" if r1.event_scoring.median_delay_sec is not None else "N/A"
        r1_fa_hr = r1.alert_rate.false_alerts_per_hour
        r1_fa = r1.alert_rate.false_alerts
        r1_nata = r1.alert_rate.natural_alerts
        p1 = f"tau={sel1[sid][0]:.0f}, P={sel1[sid][1]:.0f}s"

        r2_rec = r2.event_scoring.recall * 100.0
        r2_delay = f"{r2.event_scoring.median_delay_sec:.1f}s" if r2.event_scoring.median_delay_sec is not None else "N/A"
        r2_fa_hr = r2.alert_rate.false_alerts_per_hour
        r2_fa = r2.alert_rate.false_alerts
        r2_nata = r2.alert_rate.natural_alerts
        p2 = f"k={sel2[sid][0]:.1f}, kap={sel2[sid][1]:.1f}h, P={sel2[sid][2]:.0f}s"

        row = (
            f"{sid:<8} | "
            f"{p1:<18} {r1_rec:>6.1f}% {r1_delay:>9} {r1_fa_hr:>8.2f} {r1_fa:>5} {r1_nata:>5} | "
            f"{p2:<26} {r2_rec:>6.1f}% {r2_delay:>9} {r2_fa_hr:>8.2f} {r2_fa:>5} {r2_nata:>5}"
        )
        print(row)

    print("-" * 140)

    # Pooled strata
    for name, sids in [
        ("POOLED: All 15 Subjects", all_sids),
        ("POOLED: Without S5 (14)", without_s5),
        ("STRATUM: S5/S6/S11 (3)", stratum_s5_s6_s11),
    ]:
        p1 = pool_metrics(sids, results_arm1)
        p2 = pool_metrics(sids, results_arm2)

        row = (
            f"{name:<29} "
            f"{p1['recall']:>6.1f}% {p1['med_delay']:>8.1f}s {p1['fa_per_hour']:>8.2f} {p1['false_alerts']:>5} {p1['natural_alerts']:>5} | "
            f"{'':<26} {p2['recall']:>6.1f}% {p2['med_delay']:>8.1f}s {p2['fa_per_hour']:>8.2f} {p2['false_alerts']:>5} {p2['natural_alerts']:>5}"
        )
        print(row)
    print("=" * 140)
    print("Notes:")
    print("  1. Rec %: Event-level recall on injected synthetic tachycardia episodes.")
    print("  2. Delay(TP): Median onset detection delay (seconds) evaluated strictly over detected true-positive episodes.")
    print("  3. FA: Clean false alerts outside all injected episodes AND outside natural Amendment 1 events (+/-30s buffer).")
    print("  4. NatA: Alerts occurring inside natural Amendment 1 event buffers (+/-30s), reported separately.")
    print("  5. FA/hr: Clean False Alerts / Total Non-Event Monitoring Hours.")
    print("  6. Arm 2 Selected: Outlier multiplier k and shrinkage strength kappa (kap) are tuned and reported separately.")


if __name__ == "__main__":
    _, r1, s1, r2, s2 = run_benchmark()
    format_table(r1, s1, r2, s2)
