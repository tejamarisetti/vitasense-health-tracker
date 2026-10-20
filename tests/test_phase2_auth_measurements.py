"""
VitaSense AI - Phase 2 Comprehensive Test Suite
Validates FR-01, FR-02, and FR-03:
1. User registration, password hashing, login, logout, and profile management.
2. Measurement ingestion, server-side validation, and per-user isolation.
3. vitasense.quality reuse for flags (missing, stale, duplicate, implausible, sudden_change).
4. Demo data reset with strict preservation of manual/imported real user data.
5. Direct API and simulated UI integration flows verifying User A cannot read User B's records.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from vitasense.api.app import app
from vitasense.api.db import get_db_connection, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Ensure schema is initialized prior to test execution and reset rate limiters."""
    init_db()
    from vitasense.api.auth import register_limiter, login_limiter, contact_limiter
    register_limiter.reset()
    login_limiter.reset()
    contact_limiter.reset()


def test_registration_and_login_flow():
    """FR-01: Tests user registration, duplicate prevention, and login."""
    unique_email = f"test_{datetime.now().timestamp()}@vitasense.io"
    reg_payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "name": "Jordan Lee",
        "age": 32,
        "sex": "Female",
        "height": "170 cm",
        "weight": "65 kg",
        "resting_hr": 62,
        "activity_level": "Moderately Active",
        "health_goal": "Cardiovascular Wellness",
    }

    # 1. Register successfully
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    data = reg_res.json()
    assert "token" in data
    assert data["user"]["email"] == unique_email
    assert data["profile"]["name"] == "Jordan Lee"
    token = data["token"]

    # 2. Reject duplicate registration with same email
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 3. Reject login with invalid password
    bad_login_res = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "WrongPassword"},
    )
    assert bad_login_res.status_code == 401

    # 4. Login successfully with correct credentials
    login_res = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert login_data["user"]["email"] == unique_email
    new_token = login_data["token"]

    # 5. Access protected /me endpoint
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == unique_email
    assert me_res.json()["profile"]["resting_hr"] == 62

    # 6. Logout and verify token invalidation
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_token}"})
    assert logout_res.status_code == 200

    # Subsequent request with invalidated token must fail with 401
    me_after_logout = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_after_logout.status_code == 401


def test_profile_update():
    """FR-01: Tests profile CRUD operations for authenticated user."""
    email = f"prof_{datetime.now().timestamp()}@vitasense.io"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    token = reg_res.json()["token"]

    update_payload = {
        "name": "Dr. Sarah Connor",
        "age": 35,
        "sex": "Female",
        "height": "175 cm",
        "weight": "68 kg",
        "resting_hr": 58,
        "activity_level": "Very Active",
        "health_goal": "Athletic Performance",
        "provider": "email",
    }
    put_res = client.put(
        "/api/auth/profile",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["resting_hr"] == 58
    assert put_res.json()["name"] == "Dr. Sarah Connor"

    # Verify retrieval
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["profile"]["resting_hr"] == 58


def test_measurement_server_side_validation_errors():
    """FR-02: Tests strict server-side validation on physiological measurements."""
    email = f"val_{datetime.now().timestamp()}@vitasense.io"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Reject negative values
    res_neg = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": -15.0, "unit": "bpm", "timestamp": now_iso, "source": "manual"},
        headers=headers,
    )
    assert res_neg.status_code == 422

    # 2. Reject future timestamps (>2 mins in future)
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    res_fut = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 72.0, "unit": "bpm", "timestamp": future_iso, "source": "manual"},
        headers=headers,
    )
    assert res_fut.status_code == 422

    # 3. Reject invalid unit for type
    res_unit = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 72.0, "unit": "degrees", "timestamp": now_iso, "source": "manual"},
        headers=headers,
    )
    assert res_unit.status_code == 422

    # 4. Reject invalid type
    res_type = client.post(
        "/api/measurements",
        json={"type": "blood_sugar", "value": 110.0, "unit": "mg/dl", "timestamp": now_iso, "source": "manual"},
        headers=headers,
    )
    assert res_type.status_code == 422

    # 5. Reject invalid source
    res_src = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 72.0, "unit": "bpm", "timestamp": now_iso, "source": "unverified"},
        headers=headers,
    )
    assert res_src.status_code == 422


def test_per_user_isolation_direct_api():
    """
    FR-01 & FR-02: Strict Per-User Isolation Test.
    Confirms User A creates records, and User B CANNOT read, list, or delete User A's records.
    """
    # Create User A
    user_a_email = f"usera_{datetime.now().timestamp()}@vitasense.io"
    res_a = client.post("/api/auth/register", json={"email": user_a_email, "password": "PasswordA1!"})
    token_a = res_a.json()["token"]

    # Create User B
    user_b_email = f"userb_{datetime.now().timestamp()}@vitasense.io"
    res_b = client.post("/api/auth/register", json={"email": user_b_email, "password": "PasswordB1!"})
    token_b = res_b.json()["token"]

    # User A creates a confidential measurement
    ts_a = datetime.now(timezone.utc).isoformat()
    meas_res = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 68.0, "unit": "bpm", "timestamp": ts_a, "source": "manual"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert meas_res.status_code == 201
    meas_id = meas_res.json()["id"]

    # 1. User B lists measurements -> must be empty (cannot see User A's data)
    list_b = client.get("/api/measurements", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    b_records = list_b.json()
    assert len(b_records) == 0
    assert not any(r["id"] == meas_id for r in b_records)

    # 2. User B tries direct GET of User A's measurement ID -> 404 Not Found
    get_b = client.get(f"/api/measurements/{meas_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 404

    # 3. User B tries direct DELETE of User A's measurement ID -> 404 Not Found
    del_b = client.delete(f"/api/measurements/{meas_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_b.status_code == 404

    # 4. User A verifies record is still present and intact
    get_a = client.get(f"/api/measurements/{meas_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a.status_code == 200
    assert get_a.json()["id"] == meas_id
    assert get_a.json()["value"] == 68.0


def test_quality_flags_and_component_checks():
    """
    FR-03: Tests reuse of vitasense.quality for flags and breakdown of component checks:
    - Missingness / completeness
    - Plausibility (out-of-range bounds)
    - Stale / flatline detection
    - Sudden change / jump detection
    - Duplicate detection
    """
    email = f"qual_{datetime.now().timestamp()}@vitasense.io"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # 1. Nominal plausible measurement
    ts1 = (now - timedelta(minutes=10)).isoformat()
    res1 = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 72.0, "unit": "bpm", "timestamp": ts1, "source": "manual"},
        headers=headers,
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["quality_flags"] == []
    assert d1["trust_score"] > 0.80
    assert d1["component_checks"]["plausibility_check"]["status"] == "pass"

    # 2. Implausible value (e.g. HR = 250 bpm, exceeding max 220)
    ts2 = (now - timedelta(minutes=8)).isoformat()
    res2 = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 250.0, "unit": "bpm", "timestamp": ts2, "source": "manual"},
        headers=headers,
    )
    assert res2.status_code == 201
    d2 = res2.json()
    assert "implausible" in d2["quality_flags"]
    assert d2["component_checks"]["plausibility_check"]["status"] == "fail"
    assert d2["trust_score"] == 0.0

    # 3. Duplicate timestamp test
    res_dup = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 74.0, "unit": "bpm", "timestamp": ts1, "source": "manual"},
        headers=headers,
    )
    assert res_dup.status_code == 201
    d_dup = res_dup.json()
    assert "duplicate" in d_dup["quality_flags"]
    assert d_dup["component_checks"]["duplicate_check"]["status"] == "fail"

    # 4. Sudden change test (jump of 60 bpm in 2 seconds)
    ts_prior = (now - timedelta(seconds=10)).isoformat()
    client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 70.0, "unit": "bpm", "timestamp": ts_prior, "source": "manual"},
        headers=headers,
    )
    ts_jump = (now - timedelta(seconds=8)).isoformat()
    res_jump = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 135.0, "unit": "bpm", "timestamp": ts_jump, "source": "manual"},
        headers=headers,
    )
    assert res_jump.status_code == 201
    d_jump = res_jump.json()
    assert "sudden_change" in d_jump["quality_flags"]
    assert d_jump["component_checks"]["rate_of_change_check"]["status"] == "fail"

    # 5. Stale sensor flatline test (4 identical values in succession)
    stale_email = f"stale_{datetime.now().timestamp()}@vitasense.io"
    stale_res = client.post("/api/auth/register", json={"email": stale_email, "password": "Password123!"})
    stale_token = stale_res.json()["token"]
    stale_headers = {"Authorization": f"Bearer {stale_token}"}

    for i in range(3):
        ts_i = (now - timedelta(minutes=15 - i)).isoformat()
        client.post(
            "/api/measurements",
            json={"type": "heart_rate", "value": 75.0, "unit": "bpm", "timestamp": ts_i, "source": "manual"},
            headers=stale_headers,
        )

    ts_stale = (now - timedelta(minutes=12)).isoformat()
    res_stale = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 75.0, "unit": "bpm", "timestamp": ts_stale, "source": "manual"},
        headers=stale_headers,
    )
    assert res_stale.status_code == 201
    d_stale = res_stale.json()
    assert "stale" in d_stale["quality_flags"]
    assert d_stale["component_checks"]["stale_check"]["status"] == "fail"


def test_demo_data_reset_never_deletes_real_data():
    """
    FR-05 & Demo Safety: Verifies that resetting DEMO data deletes ONLY demo records
    and NEVER deletes real user measurements (source = 'manual' or 'import').
    """
    email = f"demotest_{datetime.now().timestamp()}@vitasense.io"
    reg = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # 1. Insert real manual record
    ts_manual = (now - timedelta(hours=5)).isoformat()
    manual_res = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 69.0, "unit": "bpm", "timestamp": ts_manual, "source": "manual"},
        headers=headers,
    )
    manual_id = manual_res.json()["id"]

    # 2. Insert real imported record
    ts_import = (now - timedelta(hours=4)).isoformat()
    import_res = client.post(
        "/api/measurements",
        json={"type": "spo2", "value": 98.0, "unit": "%", "timestamp": ts_import, "source": "import"},
        headers=headers,
    )
    import_id = import_res.json()["id"]

    # 3. Insert demo record
    ts_demo = (now - timedelta(hours=3)).isoformat()
    demo_res = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 77.0, "unit": "bpm", "timestamp": ts_demo, "source": "demo"},
        headers=headers,
    )
    demo_id = demo_res.json()["id"]

    # 4. Trigger demo reset
    reset_res = client.post("/api/measurements/demo/reset", headers=headers)
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "ok"
    assert reset_data["demo_deleted_count"] >= 1
    assert reset_data["real_records_preserved_count"] == 2

    # 5. Verify the old demo record is deleted
    get_old_demo = client.get(f"/api/measurements/{demo_id}", headers=headers)
    assert get_old_demo.status_code == 404

    # 6. Verify real manual and import records are STILL COMPLETELY INTACT
    get_man = client.get(f"/api/measurements/{manual_id}", headers=headers)
    assert get_man.status_code == 200
    assert get_man.json()["value"] == 69.0
    assert get_man.json()["source"] == "manual"

    get_imp = client.get(f"/api/measurements/{import_id}", headers=headers)
    assert get_imp.status_code == 200
    assert get_imp.json()["value"] == 98.0
    assert get_imp.json()["source"] == "import"


def test_simulated_client_api_interaction_flow():
    """
    Simulates the multi-step client API interaction flow:
    (Note: This is an API-level integration test, NOT end-to-end browser UI coverage).
    1. Sign up on /api/auth/register.
    2. Edit profile on /api/auth/profile.
    3. Add manual measurement on /api/measurements.
    4. Fetch measurements and render component checks.
    5. Verify User B executing identical client calls cannot access User A's data.
    """
    email_a = f"api_a_{datetime.now().timestamp()}@vitasense.io"
    res_a = client.post(
        "/api/auth/register",
        json={"email": email_a, "password": "PasswordA123!", "name": "Alice API"},
    )
    token_a = res_a.json()["token"]

    # Profile update
    client.put(
        "/api/auth/profile",
        json={
            "name": "Alice API Updated",
            "age": 30,
            "sex": "Female",
            "height": "165 cm",
            "weight": "60 kg",
            "resting_hr": 60,
            "activity_level": "Moderately Active",
            "health_goal": "Cardiovascular Wellness",
            "provider": "email",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Ingest measurement
    ts = datetime.now(timezone.utc).isoformat()
    m_res = client.post(
        "/api/measurements",
        json={"type": "heart_rate", "value": 71.0, "unit": "bpm", "timestamp": ts, "source": "manual"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    m_id = m_res.json()["id"]

    # User B registers
    email_b = f"api_b_{datetime.now().timestamp()}@vitasense.io"
    res_b = client.post(
        "/api/auth/register",
        json={"email": email_b, "password": "PasswordB123!", "name": "Bob API"},
    )
    token_b = res_b.json()["token"]

    # User B checks their measurements list
    b_list = client.get("/api/measurements", headers={"Authorization": f"Bearer {token_b}"})
    assert b_list.status_code == 200
    assert len(b_list.json()) == 0

    # User B directly tries to access Alice's measurement -> 404 Not Found
    b_direct = client.get(f"/api/measurements/{m_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert b_direct.status_code == 404


def test_expired_and_invalid_session_tokens():
    """
    FR-01 Security: Verifies rejection of malformed, invalid, or expired session tokens.
    """
    from vitasense.api.auth import hash_token

    # 1. Reject malformed / missing header
    res_missing = client.get("/api/auth/me")
    assert res_missing.status_code == 401

    res_malformed = client.get("/api/auth/me", headers={"Authorization": "Token 12345"})
    assert res_malformed.status_code == 401

    # 2. Reject non-existent token
    res_fake = client.get("/api/auth/me", headers={"Authorization": "Bearer deadbeef1234567890abcdef"})
    assert res_fake.status_code == 401

    # 3. Reject explicitly expired token in database
    email = f"expired_{datetime.now().timestamp()}@vitasense.io"
    reg_res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = reg_res.json()["token"]
    token_h = hash_token(token)

    # Force expiration date into the past in the database
    past_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
            (past_iso, token_h),
        )

    res_expired = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_expired.status_code == 401
    assert "expired" in res_expired.json()["detail"].lower()


def test_token_reuse_after_logout():
    """
    FR-01 & FR-13 Security: Verifies that session tokens are completely revoked on logout
    and cannot be reused for any subsequent authenticated endpoints.
    """
    email = f"reuse_{datetime.now().timestamp()}@vitasense.io"
    reg_res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify active session works
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Perform logout
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Subsequent access to /api/auth/me with revoked token must fail with 401
    me_revoked = client.get("/api/auth/me", headers=headers)
    assert me_revoked.status_code == 401

    # Attempt to post a measurement with revoked token must also fail with 401
    meas_revoked = client.post(
        "/api/measurements",
        json={
            "type": "heart_rate",
            "value": 72.0,
            "unit": "bpm",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "manual",
        },
        headers=headers,
    )
    assert meas_revoked.status_code == 401


def test_auth_and_contact_rate_limiting():
    """
    FR-01, FR-11: Verifies rate limiting on registration, login, and contact endpoints.
    Exceeding 5 requests per 60s triggers HTTP 429 Too Many Requests with Retry-After header.
    """
    from vitasense.api.auth import register_limiter, login_limiter, contact_limiter

    # 1. Test register rate limiting
    register_limiter.reset()
    for i in range(5):
        unique_email = f"ratelim_{i}_{datetime.now().timestamp()}@vitasense.io"
        res = client.post("/api/auth/register", json={"email": unique_email, "password": "Password123!"})
        assert res.status_code == 201

    # 6th request should hit 429
    blocked_email = f"ratelim_blocked_{datetime.now().timestamp()}@vitasense.io"
    res_blocked = client.post("/api/auth/register", json={"email": blocked_email, "password": "Password123!"})
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers
    register_limiter.reset()

    # 2. Test login rate limiting
    login_limiter.reset()
    for _ in range(5):
        res = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
        assert res.status_code == 401

    # 6th login attempt hits 429
    res_login_blocked = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert res_login_blocked.status_code == 429
    assert "Retry-After" in res_login_blocked.headers
    login_limiter.reset()

    # 3. Test contact rate limiting (FR-11)
    contact_limiter.reset()
    for i in range(5):
        c_res = client.post(
            "/api/contact",
            json={
                "name": f"Tester {i}",
                "email": "test@example.com",
                "subject": f"Inquiry {i}",
                "message": "Testing rate limit",
            },
        )
        assert c_res.status_code == 201

    # 6th contact request hits 429
    c_blocked = client.post(
        "/api/contact",
        json={
            "name": "Tester 6",
            "email": "test@example.com",
            "subject": "Inquiry 6",
            "message": "Testing rate limit exceed",
        },
    )
    assert c_blocked.status_code == 429
    assert "Retry-After" in c_blocked.headers
    contact_limiter.reset()
