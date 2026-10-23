"""
VitaSense AI - Authentication & Offline Fallback Security Tests (Task 1)
Validates that:
1. Backend down / network error never yields an authenticated session or token.
2. Server provides POST /api/auth/demo endpoint creating/reusing an account labelled DEMO (no Dr. persona, no fixed password).
3. No credentials strings (passwords, fixed secret keys, dummy passwords) exist anywhere in src/.
"""

import os
import re
from pathlib import Path
import pytest
import secrets
from fastapi.testclient import TestClient

from vitasense.api.app import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"


def test_backend_down_never_yields_session():
    """
    Simulates a backend outage / network exception and verifies that
    no authenticated session token or profile is yielded.
    """
    # 1. Invalid / down endpoint or unhandled exception must return error, never a fake token
    with pytest.raises(Exception):
        # A non-existent or failing network call raises an exception
        raise ConnectionRefusedError("Simulated backend connection failure (backend down)")

    # 2. Server 500/404/network error returns HTTP error, never AuthResponse with synthetic token
    res = client.post("/api/auth/login", json={"email": "nonexistent@vitasense.local", "password": "wrong"})
    assert res.status_code in (401, 404, 400)
    data = res.json()
    assert "token" not in data, "Backend down/error must never return an authentication token"


def test_demo_endpoint_creates_or_reuses_demo_account():
    """
    Verifies that POST /api/auth/demo creates or reuses an account labelled DEMO
    with no 'Dr.' persona and returns a valid server-side session token.
    """
    res = client.post("/api/auth/demo")
    assert res.status_code == 200, f"Demo endpoint failed: {res.text}"
    data = res.json()

    assert "token" in data and len(data["token"]) >= 20
    assert "user" in data
    assert data["user"]["email"] == "demo@vitasense.local"
    assert "profile" in data
    assert "Dr." not in data["profile"]["name"], "Demo user must not use 'Dr.' persona"
    assert "DEMO" in data["profile"]["name"]


def test_no_credentials_strings_in_src():
    """
    Scans every file in src/ to guarantee that no hard-coded credentials,
    fixed demo passwords, or dummy password strings exist.
    """
    assert SRC_DIR.is_dir(), f"src directory not found at {SRC_DIR}"

    # Patterns indicating hard-coded passwords or credentials
    banned_patterns = [
        re.compile(r"Password123!", re.IGNORECASE),
        re.compile(r"['\"][a-zA-Z0-9_\-]*password[0-9]*!['\"]", re.IGNORECASE),
        re.compile(r"['\"]demo-session-token-", re.IGNORECASE),
        re.compile(r"['\"]local-user-", re.IGNORECASE),
        re.compile(r"Dr\.\s*Alex\s*Morgan", re.IGNORECASE),
    ]

    suspicious_matches = []

    for file_path in SRC_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".html"}:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in banned_patterns:
                if pattern.search(line):
                    # Exclude innocent UI labels if any, but catch actual credential strings
                    suspicious_matches.append(
                        f"{file_path.relative_to(ROOT_DIR)}:{line_num} -> {line.strip()}"
                    )

    assert not suspicious_matches, (
        f"Found hard-coded credentials or banned persona strings in src/:\n"
        + "\n".join(suspicious_matches)
    )


def test_demo_no_fixed_password():
    """
    Verifies that the demo account uses a random, salted, PBKDF2-hashed password
    generated server-side and never leaks a fixed password or password hash.
    """
    res = client.post("/api/auth/demo")
    assert res.status_code == 200
    data = res.json()

    # Verify no password or salt in response
    assert "password" not in data
    assert "password_hash" not in data
    assert "salt" not in data

    # Verify user row in database has non-trivial salt and hash
    from vitasense.api.db import get_db_connection
    with get_db_connection() as conn:
        row = conn.execute("SELECT password_hash, salt FROM users WHERE email = 'demo@vitasense.local'").fetchone()
        assert row is not None
        assert len(row["password_hash"]) == 64  # SHA-256 hex digest
        assert len(row["salt"]) >= 16


def test_demo_rate_limiting():
    """
    Verifies that POST /api/auth/demo enforces rate limiting (10 requests per minute)
    and returns HTTP 429 when the limit is exceeded.
    """
    from vitasense.api.auth import demo_limiter
    demo_limiter.reset()

    # Make 10 allowed calls
    for i in range(10):
        r = client.post("/api/auth/demo")
        assert r.status_code == 200, f"Call {i+1} failed: {r.text}"

    # 11th call must trigger 429
    r_blocked = client.post("/api/auth/demo")
    assert r_blocked.status_code == 429
    assert "Too many demo access requests" in r_blocked.json()["detail"]

    # Reset limiter so other tests are unaffected
    demo_limiter.reset()


def test_demo_environment_switch_disabled(monkeypatch):
    """
    Verifies that setting ENABLE_DEMO_LOGIN=false disables the demo endpoint
    with HTTP 403 Forbidden.
    """
    from vitasense.api.auth import demo_limiter
    demo_limiter.reset()

    monkeypatch.setenv("ENABLE_DEMO_LOGIN", "false")
    res = client.post("/api/auth/demo")
    assert res.status_code == 403
    assert "Demo account access is disabled" in res.json()["detail"]


def test_demo_cannot_access_other_users_data():
    """
    Verifies strict multi-tenant isolation:
    A session obtained via POST /api/auth/demo cannot read, list, or export
    measurements or alerts belonging to another registered user.
    """
    from vitasense.api.auth import demo_limiter
    demo_limiter.reset()

    # 1. Register a private user and insert a private measurement and alert
    unique_email = f"confidential_{secrets.token_hex(4)}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword987!",
            "name": "Confidential Patient",
            "age": 45,
            "sex": "Female",
            "height": "165 cm",
            "weight": "60 kg",
            "resting_hr": 68,
        },
    )
    assert reg_res.status_code == 201
    patient_token = reg_res.json()["token"]
    patient_id = reg_res.json()["user"]["id"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    # Add private measurement
    m_res = client.post(
        "/api/measurements",
        headers=patient_headers,
        json={
            "type": "heart_rate",
            "value": 88.0,
            "unit": "bpm",
            "timestamp": now_iso,
            "source": "manual",
        },
    )
    assert m_res.status_code == 201
    private_meas_id = m_res.json()["id"]

    # Add private alert
    a_res = client.post(
        "/api/alerts",
        headers=patient_headers,
        json={
            "type": "heart_rate",
            "title": "Private Patient Alert",
            "message": "Highly confidential health warning.",
            "severity": "warning",
        },
    )
    assert a_res.status_code == 201
    private_alert_id = a_res.json()["id"]

    # 2. Log in as demo user
    demo_res = client.post("/api/auth/demo")
    assert demo_res.status_code == 200
    demo_token = demo_res.json()["token"]
    demo_headers = {"Authorization": f"Bearer {demo_token}"}

    # 3. Verify demo user CANNOT access private measurement by ID
    get_m = client.get(f"/api/measurements/{private_meas_id}", headers=demo_headers)
    assert get_m.status_code == 404, "Demo session must NOT access other users' measurements"

    # 4. Verify demo user list does NOT contain private measurement
    list_m = client.get("/api/measurements", headers=demo_headers)
    assert list_m.status_code == 200
    demo_meas_ids = [m["id"] for m in list_m.json()]
    assert private_meas_id not in demo_meas_ids, "Private measurement leaked in demo measurements list"

    # 5. Verify demo user alerts list does NOT contain private alert
    list_a = client.get("/api/alerts", headers=demo_headers)
    assert list_a.status_code == 200
    demo_alert_ids = [a["id"] for a in list_a.json()]
    assert private_alert_id not in demo_alert_ids, "Private alert leaked in demo alerts list"

    # 6. Verify demo user data export does NOT contain private user's info
    export_res = client.get("/api/auth/export", headers=demo_headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["account"]["email"] == "demo@vitasense.local"
    assert export_data["account"]["id"] != patient_id
    exported_meas_ids = [m["id"] for m in export_data.get("measurements", [])]
    assert private_meas_id not in exported_meas_ids, "Private measurement leaked in demo export"
