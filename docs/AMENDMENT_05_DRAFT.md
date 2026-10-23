# Protocol Amendment 5 (DRAFT - NOT RATIFIED)

**Document Version:** 0.1.0-DRAFT  
**Date:** 2026-10-22  
**Status:** DRAFT — NOT RATIFIED (Post Hoc Exploratory Analysis)  
**Applies To:** [docs/protocol.md](file:///d:/projects/health%20tracker/docs/protocol.md) Section 6 (Arm 4 Conformal Abstention Benchmark)

---

## 1. Context and Motivation

In the ratified research protocol (Protocol Amendments 1–4, finalized 2026-10-19), the benchmark evaluated five alerting arms:
- Arm 1: Fixed Population Threshold ($\tau_{\text{pop}}$)
- Arm 2: Personal Baseline with Shrinkage ($\tau_i(t) = \hat{\mu}_i(t) + k \cdot \hat{\sigma}_i(t)$)
- Arm 3a: Kinematic Gating ($\text{ENMO} \le \theta_{\text{rest}}$)
- Arm 3b: Multi-Signal Software Trust Score Gate ($S_{\text{trust}} \ge \theta_{\text{trust}}$)
- Arm 3b-noMotion: Trust Gate Ablation ($w_{\text{mot}} = 0$)

While Protocol Amendment 3 Section 6 specified the mathematical formulation for Arm 4 (Inductive Conformal Prediction & Multi-Attribute Trust Abstention), Arm 4 was not executed during the initial benchmark run that produced the primary findings for Arms 1–3b.

Following inspection of the primary results—specifically the finding that software trust scoring alone (Arm 3b-noMotion) failed to suppress motion-induced false alerts without kinematic gating—Arm 4 was implemented and evaluated post hoc to benchmark distribution-free selective alerting against heuristic gating.

---

## 2. Post Hoc Evaluation Notice

> [!WARNING]
> **Post Hoc Status:** Arm 4 was implemented and evaluated after inspection of benchmark results for Arms 1–3b. Consequently, all Arm 4 metrics are designated as **"added post hoc"** in all paper tables, figures, and results summaries. They must not be construed as pre-specified confirmatory findings.

---

## 3. Discrepancy in Miscoverage Parameter Grid ($\alpha$)

1. **Ratified Grid in Protocol Amendment 3:**
   - Protocol Amendment 3 Section 6.5 specified the candidate miscoverage grid as:
     $$\alpha \in \{0.05, 0.10\}$$
     corresponding to $95\%$ and $90\%$ nominal marginal coverage on resting segments.
2. **Post Hoc Grid Evaluation ($\alpha = 0.15$):**
   - In preliminary fold tuning, $\alpha \in \{0.05, 0.10\}$ resulted in wide conformal prediction bands that overlapped the alert threshold $\tau_i(t)$ across a large fraction of injected events, severely depressing event recall (below $55\%$).
   - To explore whether a less conservative coverage bound could preserve event sensitivity while retaining false alert suppression, an expanded parameter value of $\alpha = 0.15$ ($85\%$ nominal coverage) was evaluated post hoc.
   - This draft amendment explicitly documents that $\alpha = 0.15$ departs from the ratified $\{0.05, 0.10\}$ grid.

---

## 4. Parameter Selection and Tuning Specification

Arm 4 parameters were tuned strictly inside the training folds of the 15 Leave-One-Subject-Out (LOSO) splits:

### 4.1 Calibration Set Formulation
- For each test subject $S_i \in \{S_1, \dots, S_{15}\}$, the calibration set is formed from the pooled ambulatory recordings of the remaining 14 training subjects:
  $$\mathcal{D}_{\text{train}} = \bigcup_{j \neq i} \mathcal{D}_j$$
- Calibration windows are restricted to still segments where $\text{ENMO}_{10s} \le 0.05g$ and $\text{HR}$ is valid.
- For each candidate baseline pair $(k, \kappa)$, causal estimates $\hat{\mu}_j(t)$ and $\hat{\sigma}_j(t)$ are computed.
- The standardized nonconformity score for each calibration point is:
  $$s_j(t) = \frac{|\text{HR}_j(t) - \hat{\mu}_j(t)|}{\max(1.0, \hat{\sigma}_j(t))}$$
- The empirical $(1-\alpha)$ quantile $\hat{q}_{1-\alpha}$ is calculated as the $\lceil (n+1)(1-\alpha) \rceil / n$ quantile of $\{s_j(t)\}_{j \in \mathcal{D}_{\text{train}}}$.

### 4.2 Candidate Parameter Grid
The full candidate search space inside each LOSO training fold was:
- Multiplier $k \in \{2.0, 2.5, 3.0, 3.5, 4.0\}$
- Shrinkage time constant $\kappa \in \{0.5, 1.0, 2.0\}\text{ hours}$
- Miscoverage level $\alpha \in \{0.05, 0.10, 0.15\}$
- Trust uncertainty weight $\lambda_{\text{trust}} \in \{0.5, 1.0\}$
- Total uncertainty threshold $\theta_{\text{unc}} \in \{0.20, 0.30\}$
- Persistence filter $P \in \{10, 20, 30\}\text{ seconds}$
- Refractory hold-off fixed at $R = 60\text{ seconds}$

### 4.3 Abstention and Alert Emission Logic
At each evaluation window $t$:
1. Baseline threshold: $\tau_i(t) = \max(100.0, \hat{\mu}_i(t) + k \cdot \hat{\sigma}_i(t))$
2. Predictive uncertainty: $U(t) = \frac{\hat{\sigma}_i(t)}{\max(1.0, \hat{\mu}_i(t))}$
3. Augmented total uncertainty: $U_{\text{total}}(t) = U(t) + \lambda_{\text{trust}} \cdot (1.0 - S_{\text{trust}}(t))$
4. Conformal prediction interval: $\mathcal{C}(t) = [\hat{\mu}_i(t) - \hat{q}_{1-\alpha} \hat{\sigma}_i(t), \hat{\mu}_i(t) + \hat{q}_{1-\alpha} \hat{\sigma}_i(t)]$
5. Abstention rule:
   $$\text{Abstain}(t) \iff (\tau_i(t) \in \mathcal{C}(t)) \lor (U_{\text{total}}(t) > \theta_{\text{unc}})$$
6. Raw alert: $\text{RawAlert}(t) = (\text{HR}_i(t) > \tau_i(t)) \land \neg\text{Abstain}(t)$
7. Standard alert emission: $\text{Alert}(t) = \text{StandardAlertEmitter}(P, R=60\text{s})(\text{RawAlert}(t))$

### 4.4 Tuning and Fallback Rule
- As with Arms 1–3b, candidate parameters were selected by screening for $\ge 85\%$ event recall on the pooled training set, breaking ties by minimizing false alerts per hour ($\text{FA/hr}$).
- Because Arm 2's underlying baseline recall is intrinsically bounded at $\approx 80.4\%$ on training folds, Arm 4 never achieved $\ge 85\%$ training recall in any fold.
- The pre-specified fallback rule ($\arg\max \text{Recall}_{\text{train}}$) was therefore invoked in 100% (15/15) of folds across all conditions, selecting the boundary values that maximize training recall ($k = 2.0, P = 10\text{s}, \theta_{\text{unc}} = 0.30$).

---

## 5. Provenance and Script Reference

All Arm 4 evaluation metrics must be generated exclusively via:
- [scripts/run_arm4_evaluation.py](file:///d:/projects/health%20tracker/scripts/run_arm4_evaluation.py)
- Exported via [scripts/export_paper_data.py](file:///d:/projects/health%20tracker/scripts/export_paper_data.py) into `results/paper/combined_metrics.csv` and `paper/tables/tab_combined_metrics.tex`.
- No manual modifications to CSVs or `.tex` tables are permitted.
