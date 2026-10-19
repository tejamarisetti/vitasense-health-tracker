"""
VitaSense AI - Verified Benchmark Summary Provider
Renders real empirical tables from docs/RESULTS_SUMMARY.md.
No invented numbers.
"""

from typing import Dict, Any, List


def get_benchmark_summary() -> Dict[str, Any]:
    """
    Returns exact verified findings and empirical tables from docs/RESULTS_SUMMARY.md.
    """
    return {
        "finding": "H1 not supported",
        "executive_summary": [
            {
                "title": "Hypothesis H1 Not Supported",
                "text": "Arm 3b (+Trust Score) showed no statistically significant reduction in false alerts per hour over Arm 3a (+Kinematic Motion Gating alone) across any of the four evaluated experimental regimes (p-values 0.28 to 0.98; all 95% bootstrap CIs span zero).",
                "badge": "H1 Not Supported",
                "status": "danger",
            },
            {
                "title": "Kinematic Motion Gating Drives False Alarm Suppression",
                "text": "Adding an accelerometer-derived motion gate (Arm 3a) delivers the primary false alarm suppression, reducing false alerts per hour from 6.47 down to 1.63 FA/hr in no-fault conditions (~75% reduction).",
                "badge": "Primary Driver",
                "status": "success",
            },
            {
                "title": "Fixed Population Threshold (Arm 1) is a Strong Baseline",
                "text": "Arm 1 (fixed threshold at 100 bpm, P=30s) achieved the highest event recall (88.4%) across all fault regimes and moderate false alert rates (4.39 FA/hr), outperforming untuned personal baselines.",
                "badge": "Strong Baseline",
                "status": "info",
            },
            {
                "title": "Arm 2 Never Reached 85% Recall Target",
                "text": "Arm 2 (Personal Baseline with Shrinkage) never achieved >=85% training recall in any fold across any condition (maximum was 80.4%), triggering the fallback rule in 100% of folds.",
                "badge": "Fallback Invoked",
                "status": "warning",
            },
        ],
        "combined_metric_table": [
            # Condition 0: No-Fault
            {"condition": "Condition 0 (No-Fault)", "arm": "Arm 1 (Fixed)", "recall_pct": 88.4, "fa_per_hr": 4.39, "tp": 99, "fp": 154, "precision_pct": 39.1, "f1_score": 0.542},
            {"condition": "Condition 0 (No-Fault)", "arm": "Arm 2 (Personal)", "recall_pct": 80.4, "fa_per_hr": 6.47, "tp": 90, "fp": 227, "precision_pct": 28.4, "f1_score": 0.420},
            {"condition": "Condition 0 (No-Fault)", "arm": "Arm 3a (+Kinematic)", "recall_pct": 80.4, "fa_per_hr": 1.63, "tp": 90, "fp": 57, "precision_pct": 61.2, "f1_score": 0.695},
            {"condition": "Condition 0 (No-Fault)", "arm": "Arm 3b (+Trust)", "recall_pct": 79.5, "fa_per_hr": 1.76, "tp": 89, "fp": 62, "precision_pct": 58.9, "f1_score": 0.677},
            {"condition": "Condition 0 (No-Fault)", "arm": "Arm 3b-noMotion", "recall_pct": 80.4, "fa_per_hr": 6.13, "tp": 90, "fp": 215, "precision_pct": 29.5, "f1_score": 0.432},

            # Regime A: Low Duty ~10%
            {"condition": "Regime A (Low Duty ~10%)", "arm": "Arm 1 (Fixed)", "recall_pct": 88.4, "fa_per_hr": 4.39, "tp": 99, "fp": 154, "precision_pct": 39.1, "f1_score": 0.542},
            {"condition": "Regime A (Low Duty ~10%)", "arm": "Arm 2 (Personal)", "recall_pct": 80.4, "fa_per_hr": 6.47, "tp": 90, "fp": 227, "precision_pct": 28.4, "f1_score": 0.420},
            {"condition": "Regime A (Low Duty ~10%)", "arm": "Arm 3a (+Kinematic)", "recall_pct": 80.4, "fa_per_hr": 1.63, "tp": 90, "fp": 57, "precision_pct": 61.2, "f1_score": 0.695},
            {"condition": "Regime A (Low Duty ~10%)", "arm": "Arm 3b (+Trust)", "recall_pct": 79.5, "fa_per_hr": 1.82, "tp": 89, "fp": 64, "precision_pct": 58.2, "f1_score": 0.672},
            {"condition": "Regime A (Low Duty ~10%)", "arm": "Arm 3b-noMotion", "recall_pct": 80.4, "fa_per_hr": 6.27, "tp": 90, "fp": 220, "precision_pct": 29.0, "f1_score": 0.427},

            # Regime B: Nominal ~25-30%
            {"condition": "Regime B (Nominal ~25-30%)", "arm": "Arm 1 (Fixed)", "recall_pct": 88.4, "fa_per_hr": 4.39, "tp": 99, "fp": 154, "precision_pct": 39.1, "f1_score": 0.542},
            {"condition": "Regime B (Nominal ~25-30%)", "arm": "Arm 2 (Personal)", "recall_pct": 75.9, "fa_per_hr": 6.47, "tp": 85, "fp": 227, "precision_pct": 27.2, "f1_score": 0.401},
            {"condition": "Regime B (Nominal ~25-30%)", "arm": "Arm 3a (+Kinematic)", "recall_pct": 75.9, "fa_per_hr": 2.30, "tp": 85, "fp": 80, "precision_pct": 51.5, "f1_score": 0.614},
            {"condition": "Regime B (Nominal ~25-30%)", "arm": "Arm 3b (+Trust)", "recall_pct": 75.0, "fa_per_hr": 2.37, "tp": 84, "fp": 82, "precision_pct": 50.6, "f1_score": 0.604},
            {"condition": "Regime B (Nominal ~25-30%)", "arm": "Arm 3b-noMotion", "recall_pct": 75.9, "fa_per_hr": 6.44, "tp": 85, "fp": 225, "precision_pct": 27.4, "f1_score": 0.403},

            # F7: High-Motion Optical Noise (+5 dB)
            {"condition": "F7 Noise (+5 dB SNR)", "arm": "Arm 1 (Fixed)", "recall_pct": 78.6, "fa_per_hr": 3.84, "tp": 88, "fp": 135, "precision_pct": 39.5, "f1_score": 0.525},
            {"condition": "F7 Noise (+5 dB SNR)", "arm": "Arm 2 (Personal)", "recall_pct": 64.3, "fa_per_hr": 4.67, "tp": 72, "fp": 164, "precision_pct": 30.5, "f1_score": 0.414},
            {"condition": "F7 Noise (+5 dB SNR)", "arm": "Arm 3a (+Kinematic)", "recall_pct": 64.3, "fa_per_hr": 1.57, "tp": 72, "fp": 55, "precision_pct": 56.7, "f1_score": 0.603},
            {"condition": "F7 Noise (+5 dB SNR)", "arm": "Arm 3b (+Trust)", "recall_pct": 58.0, "fa_per_hr": 1.28, "tp": 65, "fp": 45, "precision_pct": 59.1, "f1_score": 0.586},
            {"condition": "F7 Noise (+5 dB SNR)", "arm": "Arm 3b-noMotion", "recall_pct": 64.3, "fa_per_hr": 4.61, "tp": 72, "fp": 162, "precision_pct": 30.8, "f1_score": 0.416},
        ],
        "paired_comparison_table": [
            {
                "condition": "Condition 0 (No-Fault)",
                "recall_3b": 79.5,
                "recall_3a": 80.4,
                "fa_3b": 1.76,
                "fa_3a": 1.63,
                "mean_diff": "+0.13 FA/hr",
                "hl_median_diff": "+0.00 FA/hr",
                "ci_95": "[-0.48, +0.69] FA/hr",
                "wilcoxon_w": 31.0,
                "p_value": 0.8589,
                "is_significant": False,
            },
            {
                "condition": "Regime A (Low Duty ~10%)",
                "recall_3b": 79.5,
                "recall_3a": 80.4,
                "fa_3b": 1.82,
                "fa_3a": 1.63,
                "mean_diff": "+0.05 FA/hr",
                "hl_median_diff": "-0.08 FA/hr",
                "ci_95": "[-0.61, +0.79] FA/hr",
                "wilcoxon_w": 40.0,
                "p_value": 0.7007,
                "is_significant": False,
            },
            {
                "condition": "Regime B (Nominal ~25-30%)",
                "recall_3b": 75.0,
                "recall_3a": 75.9,
                "fa_3b": 2.37,
                "fa_3a": 2.30,
                "mean_diff": "-0.04 FA/hr",
                "hl_median_diff": "-0.00 FA/hr",
                "ci_95": "[-0.87, +0.87] FA/hr",
                "wilcoxon_w": 52.0,
                "p_value": 0.9750,
                "is_significant": False,
            },
            {
                "condition": "F7 Noise (+5 dB SNR)",
                "recall_3b": 58.0,
                "recall_3a": 64.3,
                "fa_3b": 1.28,
                "fa_3a": 1.57,
                "mean_diff": "-0.49 FA/hr",
                "hl_median_diff": "-0.25 FA/hr",
                "ci_95": "[-1.43, +0.23] FA/hr",
                "wilcoxon_w": 17.0,
                "p_value": 0.2845,
                "is_significant": False,
            },
        ],
        "per_fault_table": [
            {"regime": "Regime A", "fault": "Clean Segments", "arm_3b_fa": 1.67, "arm_3a_fa": 1.53, "arm_1_fa": 4.12, "alerts_count": 59, "exposure_hours": 35.3},
            {"regime": "Regime A", "fault": "F1 (GAPS)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 0.82, "note": "insufficient data (<10 alerts, <1 hr)"},
            {"regime": "Regime A", "fault": "F2 (STALE)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 0.65, "note": "insufficient data (<10 alerts, <1 hr)"},
            {"regime": "Regime A", "fault": "F3 (DUPL)", "arm_3b_fa": 1.71, "arm_3a_fa": 1.71, "arm_1_fa": 4.25, "alerts_count": 12, "exposure_hours": 7.0},
            {"regime": "Regime A", "fault": "F4 (SPIKE)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 0.42, "note": "insufficient data (<10 alerts, <1 hr)"},
            {"regime": "Regime A", "fault": "F5 (DRIFT)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 0.55, "note": "insufficient data (<10 alerts, <1 hr)"},
            {"regime": "Regime A", "fault": "F6 (UNIT)", "arm_3b_fa": 1.45, "arm_3a_fa": 1.45, "arm_1_fa": 3.90, "alerts_count": 11, "exposure_hours": 7.6},

            {"regime": "Regime B", "fault": "Clean Segments", "arm_3b_fa": 2.21, "arm_3a_fa": 2.15, "arm_1_fa": 4.05, "alerts_count": 76, "exposure_hours": 34.4},
            {"regime": "Regime B", "fault": "F1 (GAPS)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 1.65, "note": "insufficient data (<10 alerts)"},
            {"regime": "Regime B", "fault": "F2 (STALE)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 1.30, "note": "insufficient data (<10 alerts)"},
            {"regime": "Regime B", "fault": "F3 (DUPL)", "arm_3b_fa": 2.25, "arm_3a_fa": 2.18, "arm_1_fa": 4.30, "alerts_count": 22, "exposure_hours": 9.8},
            {"regime": "Regime B", "fault": "F4 (SPIKE)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 0.85, "note": "insufficient data (<10 alerts, <1 hr)"},
            {"regime": "Regime B", "fault": "F5 (DRIFT)", "arm_3b_fa": 0.00, "arm_3a_fa": 0.00, "arm_1_fa": 0.00, "alerts_count": 0, "exposure_hours": 1.10, "note": "insufficient data (<10 alerts)"},
            {"regime": "Regime B", "fault": "F6 (UNIT)", "arm_3b_fa": 2.10, "arm_3a_fa": 2.05, "arm_1_fa": 4.20, "alerts_count": 21, "exposure_hours": 10.0},
        ],
        "edge_of_grid_findings": {
            "arm_1": "Selected tau_pop = 100 bpm in 15/15 folds (100%), Persistence P = 30s in 15/15 folds (100%).",
            "arm_2": "Selected k = 2.0 in 15/15 folds (100%), P = 10s in 15/15 folds (100%), kappa = 2.0h in 14/15 folds (93.3%). Arm 2 never achieved 85% recall (max training recall 80.4%), triggering fallback rule in 100% of folds.",
            "arm_3a": "Selected theta_rest = 0.08g in 14/15 folds (93.3%) to preserve recall bounded by Arm 2.",
            "arm_3b": "Selected theta_trust = 0.60 in 14/15 folds (93.3%).",
        }
    }
