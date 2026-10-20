# VitaSense AI - PRD Traceability Matrix

**Document Version:** 2.0.0  
**Generated Date:** 2026-10-20  
**PRD Reference:** `docs/PRD.pdf` (*Note: File was not present on disk at run time; requirements and numbering adhere strictly to the user-specified authoritative FR list without guessing.*)

---

## 1. Executive Summary & Traceability Overview

This matrix maps every Functional Requirement (FR-01 through FR-13) to its current implementation status, source files, and automated test coverage.

- **Total Functional Requirements:** 13
- **Implemented:** 12
- **Partial:** 1 (FR-04 Data Quality Engine: quality flags and component checks exist, but exclusion from downstream ML inference is not yet implemented)
- **Not Started:** 0

---

## 2. Comprehensive Traceability Matrix

| FR ID | Feature Name | Status | Implementation Files | Automated Test References | Notes / Architectural Details |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **FR-01** | **User Authentication** | **Implemented** | [auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)<br>[db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)<br>[LoginPage.tsx](file:///d:/projects/health%20tracker/src/pages/LoginPage.tsx)<br>[CreateAccountPage.tsx](file:///d:/projects/health%20tracker/src/pages/CreateAccountPage.tsx) | [test_phase2_auth_measurements.py:L27-L86](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L27-L86)<br>[test_phase2_auth_measurements.py:L441-L573](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L441-L573) | Hardened PBKDF2-HMAC-SHA256 (600,000 iterations); session tokens hashed with SHA-256 before storage in SQLite; rate limiting on register & login (5 req/min per IP); expired/revoked token enforcement; password reset marked "not enabled" in UI. |
| **FR-02** | **User Profile** | **Implemented** | [auth.py:L268-L308](file:///d:/projects/health%20tracker/vitasense/api/auth.py#L268-L308)<br>[ProfileModal.tsx](file:///d:/projects/health%20tracker/src/components/ProfileModal.tsx)<br>[types.ts](file:///d:/projects/health%20tracker/src/types.ts) | [test_phase2_auth_measurements.py:L88-L124](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L88-L124) | Structured profile CRUD (age, biological sex, height, weight, resting HR baseline, activity level, cardiovascular health goal). Stored in `user_profiles` table with foreign key cascade. |
| **FR-03** | **Physiological Measurements** | **Implemented** | [measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)<br>[db.py](file:///d:/projects/health%20tracker/vitasense/api/db.py)<br>[TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx) | [test_phase2_auth_measurements.py:L126-L230](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L126-L230) | Server-side validation for type (`heart_rate`, `spo2`, `respiratory_rate`, `hrv`), value (finite, non-negative), unit consistency, ISO8601 timestamp (clock-skew & future limit), and source (`manual`, `import`, `demo`). Strict per-user isolation. |
| **FR-04** | **Data Quality Engine** | **Partial** | [trust_score.py](file:///d:/projects/health%20tracker/vitasense/quality/trust_score.py)<br>[measurements.py:L89-L219](file:///d:/projects/health%20tracker/vitasense/api/measurements.py#L89-L219)<br>[TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx) | [test_phase2_auth_measurements.py:L232-L320](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L232-L320)<br>[test_trust_score.py](file:///d:/projects/health%20tracker/tests/test_trust_score.py) | **Partial Implementation:** Detects and flags `missing`, `stale` (sensor flatlines), `duplicate` (timestamps), `implausible` (physiological boundaries), and `sudden_change` (jump rates >40 bpm/s); computes component check breakdown. **Pending:** Automated exclusion of flagged records from downstream ML inference pipelines. |
| **FR-05** | **Real-Time Dashboard** | **Implemented** | [OverviewPage.tsx](file:///d:/projects/health%20tracker/src/pages/OverviewPage.tsx)<br>[MetricCard.tsx](file:///d:/projects/health%20tracker/src/components/MetricCard.tsx)<br>[Waveform.tsx](file:///d:/projects/health%20tracker/src/components/Waveform.tsx) | Verified via frontend build `npm.cmd run build` | Live vital cards (heart rate, SpO₂), animated SVG waveform rendering, daily activity metric stack, and AI insight preview. |
| **FR-06** | **Symptom Risk Assessment** | **Implemented** | [assistant.py](file:///d:/projects/health%20tracker/vitasense/api/assistant.py)<br>[CompanionPage.tsx](file:///d:/projects/health%20tracker/src/pages/CompanionPage.tsx) | [test_assistant_api.py:L14-L85](file:///d:/projects/health%20tracker/tests/test_assistant_api.py#L14-L85) | Safety-aligned intent classification; handles symptom inquiry, structured risk disclaimers, refusal of formal clinical diagnosis, and guidance to consult medical professionals. |
| **FR-07** | **AI/ML Explanation** | **Implemented** | [assistant.py](file:///d:/projects/health%20tracker/vitasense/api/assistant.py)<br>[CompanionPage.tsx](file:///d:/projects/health%20tracker/src/pages/CompanionPage.tsx)<br>[BenchmarkPage.tsx](file:///d:/projects/health%20tracker/src/pages/BenchmarkPage.tsx) | [test_assistant_api.py](file:///d:/projects/health%20tracker/tests/test_assistant_api.py)<br>[test_replay_api.py](file:///d:/projects/health%20tracker/tests/test_replay_api.py) | Explainable telemetry cards, engine indicator (`llm` vs `rule_fallback`), reason codes for abstentions, and pre-registered benchmark arm comparisons. |
| **FR-08** | **Trend Analysis** | **Implemented** | [TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx)<br>[measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py) | [test_phase2_auth_measurements.py](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py) | Multi-day observation windows (24H, 7D, 30D, 3M), deviation from personal resting baseline, and structured export to JSON, CSV, and printable digest. |
| **FR-09** | **Alerts & Notifications** | **Implemented** | [emitter.py](file:///d:/projects/health%20tracker/vitasense/alerts/emitter.py)<br>[AlertsPage.tsx](file:///d:/projects/health%20tracker/src/pages/AlertsPage.tsx) | [test_alert_emitter.py](file:///d:/projects/health%20tracker/tests/test_alert_emitter.py)<br>[test_arm_quarantine.py](file:///d:/projects/health%20tracker/tests/test_arm_quarantine.py) | Persistence filter ($P \in \{10, 20, 30\}\text{s}$), mandatory 60s refractory period ($R = 60\text{s}$), in-app notification inbox, and false-alert triage. |
| **FR-10** | **History & Search** | **Implemented** | [replay.py](file:///d:/projects/health%20tracker/vitasense/api/replay.py)<br>[SignalsPage.tsx](file:///d:/projects/health%20tracker/src/pages/SignalsPage.tsx) | [test_replay_api.py](file:///d:/projects/health%20tracker/tests/test_replay_api.py) | Telemetry replay stream across 15 PPG-DaLiA subjects, offset/limit window queries, and synchronized fault injection inspection. |
| **FR-11** | **Contact Us & Support** | **Implemented** | [auth.py:L310-L334](file:///d:/projects/health%20tracker/vitasense/api/auth.py#L310-L334)<br>[app.py:L43-L49](file:///d:/projects/health%20tracker/vitasense/api/app.py#L43-L49)<br>[SettingsPage.tsx](file:///d:/projects/health%20tracker/src/pages/SettingsPage.tsx) | [test_phase2_auth_measurements.py:L525-L573](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L525-L573) | `POST /api/contact` endpoint with database persistence in `contact_messages`, rate-limiting (5 submissions/min per IP), and frontend contact form. |
| **FR-12** | **Demo Mode & Onboarding** | **Implemented** | [measurements.py:L310-L400](file:///d:/projects/health%20tracker/vitasense/api/measurements.py#L310-L400)<br>[LandingPage.tsx](file:///d:/projects/health%20tracker/src/pages/LandingPage.tsx)<br>[TrendsPage.tsx](file:///d:/projects/health%20tracker/src/pages/TrendsPage.tsx) | [test_phase2_auth_measurements.py:L322-L379](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L322-L379) | Synthetic demo telemetry pre-population with non-destructive reset (`POST /api/measurements/demo/reset`) that deletes ONLY `source = 'demo'` and strictly preserves real user measurements (`source = 'manual'` or `'import'`). |
| **FR-13** | **Privacy & Account Controls** | **Implemented** | [auth.py](file:///d:/projects/health%20tracker/vitasense/api/auth.py)<br>[measurements.py](file:///d:/projects/health%20tracker/vitasense/api/measurements.py)<br>[SettingsPage.tsx](file:///d:/projects/health%20tracker/src/pages/SettingsPage.tsx) | [test_phase2_auth_measurements.py:L177-L230](file:///d:/projects/health%20tracker/tests/test_phase2_auth_measurements.py#L177-L230) | Strict per-user database row isolation (`WHERE user_id = :uid`), session revocation on logout, zero logging of raw credentials/tokens/bodies, and user-initiated data clearing. |

---

## 3. Specific Detail on Partial Requirement (FR-04)

- **What Exists:**
  - `vitasense.quality.trust_score.RuleBasedTrustScorer` computes deterministic multi-component SQI (`S_gap`, `S_stale`, `S_phys`, `S_motion`).
  - `vitasense/api/measurements.py` evaluates all incoming physiological readings against:
    - `missing`: missing values or non-numeric tokens.
    - `stale`: repeated flatline readings (zero variance).
    - `duplicate`: exact timestamp collisions.
    - `implausible`: values outside normative physiological bounds.
    - `sudden_change`: jumps exceeding rate limits ($>40\text{ bpm/s}$).
  - All component checks are serialized to JSON and displayed in the UI drawer.
- **What is Missing to achieve full completion:**
  - Automated inference exclusion: while alerts and quality flags are stored and presented, the offline ML training/inference routines in `vitasense/models/` or baseline predictors do not yet automatically drop or mask flagged windows during batch inference.
