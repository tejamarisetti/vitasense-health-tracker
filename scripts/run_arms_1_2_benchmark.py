"""
VitaSense AI - Benchmark Runner for Arms 1 and 2 under LOSO Cross-Validation
Protocol Section 4 (Frozen v1.0.0) & Amendment 3 (Sections 2, 4, 6)

Evaluates:
- Arm 1: Fixed Threshold (tau_pop in {100, 110, 120} bpm)
- Arm 2: Personal Baseline with Shrinkage (k in {2.0, 2.5, 3.0}, kappa in {0.5, 1.0, 2.0} hours)

LOSO Tuning Protocol:
- Full 15-subject Leave-One-Subject-Out cross-validation.
- Hyperparameter selection is conducted strictly inside the training folds (N-1 subjects).
- Selection rule: Choose candidate achieving pooled training Recall >= 85% with minimum FA/hr;
  if none achieves 85%, maximize recall.
- Evaluated on test fold; reported per subject and pooled (All-15, Without-S5, and S5/S6/S11).
- Labeled: "preliminary, Arms 1-2, no faults".
"""

import sys
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def tune_arm1(train_sids: List[str], subjects_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Tunes Arm 1 tau_pop in {100, 110, 120} bpm strictly inside training folds."""
    grid = [100.0, 110.0, 120.0]
    candidate_results = []

    for tau in grid:
        arm = Arm1FixedThreshold(tau_pop=tau)
        total_tp = 0
        total_episodes = 0
        total_fa = 0
        total_non_event_h = 0.0

        for sid in train_sids:
            d = subjects_data[sid]
            out = arm.predict(d["hr_eval"])
            res = score_alert_stream(
                alert_mask=out.alert_mask,
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
            "tau_pop": tau,
            "recall": recall,
            "fa_per_hour": fa_per_hour,
        })

    # Selection: Recall >= 0.85 with lowest FA/hr; else highest recall
    valid_candidates = [c for c in candidate_results if c["recall"] >= 0.85]
    if valid_candidates:
        best = min(valid_candidates, key=lambda c: c["fa_per_hour"])
    else:
        best = max(candidate_results, key=lambda c: c["recall"])

    return best["tau_pop"], best


def tune_arm2(
    train_sids: List[str],
    subjects_data: Dict[str, Any],
    mu_pop: float,
    sigma_pop: float,
) -> Tuple[Tuple[float, float], Dict[str, Any]]:
    """Tunes Arm 2 (k, kappa) strictly inside training folds."""
    k_grid = [2.0, 2.5, 3.0]
    kappa_grid = [0.5, 1.0, 2.0]
    candidate_results = []

    for k in k_grid:
        for kappa in kappa_grid:
            arm = Arm2PersonalBaselineShrinkage(
                k=k,
                kappa_hours=kappa,
                mu_pop=mu_pop,
                sigma_pop=sigma_pop,
            )
            total_tp = 0
            total_episodes = 0
            total_fa = 0
            total_non_event_h = 0.0

            for sid in train_sids:
                d = subjects_data[sid]
                out = arm.predict(d["hr_eval"], d["enmo_10s"])
                res = score_alert_stream(
                    alert_mask=out.alert_mask,
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
                "params": (k, kappa),
                "k": k,
                "kappa": kappa,
                "recall": recall,
                "fa_per_hour": fa_per_hour,
            })

    valid_candidates = [c for c in candidate_results if c["recall"] >= 0.85]
    if valid_candidates:
        best = min(valid_candidates, key=lambda c: c["fa_per_hour"])
    else:
        best = max(candidate_results, key=lambda c: c["recall"])

    return best["params"], best


def run_benchmark():
    subjects_data = load_subject_data()
    all_sids = [f"S{i}" for i in range(1, 16)]

    results_arm1: Dict[str, BenchmarkScoringResult] = {}
    selected_arm1: Dict[str, float] = {}

    results_arm2: Dict[str, BenchmarkScoringResult] = {}
    selected_arm2: Dict[str, Tuple[float, float]] = {}

    print("\nRunning LOSO Cross-Validation across 15 subjects...")

    for test_sid in all_sids:
        train_sids = [s for s in all_sids if s != test_sid]

        # 1. Arm 1 Tuning & Evaluation
        best_tau, a1_tune_info = tune_arm1(train_sids, subjects_data)
        selected_arm1[test_sid] = best_tau

        arm1 = Arm1FixedThreshold(tau_pop=best_tau)
        d_test = subjects_data[test_sid]
        out1 = arm1.predict(d_test["hr_eval"])
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
        best_params, a2_tune_info = tune_arm2(train_sids, subjects_data, mu_pop, sigma_pop)
        selected_arm2[test_sid] = best_params

        arm2 = Arm2PersonalBaselineShrinkage(
            k=best_params[0],
            kappa_hours=best_params[1],
            mu_pop=mu_pop,
            sigma_pop=sigma_pop,
        )
        out2 = arm2.predict(d_test["hr_eval"], d_test["enmo_10s"])
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
            f"Arm 1 (tau={best_tau:.0f}) -> Rec={res1.event_scoring.recall*100:.1f}%, FA/hr={res1.alert_rate.false_alerts_per_hour:.2f} | "
            f"Arm 2 (k={best_params[0]:.1f}, kap={best_params[1]:.1f}h) -> Rec={res2.event_scoring.recall*100:.1f}%, FA/hr={res2.alert_rate.false_alerts_per_hour:.2f}"
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

    print("\n" + "=" * 125)
    print("TABLE: preliminary, Arms 1-2, no faults")
    print("Protocol Section 4 & Amendment 3 - Leave-One-Subject-Out (LOSO) Alerting Benchmark (Condition 0: Clean Background)")
    print("=" * 125)

    header = (
        f"{'Subject':<8} | "
        f"{'Arm 1 Selected':<14} {'Rec %':>7} {'Delay':>7} {'FA/hr':>8} {'FA':>5} {'NatA':>5} | "
        f"{'Arm 2 Selected':<16} {'Rec %':>7} {'Delay':>7} {'FA/hr':>8} {'FA':>5} {'NatA':>5}"
    )
    print(header)
    print("-" * 125)

    for sid in all_sids:
        r1 = results_arm1[sid]
        r2 = results_arm2[sid]

        r1_rec = r1.event_scoring.recall * 100.0
        r1_delay = f"{r1.event_scoring.median_delay_sec:.1f}s" if r1.event_scoring.median_delay_sec is not None else "N/A"
        r1_fa_hr = r1.alert_rate.false_alerts_per_hour
        r1_fa = r1.alert_rate.false_alerts
        r1_nata = r1.alert_rate.natural_alerts
        p1 = f"tau={sel1[sid]:.0f}"

        r2_rec = r2.event_scoring.recall * 100.0
        r2_delay = f"{r2.event_scoring.median_delay_sec:.1f}s" if r2.event_scoring.median_delay_sec is not None else "N/A"
        r2_fa_hr = r2.alert_rate.false_alerts_per_hour
        r2_fa = r2.alert_rate.false_alerts
        r2_nata = r2.alert_rate.natural_alerts
        p2 = f"k={sel2[sid][0]:.1f},k={sel2[sid][1]:.1f}h"

        row = (
            f"{sid:<8} | "
            f"{p1:<14} {r1_rec:>6.1f}% {r1_delay:>7} {r1_fa_hr:>8.2f} {r1_fa:>5} {r1_nata:>5} | "
            f"{p2:<16} {r2_rec:>6.1f}% {r2_delay:>7} {r2_fa_hr:>8.2f} {r2_fa:>5} {r2_nata:>5}"
        )
        print(row)

    print("-" * 125)

    # Pooled strata
    for name, sids in [
        ("POOLED: All 15 Subjects", all_sids),
        ("POOLED: Without S5 (14)", without_s5),
        ("STRATUM: S5/S6/S11 (3)", stratum_s5_s6_s11),
    ]:
        p1 = pool_metrics(sids, results_arm1)
        p2 = pool_metrics(sids, results_arm2)

        row = (
            f"{name:<25} "
            f"{p1['recall']:>6.1f}% {p1['med_delay']:>6.1f}s {p1['fa_per_hour']:>8.2f} {p1['false_alerts']:>5} {p1['natural_alerts']:>5} | "
            f"{'':<16} {p2['recall']:>6.1f}% {p2['med_delay']:>6.1f}s {p2['fa_per_hour']:>8.2f} {p2['false_alerts']:>5} {p2['natural_alerts']:>5}"
        )
        print(row)
    print("=" * 125)


if __name__ == "__main__":
    _, r1, s1, r2, s2 = run_benchmark()
    format_table(r1, s1, r2, s2)
