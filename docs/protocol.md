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

---

## 8. Protocol Amendments

### Amendment 1: Activity-Contextualized Alert Ground Truth
- **Date:** 2026-10-18
- **Status:** Pending user ratification (formulated strictly *a priori* before any wearable alerting experiment or evaluation).
- **Affected Section:** Section 3.1 (PPG-DaLiA Alert Ground Truth).
- **Reason for Amendment:**
  In real-world free-living datasets such as PPG-DaLiA (UCI ID 495), participants engage in daily physical exertion including stair climbing, outdoor cycling, walking, and table soccer. Normal human physiology elevates heart rate above 100 bpm during physical exercise to meet metabolic demands (physiological exercise-induced sinus tachycardia).
  A naive, uncontextualized alerting rule ($HR > 100\text{ bpm}$) triggers continuous, spurious "alerts" throughout benign physical exercise. In clinical practice, wearable personal alerting systems target *unexpected* or *inappropriate* tachycardia occurring when the user is sedentary or at rest. Evaluating alerting algorithms without conditioning on motion context would improperly count benign exercise as true alert events and would unfairly penalize quality-gated suppression during movement as false negatives.
- **A Priori Ground Truth Definition:**
  An authentic **Inappropriate / At-Rest Tachycardia Alert Event** ground truth is defined strictly by the joint fulfillment of physiological and kinematic criteria continuously for at least $T_{\text{persist}} = 30\text{ seconds}$:
  1. **Physiological Reference Criterion:**
     $$HR_{\text{ref, ECG}}(t) > \tau_i$$
     where $\tau_i = \max(100\text{ bpm}, \mu_{i,\text{rest}} + 2.5\sigma_{i,\text{rest}})$, computed directly from the chest ECG reference signal during authenticated resting/baseline intervals.
  2. **Kinematic Resting Context Criterion:**
     Wrist 3D accelerometer dynamic energy (Euclidean Norm Minus One, ENMO):
     $$\text{ENMO}(t) = \max\left(0, \sqrt{a_x^2(t) + a_y^2(t) + a_z^2(t)} - 1.0g\right)$$
     averaged over a 10-second moving window satisfies:
     $$\overline{\text{ENMO}}_{10\text{s}}(t) \le \theta_{\text{rest}} = 0.05g$$
     Alternatively, where ground-truth protocol activity tags are present, the concurrent activity state must be among resting/sedentary states (`BASELINE`, `WORKING`, `LUNCH`, `DRIVING`) and not active exercise (`STAIRS`, `SOCCER`, `CYCLING`, `WALKING`).
- **Literature and Design Justifications:**
  - **$\tau_i \ge 100\text{ bpm}$ (Literature Verified):**
    - *Citation:* Page RL, et al. *2015 ACC/AHA/HRS Guideline for the Management of Adult Patients With Supraventricular Tachycardia.* J Am Coll Cardiol. 2016;67(13):e27–e115. DOI: [10.1016/j.jacc.2015.08.856](https://doi.org/10.1016/j.jacc.2015.08.856).
    - *Paper Content:* Section 7.1 explicitly defines Inappropriate Sinus Tachycardia (IST) as a persistent resting heart rate $> 100\text{ bpm}$ (or mean 24-hour heart rate $> 90\text{ bpm}$) in the absence of physiological stress or physical exertion.
  - **$\mu_{i,\text{rest}} + 2.5\sigma_{i,\text{rest}}$ (Statistical Baseline):** Standard individual outlier detection threshold, corresponding to the upper $0.6\%$ tail ($p < 0.006$) of personal resting fluctuations under Gaussian assumptions, preventing alerts on normal baseline variability.
  - **$T_{\text{persist}}$ (Design Choice with Sensitivity Analysis):**
    - Relabeled as an engineering design choice with prescribed sensitivity analysis across $T_{\text{persist}} \in \{15, 30, 60\}\text{ seconds}$ (nominal baseline $30\text{s}$) to filter out instantaneous respiratory sinus arrhythmia and transient postural shifts before raising an alert.
  - **$\theta_{\text{rest}}$ (Design Choice with Sensitivity Analysis):**
    - Relabeled as an engineering design choice with prescribed sensitivity analysis across $\theta_{\text{rest}} \in \{0.03, 0.05, 0.10\}g$ (nominal baseline $0.05g$, informed by physical activity epidemiology where wrist ENMO $< 45\text{ mg}$ indicates sedentary behavior; Hildebrand et al., *Med Sci Sports Exerc* 2014, DOI: [10.1249/MSS.0000000000000289](https://doi.org/10.1249/MSS.0000000000000289)).
- **Honest Disclosure:**
  *S1 heart rate range, wrist accelerometer magnitude, and protocol activity labels were inspected prior to drafting this amendment.*
- **Scientific Integrity Guarantee:**
  No alerting algorithms or fault-injection models were evaluated prior to formulating this definition. All sensitivity analysis grids ($T_{\text{persist}} \in \{15, 30, 60\}\text{s}$; $\theta_{\text{rest}} \in \{0.03, 0.05, 0.10\}g$) are fixed strictly *a priori* before alerting ablations.

---

### Draft Amendment 2: Labelled-SYNTHETIC Resting Tachycardia Injection Protocol
- **Date:** 2026-10-18
- **Status:** DRAFT (Submitted for user review and approval only; not ratified).
- **Reason for Proposed Amendment:**
  Empirical ground-truth evaluation across all 11 intact PPG-DaLiA subjects revealed that authentic resting tachycardia events under Amendment 1 are extremely sparse in healthy young volunteers: 9 of 11 subjects had zero natural events, and 30 of the 32 total events occurred in a single subject (`S5`). Under Leave-One-Subject-Out (LOSO) cross-validation, testing alerting precision, recall, and detection delay on test subjects with zero ground-truth events is statistically invalid (recall is undefined $0/0$).
- **Proposed Protocol:**
  1. For each subject during authenticated resting/sedentary periods (activity in `BASELINE`, `WORKING`, `LUNCH`, `DRIVING` with $\overline{\text{ENMO}}_{10\text{s}} \le 0.05g$), inject $N_{\text{tachy}} = 5$ to $10$ physiologically plausible tachycardia episodes.
  2. Episode parameters:
     - Peak heart rate: $HR_{\text{tachy}} \sim \mathcal{U}(105, 135)\text{ bpm}$.
     - Onset dynamics: physiologically gradual ramp ($+2\text{ to } +4\text{ bpm/s}$ over $15\text{s}$).
     - Sustained duration: $T_{\text{event}} \in [45, 120]\text{ seconds}$.
     - Resolution: gradual exponential decay back to personal resting baseline.
  3. Signal Injection: Applied identically to the ground-truth ECG reference stream and the derived wrist HR stream, with full labelling:
     `is_synthetic: True`, `event_type: "SYNTHETIC_RESTING_TACHYCARDIA"`.
  4. This guarantees a balanced evaluation of sensitivity, specificity, and detection delay across all 15 LOSO cross-validation folds without distorting natural resting background noise.

