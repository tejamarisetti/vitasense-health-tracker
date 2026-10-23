# Protocol Amendment 5 (DRAFT - NOT RATIFIED)

**Document Version:** 0.3.0-DRAFT  
**Date:** 2026-10-23  
**Status:** DRAFT — NOT RATIFIED (Implementation Timing Deviation Disclosure)  
**Applies To:** [docs/protocol.md](file:///d:/projects/health%20tracker/docs/protocol.md) Section 6 (Arm 4 Conformal Abstention Benchmark)

---

## 1. Context and Procedural Disclosure

In the ratified research protocol ([docs/protocol.md](file:///d:/projects/health%20tracker/docs/protocol.md), Amendment 3 Section 6, ratified 2026-10-19), Arm 4 (Inductive Conformal Prediction & Multi-Attribute Trust Abstention) was fully pre-specified:
- Architectural definition, deployment-only low-ENMO calibration set $\mathcal{T}_{\text{calib}}$, standardized nonconformity score $s(t)$, conformal interval $\mathcal{C}_{1-\alpha}(t)$, augmented uncertainty $U_{\text{total}}(t)$, and dual-condition abstention rule.
- Candidate hyperparameter grids: $\alpha \in \{0.05, 0.10\}$, $\lambda \in \{0.5, 1.0\}$, $\theta_{\text{unc}} \in \{0.20, 0.30\}$ (with persistence $P \in \{10, 20, 30\}\text{ s}$ and refractory $R = 60\text{ s}$ standardized in Amendment 4).

### Procedural Timing Deviation
While Arm 4's algorithm and parameter grids were pre-specified prior to benchmark execution in Amendment 3, its implementation and code execution were completed **after the results of Arms 1–3b across all conditions had been inspected**.

This draft amendment documents this timing deviation: Arm 4 is designated throughout the manuscript, tables, figures, and summaries as:
$$\text{"pre-specified in Amendment 3, implemented after the other arms' results were seen"}$$

---

## 2. Miscoverage Parameter Grid ($\alpha$) Truth

1. **Ratified Candidate Grid in Protocol Amendment 3 Section 6.5:**
   $$\alpha \in \{0.05, 0.10\}$$
   corresponding to $95\%$ and $90\%$ nominal marginal coverage on resting segments.
2. **Evaluation History and $\alpha = 0.15$ Clarification:**
   - $\alpha = 0.15$ was **NEVER** evaluated, selected, or present in the benchmark implementation (`vitasense/benchmarks/alerting_arms.py` and `scripts/run_arm4_evaluation.py`).
   - `git log -p -S "0.15"` on both files returns zero commits.
   - Any previous text in paper drafts or amendment notes suggesting $\alpha = 0.15$ was evaluated post hoc was factually erroneous.
3. **Selected Parameters Across LOSO Training Folds:**
   - Tuning across all 15 LOSO training folds selected $\alpha = 0.10$ (90% nominal coverage), $\lambda_{\text{trust}} = 0.5$, $\theta_{\text{unc}} = 0.30$, and persistence $P = 10\text{ s}$ in 100% of folds (with baseline multiplier $k = 2.0$ for 14 folds, and $k = 2.5, \kappa = 2.0\text{ h}$ for S5).

---

## 3. Parameter Specification: Tuned vs Fixed

Arm 4 parameters are partitioned strictly between fold-tuned hyperparameter grids and fixed architectural constants:

### 3.1 Fixed Parameters (Constant Across All Folds)
- **Refractory Period:** $R = 60\text{ seconds}$ (enforced across all alerting arms via `StandardAlertEmitter`).
- **Population Baseline Priors:** $\mu_{\text{pop}} = 75.0\text{ bpm}$, $\sigma_{\text{pop}} = 12.0\text{ bpm}$ (normative resting adult literature).
- **Hard Physiological Alert Floor:** $\tau_{\text{floor}} = 100.0\text{ bpm}$ (ensures tachycardia alert is never emitted below clinical resting floor).
- **Calibration Stillness Gate:** $\text{ENMO}_{10\text{s}} \le 0.05\text{ g}$ (restricts calibration nonconformity scoring strictly to deployment-available resting epochs).
- **Nonconformity Metric:** Standardized absolute residual $s_j(t) = \frac{|\text{HR}_j(t) - \hat{\mu}_j(t)|}{\max(1.0, \hat{\sigma}_j(t))}$.
- **Conformal Prediction Interval:** $\mathcal{C}_i(t) = [\hat{\mu}_i(t) - \hat{q}_{1-\alpha}\hat{\sigma}_i(t), \hat{\mu}_i(t) + \hat{q}_{1-\alpha}\hat{\sigma}_i(t)]$.
- **Predictive Normalized Uncertainty:** $U(t) = \frac{\hat{\sigma}_i(t)}{\max(1.0, \hat{\mu}_i(t))}$.
- **Augmented Uncertainty:** $U_{\text{total}}(t) = U(t) + \lambda_{\text{trust}} \cdot (1.0 - S_{\text{trust}}(t))$.

### 3.2 Parameters Tuned in LOSO Training Folds
For each held-out subject $S_i \in \{S_1, \dots, S_{15}\}$, the following 6 hyperparameters were tuned via grid search on the pooled remaining 14 training subjects $\mathcal{D}_{\text{train}} = \bigcup_{j \neq i} \mathcal{D}_j$:
1. **Baseline Multiplier ($k$):** $k \in \{2.0, 2.5, 3.0, 3.5, 4.0\}$
2. **Shrinkage Time Constant ($\kappa$):** $\kappa \in \{0.5, 1.0, 2.0\}\text{ hours}$
3. **Miscoverage Level ($\alpha$):** $\alpha \in \{0.05, 0.10\}$ (selected $\alpha = 0.10$ across all 15 folds)
4. **Trust Uncertainty Weight ($\lambda_{\text{trust}}$):** $\lambda_{\text{trust}} \in \{0.5, 1.0\}$
5. **Total Uncertainty Threshold ($\theta_{\text{unc}}$):** $\theta_{\text{unc}} \in \{0.20, 0.30\}$
6. **Persistence Filter ($P$):** $P \in \{10, 20, 30\}\text{ seconds}$

### 3.3 Abstention Rule & Tuning Fallback
At each evaluation time $t$:
- **Abstention Decision:**
  $$\text{Abstain}(t) \iff (\tau_i(t) \in \mathcal{C}_i(t)) \lor (U_{\text{total}}(t) > \theta_{\text{unc}})$$
- **Raw Trigger:**
  $$\text{RawAlert}(t) = (\text{HR}_i(t) > \tau_i(t)) \land \neg\text{Abstain}(t)$$
- **Alert Emission:**
  $$\text{Alert}(t) = \text{StandardAlertEmitter}(P, R=60\text{s})(\text{RawAlert}(t))$$
- **Fallback Rule Invocation:**
  - Optimization sought parameters achieving $\ge 85\%$ event recall on training folds while minimizing $\text{FA/hr}$.
  - Because Arm 2's base sensitivity on training folds peaked at $\approx 80.4\%$, Arm 4's selective abstention could not reach $\ge 85\%$ training recall in any fold.
  - Consequently, the pre-specified fallback rule ($\arg\max \text{Recall}_{\text{train}}$) was invoked in 100% (15/15) of folds across all conditions, selecting the least restrictive boundaries ($k = 2.0, P = 10\text{s}, \theta_{\text{unc}} = 0.30$).

---

## 4. Provenance and Script Reference

All Arm 4 evaluation metrics must be generated exclusively via:
- [scripts/run_arm4_evaluation.py](file:///d:/projects/health%20tracker/scripts/run_arm4_evaluation.py)
- Exported via [scripts/export_paper_data.py](file:///d:/projects/health%20tracker/scripts/export_paper_data.py) into `results/paper/combined_metrics.csv` and `paper/tables/tab_combined_metrics.tex`.
- No manual modifications to CSVs or `.tex` tables are permitted.
