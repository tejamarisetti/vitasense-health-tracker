# VitaSense AI - PRD Traceability Matrix

**Document Version:** 3.0.0  
**Generated Date:** 2026-10-22  
**PRD Reference:** [docs/PRD.pdf](file:///d:/projects/health%20tracker/docs/PRD.pdf) (*VitaSense AI Product Requirements Document Version 2.0, 16 October 2026, Section 8 Functional Requirements*).  
**Requirements Traceability Rule:** Requirement wording is transcribed verbatim from `docs/PRD.pdf` Section 8. Requirement statuses are determined strictly by verified implementation evidence and automated test execution. Per instructions, FR-06 and FR-07 are not started; FR-10 is backed by a verified backend API and interactive UI implementation.

---

## 1. Summary of Functional Requirements Status

- **Total Functional Requirements:** 13
- **Implemented (5):** FR-01, FR-02, FR-04, FR-10, FR-11
- **Implemented as Demo Ruleset, Not Evaluated (2):** FR-06, FR-07
- **Partial (6):** FR-03, FR-05, FR-08, FR-09, FR-12, FR-13
- **Not Started (0):** None

---

## 2. Requirement-by-Requirement Traceability Matrix

### FR-01 — Authentication and sessions
* **PRD Verbatim Requirement:**
  - Users can register, log in, log out, and receive understandable validation errors.
  - Passwords must be securely hashed server-side; never store plaintext passwords.
  - Protected pages and APIs require a valid session/token.
  - Users can access only their own private profile, measurements, assessments, predictions, and alerts.
  - Include password reset only if an email/reset mechanism is actually configured; otherwise clearly mark it as not enabled rather than faking it.
* **Status:** **Implemented**
* **Implementation Files:**
  - [vitasense/api/auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/LoginPage.tsx](file:///d:/projects/health%20tracker/src/pages/LoginPage.tsx)
  - [src/pages/CreateAccountPage.tsx](file:///d:/projects/health%20tracker/src/pages/CreateAccountPage.tsx)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py:L27-L86](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L27-L86) (registration, password hashing, session tokens, login/logout)
  - [tests/test_phase2_auth_measurements.py:L441-L573](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L441-L573) (rate-limiting on register & login, cross-user isolation)
  - [tests/test_auth_offline.py](file:///d:/projects/health%20tracker/tests/test_auth_offline.py) (backend down never yields session, zero credentials in src/)
* **Evidence / Notes:**
  - Server-side PBKDF2-HMAC-SHA256 with 600,000 iterations and per-user salt.
  - Hashed session tokens stored with expiration and revocation support in SQLite.
  - Real error reporting on connection failure with retry; offline fallback session bypass completely removed.
  - Server-side `POST /api/auth/demo` creates/reuses DEMO account without client credentials.
  - Password reset modal explicitly states "Password reset is not enabled in this build."

---

### FR-02 — Profile and preferences
* **PRD Verbatim Requirement:**
  - Users can view and update supported profile fields and preferred measurement units.
  - Collect only fields necessary for the stated features; sensitive or demographic fields must have a documented purpose.
  - Changes are validated and persisted, with clear success/error feedback.
  - Profile data must be used only in the context described to the user.
* **Status:** **Implemented**
* **Implementation Files:**
  - [vitasense/api/auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/components/ProfileModal.tsx](file:///d:/projects/health%20tracker/src/components/ProfileModal.tsx)
  - [src/types.ts](file:///d:/projects/health%20tracker/src/types.ts)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py:L88-L124](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L88-L124) (`test_user_profile_crud_and_validation`)
* **Evidence / Notes:**
  - `GET /api/auth/profile` and `PUT /api/auth/profile` with Pydantic validation (name, age, biological sex, height, weight, resting HR baseline, activity level, health goal).
  - Stored in `user_profiles` table with foreign key cascade to `users`.

---

### FR-03 — Measurement entry and storage
* **PRD Verbatim Requirement:**
  - Support a configurable measurement schema rather than hard-coding unsupported sensor capabilities.
  - Each record should include user ID, measurement type, value, unit, timestamp, source (manual/import/demo), and optional notes.
  - Support the initial agreed health measures only. Candidate measures may include heart rate, SpO₂, temperature, activity, and other values when data and units are defined; do not display unavailable values as real.
  - Validate numeric types, required fields, units, timestamps, and reasonable configurable ranges.
  - Permit authorized users to inspect, correct, or delete their own entries; preserve appropriate audit events if required.
* **Status:** **Partial**
* **Implementation Files:**
  - [vitasense/api/measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py:L126-L230](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L126-L230) (`test_measurement_ingestion_and_user_isolation`, `test_measurement_server_side_validation_errors`, `test_user_cannot_read_another_users_measurements`)
* **Evidence / Notes:**
  - **Implemented:** Ingestion, validation, range checking, and inspection of supported measures (`heart_rate`, `spo2`, `respiratory_rate`, `hrv`) with row-level user isolation.
  - **Missing Evidence (Partial):** Individual measurement editing (`PUT /api/measurements/{id}`) and individual entry deletion (`DELETE /api/measurements/{id}`) are not implemented. Users can view entries and delete their entire account or clear demo records, but cannot correct or delete individual recorded points.

---

### FR-04 — Data quality and trust scoring
* **PRD Verbatim Requirement:**
  - Detect missing required values, malformed values, unsupported units, duplicate records, stale timestamps, implausible ranges, and configurable sudden changes.
  - Label each issue and explain why it matters in plain language.
  - Produce a transparent data-quality/trust indicator based on documented rules; show the component checks rather than presenting an unexplained score.
  - Low-quality data must be excluded from model inference or explicitly flagged as a limitation.
  - Never interpret a software validation pass as proof of physical sensor accuracy.
* **Status:** **Implemented**
* **Implementation Files:**
  - [vitasense/quality/trust_score.py](file:///d:/projects/health%20tracker/vitasense/quality/trust_score.py)
  - [vitasense/api/measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)
  - [src/pages/TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py:L232-L320](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L232-L320) (`test_data_quality_flags_missing_stale_duplicate_implausible_sudden_change`)
  - [tests/test_phase4_assessment_and_inference_exclusion.py:L31-L71](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py#L31-L71) (`test_fr04_inference_exclusion_and_dataset_endpoint`)
  - [tests/test_trust_score.py](file:///d:/projects/health%20tracker/tests/test_trust_score.py)
* **Evidence / Notes:**
  - Deterministic detection of `missing`, `stale` (sensor flatline), `duplicate` (timestamp collisions), `implausible` (bounds), and `sudden_change` (>40 bpm/s jump rate). Trust score and component checks breakdown are rendered in the UI inspection drawer.
  - Automated inference exclusion: `exclude_from_inference` boolean and `limitation_note` are populated on every measurement. The endpoint `GET /api/measurements/inference-dataset` programmatically quarantines and drops any low-quality segments from downstream ML model batch inference.

---

### FR-05 — Dashboard
* **PRD Verbatim Requirement:**
  - Display the latest available data with timestamp and source.
  - Show a concise summary of recent trends and recent alerts.
  - Show empty states when there are no records and provide a clear action to add data or load demo data.
  - Provide quick links to symptom assessment, add measurement, history, and trends.
  - Demo/simulated values must be visibly marked as demo data.
* **Status:** **Partial**
* **Implementation Files:**
  - [src/pages/OverviewPage.tsx](file:///d:/projects/health%20tracker/src/pages/OverviewPage.tsx)
  - [src/components/Waveform.tsx](file:///d:/projects/health%20tracker/src/components/Waveform.tsx)
* **Automated Test References:**
  - Verified via frontend build `npm.cmd run build` (0 TypeScript / JSX errors)
* **Evidence / Notes:**
  - **Implemented:** Displays latest available readings, recent alerts, animated waveform, trust indicators, and quick links to Symptom Lab and Trends. Demo data is clearly tagged.
  - **Missing Evidence (Partial):** Missing dedicated empty state when zero records exist offering a direct action to add data or load demo data; missing explicit quick link to "Add Measurement" modal/flow from the dashboard.

---

### FR-06 — Symptom-based risk assessment
* **PRD Verbatim Requirement:**
  - Provide a guided, configurable symptom questionnaire with clear question wording and appropriate response types.
  - Collect only the inputs required by the selected model or ruleset.
  - Before submission, let the user review their answers and correct them.
  - Return an informational risk category or score only if a defined and evaluated model/ruleset supports it.
  - Show the factors that contributed to the result, relevant missing data, model limitations, and when to seek professional advice.
  - Do not state or imply that the user has a disease; use language such as “estimated risk signal” or “screening-style result,” not “diagnosis.”
  - If no validated model is configured, provide a clearly labelled demo/rules-based result rather than pretending a trained clinical model exists.
* **Status:** **Implemented as demo ruleset, not evaluated**
* **Implementation Files:**
  - [vitasense/api/assessment.py](file:///d:/projects/health%20tracker/vitasense/api/assessment.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/AssessmentPage.tsx](file:///d:/projects/health%20tracker/src/pages/AssessmentPage.tsx)
* **Automated Test References:**
  - [tests/test_phase4_assessment_and_inference_exclusion.py:L73-L98](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py#L73-L98) (`test_fr06_symptom_questionnaire_review_step`)
  - [tests/test_phase4_assessment_and_inference_exclusion.py:L100-L148](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py#L100-L148) (`test_fr06_fr07_assessment_submission_and_explanation`)
  - [tests/test_phase4_assessment_and_inference_exclusion.py:L150-L179](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py#L150-L179) (`test_fr06_user_isolation_for_assessments`)
* **Evidence / Notes:**
  - Guided questionnaire covering sensation, severity, duration, context, and red flags with review and edit step prior to submission.
  - Results use screening risk signal terminology ("estimated risk signal", "Low/Moderate/Elevated Risk Signal"), never diagnosis.
  - Because no clinically evaluated or trained machine learning model is configured, the engine is explicitly identified and labelled as `"DEMO RULESET v2.1, not evaluated"`.

---

### FR-07 — AI/ML explanation
* **PRD Verbatim Requirement:**
  - Explain the result in plain language using only inputs actually used by the model.
  - Where technically supported, show feature contributions or global/local explanation outputs and uncertainty/calibration information.
  - Identify the model version, timestamp, and whether the result used demo or user-entered data.
  - Do not fabricate feature importance, confidence percentages, model accuracy, or evidence.
  - If the model cannot explain an individual result reliably, state that limitation.
* **Status:** **Implemented as demo ruleset, not evaluated**
* **Implementation Files:**
  - [vitasense/api/assessment.py](file:///d:/projects/health%20tracker/vitasense/api/assessment.py)
  - [src/pages/AssessmentPage.tsx](file:///d:/projects/health%20tracker/src/pages/AssessmentPage.tsx)
* **Automated Test References:**
  - [tests/test_phase4_assessment_and_inference_exclusion.py:L100-L148](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py#L100-L148) (`test_fr06_fr07_assessment_submission_and_explanation`)
* **Evidence / Notes:**
  - Deterministic local feature contributions based on submitted inputs.
  - Arbitrary fixed margins ($\pm 0.08$) and "calibrated" claims have been removed. System now displays `"uncertainty not estimated for this demo ruleset"` (`uncertainty_range = None`).
  - Model version is explicitly reported as `"DEMO RULESET v2.1, not evaluated"`, avoiding fabricated confidence or calibration claims.

---

### FR-08 — Trend analysis
* **PRD Verbatim Requirement:**
  - Support daily, weekly, and monthly views and a selectable date range.
  - Plot actual recorded data points and label units, timestamps, missing intervals, and data source where useful.
  - Summaries may include min/max/average and direction of change only when enough valid data exists.
  - Distinguish observed historical trends from future predictions.
  - Do not fill missing data in a way that makes it appear measured; any interpolation must be explicitly marked.
* **Status:** **Partial**
* **Implementation Files:**
  - [src/pages/TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)
  - [vitasense/api/measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py)
  - Frontend build verification (`npm.cmd run build`)
* **Evidence / Notes:**
  - **Implemented:** Supports 24H, 7D, 30D, 3M views, summary metrics, units, and data export.
  - **Missing Evidence (Partial):** Discrete raw points are not plotted separately from continuous interpolated lines; missing intervals/interpolations are not visually marked on charts; future predictions are not separated from historical observations.

---

### FR-09 — Alerts
* **PRD Verbatim Requirement:**
  - Generate software alerts from documented thresholds, validated rules, data-quality issues, or model outputs.
  - Each alert includes title, reason, severity, creation time, related record, and recommended safe next step.
  - Users can acknowledge or dismiss alerts; acknowledgement must not delete the underlying event.
  - Allow configuration of supported alert preferences and avoid repeated duplicate alerts for the same event.
  - Use cautious wording and state that alerts are informational, not emergency monitoring.
  - Do not imply continuous monitoring when the application only processes data on entry/import or during a demo.
* **Status:** **Partial**
* **Implementation Files:**
  - [vitasense/api/alerts.py](file:///d:/projects/health%20tracker/vitasense/api/alerts.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/AlertsPage.tsx](file:///d:/projects/health%20tracker/src/pages/AlertsPage.tsx)
  - [vitasense/benchmarks/alert_emitter.py](file:///d:/projects/health%20tracker/vitasense/benchmarks/alert_emitter.py)
* **Automated Test References:**
  - [tests/test_phase3_features.py:L106-L230](file:///d:/projects/health%20tracker/tests/test_phase3_features.py#L106-L230) (`test_user_alerts_crud_acknowledge_dismiss`, duplicate suppression, isolation)
* **Evidence / Notes:**
  - **Implemented:** Alert retrieval, ingestion, non-destructive acknowledgment/dismissal, duplicate suppression (60s refractory), and informational disclaimers.
  - **Missing Evidence (Partial):** Automated background rule-generation of alerts directly upon measurement ingestion is missing; user configuration of alert threshold preferences is not supported in the UI or backend.

---

### FR-10 — History and search
* **PRD Verbatim Requirement:**
  - Show a chronological record of measurements, assessments, predictions, and alerts.
  - Support date/type filters and pagination or progressive loading.
  - Selecting an entry opens its details, inputs, data-quality flags, and result explanation where applicable.
  - Edits/deletions must be restricted to the authenticated owner.
* **Status:** **Implemented**
* **Implementation Files:**
  - [vitasense/api/history.py](file:///d:/projects/health%20tracker/vitasense/api/history.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase3_features.py:L232-L321](file:///d:/projects/health%20tracker/tests/test_phase3_features.py#L232-L321) (`test_user_history_pagination_and_filtering`, isolation)
* **Evidence / Notes:**
  - Unified `GET /api/history` with category filtering, type filtering, pagination metadata, and owner isolation.
  - Interactive UI with expandable payload view and page controls in `TrendsPage.tsx`.

---

### FR-11 — Contact Us
* **PRD Verbatim Requirement:**
  - Provide a form for subject/category, message, and optional reply contact.
  - Validate input length and format, protect against spam/basic injection, and show success/failure feedback.
  - Do not include private health details in email or logs unless explicitly necessary and consented to.
  - If no message-delivery backend is configured, save the submission securely or state that sending is unavailable; do not display a false success.
* **Status:** **Implemented**
* **Implementation Files:**
  - [vitasense/api/auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/SettingsPage.tsx](file:///d:/projects/health%20tracker/src/pages/SettingsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase3_features.py:L31-L104](file:///d:/projects/health%20tracker/tests/test_phase3_features.py#L31-L104) (`test_contact_us_validation_and_rate_limit`, `test_contact_us_xss_injection_prevention`)
* **Evidence / Notes:**
  - `POST /api/contact` endpoint with Pydantic validation (length, regex against script/HTML tags).
  - Secure SQLite persistence in `contact_messages` table.
  - Rate limiting (5 req/min per IP) returning HTTP 429 with truthful failure feedback.
  - Audit logging sanitized with zero private health telemetry in logs.

---

### FR-12 — Demo and onboarding
* **PRD Verbatim Requirement:**
  - Provide a guided first-run state or short onboarding explaining the app, data sources, and non-diagnostic purpose.
  - Offer optional demo data so evaluators can explore the UI without entering personal data.
  - Clearly label demo accounts, demo measurements, and simulated model outputs.
  - Provide a reset/clear-demo option that does not delete real user data.
* **Status:** **Partial**
* **Implementation Files:**
  - [vitasense/api/measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)
  - [src/pages/LandingPage.tsx](file:///d:/projects/health%20tracker/src/pages/LandingPage.tsx)
  - [src/pages/TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase2_auth_measurements.py:L322-L379](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L322-L379) (`test_demo_data_population_and_non_destructive_reset`)
* **Evidence / Notes:**
  - **Implemented:** Demo accounts, demo data seeding, clear DEMO tags, and non-destructive demo reset.
  - **Missing Evidence (Partial):** Guided first-run onboarding state explaining the application, data sources, and non-diagnostic purpose to a first-time user is not implemented.

---

### FR-13 — Privacy and account controls
* **PRD Verbatim Requirement:**
  - Explain what information is collected and why before collecting it.
  - Provide data export/deletion controls if feasible for the selected architecture and document any limitations.
  - Keep secrets and credentials out of frontend source code and version control.
  - Use secure transport in deployment and avoid sensitive information in application logs.
* **Status:** **Partial**
* **Implementation Files:**
  - [vitasense/api/auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)
  - [vitasense/api/db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)
  - [src/pages/SettingsPage.tsx](file:///d:/projects/health%20tracker/src/pages/SettingsPage.tsx)
* **Automated Test References:**
  - [tests/test_phase3_features.py:L323-L376](file:///d:/projects/health%20tracker/tests/test_phase3_features.py#L323-L376) (`test_data_export_and_account_deletion`)
  - [tests/test_auth_offline.py](file:///d:/projects/health%20tracker/tests/test_auth_offline.py) (`test_no_credentials_in_frontend_source`)
* **Evidence / Notes:**
  - **Implemented:** Data export (`GET /api/auth/export`), account deletion (`DELETE /api/auth/account`), no credentials in frontend code or logs.
  - **Missing Evidence (Partial):** An explicit explanation of what information is collected and why shown *before* collecting it is missing from registration and measurement forms.

---

## 3. Data Quality & ML Inference Exclusion Implementation (FR-04)

* **Implementation Detail:**
  - `vitasense.quality.trust_score.RuleBasedTrustScorer` computes deterministic multi-component SQI (`S_gap`, `S_stale`, `S_phys`, `S_motion`).
  - [vitasense/api/measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py) detects and labels:
    - `missing`: missing values or non-numeric tokens.
    - `stale`: repeated flatline readings (zero variance).
    - `duplicate`: exact timestamp collisions.
    - `implausible`: values outside normative physiological bounds.
    - `sudden_change`: jumps exceeding rate limits (>40 bpm/s).
  - All component checks are serialized to JSON and displayed in the UI drawer.
  - **Automated ML Inference Exclusion:** Completed and automated test-verified. Every measurement record is evaluated via `determine_inference_exclusion()` to assign `exclude_from_inference: bool` and a descriptive `limitation_note`. The endpoint `GET /api/measurements/inference-dataset` automatically filters and quarantines low-quality telemetry windows from model inference, returning only verified clean data alongside an explicit exclusion breakdown. Verified via [tests/test_phase4_assessment_and_inference_exclusion.py](file:///d:/projects/health%20tracker/tests/test_phase4_assessment_and_inference_exclusion.py).
