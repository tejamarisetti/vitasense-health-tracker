# VitaSense AI - Frozen Experimental Protocol
**Document Version:** 1.0.0 (FROZEN)  
**Date:** 2026-10-16  
**Status:** Protocol Frozen prior to wearable experiment execution.  
**Target Paper:** *"Quality-Gated, Uncertainty-Aware Personal Alerting for Wearable Health Data, with a Fault-Injection Benchmark"*

---

## 1. Scientific Objective and Core Hypotheses

The objective of this research is to evaluate whether a quality-gated, uncertainty-aware personal alerting framework can prevent false health alarms caused by wearable sensor artifacts and signal faults while preserving sensitivity to genuine physiological distress events.

### A Priori Hypotheses (Formulated Prior to Wearable Results)
- **$H_1$ (False Alert Reduction):** Incorporating a signal quality gate and conformal abstention (Arm 4) reduces false alerts per hour by $\ge 60\%$ relative to standard fixed-threshold alerting (Arm 1) and personalized alerting without quality gating (Arm 2) under realistic and synthetic sensor fault conditions, while maintaining recall $\ge 85\%$ on genuine alert events.
- **$H_2$ (Trust Score Calibration against Ground Truth):** The software trust score $S_{\text{trust}} \in [0, 1]$ negatively correlates with the true absolute measurement error $|HR_{\text{wrist}} - HR_{\text{ref, ECG}}|$ ($\text{Spearman's } \rho < -0.60$, $p < 0.001$). This validates the software checks as a faithful proxy of signal fidelity without asserting physical hardware calibration.
- **$H_3$ (Cold-Start Adaptation):** Empirical Bayes shrinkage of personal baselines toward population priors reduces detection delay during initial monitoring hours ($t < 2$ hours) by $\ge 25\%$ relative to un-regularized personal baselines.

---

## 2. Fault-Injection Benchmark Taxonomy

All injected faults are deterministically generated via seeded pseudo-random processes (seed = 42) and **strictly labelled `SYNTHETIC`** in all code structures, dataframes, logs, and visual figures.

| Fault ID | Category | Description | Severity Levels (Low / Medium / High) | Implementation Rule |
| :--- | :--- | :--- | :--- | :--- |
| **F1_GAPS** | Missing Gaps | Complete sensor packet loss (NaN / null). | Low: 5% drop rate ($T_{\text{gap}}=10\text{s}$)<br>Med: 15% drop rate ($T_{\text{gap}}=30\text{s}$)<br>High: 30% drop rate ($T_{\text{gap}}=120\text{s}$) | Contiguous blocks set to NaN. |
| **F2_STALE** | Frozen / Stale | Sensor hardware or buffer lockup; holds constant value. | Low: $15\text{s}$ freeze<br>Med: $30\text{s}$ freeze<br>High: $60\text{s}$ freeze | Repeat last valid reading across window; zero variance. |
| **F3_DUPL** | Duplicates | Transport layer packet replay or duplicated timestamps. | Low: 2% packets duplicated<br>Med: 5% packets duplicated<br>High: 15% packets duplicated | Injects duplicate records with identical timestamps or $\Delta t = 0$. |
| **F4_SPIKE** | Transient Spikes | Instantaneous motion impact or optical artifact ($\Delta \text{HR} \ge 35$ bpm). | Low: 1 spike / 15 min ($+35$ bpm)<br>Med: 1 spike / 5 min ($+50$ bpm)<br>High: 1 spike / 2 min ($+75$ bpm) | Single-sample or 2-sample impulsional deviation outside physiological bounds. |
| **F5_DRIFT** | Baseline Drift | Gradual baseline sensor shift due to temperature or loose band. | Low: $+0.05$ bpm/s ($60\text{s}$)<br>Med: $+0.15$ bpm/s ($60\text{s}$)<br>High: $+0.30$ bpm/s ($60\text{s}$) | Linear ramp function $x(t) = x_0(t) + \alpha t$. |
| **F6_UNIT** | Unit / Scale Error | Incorrect firmware unit conversion or telemetry scale factor. | Low: $\times 1.2$ or $\div 1.2$<br>Med: $\times 1.5$ or $\div 1.5$<br>High: $\times 60$ or $\div 60$ (Hz vs bpm) | Multiplicative scaling factor applied to signal block. |
| **F7_NOISE** | High-Motion Noise | Optical decoupling and motion artifact during physical exercise. | Low: $\text{SNR} = 15\text{ dB}$<br>Med: $\text{SNR} = 5\text{ dB}$<br>High: $\text{SNR} = -5\text{ dB}$ | Additive non-stationary noise correlated with 3D wrist accelerometer energy. |

### 2.1 Fault Injection Tiers and Signal Domains
To maintain rigorous scientific distinction between raw sensor acquisition faults and downstream processing anomalies, the benchmark defines two injection tiers:
1. **Tier 1: Derived Physiological Time Series (Ambulatory HR Stream):**
   - **Signal:** 0.5 Hz / 1.0 Hz heart rate time series.
   - **Evaluated Faults:** F1 (Missing Gaps), F2 (Frozen / Stale Sensor Lockup), F3 (Packet Duplicates), F4 (Transient Spikes, $+35 / +50 / +75$ bpm), F5 (Baseline Ramp Drift), F6 (Multiplicative Unit / Scale Factor Errors).
   - **Target Evaluation:** Quality gates, trust scoring, and uncertainty-aware alerting rules operating on telemetry streams.
2. **Tier 2: Raw Waveform Signals (Optical PPG and Triaxial Accelerometer):**
   - **Signal:** Raw 64 Hz wrist BVP (photoplethysmogram) and 32 Hz wrist triaxial accelerometer.
   - **Evaluated Faults:** F7 (High-Motion Non-Stationary Noise, SNR $+15\text{ dB}, +5\text{ dB}, -5\text{ dB}$ modulated by 3D wrist accelerometer energy), as well as F1 (raw optical packet loss) and F2 (sensor ADC lockup).
   - **Target Evaluation:** Front-end spectral PPG estimators and raw signal quality indices (SQI).

---

## 3. Ground Truth Definitions for Alert Events

### 3.1 PPG-DaLiA (UCI ID 495)
- **Reference Gold Standard:** Chest-worn RespiBAN device recording clinical ECG at 700 Hz. ECG R-peaks are extracted and validated to produce continuous reference heart rate $HR_{\text{ref}}(t)$.
- **Alert Event Ground Truth:**
  - An authentic tachycardia/exertion alert event occurs when $HR_{\text{ref}}(t) > \tau_i$ for at least $T_{\text{persist}} = 30$ contiguous seconds, where $\tau_i = \max(100\text{ bpm}, \mu_{i,\text{rest}} + 2.5\sigma_{i,\text{rest}})$.
  - Any alert emitted by the wrist system when $HR_{\text{ref}}(t) \le \tau_i$ is recorded as a **False Alert**.
  - Any failure to emit an alert within 60 seconds of a true event is recorded as a **Missed Alert (False Negative)**.

### 3.2 PhysioNet Wearable Stress & Exercise (1.0.1)
- **Ground Truth:** Protocol event tags (`tags.csv`) marking acute stress induction phases and structured aerobic/anaerobic exertion transitions versus baseline resting periods across 36 volunteers.

---

## 4. The Five Ablation Arms

1. **Arm 1: Fixed Threshold (Clinical Guideline Baseline)**
   - Alert triggers when raw wrist sensor reading exceeds fixed population threshold (e.g., $HR > 100\text{ bpm}$ or $HR > 120\text{ bpm}$).
   - No personalization, no signal quality checking, no uncertainty estimation.
2. **Arm 2: Personal Baseline with Cold-Start Shrinkage**
   - Alert triggers when reading exceeds personalized threshold $\tau_i(t) = \mu_i(t) + k \cdot \sigma_i(t)$.
   - Personal parameters are computed via Empirical Bayes shrinkage:
     $$\hat{\mu}_i(t) = \frac{N_i(t)}{N_i(t) + \kappa} \bar{x}_i(t) + \frac{\kappa}{N_i(t) + \kappa} \mu_{\text{pop}}$$
     where $\kappa$ controls shrinkage speed during cold-start.
3. **Arm 3a: Motion / Rest Gate Only (Kinematic Context Baseline)**
   - Suppresses alerts if concurrent wrist accelerometer dynamic energy indicates physical movement ($\overline{\text{ENMO}}_{10\text{s}}(t) > \theta_{\text{rest}}$).
   - Evaluates whether motion contextualization alone suffices without optical signal quality checking or uncertainty estimation.
4. **Arm 3b: + Full Quality Gate (Multi-Attribute Trust Score Gating)**
   - Evaluates multi-attribute Trust Score $S_{\text{trust}} \in [0, 1]$ based on signal quality indices (spectral SQI, continuity/gaps, flatline lockup, physiological bounds, and accelerometer motion energy).
   - If $S_{\text{trust}} < \theta_{\text{trust}}$ (e.g., 0.70), the alert is **gated (suppressed)**.
5. **Arm 4: + Uncertainty-Aware Abstention (Quality-Gated + Selective Prediction)**
   - Implements conformal prediction / uncertainty quantification.
   - If the predictive uncertainty $U(t)$ exceeds threshold $\theta_{\text{unc}}$ or the conformal interval covers both normal and alert regimes, the system outputs `"unable to assess"`.
   - Evaluates the explicit trade-off between decision coverage and false alert rate.

---

## 5. Metrics and Evaluation Protocol

- **False Alerts per Hour (FA/hr):** $\frac{\text{Total False Alerts}}{\text{Total Monitoring Hours}}$.
- **Detection Delay (seconds):** $t_{\text{alert}} - t_{\text{event\_onset}}$ for true events.
- **Coverage (%):** Percentage of time intervals with definitive output (not abstained).
- **Classification Metrics:** Precision, Recall (Sensitivity), Specificity, F1-Score, AUPRC, AUROC.
- **Cross-Validation Split:** **Leave-One-Subject-Out (LOSO) Cross-Validation** across all subjects (subject-wise split; zero inter-subject leakage).
- **Confidence Intervals:** 95% Bootstrap Confidence Intervals computed using 1,000 resamples on pooled out-of-fold predictions.

---

## 6. Software Trust-Score Validation Protocol (Component C Design)

To validate that the software trust score is an effective monitor of signal fidelity:
1. Align wrist-estimated heart rate $HR_{\text{wrist}}(t)$ with chest ECG reference $HR_{\text{ref}}(t)$.
2. Compute absolute measurement error: $E(t) = |HR_{\text{wrist}}(t) - HR_{\text{ref}}(t)|$.
3. **Score Decomposition and Comparison:**
   Evaluate the composite Trust Score $S_{\text{trust}}$ against two single-attribute baseline scores:
   - **(a) Wrist ACC-Energy-Only Score ($S_{\text{acc}}$):** Normalized linear kinematic penalty based strictly on wrist 3D accelerometer dynamic energy: $S_{\text{acc}} = \max(0, 1 - \text{ENMO}/\theta_{\text{severe}})$.
   - **(b) Spectral-SQI-Only Score ($S_{\text{sqi}}$):** Spectral purity ratio $Q$ of dominant cardiac peak power to total cardiac band power ($[0.7, 3.5]\text{ Hz}$).
4. **Statistical Correlation and Partial Correlation:**
   - Compute bivariate Pearson $r$ and Spearman $\rho$ between each score and absolute error $E(t)$.
   - Compute **partial Spearman correlation** $\rho_{\text{partial}}(S_{\text{trust}}, E \mid \text{Activity})$ controlling for the ground-truth physical activity label. This rigorously demonstrates whether the multi-attribute trust score provides independent explanatory information beyond crude macro-activity classification alone.
5. **Strict Leave-One-Subject-Out (LOSO) Parameter Tuning:**
   All parameters of the trust score (e.g., $\theta_{\text{trust}}$, weighting factors, bound penalties) are calibrated strictly on training subjects within each LOSO fold. Zero test-subject data is used to optimize trust score parameters.
6. Construct calibration plot: Bin $S_{\text{trust}}$ into deciles $[0.0-0.1, \dots, 0.9-1.0]$ and report mean absolute error (MAE) within each decile.
7. **Boundary Condition:** This test evaluates the software verification checks only and does not calibrate or certify the physical optical sensor hardware.

---

## 7. Protocol Freeze Enforcement

This protocol is frozen as of 2026-10-16. No modifications to hypotheses, metric definitions, or ablation arms may be made after viewing experimental results. Any post-hoc analyses must be explicitly noted as "exploratory" and recorded in `docs/protocol_amendments.md`.

### 7.1 Multi-Subject Verification Prerequisite
Wearable alerting experiments (Step 3b) will execute **only after all 15 subjects are verified** from the complete PPG-DaLiA archive. Any baseline or component evaluations computed on the current subset of 11 subjects are strictly designated and labeled **"interim, 11/15 subjects"**.

---

## 8. Protocol Amendments

### Amendment 1: Activity-Contextualized Alert Ground Truth
- **Date:** 2026-10-18 (Ratified by user, 2026-10-19)
- **Status:** Ratified by user, 2026-10-19 (formulated strictly *a priori* before any wearable alerting experiment or evaluation).
- **Affected Section:** Section 3.1 (PPG-DaLiA Alert Ground Truth).
- **Reason for Amendment:**
  In real-world free-living datasets such as PPG-DaLiA (UCI ID 495), participants engage in daily physical exertion including stair climbing, outdoor cycling, walking, and table soccer. Normal human physiology elevates heart rate above 100 bpm during physical exercise to meet metabolic demands (physiological exercise-induced sinus tachycardia).
  A naive, uncontextualized alerting rule ($HR > 100\text{ bpm}$) triggers continuous, spurious "alerts" throughout benign physical exercise. In clinical practice, wearable personal alerting systems target *unexpected* or *inappropriate* tachycardia occurring when the user is sedentary or at rest. Evaluating alerting algorithms without conditioning on motion context would improperly count benign exercise as true alert events and would unfairly penalize quality-gated suppression during movement as false negatives.
- **A Priori Ground Truth Definition:**
  An authentic **At-Rest Tachycardia Alert Event** ground truth is defined strictly by the joint fulfillment of physiological and kinematic criteria continuously for at least $T_{\text{persist}} = 30\text{ seconds}$:
  1. **Physiological Reference Criterion:**
     $$HR_{\text{ref, ECG}}(t) > \tau_i$$
     where $\tau_i = \max(100\text{ bpm}, \mu_{i,\text{rest}} + 2.5\sigma_{i,\text{rest}})$, computed directly from the chest ECG reference signal during authenticated resting/baseline intervals.
  2. **Kinematic Resting Context Criterion (Conjunctive Wording, Status: Ratified by user, 2026-10-19):**
     Wrist 3D accelerometer dynamic energy (Euclidean Norm Minus One, ENMO):
     $$\text{ENMO}(t) = \max\left(0, \sqrt{a_x^2(t) + a_y^2(t) + a_z^2(t)} - 1.0g\right)$$
     averaged over a 10-second moving window satisfies:
     $$\overline{\text{ENMO}}_{10\text{s}}(t) \le \theta_{\text{rest}} = 0.05g$$
     Where ground-truth protocol activity tags are present, the resting context criterion requires both conditions **conjunctively**:
     $$\text{Activity}(t) \in \{\text{BASELINE}, \text{DRIVING}, \text{LUNCH}, \text{WORKING}\} \quad \mathbf{AND} \quad \overline{\text{ENMO}}_{10\text{s}}(t) \le \theta_{\text{rest}}$$
     When activity tags are absent (e.g., unconstrained ambulatory deployment), the kinematic threshold $\overline{\text{ENMO}}_{10\text{s}}(t) \le \theta_{\text{rest}}$ serves as the sole resting detector.
- **Literature and Design Justifications:**
  - **Wrist Accelerometer Units (Citation: PPG-DaLiA `readme.pdf` Section III.2 & III.3):**
    - *Official Documentation:* Section heading `III.2. Data from Empatica E4` states: `"Data is provided in units of 1/64g."` (7 words). Section heading `III.3. Data synchronisation and labelling` specifies: `"Within SX.pkl, 'data' -> 'signal' -> 'wrist' -> 'ACC' includes the ACC-signal."`
    - *Implementation Verification:* In `SX.pkl`, the data has already been scaled from raw 1/64g integer counts to floating-point units of $g$ (range: $[-2.000, +1.984]g$, verified across all 15 subjects). Runtime checks enforce this range and a stationary median magnitude in $[0.8, 1.2]g$.
  - **$\tau_i \ge 100\text{ bpm}$ (Unverified via automated web fetch; treated as Design Choice):**
    - *Publisher Page Check:* Automated HTTP fetch of `https://doi.org/10.1016/j.jacc.2015.08.856` returned client-side JavaScript redirect / 403 Forbidden on the direct JACC page, preventing independent automated verification of text passages.
    - *Relabeling:* Classified as **unverified**. Treated strictly as an engineering **design choice with sensitivity analysis** across $\tau_i \in \{100, 110, 120\}\text{ bpm}$ or personalized $\mu_{i,\text{rest}} + k \cdot \sigma_{i,\text{rest}}$ ($k \in \{2.0, 2.5, 3.0\}$).
  - **$\mu_{i,\text{rest}} + 2.5\sigma_{i,\text{rest}}$ (Statistical Baseline):** Standard individual outlier detection threshold, corresponding to the upper $0.6\%$ tail ($p < 0.006$) of personal resting fluctuations under Gaussian assumptions, preventing alerts on normal baseline variability.
  - **$T_{\text{persist}}$ (Design Choice with Sensitivity Analysis):**
    - Engineering design choice with prescribed sensitivity analysis across $T_{\text{persist}} \in \{15, 30, 60\}\text{ seconds}$ (nominal baseline $30\text{s}$) to filter out instantaneous respiratory sinus arrhythmia and transient postural shifts before raising an alert.
  - **$\theta_{\text{rest}}$ (Unverified via automated web fetch; treated as Design Choice):**
    - *Publisher Page Check:* Automated HTTP fetch of `https://doi.org/10.1249/MSS.0000000000000289` (Hildebrand 2014) landed on publisher paywalled shell without the full text tables, preventing automated extraction of text quotes.
    - *Relabeling:* Classified as **unverified**. Treated strictly as an engineering **design choice with sensitivity analysis** across $\theta_{\text{rest}} \in \{0.03, 0.05, 0.10\}g$ (nominal baseline $0.05g$).
- **Honest Disclosure:**
  *S1 heart rate range, wrist accelerometer magnitude, and protocol activity labels were inspected prior to drafting this amendment.*
- **Scientific Integrity Guarantee:**
  No alerting algorithms or fault-injection models were evaluated prior to formulating this definition. All sensitivity analysis grids ($T_{\text{persist}} \in \{15, 30, 60\}\text{s}$; $\theta_{\text{rest}} \in \{0.03, 0.05, 0.10\}g$) are fixed strictly *a priori* before alerting ablations.

---

### Amendment 2: Labelled-SYNTHETIC Resting Tachycardia Injection Protocol
- **Date:** 2026-10-18 (Ratified by user, 2026-10-19)
- **Status:** Ratified by user, 2026-10-19.
- **Honest Disclosure:**
  *This amendment was drafted strictly after inspecting per-subject ground-truth event counts across the complete 15-subject PPG-DaLiA cohort (ground truth only, zero algorithm or model results). In the complete 15-subject cohort under the unified canonical implementation, natural resting tachycardia under Amendment 1 is observed in S5 (30 events, 36.5 min), S6 (5 events, 4.3 min), and S11 (2 events, 4.2 min) — with 2 additional brief episodes observed in S7 during un-filtered resting activity tags without kinematic gating. The remaining 11 to 12 subjects exhibit zero events. All natural events are reported descriptively only.*
  *Prevalence Sensitivity Grid Findings:* Across the full sensitivity grid ($\theta_{\text{rest}} \in \{0.03, 0.05, 0.10\}g$ and $T_{\text{persist}} \in \{15, 30, 60\}\text{s}$), total natural-event time across the 15 subjects ranges from 19.0 to 88.8 minutes (about 19 to 89 minutes), demonstrating that natural event totals and event counts are highly definition-dependent. Consequently, headline benchmark metrics (cross-subject precision, recall, detection delay, and F1) are computed strictly on injected synthetic events where event ground truth is deterministic and reproducible.
  *Subject S5 exhibits a **sustained elevated resting heart rate of unknown cause; ECG R-peaks verified clean** ($MAE = 0.06\text{ bpm}$, $r = 0.9999$ vs label array; $0.010\%$ RR outside 35–200 bpm). S5's data show ~90% of the entire monitoring session above $\tau_i$, meaning its Amendment 1 events represent one continuous elevated physiological state, not 30 independent alert episodes. Therefore, natural events cannot be treated as independent test samples, and LOSO cross-validation of alerting precision, recall, and detection delay on natural events is statistically undefined ($0/0$ across 11–12 of 15 folds).*
- **Two Injection Architectures (Trade-Off Analysis):**
  1. **Option (a): Injection into the Derived HR Series Only:**
     - *Mechanism:* Add synthetic tachycardia elevation profile $\Delta HR(t)$ directly to the 0.5–1.0 Hz ambulatory HR stream during resting segments ($\overline{\text{ENMO}}_{10\text{s}}(t) \le 0.05g$), mirrored identically in the reference ECG stream and the evaluated wrist HR stream.
     - *Scope Boundary:* **Option (a) tests the alert logic only, not the sensor acquisition or front-end extraction chain; the paper will claim nothing beyond alert logic validation.**
     - *Pros:* Mathematically transparent, deterministic, exact control of onset dynamics, instantaneous ground-truth synchronization, computationally light across extensive sensitivity sweeps.
     - *Cons:* Bypasses front-end optical pulse extraction and spectral peak tracking under acceleration; assumes the upstream estimator outputs an elevated estimate.
  2. **Option (b): Full-Chain Injection via Time-Warping Real BVP Segments:**
     - *Mechanism:* Extract resting optical BVP segments, time-warp (resample) the raw 64 Hz optical waveform by local dilation factor $\alpha(t) = HR_{\text{target}}(t) / HR_{\text{orig}}(t)$ so that systolic pulse rate accelerates to the target tachycardia HR, while keeping the concurrent 3D accelerometer stream completely unchanged (pure resting motion), and regenerate matching ECG R-peaks.
     - *Pros:* Fully exercises the entire algorithmic pipeline (raw BVP $\to$ spectral SQI $\to$ peak estimator $\to$ trust score $\to$ alerting gate); preserves realistic morphology, pulse amplitude, and dicrotic notch variations.
     - *Cons:* Substantially higher computational burden; time-warping optical waveforms can introduce spectral interpolation artifacts; risk of unnatural pulse morphology distortion.
  3. **Recommendation:**
     - **Adopt Option (a) as the primary benchmark architecture** for validating alerting ablation arms (Arms 1–4, personal baselines, quality gating, conformal abstention) to ensure rigorous, artifact-free mathematical reproducibility.
     - **Retain Option (b) as a targeted secondary validation probe** specifically for Component C front-end spectral estimator evaluation under rate acceleration.
- **Protocol Specifications (Fixed Prior to Results):**
  - **Random Seed:** Fixed deterministic seed (`seed = 42`) for event timing, duration jitter, and episode placement.
  - **Injection Domain:** Exclusively during verified resting periods ($\overline{\text{ENMO}}_{10\text{s}}(t) \le 0.05g$ and activity in `BASELINE`, `WORKING`, `LUNCH`, `DRIVING`).
  - **Subject-Independent Episode Parameters:**
     - Episode count: $N_{\text{tachy}} = 5\text{ to } 10$ episodes per subject.
     - Target peak HR: $HR_{\text{tachy}} \sim \mathcal{U}(105, 135)\text{ bpm}$.
     - Onset ramp rate: $+2\text{ to } +4\text{ bpm/s}$ over $15\text{s}$.
     - Sustained plateau: $T_{\text{event}} \in [45, 120]\text{ seconds}$.
     - Resolution: Exponential decay back to personal resting baseline over $20\text{s}$.
  - **Labelling:** All injected episodes are strictly labelled `is_synthetic: True`, `event_type: "SYNTHETIC_RESTING_TACHYCARDIA"`.
- **Evaluation Metrics:**
  - **Detection Delay, Precision, Recall:** Evaluated strictly on injected synthetic tachycardia events across all test folds.
  - **False Alerts per Hour (FA/hr):** Evaluated across all non-event time (natural background + fault-injected background) for every subject.

---

### Natural Event and Outlier Handling Rule (Ratified by user, 2026-10-19)
1. **Dual Reporting:** All alerting benchmark results (false alert rate, detection delay, F1) will be reported both **with S5** and **without S5** to preserve transparency regarding single-subject sensitivity.
2. **S5 Metrics Specification (Minutes Above Threshold):** Subject S5 is reported strictly in total minutes above threshold, not in event counts, because its events fragment one continuous elevated physiological state rather than representing discrete independent episodes.
3. **Sensitivity Checks for S6 and S11:** In addition to S5 dual reporting, sensitivity checks reporting performance **with and without S6 and S11** will be provided in the appendix/supplementary results.
4. **Sample Independence:** Natural events (from S5, S6, S7, S11) are never counted as independent test samples and are reported descriptively only in a dedicated observational summary.
5. **Primary Benchmark Metric:** Cross-subject precision and recall will be computed strictly on injected synthetic events.

---

### Amendment 3: Alerting Benchmark Evaluation Design, Leakage Enforcement, Conformal Calibration, and Synthetic Injection Parameter Reconciliation
- **Date:** 2026-10-19
- **Status:** **Ratified by user, 2026-10-19**.
- **Study Classification:** **Exploratory Study**. All statistical inferences, effect sizes, and p-values are pre-specified as an exploratory investigation of wearable alerting under synthetic fault injection and Option (a) rate elevation.
- **Reason for Amendment:**
  Establish non-negotiable architectural boundaries preventing data leakage into alerting ablation arms; specify the arm input stream as the real motion-corrupted wrist-PPG HR estimate from Step 3a; explicitly document the benchmark scope limitation (tests alert logic on noisy stream, not pulse sensing); quarantine ECG-derived $\tau_i$ and resting blocks strictly to harness placement and scoring; add ablation arm 3b-noMotion (trust score without motion); restate core hypothesis $H_1$ as an estimation question; count fault-window alerts as false alarms and disaggregate per fault type; rewrite Arm 4 conformal calibration to use strictly deployment-available signals (low-ENMO windows); freeze trust-score weights to `vitasense.quality.trust_score` v1.0.0; specify dual fault-duty regimes (~10% and ~25–30%); add F7 raw BVP noise before the estimator; adopt $T_{\text{gap}} = 60\text{s}$ with a post-ratification commit requirement; and establish reporting caveats for S5/S6 baseline clustering and jump-size stratification.

#### Section 1: Core Hypothesis Formulation, Attribution, and Ablation Arms
1. **Estimation-Based Hypothesis ($H_1$):**
   - The primary research question is formulated as an **estimation question**:
     $$\text{"What is the difference in False Alerts per Hour between Arm 3b and Arm 3a } (\Delta\text{FA/hr} = \text{FA/hr}_{\text{Arm 3b}} - \text{FA/hr}_{\text{Arm 3a}}), \text{ quantified with a 95\% subject-bootstrap confidence interval?"}$$
   - The previously stated targets ($\ge 60\%$ reduction in false alerts per hour relative to kinematic-only gating, and $\ge 85\%$ recall on genuine synthetic alert events) are explicitly maintained as **stated targets** (aspirational engineering and clinical design goals), **not as rigid pass/fail criteria**.
2. **ACC Signal Sharing and Attribution Note:**
   - Both Arm 3a (kinematic gate only) and Arm 3b (multi-attribute trust score gate) share the **exact same 3D wrist accelerometer (ACC) kinematic gating signal** ($\overline{\text{ENMO}}_{10\text{s}} \le \theta_{\text{rest}}$).
   - Therefore, the comparison between Arm 3b and Arm 3a directly isolates and tests **whether the software trust score $S_{\text{trust}}$ adds anything beyond motion** (kinematic gating alone).
3. **Ablation Arm "3b-noMotion":**
   - To dissect the independent contribution of non-kinematic trust score components, evaluate **Arm 3b-noMotion**: the multi-attribute trust score evaluated **without the motion term** ($S_{\text{trust, noMotion}} = S_{\text{gap}} \cdot S_{\text{stale}} \cdot S_{\text{phys}}$).
   - Comparing Arm 3b-noMotion against Arm 2 and Arm 3b directly isolates whether software quality attributes (missing gap detection, flatline/stale detection, and physiological jump bounds) provide false alert protection independent of accelerometer motion gating.
   - Arm 3b-noMotion is formally added to all headline metric reporting tables (FA/hr under no-fault, Regime A, Regime B, per-fault $F_1\text{--}F_7$, recall, and detection delay).
4. **Statistical Inference & Effect Sizes (Exploratory Study):**
   - Paired two-sided Wilcoxon signed-rank test on per-subject FA/hr between Arm 3b and Arm 3a evaluated at significance level $\alpha_{\text{stat}} = 0.05$.
   - Effect size reporting: Paired rank-biserial correlation $r_{\text{rb}}$ and Hodges-Lehmann median difference estimator.
   - Confidence intervals: 95% Subject-Level Bootstrap Confidence Intervals (1,000 resamples).
   - Labeled explicitly as exploratory.

#### Section 2: Subject Partitioning, LOSO Cross-Validation, and Reporting Strata
1. **Full 15-Subject LOSO Evaluation:**
   - All 15 PPG-DaLiA subjects ($S1$ through $S15$) are evaluated under Leave-One-Subject-Out (LOSO) cross-validation.
   - The previously proposed S1–S3 "development" role is **completely removed**.
   - Hyperparameter selection and threshold tuning are conducted **strictly inside the training folds** ($N-1$ subjects) of each LOSO split. Zero test-fold data is ever used for tuning.
2. **Stratified Reporting Strata:**
   - **All-15 Cohort:** All 15 subjects pooled.
   - **Without-S5 Cohort:** 14 subjects, excluding the sustained elevated baseline outlier S5.
   - **Outlier Disclosures:** S5, S6, and S11 reported separately in dedicated individual rows/disclosures.

#### Section 3: Rigorous False Alert and Natural Event Accounting
1. **False Alert Definition:**
   An emitted alert at time $t$ is defined as a **False Alert** if and only if:
   - $t$ falls outside every injected synthetic tachycardia episode window ($[t_{\text{start}}, t_{\text{end}}]$), **AND**
   - $t$ falls outside all natural Amendment 1 event windows expanded by a **$\pm 30\text{ s}$ temporal buffer** ($[t_{\text{nat\_start}} - 30\text{s}, t_{\text{nat\_end}} + 30\text{s}]$), preventing physiological transition delays or boundary jitter from being counted as false alarms.
2. **Alerts Inside Fault Windows Counted as False Alerts (Not Excluded):**
   - Alerts triggered inside synthetic fault windows ($F_1\text{--}F_7$) outside of injected episodes and natural events **ARE COUNTED AS FALSE ALERTS (THEY ARE NOT EXCLUDED)**.
   - Evaluating whether sensor corruption and motion artifacts provoke false alarms is a primary benchmark objective.
3. **Disaggregated FA/hr Reporting:**
   - Report FA/hr for the **No-Fault Baseline (Condition 0)**.
   - Report FA/hr disaggregated **per fault type** ($F_1\text{ through } F_7$).
   - Report overall aggregate FA/hr under the complete fault schedule.
4. **Natural Event Accounting:**
   - Alerts emitted during natural Amendment 1 event windows (or their $\pm 30\text{s}$ buffers) are tracked and **reported separately as a distinct natural alert count/rate**.
   - Natural alerts are strictly excluded from the clean false alert count and do not enter the FA/hr denominator.
5. **Metric Formulas:**
   - $\text{FA/hr} = \frac{\text{Clean False Alerts}}{\text{Total Evaluated Non-Event Hours}}$.
   - Non-event time excludes both injected synthetic episodes and natural events ($\pm 30\text{s}$).

#### Section 4: Strict Leakage Enforcement Rule & Arm Input Stream Specification
1. **Arm Input Stream Specification (Step 3a Wrist-PPG Estimator):**
   - The primary heart rate time series fed into all alerting arms (Arms 1 through 4) is the **wrist-PPG heart rate estimate $HR_{\text{ppg}}(t)$ from the Step 3a estimator (`WristPPGHREstimator`) operating on raw wrist 64 Hz optical BVP and 32 Hz triaxial ACC**.
   - This stream inherently contains real optical motion artifacts, spectral peak tracking errors, and physiologic estimate noise.
   - The clean reference ECG label stream (`data['label']`) is **strictly quarantined** and is never provided as an arm input.
2. **Synthetic Tachycardia Mirroring:**
   - For every injected synthetic episode $k$, the rate elevation profile $\Delta HR_k(t) = HR_{\text{synth},k}(t) - HR_{\text{base},k}$ generated by `SyntheticTachycardiaInjector` (computed during verified resting periods) is mirrored directly into the wrist-PPG estimate stream:
     $$HR_{\text{eval}}(t) = HR_{\text{ppg}}(t) + \Delta HR_k(t) \quad \text{for } t \in [t_{\text{start},k}, t_{\text{end},k}]$$
   - This superimposes the deterministic rate acceleration directly onto the real-world baseline and motion-corrupted estimator noise without artificial smoothing.
3. **Scope Limitation Disclosure:**
   - Because synthetic tachycardia $\Delta HR(t)$ is added directly to the derived wrist-PPG heart rate estimate, **this benchmark tests alert decision logic on a realistic noisy stream, not the optical sensor's physical or front-end ability to detect an increased pulse rate from raw waveforms**.
4. **Strict Quarantine of ECG-Derived Thresholds and Placement Variables:**
   - The personal baseline threshold $\tau_i$ (computed from the ECG label stream during `BASELINE`) and the clean-resting-block selection mask (`is_resting`) are used **strictly and exclusively by the benchmark test harness for injector placement and for scoring**.
   - Evaluated alerting arms **NEVER receive $\tau_i$ or the resting mask**. If an arm requires a personal baseline (e.g. Arm 2, Arm 3, Arm 4), it must compute its own threshold from its permitted input stream.
5. **Scoring Window Rule:**
   - Event detection scoring (True Positives, False Negatives, recall, and detection delay) uses **injected-episode times only** ($[t_{\text{start},k}, t_{\text{end},k}]$).
6. **Prohibited Inputs:** Alerting arms must **NEVER** receive or inspect:
   - The synthetic injector's resting mask (`is_resting`).
   - Ground-truth protocol activity tags (`activity` / `act_aligned`).
   - Ground-truth event indicators, onset times, or durations (`synthetic_mask`, `event_type`, `InjectedEpisode`).
   - ECG reference label arrays (`label`) or ECG-derived personal thresholds ($\tau_i$).
7. **Activity Label Role:** Protocol activity labels are strictly restricted to ground-truth performance evaluation and scoring; they may **NEVER** serve as an arm input, feature, or conditioning variable.

#### Section 5: Deterministic Fault-Injection Schedule, Dual-Duty Regimes, and F7 Optical Noise
All injected faults are seeded deterministically (`seed = 42`), specified before any run, and applied strictly to non-event background monitoring time:
1. **Condition 0 (Clean Baseline / No-Fault):** Real-world ambulatory signal with zero injected faults.
2. **Dual Fault-Duty Regimes across Background Non-Event Time (Both Reported):**
   - **Regime A: Low Fault-Duty Condition (~10% total faulted background time):**
     - $F_1$ (Missing Gaps): Contiguous NaN blocks, length $T_{\text{gap}} = 30\text{s}$, duty cycle = 3% of non-event time.
     - $F_2$ (Frozen / Stale): Zero-variance constant value, length $T_{\text{freeze}} = 30\text{s}$, duty cycle = 2% of non-event time.
     - $F_3$ (Duplicates): Duplicated packets ($\Delta t = 0$), duty cycle = 2% of packets.
     - $F_4$ (Transient Spikes): Impulsive $+50\text{ bpm}$ spike lasting 1 sample ($2\text{s}$), rate = 1 spike per 15 minutes ($0.0011\text{ Hz}$).
     - $F_5$ (Baseline Drift): Linear ramp $+0.15\text{ bpm/s}$ sustained over $60\text{s}$ (maximum $+9\text{ bpm}$), duty cycle = 1.5% of non-event time.
     - $F_6$ (Unit / Scale Error): Multiplicative scale factor $\times 1.5$ applied to $60\text{s}$ blocks, duty cycle = 1.5% of non-event time.
     - Total faulted background time: $\approx 10.0\%$.
   - **Regime B: Nominal / Standard Fault-Duty Condition (~25–30% total faulted background time):**
     - $F_1$ (Missing Gaps): Contiguous NaN blocks, length $T_{\text{gap}} = 30\text{s}$, duty cycle = 10% of non-event time.
     - $F_2$ (Frozen / Stale): Zero-variance constant value repeating previous estimate, length $T_{\text{freeze}} = 30\text{s}$, duty cycle = 5% of non-event time.
     - $F_3$ (Duplicates): Duplicated packets ($\Delta t = 0$), duty cycle = 5% of packets.
     - $F_4$ (Transient Spikes): Impulsive $+50\text{ bpm}$ spike lasting 1 sample ($2\text{s}$), rate = 1 spike per 5 minutes ($0.0033\text{ Hz}$).
     - $F_5$ (Baseline Drift): Linear ramp $+0.15\text{ bpm/s}$ sustained over $60\text{s}$ (maximum $+9\text{ bpm}$), duty cycle = 5% of non-event time.
     - $F_6$ (Unit / Scale Error): Multiplicative scale factor $\times 1.5$ applied to $60\text{s}$ blocks, duty cycle = 5% of non-event time.
     - Total faulted background time: $\approx 25\text{--}30\%$.
   - **Reporting Requirement:** Benchmark results will report false alert rates ($\text{FA/hr}$) under **both** Regime A (Low Fault-Duty) and Regime B (Nominal Fault-Duty), alongside Condition 0 (No-Fault).
3. **F7 (High-Motion Optical BVP Noise):**
   - Applied directly to the **raw 64 Hz optical BVP stream before the Step 3a `WristPPGHREstimator`**.
   - Additive colored in-band noise modulated by wrist ACC dynamic energy, matching `vitasense.benchmarks.fault_injection.FaultInjector.inject_noise()`.
   - Applied across three standardized SNR levels:
     - Low Severity: $\text{SNR} = +15\text{ dB}$
     - Med Severity: $\text{SNR} = +5\text{ dB}$
     - High Severity: $\text{SNR} = -5\text{ dB}$
   - The corrupted BVP is processed through the 4th-order Butterworth bandpass filter and periodogram peak tracker to generate degraded $HR_{\text{ppg}}(t)$ and spectral SQI $Q(t)$, which then feed into the alerting arms.
   - Arm performance (FA/hr, recall, detection delay) will be reported across these SNR levels.
4. **Fault Overlap Rule:**
   - In the primary benchmark, faults are injected exclusively into **non-event background time**.
   - Faults **NEVER overlap active synthetic tachycardia episodes**, ensuring detection delay and recall reflect genuine event physics without artificial distortion.
5. **Pre-Run Fixation:** The fault schedule (timing, indices, values) is generated and frozen prior to executing any alerting algorithm.

#### Section 6: Trust-Score Weight Specification, Conformal Calibration Protocol, and Hyperparameter Grids (Arm 4)
1. **Fixed Trust-Score Weights and Combination Rule:**
   - The mathematical penalty functions, sub-score weights ($S_{\text{gap}}, S_{\text{stale}}, S_{\text{phys}}, S_{\text{motion}}$), and multiplicative combination rule ($S_{\text{trust}} = S_{\text{gap}} \cdot S_{\text{stale}} \cdot S_{\text{phys}} \cdot S_{\text{motion}}$) are **strictly fixed prior to evaluation** as implemented in `vitasense.quality.trust_score.RuleBasedTrustScorer` (Module Version 1.0.0, frozen in Protocol Sections 4 and 6).
   - They are **NOT tuned, optimized, or learned inside LOSO folds**.
   - The only parameter selected via LOSO cross-validation inside training folds is the decision gate threshold $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$.
2. **Concrete Predictive Uncertainty Metric:**
   - For each window $t$, the personal baseline model estimates predictive mean $\hat{\mu}_i(t)$ and standard deviation $\hat{\sigma}_i(t)$ via Empirical Bayes shrinkage towards the population mean across training folds.
   - Normalized predictive uncertainty: $U(t) = \frac{\hat{\sigma}_i(t)}{\hat{\mu}_i(t)}$.
   - Augmented uncertainty metric incorporating trust score defect:
     $$U_{\text{total}}(t) = U(t) + \lambda (1 - S_{\text{trust}}(t))$$
     where $\lambda \ge 0$ is the trust penalty weight.
3. **Deployment-Only Conformal Calibration Protocol:**
   - The calibration set $\mathcal{T}_{\text{calib}}$ is formed strictly from **deployment-available signals** in the $N-1$ training folds:
     $$\mathcal{T}_{\text{calib}} = \left\{ t \in \text{training folds} : \overline{\text{ENMO}}_{10\text{s}}(t) \le \theta_{\text{rest}} \text{ and } HR_{\text{ppg}}(t) \text{ is valid (non-NaN)} \right\}$$
   - Prohibited: Calibration **never** uses ground-truth protocol activity tags (`activity`), nor does it inspect the injector's resting mask (`is_resting`) or event timestamps. It operates strictly on signals accessible in real-world deployment.
   - Nonconformity score: normalized absolute residual on calibration windows:
     $$s(t) = \frac{|HR_{\text{ppg}}(t) - \hat{\mu}_i(t)|}{\hat{\sigma}_i(t)}$$
   - Conformal threshold: compute $(1 - \alpha)$-quantile $\hat{q}_{1-\alpha}$ on calibration scores:
     $$\hat{q}_{1-\alpha} = \text{Quantile}_{1-\alpha}\left(\{s(t) : t \in \mathcal{T}_{\text{calib}}\}\right)$$
   - Conformal prediction band:
     $$\mathcal{C}_{1-\alpha}(t) = \left[\hat{\mu}_i(t) - \hat{q}_{1-\alpha}\hat{\sigma}_i(t), \; \hat{\mu}_i(t) + \hat{q}_{1-\alpha}\hat{\sigma}_i(t)\right]$$
4. **Abstention Decision Rule:**
   - The system outputs `"ABSTAIN / UNABLE TO ASSESS"` if:
     a) The conformal prediction band spans the alert threshold: $\hat{\mu}_i(t) - \hat{q}_{1-\alpha}\hat{\sigma}_i(t) \le \tau_i(t) \le \hat{\mu}_i(t) + \hat{q}_{1-\alpha}\hat{\sigma}_i(t)$, OR
     b) Augmented uncertainty $U_{\text{total}}(t) > \theta_{\text{unc}}$.
5. **Pre-Specified Candidate Grids (Undefined Entries Removed):**
   - Any informal, heuristic, or undefined candidate grid dimensions from earlier discussions are explicitly removed.
   - **Arm 1 (Fixed Threshold):** $\tau_{\text{pop}} \in \{100, 110, 120\}\text{ bpm}$.
   - **Arm 2 (Personal Baseline with Shrinkage):** Outlier multiplier $k \in \{2.0, 2.5, 3.0\}$; shrinkage strength $\kappa \in \{0.5, 1.0, 2.0\}\text{ hours}$.
   - **Arm 3a (Kinematic Gate Only):** Motion rest threshold $\theta_{\text{rest}} \in \{0.03, 0.05, 0.08\}g$ (nominal $0.05g$).
   - **Arm 3b (Multi-Attribute Trust Score Gate):** Trust gate threshold $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$.
   - **Arm 3b-noMotion (Trust Gate without Motion):** $S_{\text{trust, noMotion}} \ge \theta_{\text{trust}}$ with $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$.
   - **Arm 4 (Conformal Abstention):** Miscoverage significance $\alpha \in \{0.05, 0.10\}$; trust penalty weight $\lambda \in \{0.5, 1.0\}$; uncertainty threshold $\theta_{\text{unc}} \in \{0.20, 0.30\}$.

#### Section 7: Inter-Episode Gap Specification and Post-Ratification Implementation Requirement
1. **Adoption of $T_{\text{gap}} = 60\text{s}$:**
   - Adopt minimum inter-episode gap $T_{\text{gap}} = 60\text{ seconds}$ in Amendment 3.
2. **Exact Episode Impact Across Cohort (3 Episodes Lost):**
   - **Subject S5 (582s block):** Drops from 5 episodes to 4 episodes (1 episode lost: Episode #5 at $t = 552\text{s}$).
   - **Subject S6 (634s block):** Drops from 6 episodes to 4 episodes (2 episodes lost: Episode #5 at $t = 494\text{s}$ and Episode #6 at $t = 594\text{s}$).
   - **Subjects S1–S4, S7–S15 (13 subjects):** 0 episodes lost.
   - **Cohort Total:** Drops from 115 episodes to 112 episodes.
3. **Post-Ratification Implementation Requirement:**
   - **Mandatory Post-Ratification Commit:** Immediately following ratification of Amendment 3, a dedicated commit must:
     a) Update `min_inter_event_gap_sec = 60.0` in `SyntheticTachycardiaInjector` (`vitasense/benchmarks/synthetic_alert_injection.py`).
     b) Add a dedicated unit test in `tests/test_synthetic_alert_injection.py` asserting that the minimum inter-episode gap between every pair of consecutive injected episodes across all 15 subjects is $\ge 60.0\text{ seconds}$.
     c) Re-generate and commit the updated 112-episode audit CSV files (`docs/synthetic_injection_audit.csv` and `results/synthetic_injection_audit.csv`).

#### Section 8: S5/S6 Baseline-Only Caveat & Jump-Size Stratification
1. **S5 and S6 Initial Baseline Clustering Caveat:**
   - In subjects S5 and S6, **100% of injected synthetic episodes lie exclusively within the initial `BASELINE` protocol block ($t < 600\text{s}$)**.
   - Performance metrics for S5 and S6 must be reported separately in dedicated rows and must **never be pooled into cross-subject summary aggregates without that explicit caveat**.
2. **Jump-Size Stratification:**
   In addition to aggregate metrics, report recall and detection delay stratified by physiological jump size ($\Delta HR = HR_{\text{peak}} - \mu_{i,\text{rest}}$):
   - *Small Jump ($+15\text{ to } +30\text{ bpm}$ above baseline)*: subtle resting elevation.
   - *Moderate Jump ($+30\text{ to } +50\text{ bpm}$ above baseline)*: typical clinical tachycardia onset.
   - *Large Jump ($> +50\text{ bpm}$ above baseline)*: acute resting surge.

#### Section 9: Synthetic Injection Parameter Reconciliation (Deviation from Ratified Amendment 2)
1. **Explicit Statement of Protocol Deviation:**
   - The adaptive ramp bounding rule implemented in `SyntheticTachycardiaInjector` **deviates from Amendment 2 as ratified**.
   - In ratified Amendment 2, onset ramp rate ($+2.0\text{ to } +4.0\text{ bpm/s}$ over $15\text{s}$) and target peak HR ($105.0\text{ to } 135.0\text{ bpm}$) were specified as independent uniform draws. However, over a fixed 15-second ramp, $\Delta HR = r_{\text{ramp}} \times 15\text{s} \in [30.0, 60.0]\text{ bpm}$. For participants with baseline HR below 75 bpm (e.g., S12 at 45 bpm), an independent draw of $r = 2.0\text{ bpm/s}$ yields a peak of only 75 bpm (violating the 105 bpm floor). For participants with baseline HR above 75 bpm (e.g., S5 at 93 bpm), an independent draw of $r = 4.0\text{ bpm/s}$ yields a peak of 153 bpm (violating the 135 bpm ceiling).
2. **Adaptive Rule & Rationale (Ratified in Amendment 3):**
   - Lower ramp bound is adaptively raised to $r_{\text{lo}} = \max(2.0, (105 - HR_{\text{base}})/15)$.
   - Upper ramp bound is adaptively lowered to $r_{\text{hi}} = \min(4.0, (135 - HR_{\text{base}})/15)$.
   - Plateau Ceiling & Floor Clamping: Values during the plateau exceeding 135.0 bpm due to baseline variability are clamped at 135.0 bpm; values below 105.0 bpm are clamped at 105.0 bpm.
   - Plateau Sampling Range Bounding: In short blocks (S5: 582s; S6: 634s), plateau sampling is bounded to ~45–62s to accommodate non-overlapping episodes with inter-event buffers.
   - Cohort Parameter Accounting: In the ratified 112-episode cohort under the 60s minimum inter-episode gap rule, exactly 20 episodes have their plateau clamped at the 135.0 bpm ceiling (updated from 16 clamped among 115 episodes prior to the 60s gap enforcement), 3 are clamped at the 105.0 bpm floor, 50 have upper ramp rate bound adjusted, and 40 have lower ramp rate bound adjusted.

---

### Draft Amendment 4: Standardized Alert-Emission Persistence ($P$) and Refractory Hold-off ($R$) Rules
- **Date:** 2026-10-19
- **Status:** DRAFT (Submitted for user review and approval only; not ratified).
- **Reason for Amendment & Empirical Disclosure:**
  This amendment is drafted strictly following inspection of preliminary evaluation results for Arm 1 (Fixed Threshold) and Arm 2 (Personal Baseline with Shrinkage) under Condition 0 (Clean Background / No-Fault). Without an alert-emission rule, evaluating instantaneous single-window (2-second) threshold crossings produces unsustainable false alarm rates of approximately 100 FA/hr across the cohort (Arm 1: 111.61 FA/hr, 3,490 clean false alerts; Arm 2: 96.42 FA/hr, 3,015 clean false alerts), driven predominantly by transient ambulatory optical motion artifacts and momentary estimator tracking errors during daytime activity.
  
  *Preliminary Benchmark Results (Condition 0: Clean Background, Instantaneous 2s Threshold Crossing):*
  - **Arm 1 (Fixed Threshold, tuned to $\tau_{\text{pop}} = 120\text{ bpm}$ across all 15 folds):**
    - Pooled All-15: Event Recall = 88.4% (99/112 episodes), Median Delay (detected episodes only) = 16.0s, Clean False Alerts = 3,490, Clean FA/hr = 111.61, Natural Alerts = 188 (S5: 185, S6: 3).
    - Pooled Without-S5 (14 subjects): Recall = 88.0% (95/108 episodes), Median Delay = 16.0s, Clean FA = 2,918, Clean FA/hr = 98.30, Natural Alerts = 3.
    - S5/S6/S11 Stratum (3 subjects): Recall = 100.0% (18/18 episodes), Median Delay = 14.0s, Clean FA = 1,748, Clean FA/hr = 356.86, Natural Alerts = 188.
  - **Arm 2 (Personal Baseline with Shrinkage, predominantly tuned to $k = 2.5, \kappa = 2.0\text{h}$):**
    - Pooled All-15: Event Recall = 85.7% (96/112 episodes), Median Delay (detected episodes only) = 16.0s, Clean False Alerts = 3,015 (reduction of 475 false alarms vs Arm 1), Clean FA/hr = 96.42, Natural Alerts = 2 (S5: 2, S6: 0).
    - Pooled Without-S5 (14 subjects): Recall = 85.2% (92/108 episodes), Median Delay = 16.0s, Clean FA = 2,700, Clean FA/hr = 90.96, Natural Alerts = 0.
    - S5/S6/S11 Stratum (3 subjects): Recall = 88.9% (16/18 episodes), Median Delay = 15.0s, Clean FA = 1,137 (35% reduction vs Arm 1), Clean FA/hr = 232.12, Natural Alerts = 2.
    - Subject S5 alone: Clean false alerts fell from 572 (Arm 1) to 315 (Arm 2), dropping FA/hr from 360.76 to 198.67.

#### Section 1: Standardized Alert-Emission Rule ($P$-Persistence & $R$-Refractory)
1. **Temporal Persistence Requirement ($P$):**
   - An alert is emitted if and only if the arm's specific alert condition holds continuously for at least $P$ consecutive seconds ($P \in \{10, 20, 30\}\text{ seconds}$, corresponding to $\{5, 10, 15\}$ contiguous 2-second windows).
   - Momentary threshold excursions shorter than $P$ seconds are suppressed as transient artifacts.
2. **Refractory Hold-off Period ($R$):**
   - Following any emitted alert, an alarm refractory period of $R = 120\text{ seconds}$ is enforced.
   - During the refractory period, subsequent alert triggers are suppressed to avoid duplicate alerts and notification fatigue from the same ongoing physiological surge or prolonged artifact.
3. **Universal Application Across All Arms:**
   - The persistence ($P$) and refractory ($R$) rules apply equally and identically across all evaluation arms (Arm 1, Arm 2, Arm 3a, Arm 3b, Arm 3b-noMotion, and Arm 4).
   - Standardizing emission logic across arms ensures that differences in false alert reduction reflect genuine algorithmic capabilities (motion gating, trust scoring, conformal abstention) rather than differences in emission smoothing.

#### Section 2: Cross-Validation Hyperparameter Selection Rule & Fallback Specification
1. **Primary Selection Rule (Within Training Folds Only):**
   - In each Leave-One-Subject-Out (LOSO) fold, candidate hyperparameter combinations are evaluated on the pooled $N-1$ training subjects.
   - The parameter set that achieves pooled training **Event Recall $\ge 85\%$ ($0.85$) while minimizing pooled training False Alerts per Hour ($\text{FA/hr}$)** is selected:
     $$\theta^* = \arg\min_{\theta \in \Theta \,:\, \text{Recall}_{\text{train}}(\theta) \ge 0.85} \text{FA/hr}_{\text{train}}(\theta)$$
2. **Fallback Rule (When No Candidate Reaches 85% Recall):**
   - If no candidate parameter setting achieves $\ge 85\%$ recall on the training folds, the harness automatically falls back to selecting the candidate that **maximizes pooled training recall**:
     $$\theta^* = \arg\max_{\theta \in \Theta} \text{Recall}_{\text{train}}(\theta)$$
     (with ties broken by lowest training $\text{FA/hr}$).
   - This ensures deterministic, robust parameter selection even under severe fault degradation or conservative candidate sets.

#### Section 3: Candidate Grid Analysis, Proposed Widening, and Edge-of-Grid Rationale
1. **Observed Edge Selection in Preliminary Arm 1:**
   - In the preliminary un-gated evaluation, Arm 1 selected $\tau_{\text{pop}} = 120\text{ bpm}$ across all 15 folds, hitting the upper boundary of the candidate grid $\{100, 110, 120\}\text{ bpm}$.
   - Lower thresholds ($100$ and $110\text{ bpm}$) produced intolerable false alarm rates due to ambulatory motion artifacts, while $120\text{ bpm}$ suppressed substantial noise while still achieving 88.4% recall on injected episodes (which plateau in $[105, 135]\text{ bpm}$).
2. **Proposed Widened Candidate Grids:**
   - **Arm 1 (Fixed Threshold):** $\tau_{\text{pop}} \in \{100, 110, 120, 125, 130\}\text{ bpm}$.
   - **Arm 2 (Personal Baseline with Shrinkage):** Outlier multiplier $k \in \{2.0, 2.5, 3.0, 3.5, 4.0\}$; shrinkage strength $\kappa \in \{0.5, 1.0, 2.0\}\text{ hours}$.
3. **Scientific Justification for Edge-of-Grid Selection ($120\text{ bpm}$):**
   - Even without grid widening, selecting $120\text{ bpm}$ at the edge of $\{100, 110, 120\}\text{ bpm}$ is scientifically and clinically justified:
     a) **Clinical Guideline Validity:** In cardiovascular medicine (AHA/ACC guidelines), resting tachycardia is defined as $HR > 100\text{ bpm}$. A threshold of $120\text{ bpm}$ is already 20 bpm above clinical resting tachycardia. Raising $\tau_{\text{pop}} > 120\text{ bpm}$ (e.g. 130 or 140 bpm) would render the monitoring system clinically insensitive to low-grade or moderate tachycardia.
     b) **Synthetic Episode Physics:** Synthetic injected episodes have target plateaus sampled uniformly in $[105, 135]\text{ bpm}$. Raising $\tau_{\text{pop}}$ above $125\text{ bpm}$ mechanically guarantees false negatives on all episodes with plateaus in $[105, 125]\text{ bpm}$, violating the $H_1$ target recall $\ge 85\%$.
     c) **Paper Objective:** The primary paper hypothesis ($H_1$) is NOT that un-gated fixed thresholds can be arbitrarily raised to eliminate motion noise, but rather that **quality-gated personal alerting (Arm 3b/4) suppresses motion noise at standard physiological thresholds ($100\text{--}120\text{ bpm}$) where un-gated baselines (Arms 1 and 2) fail**.
4. **Strict Testing Freeze:** Zero evaluations on test subjects will be run with the new widened grids until formally ratified by the user.

---

## 9. CHANGELOG

| Revision / Amendment | Date | Description & Reason | Status |
| :--- | :---: | :--- | :--- |
| **Protocol v1.0.0 (Freeze)** | 2026-10-16 | Initial frozen experimental protocol defining core hypotheses $H_1\text{--}H_3$, fault taxonomy F1–F7, and LOSO cross-validation. | **FROZEN (Tag: `protocol-freeze-v1`)** |
| **Amendment 1** | 2026-10-18 | Activity-contextualized alert ground truth ($HR > \tau_i$ during rest only) to prevent benign exercise from being counted as false alert events. Thresholds relabeled as design choices with sensitivity analysis following web fetch verification check. Honest disclosure of S1 inspection added. Refined after viewing ground-truth prevalence only (no alerting or algorithm results); fixes made: corrected redundant /64 accelerometer scaling bug, unified implementation in `vitasense.quality.event_prevalence`, and added explicit dual unit checks (physical range $[-3, +3]g$ and median norm $[0.8, 1.2]g$). | **Ratified by user, 2026-10-19** |
| **Amendment 2** | 2026-10-18 | Labelled-SYNTHETIC resting tachycardia injection protocol formulated after observing extreme sparsity in healthy subjects. Option (a) adopted as primary benchmark injection architecture into resting segments only with seed 42, tagging every episode SYNTHETIC; validates alert logic only. Natural events in S5, S6, S7, S11 treated descriptively only. Refined after viewing ground-truth prevalence only (no alerting or algorithm results); incorporates outlier handling rule (S5 dual reporting and minutes-based evaluation, S6/S11 sensitivity checks). | **Ratified by user, 2026-10-19** |
| **Outlier Handling Rule** | 2026-10-18 | Dual reporting with/without S5; sensitivity checks with/without S6 and S11; non-independence of natural events; precision/recall restricted to synthetic events; S5 evaluated strictly in minutes above threshold. | **Ratified by user, 2026-10-19** |
| **Implementation Correction** | 2026-10-19 | Unified Event Prevalence Module (`vitasense.quality.event_prevalence`). Corrected redundant `/64` accelerometer scaling in rerun prototype that disabled the kinematic filter; standardized window alignment to 8s window midpoint ($t = 2i+4$s); added dual physical unit checks (range and median gravity baseline); added synthetic test coverage (`test_event_prevalence.py`). Regenerated 15-subject prevalence and sensitivity tables. | **Implementation Correction** |
| **Amendment 3** | 2026-10-19 | Alerting benchmark evaluation design: restated $H_1$ as estimation question with 95% bootstrap CI and exploratory label, ACC sharing note for Arms 3a/3b, full 15-subject LOSO evaluation, wrist-PPG HR input stream with real motion errors from Step 3a estimator, explicit scope limitation (tests alert logic on noisy stream, not pulse sensing), strict quarantine of ECG-derived $\tau_i$ and resting blocks, inclusion of ablation arm 3b-noMotion (trust score without motion term), fault-window alerts counted as false alarms with disaggregated FA/hr reporting per fault type and no-fault, deployment-only low-ENMO conformal calibration, fixed trust-score weights (`vitasense.quality.trust_score` v1.0.0), dual fault-duty regimes (~10% and ~25–30%), F7 raw BVP noise before estimator with SNR levels, adopted $T_{\text{gap}} = 60\text{s}$ with 3 lost episodes listed and post-ratification commit requirement, S5/S6 baseline clustering caveat, jump-size stratification, and adaptive ramp reconciliation. | **Ratified by user, 2026-10-19** |
| **Protocol Update** | 2026-10-19 | Updated synthetic injection audit figures to ratified 112 episodes and 20 clamped ceiling (from 115 episodes and 16 clamped); the 60 s gap enforcement fixed a cross-block gap bug found while implementing the unit test. | **Updated** |
| **Draft Amendment 4** | 2026-10-19 | Draft alert-emission rule: persistence P in {10, 20, 30}s, refractory R = 120s across all arms; documented selection rule (recall >= 85% then min FA/hr) and fallback; listed preliminary Arms 1-2 results; candidate widened grids with edge-of-grid rationale. | **DRAFT (For user review only)** |

*(Note: Ratified Amendments 1, 2, and 3 frozen under tag `protocol-freeze-v3`. Tag `protocol-freeze-v1` remains permanently unmoved at commit `41eff1e`; tag `protocol-freeze-v2` remains permanently unmoved at commit `3b1f2f6`.)*






