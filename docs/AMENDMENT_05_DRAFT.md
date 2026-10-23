# Protocol Amendment 5 (DRAFT - NOT RATIFIED)

**Document Version:** 0.2.0-DRAFT  
**Date:** 2026-10-23  
**Status:** DRAFT — NOT RATIFIED (Post Hoc Exploratory Analysis)  
**Applies To:** [docs/protocol.md](file:///d:/projects/health%20tracker/docs/protocol.md) Section 6 (Arm 4 Conformal Abstention Benchmark)

---

## 1. Context and Motivation

In the ratified research protocol (Protocol Amendments 1–4, finalized 2026-10-19), the benchmark evaluated five alerting arms across four conditions:
- Arm 1: Fixed Population Threshold ($\tau_{\text{pop}}$)
- Arm 2: Personal Baseline with Shrinkage ($\tau_i(t) = \hat{\mu}_i(t) + k \cdot \hat{\sigma}_i(t)$)
- Arm 3a: Kinematic Gating ($\text{ENMO}_{10\text{s}} \le \theta_{\text{rest}}$)
- Arm 3b: Multi-Signal Software Trust Score Gate ($S_{\text{trust}} \ge \theta_{\text{trust}}$)
- Arm 3b-noMotion: Trust Gate Ablation ($w_{\text{mot}} = 0$)

While Protocol Amendment 3 Section 6 outlined the theoretical formulation for Arm 4 (Inductive Conformal Prediction & Multi-Attribute Trust Abstention), Arm 4 was not executed during the pre-specified benchmark run.

Instead, Arm 4 was implemented and evaluated post hoc **after all five arms and fault regimes had been run** and their results were reviewed. This post hoc investigation explored whether distribution-free selective prediction could offer principled abstention where heuristic software trust scoring had shown no statistically detectable incremental benefit.

---

## 2. Post Hoc Evaluation Notice

> [!WARNING]
> **Post Hoc Status:** Arm 4 was implemented and evaluated after all five arms and fault regimes had been run. Consequently, all Arm 4 metrics are designated as **"added post hoc"** in all paper tables, figures, and results summaries. They must not be construed as pre-specified confirmatory findings.

---

## 3. Discrepancy in Miscoverage Parameter Grid ($\alpha$)

1. **Ratified Grid in Protocol Amendment 3:**
   - Protocol Amendment 3 Section 6.5 specified the candidate miscoverage grid as:
     $$\alpha \in \{0.05, 0.10\}$$
     corresponding to $95\%$ and $90\%$ nominal marginal coverage on resting segments.
2. **Post Hoc Grid Evaluation ($\alpha = 0.15$):**
   - In preliminary fold tuning, the ratified grid values $\alpha \in \{0.05, 0.10\}$ produced wide conformal prediction intervals that overlapped the alerting threshold $\tau_i(t)$ during injected episodes, depressing event recall below $55\%$.
   - To investigate whether a less conservative coverage band could retain event sensitivity while suppressing false alerts, the miscoverage parameter was expanded post hoc to include $\alpha = 0.15$ ($85\%$ nominal marginal coverage).
   - **Crucially, $\alpha = 0.15$ is outside the ratified grid $\{0.05, 0.10\}$**. This unratified value was evaluated strictly as exploratory post hoc tuning.

---

## 4. Parameter Specification: Tuned vs Fixed

Arm 4 parameters were partitioned strictly between fold-tuned hyperparameter grids and fixed architectural constants:

### 4.1 Fixed Parameters (Constant Across All Folds)
- **Refractory Period:** $R = 60\text{ seconds}$ (enforced across all alerting arms via `StandardAlertEmitter`).
- **Population Baseline Priors:** $\mu_{\text{pop}} = 75.0\text{ bpm}$, $\sigma_{\text{pop}} = 12.0\text{ bpm}$ (derived from normative resting adult literature).
- **Hard Physiological Alert Floor:** $\tau_{\text{floor}} = 100.0\text{ bpm}$ (ensures tachycardia alert condition is never emitted below nominal clinical resting floor).
- **Calibration Stillness Gate:** $\text{ENMO}_{10\text{s}} \le 0.05\text{ g}$ (restricts calibration nonconformity scoring strictly to resting epochs).
- **Nonconformity Metric:** Standardized absolute residual $s_j(t) = \frac{|\text{HR}_j(t) - \hat{\mu}_j(t)|}{\max(1.0, \hat{\sigma}_j(t))}$.
- **Conformal Prediction Interval:** $\mathcal{C}_i(t) = [\hat{\mu}_i(t) - \hat{q}_{1-\alpha}\hat{\sigma}_i(t), \hat{\mu}_i(t) + \hat{q}_{1-\alpha}\hat{\sigma}_i(t)]$.
- **Predictive Normalized Uncertainty:** $U(t) = \frac{\hat{\sigma}_i(t)}{\max(1.0, \hat{\mu}_i(t))}$.
- **Augmented Uncertainty:** $U_{\text{total}}(t) = U(t) + \lambda_{\text{trust}} \cdot (1.0 - S_{\text{trust}}(t))$.

### 4.2 Parameters Tuned in LOSO Training Folds
For each held-out subject $S_i \in \{S_1, \dots, S_{15}\}$, the following 6 hyperparameters were tuned via grid search on the pooled remaining 14 training subjects $\mathcal{D}_{\text{train}} = \bigcup_{j \neq i} \mathcal{D}_j$:
1. **Baseline Multiplier ($k$):** $k \in \{2.0, 2.5, 3.0, 3.5, 4.0\}$
2. **Shrinkage Time Constant ($\kappa$):** $\kappa \in \{0.5, 1.0, 2.0\}\text{ hours}$
3. **Miscoverage Level ($\alpha$):** $\alpha \in \{0.05, 0.10, 0.15\}$ (noting $\alpha = 0.15$ is outside the ratified grid)
4. **Trust Uncertainty Weight ($\lambda_{\text{trust}}$):** $\lambda_{\text{trust}} \in \{0.5, 1.0\}$
5. **Total Uncertainty Threshold ($\theta_{\text{unc}}$):** $\theta_{\text{unc}} \in \{0.20, 0.30\}$
6. **Persistence Filter ($P$):** $P \in \{10, 20, 30\}\text{ seconds}$

### 4.3 Abstention Rule & Tuning Fallback
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

## 5. Provenance and Script Reference

All Arm 4 evaluation metrics must be generated exclusively via:
- [scripts/run_arm4_evaluation.py](file:///d:/projects/health%20tracker/scripts/run_arm4_evaluation.py)
- Exported via [scripts/export_paper_data.py](file:///d:/projects/health%20tracker/scripts/export_paper_data.py) into `results/paper/combined_metrics.csv` and `paper/tables/tab_combined_metrics.tex`.
- No manual modifications to CSVs or `.tex` tables are permitted.
