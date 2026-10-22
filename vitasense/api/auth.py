"""
VitaSense AI - Authentication & Profile Management Module
Hardened per PRD Section 13, FR-01, FR-02, FR-11, FR-13:
1. PBKDF2-HMAC-SHA256 password hashing with 600,000 iterations (OWASP guidance).
2. Hashed session tokens at rest: database stores SHA-256 hash of tokens; plaintext tokens never persisted.
3. In-memory sliding-window rate limiting on registration, login, and contact endpoints.
4. Privacy guarantee: passwords, tokens, and raw credentials are never logged or echoed.
"""

import os
import time
import hashlib
import secrets
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from collections import defaultdict
from threading import Lock
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status

from vitasense.api.db import get_db_connection

logger = logging.getLogger("vitasense.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 600_000  # OWASP current recommended cost for PBKDF2-HMAC-SHA256


# --- Sliding Window Rate Limiter ---

class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter for brute-force and abuse protection."""
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def check(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            cutoff = now - self.window_seconds
            self.requests[key] = [t for t in self.requests[key] if t > cutoff]
            if len(self.requests[key]) >= self.max_requests:
                return False
            self.requests[key].append(now)
            return True

    def reset(self):
        with self.lock:
            self.requests.clear()


# Rate limiters: 5 requests per 60 seconds per client key
register_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)
login_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)
contact_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0)


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely from request headers or direct client."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


# --- Security Utilities ---

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return pw_hash, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time verification of password against stored hash with fallback."""
    # Check with current standard (600,000 iterations)
    computed_hash, _ = hash_password(password, salt)
    if secrets.compare_digest(computed_hash, expected_hash):
        return True
    # Backwards compatibility check for 100,000 iterations
    legacy_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return secrets.compare_digest(legacy_hash, expected_hash)


def generate_session_token() -> str:
    """Generates a cryptographically secure random session token."""
    return secrets.token_hex(32)


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a session token for secure storage at rest."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# --- Pydantic Schemas ---

class ProfileSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=1, le=130)
    sex: Literal["Male", "Female", "Other", "Prefer not to say"]
    height: str = Field(..., min_length=2, max_length=20)
    weight: str = Field(..., min_length=2, max_length=20)
    resting_hr: int = Field(..., ge=30, le=220)
    activity_level: Literal["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]
    health_goal: Literal["Cardiovascular Wellness", "Athletic Performance", "Stress & Recovery", "Sleep Optimization"]
    provider: Literal["email", "google", "apple"] = "email"


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    name: Optional[str] = Field("Alex Morgan", max_length=100)
    age: Optional[int] = Field(29, ge=1, le=130)
    sex: Optional[Literal["Male", "Female", "Other", "Prefer not to say"]] = "Male"
    height: Optional[str] = "178 cm"
    weight: Optional[str] = "72 kg"
    resting_hr: Optional[int] = Field(64, ge=30, le=220)
    activity_level: Optional[Literal["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]] = "Moderately Active"
    health_goal: Optional[Literal["Cardiovascular Wellness", "Athletic Performance", "Stress & Recovery", "Sleep Optimization"]] = "Cardiovascular Wellness"
    provider: Optional[Literal["email", "google", "apple"]] = "email"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address format: '{v}'")
        return clean


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address format: '{v}'")
        return clean


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    profile: ProfileSchema


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address format: '{v}'")
        return clean

    @field_validator("name", "subject", "message")
    @classmethod
    def sanitize_input(cls, v: str) -> str:
        clean = v.strip()
        lowered = clean.lower()
        if "<script" in lowered or "javascript:" in lowered or "onerror=" in lowered or "<iframe" in lowered:
            raise ValueError("Input contains disallowed script markup tokens.")
        return clean


# --- Current User Dependency ---

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extracts and validates the bearer token from the Authorization header.
    Compares SHA-256 hash of token against database sessions.
    Raises 401 HTTPException if missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = authorization[7:].strip()
    token_hash = hash_token(raw_token)
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT s.token_hash, s.expires_at, u.id, u.email, u.created_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (token_hash, now_iso),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token is invalid or has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": row["id"],
            "email": row["email"],
            "created_at": row["created_at"],
            "token_hash": token_hash,
        }


# --- Authentication Endpoints ---

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, request: Request):
    """
    Registers a new user with hardened PBKDF2 password hashing and default profile.
    Stores only the SHA-256 hash of the session token.
    Rate limited to 5 registrations per minute per IP.
    """
    client_ip = get_client_ip(request)
    if not register_limiter.check(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait before retrying.",
            headers={"Retry-After": "60"},
        )

    clean_email = req.email.strip().lower()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_at = (now + timedelta(days=14)).isoformat()

    pw_hash, salt = hash_password(req.password)
    raw_token = generate_session_token()
    token_h = hash_token(raw_token)

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (clean_email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{clean_email}' already exists.",
            )

        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean_email, pw_hash, salt, now_iso),
        )
        user_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, name, age, sex, height, weight,
                resting_hr, activity_level, health_goal, provider, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                req.name or clean_email.split("@")[0],
                req.age or 29,
                req.sex or "Male",
                req.height or "178 cm",
                req.weight or "72 kg",
                req.resting_hr or 64,
                req.activity_level or "Moderately Active",
                req.health_goal or "Cardiovascular Wellness",
                req.provider or "email",
                now_iso,
            ),
        )

        conn.execute(
            """
            INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token_h, user_id, now_iso, expires_at),
        )

    logger.info("Registration successful for sanitized account ID %d", user_id)

    profile_data = ProfileSchema(
        name=req.name or clean_email.split("@")[0],
        age=req.age or 29,
        sex=req.sex or "Male",
        height=req.height or "178 cm",
        weight=req.weight or "72 kg",
        resting_hr=req.resting_hr or 64,
        activity_level=req.activity_level or "Moderately Active",
        health_goal=req.health_goal or "Cardiovascular Wellness",
        provider=req.provider or "email",
    )

    return AuthResponse(
        token=raw_token,
        user=UserResponse(id=user_id, email=clean_email, created_at=now_iso),
        profile=profile_data,
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, request: Request):
    """
    Authenticates user credentials and returns a secure session token.
    Stores only the SHA-256 hash of the session token in the database.
    Rate limited to 5 login attempts per minute per IP.
    """
    client_ip = get_client_ip(request)
    if not login_limiter.check(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait before retrying.",
            headers={"Retry-After": "60"},
        )

    clean_email = req.email.strip().lower()

    with get_db_connection() as conn:
        user_row = conn.execute(
            """
            SELECT id, email, password_hash, salt, created_at
            FROM users WHERE email = ?
            """,
            (clean_email,),
        ).fetchone()

        if not user_row or not verify_password(req.password, user_row["salt"], user_row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user_id = user_row["id"]
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_at = (now + timedelta(days=14)).isoformat()
        raw_token = generate_session_token()
        token_h = hash_token(raw_token)

        conn.execute(
            """
            INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token_h, user_id, now_iso, expires_at),
        )

        prof_row = conn.execute(
            """
            SELECT name, age, sex, height, weight, resting_hr,
                   activity_level, health_goal, provider
            FROM user_profiles WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    logger.info("Login successful for sanitized account ID %d", user_id)

    if prof_row:
        profile = ProfileSchema(
            name=prof_row["name"],
            age=prof_row["age"],
            sex=prof_row["sex"],
            height=prof_row["height"],
            weight=prof_row["weight"],
            resting_hr=prof_row["resting_hr"],
            activity_level=prof_row["activity_level"],
            health_goal=prof_row["health_goal"],
            provider=prof_row["provider"],
        )
    else:
        profile = ProfileSchema(
            name=clean_email.split("@")[0],
            age=29,
            sex="Male",
            height="178 cm",
            weight="72 kg",
            resting_hr=64,
            activity_level="Moderately Active",
            health_goal="Cardiovascular Wellness",
            provider="email",
        )

    return AuthResponse(
        token=raw_token,
        user=UserResponse(id=user_id, email=clean_email, created_at=user_row["created_at"]),
        profile=profile,
    )


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """
    Invalidates current session token by deleting its SHA-256 hash.
    """
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (current_user["token_hash"],),
        )
    return {"status": "ok", "message": "Successfully logged out."}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns current user info and associated clinical profile.
    """
    with get_db_connection() as conn:
        prof_row = conn.execute(
            """
            SELECT name, age, sex, height, weight, resting_hr,
                   activity_level, health_goal, provider, updated_at
            FROM user_profiles WHERE user_id = ?
            """,
            (current_user["id"],),
        ).fetchone()

    profile_dict = dict(prof_row) if prof_row else {}
    return {
        "user": {
            "id": current_user["id"],
            "email": current_user["email"],
            "created_at": current_user["created_at"],
        },
        "profile": profile_dict,
    }


@router.put("/profile", response_model=ProfileSchema)
def update_profile(profile: ProfileSchema, current_user: dict = Depends(get_current_user)):
    """
    Updates the authenticated user's clinical profile.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, name, age, sex, height, weight,
                resting_hr, activity_level, health_goal, provider, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                sex = excluded.sex,
                height = excluded.height,
                weight = excluded.weight,
                resting_hr = excluded.resting_hr,
                activity_level = excluded.activity_level,
                health_goal = excluded.health_goal,
                provider = excluded.provider,
                updated_at = excluded.updated_at
            """,
            (
                current_user["id"],
                profile.name,
                profile.age,
                profile.sex,
                profile.height,
                profile.weight,
                profile.resting_hr,
                profile.activity_level,
                profile.health_goal,
                profile.provider,
                now_iso,
            ),
        )

    return profile


# --- Contact Us Endpoint (FR-11) ---

@router.post("/contact", status_code=status.HTTP_201_CREATED)
def submit_contact_inquiry(req: ContactRequest, request: Request):
    """
    FR-11: Receives Contact Us inquiry with server-side validation and rate limiting.
    Securely persists message in database.
    Does NOT log any health data or message body.
    """
    client_ip = get_client_ip(request)
    if not contact_limiter.check(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many contact submissions. Please wait before retrying.",
            headers={"Retry-After": "60"},
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO contact_messages (name, email, subject, message, created_at, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (req.name, req.email, req.subject, req.message, now_iso, client_ip),
        )
        msg_id = cur.lastrowid

    # Strictly metadata only - zero health details or message text logged
    logger.info("Contact submission successfully saved: msg_id=%s, ip=%s", msg_id, client_ip)

    return {
        "status": "ok",
        "message": "Inquiry received and securely stored in support queue. VitaSense team will respond shortly.",
    }


# --- Privacy and Account Controls (FR-13) ---

@router.get("/export")
def export_user_data(current_user: dict = Depends(get_current_user)):
    """
    FR-13: Full data export for the authenticated user only.
    Exports account metadata, profile, measurements, and alerts.
    Never exports passwords or password hashes.
    """
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        # User Profile
        cur = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        profile_row = cur.fetchone()
        profile_data = dict(profile_row) if profile_row else {}

        # Measurements
        cur = conn.execute(
            "SELECT id, type, value, unit, timestamp, source, trust_score, quality_flags, component_checks, created_at "
            "FROM measurements WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        )
        measurements = []
        for r in cur.fetchall():
            m = dict(r)
            try:
                m["quality_flags"] = json.loads(m["quality_flags"])
            except Exception:
                pass
            try:
                m["component_checks"] = json.loads(m["component_checks"])
            except Exception:
                pass
            measurements.append(m)

        # Alerts
        cur = conn.execute(
            "SELECT id, type, title, message, severity, status, reason, recommended_step, related_record_id, created_at, acknowledged_at, dismissed_at "
            "FROM user_alerts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        alerts = [dict(r) for r in cur.fetchall()]

    return {
        "export_metadata": {
            "format": "VitaSense-AI-Export",
            "version": "1.0",
            "exported_at": now_iso,
            "user_id": user_id,
        },
        "account": {
            "id": current_user["id"],
            "email": current_user["email"],
            "created_at": current_user["created_at"],
        },
        "profile": profile_data,
        "measurements": measurements,
        "alerts": alerts,
    }


@router.delete("/account")
def delete_user_account(current_user: dict = Depends(get_current_user)):
    """
    FR-13: Permanent account and data deletion for the authenticated user only.
    Foreign key cascading automatically purges sessions, profile, measurements, and alerts.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    logger.info("User account permanently deleted: user_id=%s", user_id)
    return {
        "status": "ok",
        "message": "Account and all associated health records permanently deleted.",
    }

