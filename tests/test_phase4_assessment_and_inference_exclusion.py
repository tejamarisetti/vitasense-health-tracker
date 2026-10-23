"""
VitaSense AI - Phase 4 Integration Tests
Validates:
- FR-04: Low-quality telemetry data exclusion from ML model inference and limitation flagging.
- FR-06: Symptom questionnaire, pre-submission review/edit step, screening risk categorization,
         contributing factors, and clinical safety disclaimers.
- FR-07: Transparent AI/ML explanation, feature contributions, calibrated uncertainty intervals,
         and model version provenance.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from vitasense.api.app import app
from vitasense.api.auth import register_limiter, login_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_rate_limiters():
    register_limiter.requests.clear()
    login_limiter.requests.clear()
    yield


def get_authenticated_client(email_prefix: str = "phase4_user"):
    register_limiter.requests.clear()
    email = f"{email_prefix}_{datetime.now().timestamp()}@vitasense.io"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert res.status_code == 201
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return email, headers


def test_fr04_inference_exclusion_and_dataset_endpoint():
    """FR-04: Tests that low-quality records are flagged and quarantined from ML inference."""
    _, headers = get_authenticated_client("fr04_user")
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Ingest clean measurement
    res_clean = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 72.0, "unit": "bpm", "timestamp": now_iso, "source": "manual"},
        headers=headers,
    )
    assert res_clean.status_code == 201
    clean_data = res_clean.json()
    assert clean_data["exclude_from_inference"] is False
    assert clean_data["limitation_note"] is None

    # 2. Ingest implausible measurement (e.g. 280 bpm out of bounds)
    res_bad = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 280.0, "unit": "bpm", "timestamp": now_iso, "source": "manual"},
        headers=headers,
    )
    assert res_bad.status_code == 201
    bad_data = res_bad.json()
    assert bad_data["exclude_from_inference"] is True
    assert "implausible" in bad_data["quality_flags"]
    assert "Excluded from ML inference" in bad_data["limitation_note"]

    # 3. Query inference-dataset endpoint
    inf_res = client.get("/api/measurements/inference-dataset", headers=headers)
    assert inf_res.status_code == 200
    inf_data = inf_res.json()
    assert inf_data["total_records"] >= 2
    assert inf_data["excluded_records"] >= 1
    assert inf_data["exclusion_breakdown"]["implausible"] >= 1
    assert any(rec["id"] == clean_data["id"] for rec in inf_data["clean_records"])
    assert all(rec["id"] != bad_data["id"] for rec in inf_data["clean_records"])
    assert "quarantined and excluded from model inference" in inf_data["inference_limitation_statement"]


def test_fr06_symptom_questionnaire_review_step():
    """FR-06: Tests questionnaire review step prior to submission."""
    _, headers = get_authenticated_client("fr06_review")
    payload = {
        "primary_symptom": "racing_heart",
        "intensity": "moderate",
        "duration": "15_to_30m",
        "activity_context": "resting",
        "warning_signs": ["radiating_pain"],
        "notes": "Felt sudden flutter while watching television",
        "is_demo": False,
    }

    # Step 2 Review Endpoint
    review_res = client.post("/api/assessment/review", json=payload, headers=headers)
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["is_valid"] is True
    assert review_data["ready_for_submission"] is True
    assert "Racing Heart" in review_data["summary"]["Primary Symptom"]
    assert "Resting" in review_data["summary"]["Activity Context"]
    assert "review your answers carefully" in review_data["notice"]


def test_fr06_fr07_assessment_submission_and_explanation():
    """FR-06 & FR-07: Tests submission, screening categorization, and transparent ML explanations."""
    _, headers = get_authenticated_client("fr06_submit")
    payload = {
        "primary_symptom": "chest_tightness",
        "intensity": "severe",
        "duration": "over_30m",
        "activity_context": "resting",
        "warning_signs": ["radiating_pain", "acute_breathlessness"],
        "notes": "High tightness at rest",
        "is_demo": False,
    }

    # Submit assessment
    sub_res = client.post("/api/assessment/submit", json=payload, headers=headers)
    assert sub_res.status_code == 201
    res_data = sub_res.json()

    # FR-06 Validation
    assert res_data["risk_level"] in ("Elevated Risk Signal", "Moderate Risk Signal")
    assert res_data["risk_score"] > 0.60
    assert len(res_data["contributing_factors"]) >= 2
    assert "NOT a medical diagnosis" in res_data["disclaimer"]
    assert "Seek immediate emergency medical care" in res_data["when_to_seek_care"]

    # FR-07 Validation: Model labelled as DEMO RULESET v2.1, not evaluated
    assert res_data["model_version"] == "DEMO RULESET v2.1, not evaluated"
    feat_contribs = res_data["feature_contributions"]
    assert "symptom_severity_factor" in feat_contribs
    assert "activity_context_factor" in feat_contribs
    assert "red_flag_indicators_factor" in feat_contribs
    assert feat_contribs["symptom_severity_factor"] > 0.0

    # Uncertainty note: uncertainty not estimated for this demo ruleset
    assert res_data["uncertainty_note"] == "uncertainty not estimated for this demo ruleset"
    assert res_data["uncertainty_range"] is None

    # History & Latest checks
    latest_res = client.get("/api/assessment/latest", headers=headers)
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == res_data["id"]

    hist_res = client.get("/api/history?category=assessments", headers=headers)
    assert hist_res.status_code == 200
    hist_items = hist_res.json()["items"]
    assert len(hist_items) >= 1
    assert hist_items[0]["category"] == "assessment"


def test_fr06_user_isolation_for_assessments():
    """FR-06: Strict per-user isolation for symptom assessment records."""
    _, headers_a = get_authenticated_client("user_a")
    _, headers_b = get_authenticated_client("user_b")

    payload = {
        "primary_symptom": "palpitations",
        "intensity": "mild",
        "duration": "under_5m",
        "activity_context": "sitting_desk",
        "warning_signs": [],
        "is_demo": False,
    }

    sub_a = client.post("/api/assessment/submit", json=payload, headers=headers_a)
    assert sub_a.status_code == 201
    assess_id = sub_a.json()["id"]

    # User B lists assessments -> must be empty
    list_b = client.get("/api/assessment/history", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0
    assert not any(a["id"] == assess_id for a in list_b.json())

    # User A lists assessments -> contains their own record
    list_a = client.get("/api/assessment/history", headers=headers_a)
    assert list_a.status_code == 200
    assert any(a["id"] == assess_id for a in list_a.json())
