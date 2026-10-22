"""
VitaSense AI - Phase 3 Automated Test Suite
Tests for:
(a) FR-11: Contact Us form with server validation, secure storage, truthful success/failure, rate limit, no health data in logs.
(b) FR-09: Alerts for user's own records with acknowledge/dismiss that never deletes the event, duplicate suppression, informational-only wording.
(c) FR-10: History of user's own measurements, alerts and assessments with filters and pagination.
(d) FR-13: Data export and account deletion for signed-in user only.
"""

import pytest
import logging
from fastapi.testclient import TestClient

from vitasense.api.app import app
from vitasense.api.db import get_db_connection, init_db
from vitasense.api.auth import contact_limiter, register_limiter, login_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    contact_limiter.requests.clear()
    register_limiter.requests.clear()
    login_limiter.requests.clear()
    yield


import uuid

def register_user(email: str, password: str = "SecurePass123!", name: str = "Test User"):
    unique_email = f"{email.split('@')[0]}_{uuid.uuid4().hex[:8]}@{email.split('@')[1]}"
    res = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": password, "name": name},
    )
    assert res.status_code == 201
    data = res.json()
    return data["token"], data["user"]


# ==============================================================================
# (a) FR-11: Contact Us Tests
# ==============================================================================

def test_contact_submission_success_and_secure_storage():
    res = client.post(
        "/api/contact",
        json={
            "name": "Alex Morgan",
            "email": "alex.morgan@example.com",
            "subject": "Platform inquiry",
            "message": "Question regarding data privacy and local storage.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "ok"
    assert "Inquiry received and securely stored" in data["message"]

    # Verify saved in SQLite contact_messages table
    with get_db_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM contact_messages WHERE email = ? ORDER BY id DESC LIMIT 1",
            ("alex.morgan@example.com",),
        )
        row = cur.fetchone()
        assert row is not None
        assert row["name"] == "Alex Morgan"
        assert row["subject"] == "Platform inquiry"
        assert row["message"] == "Question regarding data privacy and local storage."


def test_contact_server_validation_invalid_email():
    res = client.post(
        "/api/contact",
        json={
            "name": "Jane",
            "email": "invalid-email-format",
            "subject": "Hello",
            "message": "Test message.",
        },
    )
    assert res.status_code == 422


def test_contact_server_validation_empty_or_too_long():
    # Empty message
    res = client.post(
        "/api/contact",
        json={"name": "Jane", "email": "jane@example.com", "subject": "Hello", "message": ""},
    )
    assert res.status_code == 422

    # Message exceeding 2000 chars
    res = client.post(
        "/api/contact",
        json={
            "name": "Jane",
            "email": "jane@example.com",
            "subject": "Hello",
            "message": "A" * 2001,
        },
    )
    assert res.status_code == 422


def test_contact_script_injection_protection():
    res = client.post(
        "/api/contact",
        json={
            "name": "Attacker",
            "email": "hacker@example.com",
            "subject": "XSS Probe",
            "message": "<script>alert('pwned')</script>",
        },
    )
    assert res.status_code == 422


def test_contact_rate_limiting():
    # Allow 5 submissions, 6th should return 429
    for i in range(5):
        res = client.post(
            "/api/contact",
            json={
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "subject": "Rate limit check",
                "message": f"Message number {i}",
            },
        )
        assert res.status_code == 201

    res_blocked = client.post(
        "/api/contact",
        json={
            "name": "User 6",
            "email": "user6@example.com",
            "subject": "Rate limit check",
            "message": "Blocked message",
        },
    )
    assert res_blocked.status_code == 429
    assert "Too many contact submissions" in res_blocked.json()["detail"]


def test_contact_logging_zero_health_data(caplog):
    caplog.set_level(logging.INFO)
    sensitive_text = "Patient glucose 145 mg/dL with arrhythmia symptoms"
    res = client.post(
        "/api/contact",
        json={
            "name": "Test User",
            "email": "patient@example.com",
            "subject": "Health query",
            "message": sensitive_text,
        },
    )
    assert res.status_code == 201

    # Verify that the sensitive message text is NEVER printed in logs
    log_output = "\n".join([rec.message for rec in caplog.records])
    assert sensitive_text not in log_output
    assert "Contact submission successfully saved" in log_output


# ==============================================================================
# (b) FR-09: User Alerts Lifecycle Tests
# ==============================================================================

def test_alert_creation_and_informational_wording():
    token_a, user_a = register_user("alert_a@example.com")
    res = client.post(
        "/api/alerts",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "type": "heart_rate",
            "title": "Elevated Pulse Observation",
            "message": "Heart rate observed at 112 bpm during resting period.",
            "severity": "warning",
            "reason": "Resting baseline deviation >25 bpm",
            "recommended_step": "Rest for 10 minutes and re-test.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Elevated Pulse Observation"
    assert data["status"] == "active"
    assert data["severity"] == "warning"
    assert "Informational notice only" in data["disclaimer"]


def test_alert_duplicate_suppression_refractory_window():
    token, _ = register_user("duplicate_alert@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "type": "spo2_drop",
        "title": "SpO2 Transitory Dip",
        "message": "Observed reading below 94%.",
        "severity": "warning",
    }

    res1 = client.post("/api/alerts", headers=headers, json=payload)
    assert res1.status_code == 201
    id1 = res1.json()["id"]

    # Second immediate call with identical type and title should be suppressed (returning existing alert id)
    res2 = client.post("/api/alerts", headers=headers, json=payload)
    assert res2.status_code == 200 or res2.status_code == 201
    id2 = res2.json()["id"]
    assert id1 == id2


def test_alert_per_user_isolation():
    token_a, _ = register_user("user_a_alerts@example.com")
    token_b, _ = register_user("user_b_alerts@example.com")

    # User A creates alert
    client.post(
        "/api/alerts",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "type": "tachycardia_warn",
            "title": "User A Private Alert",
            "message": "Private heart rate signal.",
            "severity": "info",
        },
    )

    # User B lists alerts
    res_b = client.get("/api/alerts", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    alerts_b = res_b.json()
    assert len(alerts_b) == 0

    # User A lists alerts
    res_a = client.get("/api/alerts", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    alerts_a = res_a.json()
    assert len(alerts_a) == 1
    assert alerts_a[0]["title"] == "User A Private Alert"


def test_alert_acknowledge_and_dismiss_never_deletes_event():
    token, _ = register_user("ack_dismiss_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create alert
    res_create = client.post(
        "/api/alerts",
        headers=headers,
        json={
            "type": "arrhythmia_eval",
            "title": "Irregular Rhythm Signal",
            "message": "Transient pulse irregularity noted.",
            "severity": "info",
        },
    )
    alert_id = res_create.json()["id"]

    # 2. Acknowledge alert
    res_ack = client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)
    assert res_ack.status_code == 200
    data_ack = res_ack.json()
    assert data_ack["status"] == "acknowledged"
    assert data_ack["acknowledged_at"] is not None

    # Confirm event is STILL in database
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM user_alerts WHERE id = ?", (alert_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["status"] == "acknowledged"

    # 3. Dismiss alert
    res_dism = client.post(f"/api/alerts/{alert_id}/dismiss", headers=headers)
    assert res_dism.status_code == 200
    data_dism = res_dism.json()
    assert data_dism["status"] == "dismissed"
    assert data_dism["dismissed_at"] is not None

    # Confirm event is NEVER deleted from database
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM user_alerts WHERE id = ?", (alert_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["status"] == "dismissed"


# ==============================================================================
# (c) FR-10: History of User's Own Records Tests
# ==============================================================================

def test_user_history_pagination_and_filters():
    token, user = register_user("history_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Add 5 measurements
    for i in range(5):
        client.post(
            "/api/measurements",
            headers=headers,
            json={
                "type": "heart_rate",
                "value": 70.0 + i,
                "unit": "bpm",
                "timestamp": f"2026-10-20T10:0{i}:00Z",
                "source": "manual",
            },
        )

    # Add 2 alerts
    for i in range(2):
        client.post(
            "/api/alerts",
            headers=headers,
            json={
                "type": "pulse_warn",
                "title": f"Alert {i}",
                "message": f"Sample alert {i}",
                "severity": "info",
            },
        )

    # Query all history with pagination (page_size=3)
    res_p1 = client.get("/api/history?page=1&page_size=3", headers=headers)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 3
    assert data_p1["pagination"]["page"] == 1
    assert data_p1["pagination"]["total_items"] == 7
    assert data_p1["pagination"]["total_pages"] == 3
    assert data_p1["pagination"]["has_next"] is True

    # Filter category = measurements
    res_meas = client.get("/api/history?category=measurements", headers=headers)
    assert res_meas.status_code == 200
    data_meas = res_meas.json()
    assert data_meas["pagination"]["total_items"] == 5
    assert all(item["category"] == "measurement" for item in data_meas["items"])

    # Filter category = alerts
    res_alerts = client.get("/api/history?category=alerts", headers=headers)
    assert res_alerts.status_code == 200
    data_alerts = res_alerts.json()
    assert data_alerts["pagination"]["total_items"] == 2
    assert all(item["category"] == "alert" for item in data_alerts["items"])


def test_user_history_isolation():
    token_a, _ = register_user("history_a@example.com")
    token_b, _ = register_user("history_b@example.com")

    client.post(
        "/api/measurements",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "type": "spo2",
            "value": 98.0,
            "unit": "%",
            "timestamp": "2026-10-20T12:00:00Z",
            "source": "manual",
        },
    )

    # User B history should be empty
    res_b = client.get("/api/history", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["pagination"]["total_items"] == 0


# ==============================================================================
# (d) FR-13: Data Export and Account Deletion Tests
# ==============================================================================

def test_user_data_export_and_sanitization():
    token, user = register_user("export_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Add measurement and alert
    client.post(
        "/api/measurements",
        headers=headers,
        json={
            "type": "heart_rate",
            "value": 75.0,
            "unit": "bpm",
            "timestamp": "2026-10-20T14:00:00Z",
            "source": "manual",
        },
    )
    client.post(
        "/api/alerts",
        headers=headers,
        json={
            "type": "heart_rate",
            "title": "Export Test Alert",
            "message": "Informational alert for export.",
            "severity": "info",
        },
    )

    res = client.get("/api/auth/export", headers=headers)
    assert res.status_code == 200
    export_bundle = res.json()

    assert export_bundle["export_metadata"]["user_id"] == user["id"]
    assert export_bundle["account"]["email"] == user["email"]
    # STRICT PRIVACY: verify password, password_hash, salt are NEVER exported
    assert "password" not in export_bundle["account"]
    assert "password_hash" not in export_bundle["account"]
    assert "salt" not in export_bundle["account"]

    assert len(export_bundle["measurements"]) == 1
    assert len(export_bundle["alerts"]) == 1
    assert export_bundle["profile"]["name"] == "Test User"


def test_user_account_deletion_cascades_all_data():
    token, user = register_user("delete_me@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = user["id"]

    # Seed profile, measurement, and alert
    client.post(
        "/api/measurements",
        headers=headers,
        json={
            "type": "respiratory_rate",
            "value": 16.0,
            "unit": "brpm",
            "timestamp": "2026-10-20T15:00:00Z",
            "source": "manual",
        },
    )
    client.post(
        "/api/alerts",
        headers=headers,
        json={
            "type": "respiratory_rate",
            "title": "Deletion Test Alert",
            "message": "Testing cascade on deletion.",
            "severity": "info",
        },
    )

    # Perform account deletion
    res_del = client.delete("/api/auth/account", headers=headers)
    assert res_del.status_code == 200
    assert "permanently deleted" in res_del.json()["message"]

    # Verify everything cascaded in SQLite
    with get_db_connection() as conn:
        assert conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone() is None
        assert conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone() is None
        assert conn.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,)).fetchone() is None
        assert conn.execute("SELECT * FROM measurements WHERE user_id = ?", (user_id,)).fetchone() is None
        assert conn.execute("SELECT * FROM user_alerts WHERE user_id = ?", (user_id,)).fetchone() is None

    # Verify session token is dead
    res_dead_token = client.get("/api/auth/me", headers=headers)
    assert res_dead_token.status_code == 401
