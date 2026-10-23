"""
VitaSense AI - Arm 4 (Conformal Prediction / Multi-attribute Trust Abstention) Evaluation Script
Protocol Amendment 3 Section 6 & Amendment 4.
Evaluates Arm 4 across all 15 LOSO folds for all 4 benchmark conditions:
1. Condition 0: No-Fault Clean Background
2. Regime A: Low Fault-Duty (~10%)
3. Regime B: Nominal Fault-Duty (~25-30%)
4. F7: Optical BVP Noise (+5 dB SNR)
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vitasense.benchmarks.alert_emitter import StandardAlertEmitter
from vitasense.benchmarks.alerting_arms import (
    Arm4ConformalAbstention,
    compute_causal_baseline_threshold_and_stats,
    compute_causal_baseline_threshold,
)
from vitasense.benchmarks.scoring import score_alert_stream, BenchmarkScoringResult
from vitasense.benchmarks.fault_schedule import FaultRegime
from scripts.run_fault_regimes_benchmark import (
    build_regime_subject_dataset,
    build_f7_subject_dataset,
    build_fast_scoring_caches,
    compute_pop_priors,
    fast_eval_mask,
    pool_metrics,
    FastSubjectScoringCache,
)

OUT_DIR = ROOT / "results" / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def tune_arm4_loso(
    train_sids: List[str],
    dataset: Dict[str, Any],
    caches: Dict[str, FastSubjectScoringCache],
    mu_pop: float,
    sigma_pop: float,
):
    k_grid = [2.0, 2.5, 3.0, 3.5, 4.0]
    kap_grid = [0.5, 1.0, 2.0]
    alpha_grid = [0.05, 0.10]
    lambda_grid = [0.5, 1.0]
    th_unc_grid = [0.20, 0.30]
    p_grid = [10.0, 20.0, 30.0]
    r_sec = 60.0

    # 1. Precompute stats & raw alerts for each (k, kap) across training subjects
    subject_stats = {}
    raw_conds_a2 = {}
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            subject_stats[pair] = {}
            raw_conds_a2[pair] = {}
            for sid in train_sids:
                d = dataset[sid]
                tau_ser, mu_hat, std_hat = compute_causal_baseline_threshold_and_stats(
                    hr_arr=d["hr_eval"],
                    enmo_arr=d["enmo_10s"],
                    k=k,
                    kappa_hours=kap,
                    mu_pop=mu_pop,
                    sigma_pop=sigma_pop,
                )
                subject_stats[pair][sid] = (tau_ser, mu_hat, std_hat)
                raw_conds_a2[pair][sid] = (d["hr_eval"] > tau_ser) & np.isfinite(d["hr_eval"])

    # 2. Conformal calibration on low-motion windows across training subjects
    # s(t) = |HR(t) - mu_hat(t)| / max(1.0, std_hat(t)) for windows with enmo <= 0.05
    q_calibs = {}
    for pair in subject_stats:
        scores = []
        for sid in train_sids:
            d = dataset[sid]
            _, mu_hat, std_hat = subject_stats[pair][sid]
            calib_mask = (d["enmo_10s"] <= 0.05) & np.isfinite(d["hr_eval"])
            if np.any(calib_mask):
                sc = np.abs(d["hr_eval"][calib_mask] - mu_hat[calib_mask]) / np.maximum(1.0, std_hat[calib_mask])
                scores.extend(sc)
        scores_arr = np.array(scores) if scores else np.array([1.96])
        q_calibs[pair] = {
            alpha: float(np.quantile(scores_arr, 1.0 - alpha))
            for alpha in alpha_grid
        }

    tot_ep = sum(caches[sid].n_episodes for sid in train_sids)
    tot_nh = sum(caches[sid].non_event_hours for sid in train_sids)

    cands = []
    for k in k_grid:
        for kap in kap_grid:
            pair = (k, kap)
            for alpha in alpha_grid:
                q = q_calibs[pair][alpha]
                for lam in lambda_grid:
                    for th_unc in th_unc_grid:
                        raw_arm4 = {}
                        for sid in train_sids:
                            d = dataset[sid]
                            tau_ser, mu_hat, std_hat = subject_stats[pair][sid]
                            safe_mu = np.maximum(1.0, mu_hat)
                            safe_std = np.maximum(1.0, std_hat)
                            u_t = safe_std / safe_mu
                            u_total = u_t + lam * (1.0 - d["s_trust"])
                            band_lo = mu_hat - q * safe_std
                            band_hi = mu_hat + q * safe_std
                            spans_tau = (band_lo <= tau_ser) & (tau_ser <= band_hi)
                            excessive_unc = (u_total > th_unc)
                            abstain = spans_tau | excessive_unc
                            raw_arm4[sid] = raw_conds_a2[pair][sid] & (~abstain)

                        for p in p_grid:
                            em = StandardAlertEmitter(p_persist_sec=p, r_refractory_sec=r_sec)
                            tp, fa = 0, 0
                            for sid in train_sids:
                                m = em.emit(raw_arm4[sid])
                                t, f = fast_eval_mask(m, caches[sid])
                                tp += t
                                fa += f

                            rec = tp / tot_ep if tot_ep > 0 else 0.0
                            fa_hr = fa / tot_nh if tot_nh > 0 else 0.0
                            cands.append({
                                "params": (k, kap, alpha, lam, th_unc, p, q),
                                "rec": rec,
                                "fa_hr": fa_hr,
                            })

    valid = [c for c in cands if c["rec"] >= 0.85]
    best = min(valid, key=lambda c: (c["fa_hr"], -c["rec"])) if valid else max(cands, key=lambda c: (c["rec"], c["fa_hr"]))
    return best["params"], best


def evaluate_arm4_condition(condition_name: str, dataset: Dict[str, Any]):
    all_sids = [f"S{i}" for i in range(1, 16)]
    caches = build_fast_scoring_caches(dataset)
    res_a4, sel_a4 = {}, {}

    print(f"\n>>> Running Arm 4 LOSO Evaluation: {condition_name} ...", flush=True)
    t0 = time.time()

    for test_sid in all_sids:
        train_sids = [s for s in all_sids if s != test_sid]
        d_test = dataset[test_sid]
        mu_pop, sigma_pop = compute_pop_priors(train_sids, dataset)

        p_a4, best_cand = tune_arm4_loso(train_sids, dataset, caches, mu_pop, sigma_pop)
        sel_a4[test_sid] = p_a4

        arm4 = Arm4ConformalAbstention(
            k=p_a4[0],
            kappa_hours=p_a4[1],
            alpha=p_a4[2],
            lambda_trust=p_a4[3],
            theta_unc=p_a4[4],
            q_calib=p_a4[6],
            mu_pop=mu_pop,
            sigma_pop=sigma_pop,
        )
        em4 = StandardAlertEmitter(p_persist_sec=p_a4[5], r_refractory_sec=60.0)
        out4 = arm4.predict(
            hr_series=d_test["hr_eval"],
            enmo_10s=d_test["enmo_10s"],
            trust_series=d_test["s_trust"],
            emitter=em4,
        )

        res_a4[test_sid] = score_alert_stream(
            out4.alert_mask,
            d_test["injected_episodes"],
            d_test["natural_events"],
            fault_types=d_test["fault_types"],
            subject_id=test_sid,
        )
        print(f"  {test_sid} evaluated. (Best train Rec: {best_cand['rec']*100:.1f}%, FA/hr: {best_cand['fa_hr']:.2f})", flush=True)

    elapsed = time.time() - t0
    m = pool_metrics(all_sids, res_a4)
    tp = m["tp"]
    fn = m["fn"]
    fa = m["false_alerts"]
    prec = (tp / (tp + fa) * 100.0) if (tp + fa) > 0 else 0.0
    f1 = (2 * tp / (2 * tp + fa + fn)) if (2 * tp + fa + fn) > 0 else 0.0

    m["precision_pct"] = prec
    m["f1_score"] = f1

    print(f"[{condition_name}] Arm 4 Completed in {elapsed:.1f}s:")
    print(f"  Recall: {m['recall']:.1f}% ({tp}/{m['n_episodes']})")
    print(f"  Clean FA/hr: {m['fa_per_hour']:.2f} ({fa} FA in {m['non_event_hours']:.2f}h)")
    print(f"  Precision: {prec:.1f}% | F1: {f1:.3f}")

    return res_a4, sel_a4, m


def main():
    print("=" * 80)
    print("EXECUTING BENCHMARK FOR ARM 4 (CONFORMAL ABSTENTION)")
    print("=" * 80)

    # 1. Condition 0: No-Fault
    data_c0 = build_regime_subject_dataset(FaultRegime.NO_FAULT)
    res_c0, sel_c0, m_c0 = evaluate_arm4_condition("Condition 0 (No-Fault)", data_c0)

    # 2. Regime A: Low Duty (~10%)
    data_ra = build_regime_subject_dataset(FaultRegime.REGIME_A, seed=42)
    res_ra, sel_ra, m_ra = evaluate_arm4_condition("Regime A (Low Duty ~10%)", data_ra)

    # 3. Regime B: Nominal Duty (~25-30%)
    data_rb = build_regime_subject_dataset(FaultRegime.REGIME_B, seed=42)
    res_rb, sel_rb, m_rb = evaluate_arm4_condition("Regime B (Nominal ~25-30%)", data_rb)

    # 4. F7: Optical BVP Noise
    data_f7 = build_f7_subject_dataset()
    res_f7, sel_f7, m_f7 = evaluate_arm4_condition("F7 (High-Motion BVP Noise)", data_f7)

    arm4_summary = [
        {"Condition": "Condition 0 (No-Fault)", "Arm": "Arm 4 (Conformal Abstention)", "Event_Recall_pct": round(m_c0["recall"], 1), "Clean_FA_hr": round(m_c0["fa_per_hour"], 2), "True_Alerts_TP": m_c0["tp"], "False_Alerts_FP": m_c0["false_alerts"], "Precision_pct": round(m_c0["precision_pct"], 1), "F1_Score": round(m_c0["f1_score"], 3)},
        {"Condition": "Regime A (Low Duty ~10%)", "Arm": "Arm 4 (Conformal Abstention)", "Event_Recall_pct": round(m_ra["recall"], 1), "Clean_FA_hr": round(m_ra["fa_per_hour"], 2), "True_Alerts_TP": m_ra["tp"], "False_Alerts_FP": m_ra["false_alerts"], "Precision_pct": round(m_ra["precision_pct"], 1), "F1_Score": round(m_ra["f1_score"], 3)},
        {"Condition": "Regime B (Nominal ~25-30%)", "Arm": "Arm 4 (Conformal Abstention)", "Event_Recall_pct": round(m_rb["recall"], 1), "Clean_FA_hr": round(m_rb["fa_per_hour"], 2), "True_Alerts_TP": m_rb["tp"], "False_Alerts_FP": m_rb["false_alerts"], "Precision_pct": round(m_rb["precision_pct"], 1), "F1_Score": round(m_rb["f1_score"], 3)},
        {"Condition": "F7 (High-Motion BVP Noise)", "Arm": "Arm 4 (Conformal Abstention)", "Event_Recall_pct": round(m_f7["recall"], 1), "Clean_FA_hr": round(m_f7["fa_per_hour"], 2), "True_Alerts_TP": m_f7["tp"], "False_Alerts_FP": m_f7["false_alerts"], "Precision_pct": round(m_f7["precision_pct"], 1), "F1_Score": round(m_f7["f1_score"], 3)},
    ]

    df_arm4 = pd.DataFrame(arm4_summary)
    print("\n--- ARM 4 SUMMARY METRICS ---")
    print(df_arm4.to_string(index=False))

    # Save to disk
    df_arm4.to_csv(OUT_DIR / "arm4_metrics.csv", index=False)
    print(f"\nSaved Arm 4 metrics to {OUT_DIR / 'arm4_metrics.csv'}")

    # Save detailed per-subject Arm 4 results for provenance
    arm4_persub = []
    for cond_name, r_dict in [
        ("Condition 0 (No-Fault)", res_c0),
        ("Regime A (Low Duty ~10%)", res_ra),
        ("Regime B (Nominal ~25-30%)", res_rb),
        ("F7 (High-Motion BVP Noise)", res_f7),
    ]:
        for sid, res in r_dict.items():
            arm4_persub.append({
                "Condition": cond_name,
                "Subject": sid,
                "Recall_pct": round(res.event_scoring.recall * 100.0, 1),
                "FA_hr": round(res.alert_rate.false_alerts_per_hour, 2),
                "TP": res.event_scoring.true_positives,
                "FP": res.alert_rate.false_alerts,
            })
    df_persub = pd.DataFrame(arm4_persub)
    df_persub.to_csv(OUT_DIR / "arm4_per_subject.csv", index=False)
    print(f"Saved Arm 4 per-subject metrics to {OUT_DIR / 'arm4_per_subject.csv'}")


if __name__ == "__main__":
    main()
