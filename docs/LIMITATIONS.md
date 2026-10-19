# VitaSense AI - Scientific Limitations and Scope Boundaries

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Protocol-Compliant Limitations Disclosure  

This document explicitly catalogues the scientific, methodological, and experimental limitations of the VitaSense AI wearable alerting benchmark. To prevent over-interpretation or unwarranted generalization, no claims beyond the empirical data are asserted.

---

## 1. Synthetic Alert Injection Architecture
- **Non-Clinical Synthetic Surrogates:** All true-positive tachycardia events were synthetically generated and added to the recording streams rather than occurring spontaneously in patient populations.
- **Narrow Peak Distribution ($105\text{--}135\text{ bpm}$):** Target episode plateaus were sampled strictly from $[105.0, 135.0]\text{ bpm}$. The benchmark does not evaluate extreme tachyarrhythmias ($>140\text{ bpm}$) or modest physiological elevations ($90\text{--}105\text{ bpm}$).
- **Predominance of Large Jumps ($>50\text{ bpm}$):** In the ratified 112-episode cohort:
  - Jumps $> 50\text{ bpm}$: **101 of 112 episodes (90.2%)**
  - Jumps $30\text{--}50\text{ bpm}$: **11 of 112 episodes (9.8%)**
  - Jumps $< 30\text{ bpm}$: **0 of 112 episodes (0.0%)**  
  The benchmark primarily tests detection of large, salient physiological steps; performance on subtle, borderline tachycardia ($<30\text{ bpm}$ elevation above resting baseline) remains unexercised.
- **Derived-Stream Injection (Pulse Sensing Bypassed):** Per Protocol Amendment 3 Limitation 1.1, synthetic tachycardia is added directly to the derived wrist-PPG HR estimate from the Step 3a estimator. The benchmark validates downstream alerting logic on a noisy ambulatory stream; it does **not** test the physical optical sensor's capability to detect an increased pulse rate from raw vascular volume changes.

---

## 2. Small Cohort Size ($N = 15$ Subjects)
- The entire wearable evaluation is based on 15 individuals ($S_1$ to $S_{15}$).
- All participants were healthy, young volunteers (mean age $30.6 \pm 9.6$ years, range 21–55; 8 male, 7 female).
- Statistical comparisons between alerting arms (e.g. Wilcoxon signed-rank tests) rely on $N = 15$ pairs, giving limited power to detect subtle effect sizes between closely related gating algorithms.

---

## 3. Single Dataset and Scripted Protocol (PPG-DaLiA)
- All wearable evaluations were performed exclusively on the PPG-DaLiA dataset (UCI ID 495).
- Data collection followed a scripted ~2.5-hour multimodal daily protocol (sitting, ascending/descending stairs, playing soccer, cycling, driving, eating lunch, and table soccer).
- Results cannot be generalized to:
  - 24/7 continuous free-living monitoring
  - Overnight sleep stages and nocturnal arrhythmias
  - Diverse clinical cohorts (e.g. elderly patients, pediatric populations, patients with cardiovascular disease)
  - Alternative wrist-worn hardware platforms (e.g. Apple Watch, Garmin, Fitbit, Polar)

---

## 4. Front-End PPG Estimator Tracking Errors During Motion
- The Step 3a front-end spectral peak estimator (`WristPPGHREstimator`) exhibits well-known vulnerability to ambulatory motion artifacts.
- During vigorous rhythmic movements (such as cycling, climbing stairs, and soccer), the optical PPG spectrum is dominated by motion harmonics, frequently causing the estimator to lock onto movement cadence rather than cardiac pulse rate.
- Superimposing synthetic tachycardia onto this derived stream means downstream alerting algorithms interact directly with front-end estimator tracking failures.

---

## 5. Temporal Clustering of Injections in Outlier Subjects (S5 and S6)
- Subjects S5 and S6 exhibited high ambulatory heart rates throughout active protocol periods.
- Consequently, qualifying clean resting intervals with low motion ($\text{ENMO} \le 0.05g$) were confined almost entirely to the initial baseline period ($t < 600\text{ seconds}$):
  - **Subject S5:** All 4 episodes were injected between $t = 102.0\text{s}$ and $t = 556.0\text{s}$.
  - **Subject S6:** All 4 episodes were injected between $t = 78.0\text{s}$ and $t = 562.0\text{s}$.
- Performance for S5 and S6 does not evaluate alert detection spread across hours of ambulatory wear, but tests repeated episodes within a single early sedentary window.

---

## 6. Pervasive Edge-of-Grid Parameter Selections
Under Leave-One-Subject-Out (LOSO) cross-validation with grid tuning inside training folds, hyperparameter optimization frequently collapsed to candidate search boundaries:
- **Arm 1 (Fixed Population Threshold):** Selected $\tau_{\text{pop}} = 100\text{ bpm}$ (lower bound) in **100% (15/15) of folds**, and persistence $P = 30\text{s}$ (upper bound) in **100% (15/15) of folds**.
- **Arm 2 (Personal Baseline with Shrinkage):** Selected outlier multiplier $k = 2.0$ (lower bound) in **100% (15/15) of folds**, and persistence $P = 10\text{s}$ (lower bound) in **100% (15/15) of folds**.
- **Arm 3a (Kinematic Gating):** Selected $\theta_{\text{rest}} = 0.08g$ (upper bound) in **93.3% (14/15) of folds**.
- **Arm 3b (Software Trust Gate):** Selected $\theta_{\text{trust}} = 0.60$ (lower bound) in **93.3% (14/15) of folds**.

Boundary selections demonstrate that the tuning objective is heavily constrained by the predefined grid borders rather than discovering an unconstrained interior optimum.

---

## 7. Invocation of Fallback Selection Rule for Arm 2 in 100% of Folds
- The primary tuning objective required candidate combinations to reach $\ge 85\%$ event recall on pooled training folds before minimizing false alerts per hour ($\text{FA/hr}$).
- **Arm 2 never achieved $\ge 85\%$ training recall in any fold across any tested condition** (maximum training recall attained was $\approx 80.4\%$).
- As a consequence, the fallback selection rule (maximize training recall) was triggered in **100% (15/15) of folds across all conditions**, mechanically forcing the tuner to pick the lowest multiplier ($k = 2.0$) and shortest persistence ($P = 10\text{s}$) to prevent further recall loss.

---

## 8. Post-Result Protocol Amendments and Design Changes
Multiple methodological decisions were formulated or refined *after* inspecting preliminary data and results:
- **Amendment 4 (Alert Emitter & Grid Widening):** Formulated after observing that single-window threshold crossings caused catastrophic false alert rates ($\sim 100\text{ FA/hr}$). The introduction of persistence ($P$), refractory hold-off ($R = 60\text{s}$), and candidate grid widening ($\tau \in \{125, 130\}$, $k \in \{3.5, 4.0\}$) occurred post-preliminary inspection.
- **Adaptive Ramp Bounding Rule:** Implemented after discovering that independent uniform draws of ramp rate and target peak HR violated physiological floor and ceiling constraints on real baseline distributions.
- **Post-Hoc Risk:** While all amendments were logged transparently in the protocol CHANGELOG and ratified prior to running subsequent regimes, post-result adjustments inherently increase the risk of tuning benchmark structures to dataset-specific idiosyncrasies.

---

## 9. Unverified External Literature Citations
- Two clinical and epidemiological guidelines cited in early protocol drafts could not be verified via automated HTTP retrieval:
  1. ACC/AHA/HRS 2015 SVT Guideline (Page et al., *JACC* 2016; DOI: [10.1016/j.jacc.2015.08.856](https://doi.org/10.1016/j.jacc.2015.08.856)) returned client-side JavaScript redirects / HTTP 403 Forbidden.
  2. Hildebrand et al. 2014 (*Med Sci Sports Exerc*; DOI: [10.1249/MSS.0000000000000289](https://doi.org/10.1249/MSS.0000000000000289)) could not be opened during automated verification.
- Consequently, threshold constants ($\tau_i \ge 100\text{ bpm}$, $\theta_{\text{rest}} = 0.05g$) are classified as **unverified engineering design choices with sensitivity analysis**, not formally verified external standards.

---

## 10. Complete Absence of Clinical Diagnostic Validity
- VitaSense AI benchmark evaluations assess algorithmic signal-processing filters and thresholding rules on healthy volunteers with synthetically added rate surges.
- This software has **zero clinical diagnostic validity**.
- It has not been tested on clinical populations with genuine cardiac arrhythmias (e.g. supraventricular tachycardia, atrial fibrillation, atrial flutter, ventricular tachycardia) or clinical dysautonomia (e.g. postural orthostatic tachycardia syndrome / POTS).
- These results must not be used to assert medical efficacy, diagnostic safety, or readiness for clinical decision support.

---

## 11. Arm 4 (Conformal Abstention) Was Never Implemented
- Arm 4 (uncertainty-aware conformal alerting with abstention), which served as the cornerstone of the original hypothesis $H_1$, was placed on indefinite experimental hold.
- **Arm 4 was never built, calibrated, or evaluated in this benchmark suite.**
- Consequently, hypothesis $H_1$ as originally conceived (evaluating conformal prediction sets for false alarm suppression) remains entirely untested in this work.
