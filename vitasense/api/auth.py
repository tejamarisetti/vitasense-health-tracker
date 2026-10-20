"""
VitaSense AI - Authentication & Profile Management Module
Handles user registration, login, logout, password hashing (PBKDF2-HMAC-SHA256),
session management, profile CRUD, and per-user identity resolution.
"""

import os
import hashlib
import secrets
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, Header, status

from vitasense.api.db import get_db_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Security Utilities ---

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return pw_hash, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time verification of password against stored hash."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, expected_hash)


def generate_session_token() -> str:
    """Generates a cryptographically secure random session token."""
    return secrets.token_hex(32)


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


# --- Current User Dependency ---

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extracts and validates the bearer token from the Authorization header.
    Returns the authenticated user dict: {'id': ..., 'email': ...}.
    Raises 401 HTTPException if missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT s.token, s.expires_at, u.id, u.email, u.created_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
            """,
            (token, now_iso),
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
            "token": token,
        }


# --- Authentication Endpoints ---

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    """
    Registers a new user with hashed password and default profile.
    Automatically creates a valid session token.
    """
    clean_email = req.email.strip().lower()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_at = (now + timedelta(days=14)).isoformat()

    pw_hash, salt = hash_password(req.password)
    token = generate_session_token()

    with get_db_connection() as conn:
        # Check if email is already registered
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (clean_email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{clean_email}' already exists.",
            )

        # Insert user
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean_email, pw_hash, salt, now_iso),
        )
        user_id = cur.lastrowid

        # Insert profile
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

        # Create initial session
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now_iso, expires_at),
        )

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
        token=token,
        user=UserResponse(id=user_id, email=clean_email, created_at=now_iso),
        profile=profile_data,
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """
    Authenticates user credentials and issues a session token.
    """
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
        token = generate_session_token()

        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now_iso, expires_at),
        )

        prof_row = conn.execute(
            """
            SELECT name, age, sex, height, weight, resting_hr,
                   activity_level, health_goal, provider
            FROM user_profiles WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

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
        token=token,
        user=UserResponse(id=user_id, email=clean_email, created_at=user_row["created_at"]),
        profile=profile,
    )


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """
    Invalidates current session token.
    """
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token = ?",
            (current_user["token"],),
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
