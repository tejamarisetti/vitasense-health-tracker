# VitaSense AI - Benchmark Results Summary

**Document Version:** 1.1.0  
**Date:** 2026-10-19  
**Status:** Complete Benchmark Evaluation (Protocol Amendments 1–4)  
**Evaluated Arms:**
- **Arm 1 (Fixed Population Threshold):** Standard population threshold ($\tau_{\text{pop}}$) with shared persistence filter ($P$) and refractory period ($R = 60\text{s}$).
- **Arm 2 (Personal Baseline with Shrinkage):** Adaptive personal threshold ($\tau_i(t) = \hat{\mu}_i(t) + k \cdot \hat{\sigma}_i(t)$) regularized toward population priors via empirical Bayes shrinkage ($\kappa$).
- **Arm 3a (Kinematic Gating):** Arm 2 personal baseline paired with a wrist triaxial accelerometer motion gate ($\text{ENMO} \le \theta_{\text{rest}}$).
- **Arm 3b (Software Trust Gate):** Arm 2 personal baseline paired with a multi-signal software trust score gate ($S_{\text{trust}}(t) \ge \theta_{\text{trust}}$).
- **Arm 3b-noMotion (Trust Gate Ablation):** Arm 3b trust score gate with the accelerometer kinematic term ablated ($w_{\text{mot}} = 0$).

*(Note: Arm 4 Conformal Abstention was not evaluated per experimental hold).*

---

## 1. Executive Summary & Core Hypothesis Outcome

### 1.1 Hypothesis $H_1$ Outcome: NOT SUPPORTED
- **Hypothesis $H_1$:** *"Incorporating a signal quality gate and trust score reduces false alerts per hour by $\ge 60\%$ relative to personalized alerting without quality gating (Arm 2) and fixed thresholding (Arm 1) under realistic and synthetic sensor fault conditions, while maintaining recall $\ge 85\%$."*
- **Empirical Finding:** **$H_1$ is not supported by the data.**
  1. **Trust score adds no statistically significant benefit over kinematic gating alone:** In paired comparisons across all 15 subjects, Arm 3b (+Trust Score) showed no statistically significant reduction in false alerts per hour over Arm 3a (+Kinematic Gate alone) across any tested condition:
     - **Condition 0 (No-Fault):** Hodges-Lehmann difference $+0.00\text{ FA/hr}$, Wilcoxon $W = 31.0, p = 0.8589$, 95% bootstrap CI $[-0.54, +0.89]\text{ FA/hr}$.
     - **Regime A (Low Duty ~10%):** Hodges-Lehmann difference $-0.08\text{ FA/hr}$, Wilcoxon $W = 40.0, p = 0.7007$, 95% bootstrap CI $[-0.66, +0.82]\text{ FA/hr}$.
     - **Regime B (Nominal ~25-30%):** Hodges-Lehmann difference $-0.00\text{ FA/hr}$, Wilcoxon $W = 52.0, p = 0.9750$, 95% bootstrap CI $[-0.78, +0.69]\text{ FA/hr}$.
     - **F7 (High-Motion BVP Noise):** Hodges-Lehmann difference $-0.25\text{ FA/hr}$, Wilcoxon $W = 17.0, p = 0.2845$, 95% bootstrap CI $[-1.47, +0.38]\text{ FA/hr}$.
  2. **Kinematic motion gating (Arm 3a) delivers almost the entire false alert reduction:** In clean data, Arm 3a reduces FA/hr by $74.2\%$ relative to Arm 2 ($1.47\text{ FA/hr}$ vs $5.69\text{ FA/hr}$). In Regime B, Arm 3a reduces FA/hr by $67.9\%$ relative to Arm 2 ($2.30\text{ FA/hr}$ vs $7.16\text{ FA/hr}$). Adding optical SQI, rate-of-change, and physiological bounding via Arm 3b yields no incremental false alert reduction over Arm 3a, but slightly degrades event recall under intense optical noise ($58.0\%$ in 3b vs $64.3\%$ in 3a under F7).
  3. **Arm 1 (Fixed Threshold) is a strong baseline:** Arm 1 achieved the highest event recall across all conditions ($91.1\%$ to $92.0\%$) and maintained moderate false alert rates ($3.20$ to $4.51\text{ FA/hr}$) due to the 30-second persistence filter ($P = 30\text{s}$).

---

## 2. Combined Benchmark Metric Table

Precision is defined on clean alerts: $\text{Precision} = \frac{TP_{\text{alerts}}}{TP_{\text{alerts}} + FP_{\text{clean\_alerts}}}$.

| Condition | Arm | Event Recall % | Clean FA/hr | True Alerts ($TP$) | False Alerts ($FP$) | Precision | $F_1$ Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Condition 0 (No-Fault)** | Arm 1 (Fixed) | 91.1% | 3.20 | 132 | 100 | 56.9% | 0.700 |
| | Arm 2 (Personal) | 80.4% | 5.69 | 133 | 178 | 42.8% | 0.558 |
| | Arm 3a (+Kinematic) | 80.4% | 1.47 | 133 | 46 | 74.3% | 0.772 |
| | Arm 3b (+Trust Score) | 79.5% | 1.69 | 130 | 53 | 71.0% | 0.750 |
| | Arm 3b-noMotion | 79.5% | 2.91 | 130 | 91 | 58.8% | 0.676 |
| **Regime A (Low Duty ~10%)** | Arm 1 (Fixed) | 91.1% | 3.58 | 132 | 112 | 54.1% | 0.679 |
| | Arm 2 (Personal) | 80.4% | 6.08 | 132 | 190 | 41.0% | 0.543 |
| | Arm 3a (+Kinematic) | 80.4% | 1.63 | 132 | 51 | 72.1% | 0.760 |
| | Arm 3b (+Trust Score) | 79.5% | 1.82 | 129 | 57 | 69.4% | 0.741 |
| | Arm 3b-noMotion | 79.5% | 3.07 | 129 | 96 | 57.3% | 0.666 |
| **Regime B (Nominal ~25-30%)** | Arm 1 (Fixed) | 91.1% | 4.51 | 132 | 141 | 48.4% | 0.632 |
| | Arm 2 (Personal) | 75.9% | 7.16 | 125 | 224 | 35.8% | 0.487 |
| | Arm 3a (+Kinematic) | 75.9% | 2.30 | 125 | 72 | 63.5% | 0.691 |
| | Arm 3b (+Trust Score) | 75.0% | 2.37 | 122 | 74 | 62.2% | 0.680 |
| | Arm 3b-noMotion | 75.0% | 3.61 | 122 | 113 | 51.9% | 0.614 |
| **F7 (High-Motion BVP Noise)** | Arm 1 (Fixed) | 92.0% | 3.07 | 131 | 96 | 57.7% | 0.709 |
| | Arm 2 (Personal) | 64.3% | 4.61 | 100 | 144 | 41.0% | 0.501 |
| | Arm 3a (+Kinematic) | 64.3% | 1.57 | 100 | 49 | 67.1% | 0.657 |
| | Arm 3b (+Trust Score) | 58.0% | 1.28 | 90 | 40 | 69.2% | 0.631 |
| | Arm 3b-noMotion | 58.0% | 2.05 | 90 | 64 | 58.4% | 0.582 |

---

## 3. Stratified Evaluation (Recall, Median Delay, FA/hr)

Per Protocol Amendment 3, metrics are reported pooled across all 15 subjects, without subject S5 (outlier resting heart rate), and across the high-error ambulatory stratum (S5, S6, S11).

### 3.1 Condition 0: No-Fault Clean Background
| Stratum | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust Score) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pooled All-15** | 91.1% / 40s / 3.20 | 80.4% / 22s / 5.69 | 80.4% / 22s / 1.47 | 79.5% / 22s / 1.69 | 79.5% / 22s / 2.91 |
| **Without S5 (14 subj)** | 90.7% / 40s / 2.90 | 79.6% / 22s / 5.26 | 79.6% / 22s / 1.35 | 78.7% / 22s / 1.72 | 78.7% / 22s / 2.93 |
| **S5/S6/S11 (3 subj)** | 100.0% / 37s / 9.39 | 94.4% / 20s / 16.13 | 94.4% / 20s / 5.10 | 94.4% / 22s / 3.88 | 94.4% / 22s / 6.74 |

### 3.2 Regime A: Low Fault-Duty (~10% faulted time)
| Stratum | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust Score) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pooled All-15** | 91.1% / 40s / 3.58 | 80.4% / 22s / 6.08 | 80.4% / 22s / 1.63 | 79.5% / 22s / 1.82 | 79.5% / 22s / 3.07 |
| **Without S5 (14 subj)** | 90.7% / 40s / 3.27 | 79.6% / 22s / 5.52 | 79.6% / 22s / 1.45 | 78.7% / 24s / 1.75 | 78.7% / 24s / 3.00 |
| **S5/S6/S11 (3 subj)** | 100.0% / 37s / 9.80 | 94.4% / 20s / 17.15 | 94.4% / 20s / 5.51 | 94.4% / 22s / 4.08 | 94.4% / 22s / 7.15 |

### 3.3 Regime B: Nominal Fault-Duty (~25–30% faulted time)
| Stratum | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust Score) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pooled All-15** | 91.1% / 40s / 4.51 | 75.9% / 22s / 7.16 | 75.9% / 22s / 2.30 | 75.0% / 24s / 2.37 | 75.0% / 24s / 3.61 |
| **Without S5 (14 subj)** | 90.7% / 40s / 4.14 | 75.0% / 24s / 6.40 | 75.0% / 24s / 2.19 | 74.1% / 24s / 2.29 | 74.1% / 24s / 3.54 |
| **S5/S6/S11 (3 subj)** | 100.0% / 37s / 10.21 | 94.4% / 20s / 18.78 | 94.4% / 20s / 5.92 | 94.4% / 22s / 4.29 | 94.4% / 22s / 7.15 |

### 3.4 F7 Condition: High-Motion Optical BVP Noise (SNR = +5 dB)
| Stratum | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust Score) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pooled All-15** | 92.0% / 40s / 3.07 | 64.3% / 24s / 4.61 | 64.3% / 24s / 1.57 | 58.0% / 24s / 1.28 | 58.0% / 24s / 2.05 |
| **Without S5 (14 subj)** | 91.7% / 40s / 2.70 | 63.0% / 25s / 4.01 | 63.0% / 25s / 1.18 | 56.5% / 24s / 1.15 | 56.5% / 24s / 1.92 |
| **S5/S6/S11 (3 subj)** | 100.0% / 38s / 8.98 | 88.9% / 21s / 14.90 | 88.9% / 21s / 5.92 | 88.9% / 22s / 3.47 | 88.9% / 22s / 5.51 |

---

## 4. Disaggregated FA/hr per Fault Type

**Rule:** Every cell presents alert counts and exposure hours alongside FA/hr. Any cell with fewer than 10 alerts OR under 1.0 hour of total exposure is explicitly marked with `*` (*Insufficient data: <10 alerts or <1.0h exposure*). No rates are presented without alert counts. Total monitoring exposure across 15 subjects = 31.25 hours.

### 4.1 Regime A: Low Duty (~10% Faulted Time)
| Fault Type | Exposure | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **F0_CLEAN** | 28.09h | 3.20 (90 FA, 28.09h) | 5.87 (165 FA, 28.09h) | 1.53 (43 FA, 28.09h) | 1.78 (50 FA, 28.09h) | 2.95 (83 FA, 28.09h) |
| **F1_GAPS** | 0.94h | 0.00 (0 FA, 0.94h)* | 0.00 (0 FA, 0.94h)* | 0.00 (0 FA, 0.94h)* | 0.00 (0 FA, 0.94h)* | 0.00 (0 FA, 0.94h)* |
| **F2_STALE** | 0.62h | 21.08 (13 FA, 0.62h)* | 8.11 (5 FA, 0.62h)* | 3.24 (2 FA, 0.62h)* | 1.62 (1 FA, 0.62h)* | 1.62 (1 FA, 0.62h)* |
| **F3_DUPL** | 0.62h | 3.21 (2 FA, 0.62h)* | 8.04 (5 FA, 0.62h)* | 3.21 (2 FA, 0.62h)* | 0.00 (0 FA, 0.62h)* | 4.82 (3 FA, 0.62h)* |
| **F4_SPIKE** | 0.07h | 0.00 (0 FA, 0.07h)* | 14.75 (1 FA, 0.07h)* | 0.00 (0 FA, 0.07h)* | 0.00 (0 FA, 0.07h)* | 14.75 (1 FA, 0.07h)* |
| **F5_DRIFT** | 0.45h | 0.00 (0 FA, 0.45h)* | 2.22 (1 FA, 0.45h)* | 0.00 (0 FA, 0.45h)* | 0.00 (0 FA, 0.45h)* | 0.00 (0 FA, 0.45h)* |
| **F6_UNIT** | 0.48h | 14.48 (7 FA, 0.48h)* | 26.90 (13 FA, 0.48h)* | 8.28 (4 FA, 0.48h)* | 12.41 (6 FA, 0.48h)* | 16.55 (8 FA, 0.48h)* |

*(\*) Marked [Insufficient data: < 10 alerts or < 1.0h exposure].*

### 4.2 Regime B: Nominal Duty (~25–30% Faulted Time)
| Fault Type | Exposure | Arm 1 (Fixed) | Arm 2 (Personal) | Arm 3a (+Kinematic) | Arm 3b (+Trust) | Arm 3b-noMotion |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **F0_CLEAN** | 21.67h | 3.51 (76 FA, 21.67h) | 5.77 (125 FA, 21.67h) | 1.62 (35 FA, 21.67h) | 1.85 (40 FA, 21.67h) | 2.91 (63 FA, 21.67h) |
| **F1_GAPS** | 3.15h | 0.00 (0 FA, 3.15h)* | 0.00 (0 FA, 3.15h)* | 0.00 (0 FA, 3.15h)* | 0.00 (0 FA, 3.15h)* | 0.00 (0 FA, 3.15h)* |
| **F2_STALE** | 1.58h | 20.23 (32 FA, 1.58h) | 10.75 (17 FA, 1.58h) | 3.16 (5 FA, 1.58h)* | 4.43 (7 FA, 1.58h)* | 7.59 (12 FA, 1.58h) |
| **F3_DUPL** | 1.56h | 3.21 (5 FA, 1.56h)* | 9.62 (15 FA, 1.56h) | 1.92 (3 FA, 1.56h)* | 1.28 (2 FA, 1.56h)* | 1.92 (3 FA, 1.56h)* |
| **F4_SPIKE** | 0.21h | 0.00 (0 FA, 0.21h)* | 0.00 (0 FA, 0.21h)* | 0.00 (0 FA, 0.21h)* | 4.84 (1 FA, 0.21h)* | 4.84 (1 FA, 0.21h)* |
| **F5_DRIFT** | 1.55h | 2.58 (4 FA, 1.55h)* | 6.46 (10 FA, 1.55h) | 1.94 (3 FA, 1.55h)* | 0.65 (1 FA, 1.55h)* | 1.94 (3 FA, 1.55h)* |
| **F6_UNIT** | 1.56h | 15.40 (24 FA, 1.56h) | 36.56 (57 FA, 1.56h) | 16.68 (26 FA, 1.56h) | 14.75 (23 FA, 1.56h) | 19.89 (31 FA, 1.56h) |

*(\*) Marked [Insufficient data: < 10 alerts or < 1.0h exposure].*

---

## 5. Pre-Specified Paired Statistical Comparison: Arm 3b vs Arm 3a

Every comparison presents per-subject event recall alongside Clean FA/hr, the difference ($\Delta = 3\text{b} - 3\text{a}$), Wilcoxon signed-rank test (two-sided, $\alpha = 0.05$), Hodges-Lehmann median difference estimator, and 95% subject-bootstrap confidence intervals.

### 5.1 Condition 0: No-Fault Clean Background
- **Pooled Recall:** Arm 3b = 79.5% vs Arm 3a = 80.4% ($\Delta = -0.9\%$)
- **Pooled Clean FA/hr:** Arm 3b = 1.69 vs Arm 3a = 1.47 ($\Delta = +0.22\text{ FA/hr}$)
- **Per-Subject Metrics (Recall % / Clean FA/hr):**
  - **S1:** 3b: 62.5% / 0.44 | 3a: 75.0% / 0.44 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = -12.5\%$
  - **S2:** 3b: 85.7% / 0.49 | 3a: 85.7% / 0.00 | $\Delta\text{FA/hr} = +0.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S3:** 3b: 80.0% / 0.00 | 3a: 80.0% / 0.00 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S4:** 3b: 85.7% / 0.44 | 3a: 85.7% / 0.87 | $\Delta\text{FA/hr} = -0.44$ | $\Delta\text{Rec} = +0.0\%$
  - **S5:** 3b: 100.0% / 1.26 | 3a: 100.0% / 3.78 | $\Delta\text{FA/hr} = -2.52$ | $\Delta\text{Rec} = +0.0\%$
  - **S6:** 3b: 100.0% / 9.96 | 3a: 100.0% / 10.79 | $\Delta\text{FA/hr} = -0.83$ | $\Delta\text{Rec} = +0.0\%$
  - **S7:** 3b: 83.3% / 3.33 | 3a: 83.3% / 1.67 | $\Delta\text{FA/hr} = +1.67$ | $\Delta\text{Rec} = +0.0\%$
  - **S8:** 3b: 57.1% / 0.48 | 3a: 57.1% / 1.45 | $\Delta\text{FA/hr} = -0.97$ | $\Delta\text{Rec} = +0.0\%$
  - **S9:** 3b: 77.8% / 1.43 | 3a: 77.8% / 1.43 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S10:** 3b: 70.0% / 0.00 | 3a: 70.0% / 0.76 | $\Delta\text{FA/hr} = -0.76$ | $\Delta\text{Rec} = +0.0\%$
  - **S11:** 3b: 90.0% / 2.37 | 3a: 90.0% / 2.85 | $\Delta\text{FA/hr} = -0.47$ | $\Delta\text{Rec} = +0.0\%$
  - **S12:** 3b: 80.0% / 0.98 | 3a: 80.0% / 0.49 | $\Delta\text{FA/hr} = +0.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S13:** 3b: 85.7% / 4.32 | 3a: 85.7% / 0.43 | $\Delta\text{FA/hr} = +3.89$ | $\Delta\text{Rec} = +0.0\%$
  - **S14:** 3b: 88.9% / 2.75 | 3a: 88.9% / 1.38 | $\Delta\text{FA/hr} = +1.38$ | $\Delta\text{Rec} = +0.0\%$
  - **S15:** 3b: 66.7% / 0.53 | 3a: 66.7% / 0.53 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
- **Statistical Tests:**
  - Mean Difference: $+0.13\text{ FA/hr}$
  - Median Difference: $+0.00\text{ FA/hr}$
  - Hodges-Lehmann Difference: $+0.00\text{ FA/hr}$
  - Wilcoxon Signed-Rank Test: $W = 31.0, p = 0.8589$
  - 95% Bootstrap CI on Mean Diff: $[-0.54, +0.89]\text{ FA/hr}$
  - 95% Bootstrap CI on HL Median: $[-0.48, +0.69]\text{ FA/hr}$
  - **Conclusion:** Not Statistically Significant ($p \ge 0.05$).

### 5.2 Regime A: Low Fault-Duty (~10%)
- **Pooled Recall:** Arm 3b = 79.5% vs Arm 3a = 80.4% ($\Delta = -0.9\%$)
- **Pooled Clean FA/hr:** Arm 3b = 1.82 vs Arm 3a = 1.63 ($\Delta = +0.19\text{ FA/hr}$)
- **Per-Subject Metrics (Recall % / Clean FA/hr):**
  - **S1:** 3b: 62.5% / 0.44 | 3a: 75.0% / 0.00 | $\Delta\text{FA/hr} = +0.44$ | $\Delta\text{Rec} = -12.5\%$
  - **S2:** 3b: 85.7% / 0.49 | 3a: 85.7% / 0.99 | $\Delta\text{FA/hr} = -0.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S3:** 3b: 80.0% / 0.47 | 3a: 80.0% / 0.47 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S4:** 3b: 85.7% / 0.87 | 3a: 85.7% / 1.31 | $\Delta\text{FA/hr} = -0.44$ | $\Delta\text{Rec} = +0.0\%$
  - **S5:** 3b: 100.0% / 3.15 | 3a: 100.0% / 5.05 | $\Delta\text{FA/hr} = -1.89$ | $\Delta\text{Rec} = +0.0\%$
  - **S6:** 3b: 100.0% / 8.30 | 3a: 100.0% / 10.79 | $\Delta\text{FA/hr} = -2.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S7:** 3b: 83.3% / 3.75 | 3a: 83.3% / 1.67 | $\Delta\text{FA/hr} = +2.08$ | $\Delta\text{Rec} = +0.0\%$
  - **S8:** 3b: 57.1% / 0.48 | 3a: 57.1% / 0.97 | $\Delta\text{FA/hr} = -0.48$ | $\Delta\text{Rec} = +0.0\%$
  - **S9:** 3b: 77.8% / 0.95 | 3a: 77.8% / 1.43 | $\Delta\text{FA/hr} = -0.48$ | $\Delta\text{Rec} = +0.0\%$
  - **S10:** 3b: 70.0% / 0.38 | 3a: 70.0% / 1.14 | $\Delta\text{FA/hr} = -0.76$ | $\Delta\text{Rec} = +0.0\%$
  - **S11:** 3b: 90.0% / 2.37 | 3a: 90.0% / 2.85 | $\Delta\text{FA/hr} = -0.47$ | $\Delta\text{Rec} = +0.0\%$
  - **S12:** 3b: 80.0% / 0.98 | 3a: 80.0% / 0.49 | $\Delta\text{FA/hr} = +0.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S13:** 3b: 85.7% / 4.32 | 3a: 85.7% / 0.86 | $\Delta\text{FA/hr} = +3.46$ | $\Delta\text{Rec} = +0.0\%$
  - **S14:** 3b: 88.9% / 2.75 | 3a: 88.9% / 0.92 | $\Delta\text{FA/hr} = +1.83$ | $\Delta\text{Rec} = +0.0\%$
  - **S15:** 3b: 66.7% / 0.53 | 3a: 66.7% / 0.53 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
- **Statistical Tests:**
  - Mean Difference: $+0.05\text{ FA/hr}$
  - Median Difference: $-0.44\text{ FA/hr}$
  - Hodges-Lehmann Difference: $-0.08\text{ FA/hr}$
  - Wilcoxon Signed-Rank Test: $W = 40.0, p = 0.7007$
  - 95% Bootstrap CI on Mean Diff: $[-0.66, +0.82]\text{ FA/hr}$
  - 95% Bootstrap CI on HL Median: $[-0.61, +0.79]\text{ FA/hr}$
  - **Conclusion:** Not Statistically Significant ($p \ge 0.05$).

### 5.3 Regime B: Nominal Fault-Duty (~25–30%)
- **Pooled Recall:** Arm 3b = 75.0% vs Arm 3a = 75.9% ($\Delta = -0.9\%$)
- **Pooled Clean FA/hr:** Arm 3b = 2.37 vs Arm 3a = 2.30 ($\Delta = +0.07\text{ FA/hr}$)
- **Per-Subject Metrics (Recall % / Clean FA/hr):**
  - **S1:** 3b: 62.5% / 1.31 | 3a: 75.0% / 0.44 | $\Delta\text{FA/hr} = +0.87$ | $\Delta\text{Rec} = -12.5\%$
  - **S2:** 3b: 85.7% / 1.98 | 3a: 85.7% / 0.99 | $\Delta\text{FA/hr} = +0.99$ | $\Delta\text{Rec} = +0.0\%$
  - **S3:** 3b: 80.0% / 0.47 | 3a: 80.0% / 1.42 | $\Delta\text{FA/hr} = -0.94$ | $\Delta\text{Rec} = +0.0\%$
  - **S4:** 3b: 71.4% / 1.31 | 3a: 71.4% / 2.18 | $\Delta\text{FA/hr} = -0.87$ | $\Delta\text{Rec} = +0.0\%$
  - **S5:** 3b: 100.0% / 3.78 | 3a: 100.0% / 4.41 | $\Delta\text{FA/hr} = -0.63$ | $\Delta\text{Rec} = +0.0\%$
  - **S6:** 3b: 100.0% / 8.30 | 3a: 100.0% / 11.62 | $\Delta\text{FA/hr} = -3.32$ | $\Delta\text{Rec} = +0.0\%$
  - **S7:** 3b: 66.7% / 4.16 | 3a: 66.7% / 2.91 | $\Delta\text{FA/hr} = +1.25$ | $\Delta\text{Rec} = +0.0\%$
  - **S8:** 3b: 42.9% / 1.93 | 3a: 42.9% / 1.93 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S9:** 3b: 66.7% / 0.95 | 3a: 66.7% / 1.43 | $\Delta\text{FA/hr} = -0.48$ | $\Delta\text{Rec} = +0.0\%$
  - **S10:** 3b: 70.0% / 0.76 | 3a: 70.0% / 2.27 | $\Delta\text{FA/hr} = -1.51$ | $\Delta\text{Rec} = +0.0\%$
  - **S11:** 3b: 90.0% / 2.37 | 3a: 90.0% / 3.80 | $\Delta\text{FA/hr} = -1.42$ | $\Delta\text{Rec} = +0.0\%$
  - **S12:** 3b: 80.0% / 1.47 | 3a: 80.0% / 0.49 | $\Delta\text{FA/hr} = +0.98$ | $\Delta\text{Rec} = +0.0\%$
  - **S13:** 3b: 71.4% / 4.75 | 3a: 71.4% / 1.73 | $\Delta\text{FA/hr} = +3.02$ | $\Delta\text{Rec} = +0.0\%$
  - **S14:** 3b: 88.9% / 3.67 | 3a: 88.9% / 2.75 | $\Delta\text{FA/hr} = +0.92$ | $\Delta\text{Rec} = +0.0\%$
  - **S15:** 3b: 66.7% / 1.06 | 3a: 66.7% / 0.53 | $\Delta\text{FA/hr} = +0.53$ | $\Delta\text{Rec} = +0.0\%$
- **Statistical Tests:**
  - Mean Difference: $-0.04\text{ FA/hr}$
  - Median Difference: $+0.00\text{ FA/hr}$
  - Hodges-Lehmann Difference: $-0.00\text{ FA/hr}$
  - Wilcoxon Signed-Rank Test: $W = 52.0, p = 0.9750$
  - 95% Bootstrap CI on Mean Diff: $[-0.78, +0.69]\text{ FA/hr}$
  - 95% Bootstrap CI on HL Median: $[-0.87, +0.87]\text{ FA/hr}$
  - **Conclusion:** Not Statistically Significant ($p \ge 0.05$).

### 5.4 F7 Condition: High-Motion Optical BVP Noise (SNR = +5 dB)
- **Pooled Recall:** Arm 3b = 58.0% vs Arm 3a = 64.3% ($\Delta = -6.3\%$)
- **Pooled Clean FA/hr:** Arm 3b = 1.28 vs Arm 3a = 1.57 ($\Delta = -0.29\text{ FA/hr}$)
- **Per-Subject Metrics (Recall % / Clean FA/hr):**
  - **S1:** 3b: 75.0% / 0.44 | 3a: 75.0% / 0.44 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S2:** 3b: 71.4% / 0.00 | 3a: 71.4% / 0.49 | $\Delta\text{FA/hr} = -0.49$ | $\Delta\text{Rec} = +0.0\%$
  - **S3:** 3b: 40.0% / 0.00 | 3a: 40.0% / 0.00 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S4:** 3b: 57.1% / 0.00 | 3a: 57.1% / 0.87 | $\Delta\text{FA/hr} = -0.87$ | $\Delta\text{Rec} = +0.0\%$
  - **S5:** 3b: 100.0% / 3.78 | 3a: 100.0% / 8.83 | $\Delta\text{FA/hr} = -5.05$ | $\Delta\text{Rec} = +0.0\%$
  - **S6:** 3b: 100.0% / 6.64 | 3a: 100.0% / 9.96 | $\Delta\text{FA/hr} = -3.32$ | $\Delta\text{Rec} = +0.0\%$
  - **S7:** 3b: 50.0% / 2.91 | 3a: 50.0% / 1.25 | $\Delta\text{FA/hr} = +1.67$ | $\Delta\text{Rec} = +0.0\%$
  - **S8:** 3b: 28.6% / 0.48 | 3a: 28.6% / 1.93 | $\Delta\text{FA/hr} = -1.45$ | $\Delta\text{Rec} = +0.0\%$
  - **S9:** 3b: 22.2% / 0.48 | 3a: 66.7% / 1.43 | $\Delta\text{FA/hr} = -0.95$ | $\Delta\text{Rec} = -44.4\%$
  - **S10:** 3b: 60.0% / 0.00 | 3a: 60.0% / 0.38 | $\Delta\text{FA/hr} = -0.38$ | $\Delta\text{Rec} = +0.0\%$
  - **S11:** 3b: 80.0% / 1.42 | 3a: 80.0% / 1.42 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
  - **S12:** 3b: 40.0% / 0.00 | 3a: 80.0% / 0.00 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = -40.0\%$
  - **S13:** 3b: 85.7% / 3.46 | 3a: 85.7% / 0.43 | $\Delta\text{FA/hr} = +3.02$ | $\Delta\text{Rec} = +0.0\%$
  - **S14:** 3b: 55.6% / 1.83 | 3a: 66.7% / 1.38 | $\Delta\text{FA/hr} = +0.46$ | $\Delta\text{Rec} = -11.1\%$
  - **S15:** 3b: 44.4% / 0.53 | 3a: 44.4% / 0.53 | $\Delta\text{FA/hr} = +0.00$ | $\Delta\text{Rec} = +0.0\%$
- **Statistical Tests:**
  - Mean Difference: $-0.49\text{ FA/hr}$
  - Median Difference: $+0.00\text{ FA/hr}$
  - Hodges-Lehmann Difference: $-0.25\text{ FA/hr}$
  - Wilcoxon Signed-Rank Test: $W = 17.0, p = 0.2845$
  - 95% Bootstrap CI on Mean Diff: $[-1.47, +0.38]\text{ FA/hr}$
  - 95% Bootstrap CI on HL Median: $[-1.43, +0.23]\text{ FA/hr}$
  - **Conclusion:** Not Statistically Significant ($p \ge 0.05$).

### 5.5 Detailed Analysis of F7 Subject-Level Heterogeneity (Post-Hoc Exploratory)
1. **Drivers of F7 Recall Degradation in Arm 3b:**
   - The pooled recall deficit in Arm 3b relative to Arm 3a ($58.0\%$ vs $64.3\%$, a $-6.3\text{ percentage point}$ drop) is driven almost entirely by **two specific subjects**:
     - **S9:** Recall falls by **$-44.4\text{ percentage points}$** (from $66.7\%$ in 3a down to $22.2\%$ in 3b).
     - **S12:** Recall falls by **$-40.0\text{ percentage points}$** (from $80.0\%$ in 3a down to $40.0\%$ in 3b).
     - In 11 of the remaining 13 subjects, Arm 3b and Arm 3a achieve identical recall.
   - Mechanism: Under optical corruption, the front-end spectral SQI drops sharply during true episodes in S9 and S12, driving $S_{\text{trust}}$ below $\theta_{\text{trust}} = 0.60$ even though wrist motion is low, thereby suppressing genuine alerts that Arm 3a's pure kinematic gate passes.
2. **Subject-Level Heterogeneity in False Alert Rates:**
   - **Where Arm 3b outperforms Arm 3a:** In subjects with severe motion artifact (the S5/S6/S11 stratum), the trust score gate blocks substantial false alerts that slip past the kinematic gate:
     - **S5:** $3.78\text{ FA/hr}$ (3b) vs $8.83\text{ FA/hr}$ (3a), a reduction of **$-5.05\text{ FA/hr}$** (recall 100% in both).
     - **S6:** $6.64\text{ FA/hr}$ (3b) vs $9.96\text{ FA/hr}$ (3a), a reduction of **$-3.32\text{ FA/hr}$** (recall 100% in both).
     - **S11:** Identical at $1.42\text{ FA/hr}$ (recall 80% in both).
   - **Where Arm 3a outperforms Arm 3b:** In other subjects, Arm 3a maintains a lower false alert rate:
     - **S7:** $2.91\text{ FA/hr}$ (3b) vs $1.25\text{ FA/hr}$ (3a), difference $+1.67\text{ FA/hr}$.
     - **S13:** $3.46\text{ FA/hr}$ (3b) vs $0.43\text{ FA/hr}$ (3a), difference $+3.02\text{ FA/hr}$.
     - **S14:** $1.83\text{ FA/hr}$ (3b) vs $1.38\text{ FA/hr}$ (3a), difference $+0.46\text{ FA/hr}$.
3. **Scientific Classification:**
   - **Crucial note:** All subgroup analyses and subject-level breakdowns (S9/S12 recall vulnerability, S5/S6 vs S7/S13/S14 divergence) are **strictly post-hoc exploratory**. They were not formulated as a priori hypotheses and must not be used to assert general superiority in specific patient subgroups without prospective validation.

---

## 6. Implementation of F7 (Tier 2 Optical BVP Noise)

### 6.1 Code Implementation and Exact Parameters
- **Noise Injection Function:** `FaultInjector.inject_noise`
- **Source File:** `vitasense/benchmarks/fault_injection.py` (lines 382–446)
- **Invocation Context:** `scripts/build_f7_cache.py` (`build_f7_cache_for_subject`, lines 57–63)
- **Input Signal:** Raw 64 Hz optical photoplethysmogram (`signal = data["signal"]["wrist"]["BVP"].flatten()`).
- **Parameters:**
  - `severity = FaultSeverity.MED` $\implies$ Target Signal-to-Noise Ratio: **$\text{SNR} = +5.0\text{ dB}$**.
  - `motion_acc`: Interpolated 64 Hz wrist 3D accelerometer magnitude (`np.repeat(np.linalg.norm(acc_32hz, axis=1), 2)[:len(bvp)]`).
- **Mathematical Formulation:**
  $$\sigma^2_{\text{noise}} = \frac{\sigma^2_{\text{clean}}}{10^{(\text{SNR}_{\text{dB}}/10)}} = \frac{\sigma^2_{\text{clean}}}{10^{0.5}} \approx \frac{\sigma^2_{\text{clean}}}{3.1623}$$
  $$\epsilon(t) \sim \mathcal{N}(0, \sigma^2_{\text{noise}})$$
  $$E_{\text{norm}}(t) = \frac{|\mathbf{a}(t)|}{\frac{1}{N}\sum_{\tau} |\mathbf{a}(\tau)| + 10^{-6}}$$
  $$BVP_{\text{corrupted}}(t) = BVP(t) + \epsilon(t) \cdot E_{\text{norm}}(t)$$
- **Motion Modulation Mechanism:**
  - The additive zero-mean Gaussian noise is scaled continuously sample-by-sample by the normalized 3D accelerometer magnitude ($E_{\text{norm}}(t)$).
- **Estimator Re-run:**
  - Estimator Class: `WristPPGHREstimator`
  - Source File: `vitasense/estimators/ppg_hr_estimator.py` (lines 20–30 in `scripts/build_f7_cache.py`), window length 8.0 s, step 2.0 s.
  - Generates derived heart rate estimates (`hr_ppg`), spectral signal quality index (`spectral_sqi`), and dominant frequency (`dominant_freq_hz`) across all 15 subjects.
- **Cache File Paths and Names:**
  - Cached flat in: `data/processed/{sid}_f7_ppg_cache.npz` (files: `S1_f7_ppg_cache.npz` through `S15_f7_ppg_cache.npz`).
  - Completely preserves the clean no-fault cache: `data/processed/{sid}_ppg_cache.npz`.

### 6.2 Correction of Erroneous Prior Report Descriptions
- **Correction 1 (Motion Gating vs Continuous Modulation):** An earlier draft report stated that F7 noise was *"injected during active motion epochs ($\text{ENMO} \ge 0.10g$)"*. **That description was incorrect.** In the actual code, there is no discrete ENMO thresholding or binary gating inside `FaultInjector.inject_noise`. Instead, Gaussian noise at target SNR $+5\text{ dB}$ is continuously multiplied across the entire session by normalized accelerometer magnitude $E_{\text{norm}}(t)$.
- **Correction 2 (Estimator Module Path):** The earlier draft report cited `vitasense/ppg/estimator.py`. **That path was incorrect.** The actual class used in cache generation is `WristPPGHREstimator` from `vitasense/estimators/ppg_hr_estimator.py`.
- **Correction 3 (Cache Directory Path):** An earlier mention referenced `data/processed/f7_cache/`. The cache files are stored directly in `data/processed/` with the `{sid}_f7_ppg_cache.npz` naming pattern.
- **Scientific Distinction:** F7 was evaluated strictly as a standalone condition to isolate front-end spectral estimator breakdown under optical noise. It **differs from a combined regime** where Tier 1 telemetry faults (F1–F6) and Tier 2 raw optical noise (F7) co-occur simultaneously.

---

## 7. Hyperparameter Selection and Edge-of-Grid Analysis

Hyperparameters were tuned inside the training folds of the 15 Leave-One-Subject-Out (LOSO) splits per Amendment 4. The pre-specified selection rule selects candidate parameter combinations achieving $\ge 85\%$ event recall on the pooled training set, breaking ties by minimizing false alerts per hour ($\text{FA/hr}$). If no parameter combination reaches $85\%$ recall, the fallback rule selects the point that maximizes training recall.

### 7.1 Fraction of Folds Selecting Candidate Grid Boundary Values

| Condition | Arm | Grid Dimension | Candidate Grid | Boundary Picked | Fold Fraction |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Condition 0 (No-Fault)** | Arm 1 (Fixed) | $\tau_{\text{pop}}$ (bpm) | $\{100, 110, 120, 125, 130\}$ | 100 (lower) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 30 (upper) | 100.0% (15/15) |
| | Arm 2 (Personal) | Multiplier $k$ | $\{2.0, 2.5, 3.0, 3.5, 4.0\}$ | 2.0 (lower) | 100.0% (15/15) |
| | | Shrinkage $\kappa$ (h) | $\{0.5, 1.0, 2.0\}$ | 2.0 (upper) | 93.3% (14/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 10 (lower) | 100.0% (15/15) |
| | Arm 3a (+Kinematic) | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.08 (upper) | 93.3% (14/15) |
| | | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.03 (lower) | 6.7% (1/15) |
| | Arm 3b (+Trust) | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.60 (lower) | 93.3% (14/15) |
| | | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.80 (upper) | 6.7% (1/15) |
| **Regime A (Low Duty ~10%)** | Arm 1 (Fixed) | $\tau_{\text{pop}}$ (bpm) | $\{100, 110, 120, 125, 130\}$ | 100 (lower) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 30 (upper) | 100.0% (15/15) |
| | Arm 2 (Personal) | Multiplier $k$ | $\{2.0, 2.5, 3.0, 3.5, 4.0\}$ | 2.0 (lower) | 100.0% (15/15) |
| | | Shrinkage $\kappa$ (h) | $\{0.5, 1.0, 2.0\}$ | 2.0 (upper) | 93.3% (14/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 10 (lower) | 100.0% (15/15) |
| | Arm 3a (+Kinematic) | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.08 (upper) | 93.3% (14/15) |
| | | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.03 (lower) | 6.7% (1/15) |
| | Arm 3b (+Trust) | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.60 (lower) | 93.3% (14/15) |
| | | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.80 (upper) | 6.7% (1/15) |
| **Regime B (Nominal ~25-30%)**| Arm 1 (Fixed) | $\tau_{\text{pop}}$ (bpm) | $\{100, 110, 120, 125, 130\}$ | 100 (lower) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 30 (upper) | 100.0% (15/15) |
| | Arm 2 (Personal) | Multiplier $k$ | $\{2.0, 2.5, 3.0, 3.5, 4.0\}$ | 2.0 (lower) | 100.0% (15/15) |
| | | Shrinkage $\kappa$ (h) | $\{0.5, 1.0, 2.0\}$ | 2.0 (upper) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 10 (lower) | 100.0% (15/15) |
| | Arm 3a (+Kinematic) | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.08 (upper) | 93.3% (14/15) |
| | | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.03 (lower) | 6.7% (1/15) |
| | Arm 3b (+Trust) | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.60 (lower) | 93.3% (14/15) |
| | | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.80 (upper) | 6.7% (1/15) |
| **F7 (High-Motion BVP Noise)**| Arm 1 (Fixed) | $\tau_{\text{pop}}$ (bpm) | $\{100, 110, 120, 125, 130\}$ | 100 (lower) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 30 (upper) | 100.0% (15/15) |
| | Arm 2 (Personal) | Multiplier $k$ | $\{2.0, 2.5, 3.0, 3.5, 4.0\}$ | 2.0 (lower) | 100.0% (15/15) |
| | | Shrinkage $\kappa$ (h) | $\{0.5, 1.0, 2.0\}$ | 2.0 (upper) | 100.0% (15/15) |
| | | Persistence $P$ (s) | $\{10, 20, 30\}$ | 10 (lower) | 100.0% (15/15) |
| | Arm 3a (+Kinematic) | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.08 (upper) | 100.0% (15/15) |
| | | $\theta_{\text{rest}}$ (g) | $\{0.03, 0.05, 0.08\}$ | 0.03 (lower) | 0.0% (0/15) |
| | Arm 3b (+Trust) | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.60 (lower) | 100.0% (15/15) |
| | | $\theta_{\text{trust}}$ | $\{0.60, 0.70, 0.80\}$ | 0.80 (upper) | 0.0% (0/15) |

### 7.2 Critical Finding: Arm 2 Never Reached 85% Recall
- **Arm 2 (Personal Baseline with Shrinkage) NEVER achieved the $\ge 85\%$ recall target on the pooled training set in ANY fold across ANY condition.**
- The maximum training recall attained by Arm 2 was $\approx 80.4\%$ (achieved at the boundary parameter $k = 2.0, P = 10\text{s}$).
- Consequently, the fallback selection rule (maximizing training recall) was triggered in **100% (15/15) of folds for Arm 2 across all conditions**, forcing the tuner to pick the lowest multiplier ($k = 2.0$) and shortest persistence ($P = 10\text{s}$) to avoid further recall degradation.
- When motion gating (Arm 3a) was added, training recall was inherently upper-bounded by Arm 2's recall ($80.4\%$). In 14 of 15 folds, the tuner selected the most permissive motion gate ($\theta_{\text{rest}} = 0.08g$) to preserve as much recall as possible.

---

## 8. Protocol Deviations and Post-Result Decisions

To maintain scientific integrity, this table catalogues every formal amendment, pipeline defect correction, and post-result hyperparameter or design decision strictly using commit hashes and dates copied from `git log --format="%h | %ci | %s"` and descriptions copied from the protocol text and CHANGELOG:

| Revision / Event | Commit Hash | Date (from git) | Description (copied from Protocol text & CHANGELOG) |
| :--- | :---: | :---: | :--- |
| **Protocol v1.0.0 (Freeze)** | `41eff1e` | 2026-10-18 19:28:01 +0530 | Initial frozen experimental protocol defining core hypotheses $H_1\text{--}H_3$, fault taxonomy F1–F7, and LOSO cross-validation. (Protocol CHANGELOG line 453). |
| **Amendment 1** | `75f10d4` (ratified `3b1f2f6`) | 2026-10-19 14:05:51 +0530 (ratified 14:56:41) | Activity-contextualized alert ground truth ($HR > \tau_i$ during rest only) to prevent benign exercise from being counted as false alert events; thresholds relabeled as design choices with sensitivity analysis following web fetch verification check. (Protocol CHANGELOG line 454). |
| **Implementation Correction** | `3a5ccc2`, `1dd80b2` | 2026-10-19 14:24:11 +0530, 14:48:31 +0530 | Corrected redundant `/64` accelerometer scaling (double division by 64 in `rerun_15_subjects.py` prototype) that disabled the kinematic filter; standardized window alignment to 8s window midpoint ($t = 2i+4$s); added dual physical unit checks (physical range $[-3, +3]g$ and median norm $[0.8, 1.2]g$). (Protocol CHANGELOG line 457). |
| **Amendment 2** | `3b1f2f6`, `696fd00` | 2026-10-19 14:56:41 +0530, 15:18:44 +0530 | Labelled-SYNTHETIC resting tachycardia injection protocol formulated after observing extreme sparsity in healthy subjects; Option (a) adopted as primary benchmark injection architecture into resting segments only with seed 42, tagging every episode SYNTHETIC to validate alert logic only; incorporates outlier handling rule (S5 dual reporting and minutes-based evaluation, S6/S11 sensitivity checks). (Protocol CHANGELOG line 455). |
| **Adaptive Ramp Deviation** | `e358bf1` (ratified `a0d682a`) | 2026-10-19 15:52:29 +0530 (ratified 16:25:29) | Independent uniform draws of 15s ramp rate and target peak HR violate the 105 bpm floor for low-baseline participants or the 135 bpm ceiling for high-baseline participants, so lower and upper ramp bounds were adaptively adjusted to baseline HR ($r_{\text{lo}} = \max(2.0, (105 - HR_{\text{base}})/15)$, $r_{\text{hi}} = \min(4.0, (135 - HR_{\text{base}})/15)$) with plateau clamping to $[105.0, 135.0]\text{ bpm}$. (Protocol Section 9, lines 381–389). |
| **Amendment 3** | `a0d682a` | 2026-10-19 16:25:29 +0530 | Alerting benchmark evaluation design: restated $H_1$ as estimation question with 95% bootstrap CI and exploratory label, full 15-subject LOSO evaluation, wrist-PPG HR input stream with real motion errors from Step 3a estimator, strict quarantine of ECG-derived $\tau_i$, inclusion of ablation arm 3b-noMotion, fault-window alerts counted as false alarms with disaggregated FA/hr reporting per fault type and no-fault, dual fault regimes (~10% and ~25–30%), and F7 raw BVP noise before estimator. (Protocol CHANGELOG line 458). |
| **Gap Enforcement Update** | `0bf4ca4` | 2026-10-19 17:01:22 +0530 | Updated synthetic injection audit figures to ratified 112 episodes and 20 clamped ceiling (from 115 episodes and 16 clamped); the 60 s gap enforcement fixed a cross-block gap bug found while implementing the unit test. (Protocol CHANGELOG line 459). |
| **Amendment 4 (Alert Emitter & Grid Widening)** | `cad4c7f`, `a9ce657`, `d55d432` | 2026-10-19 17:42:25 +0530, 17:46:25, 17:53:55 | Ratified alert-emission rule: persistence P in {10, 20, 30}s, refractory R = 60s across all arms (R=60s justified by 56 consecutive episodes starting within 120s of previous end); widened grids (tau in {100, 110, 120, 125, 130} bpm, k in {2.0, 2.5, 3.0, 3.5, 4.0}) adopted after observing edge-of-grid picks in preliminary run; documented that Arm 1 recall is inherently tied to synthetic peak HR distribution [105, 135] bpm. (Protocol CHANGELOG line 460). |
| **Fallback Selection Rule Execution for Arm 2** | `f92ca8d` | 2026-10-19 18:09:13 +0530 | If no candidate parameter setting achieves $\ge 85\%$ recall on the training folds, the harness automatically falls back to selecting the candidate that maximizes pooled training recall ($\theta^* = \arg\max_{\theta \in \Theta} \text{Recall}_{\text{train}}(\theta)$); Arm 2 never achieved $\ge 85\%$ recall on any training fold across any condition (maximum training recall achieved was $\approx 80.4\%$), invoking the fallback rule in 100% of folds. (Protocol Section 2, lines 430–432; Section 7.2, lines 342–346). |

---

## 9. Scientific Limitations & Threats to Validity

1. **Synthetic Alert Injection:**
   - Injected tachycardia episodes were synthetically added to the derived ambulatory wrist-PPG HR stream rather than occurring naturally. Consequently, absolute recall values are intrinsically tied to the synthetic injection distribution (plateau HRs sampled from 105–135 bpm).
2. **Small Cohort Size ($N = 15$):**
   - The PPG-DaLiA dataset comprises 15 healthy young individuals. The statistical power to detect small differences in false alert rates is limited ($N = 15$ pairs for Wilcoxon signed-rank test).
3. **Front-End Estimator Noise & Coupling:**
   - True motion artifacts introduce non-stationary bias into the Step 3a spectral peak PPG estimator. When injected tachycardia is mirrored onto a noisy estimator stream, downstream alerts interact directly with tracking failures.
4. **Edge-of-Grid Parameter Selections:**
   - As documented in Section 7, the hyperparameter tuning harness consistently selected boundary values ($\tau_{\text{pop}} = 100$, $k = 2.0$, $P = 10\text{s}$, $P = 30\text{s}$), indicating severe trade-offs between sensitivity and false alert suppression.
5. **Single Ambulatory Protocol:**
   - Results are derived solely from the 2.5-hour multimodal activity protocol of PPG-DaLiA (sitting, stairs, soccer, cycling, driving, lunch, table soccer). Generalizability to free-living 24/7 continuous monitoring remains unproven.

No claims beyond these empirical data are asserted.
