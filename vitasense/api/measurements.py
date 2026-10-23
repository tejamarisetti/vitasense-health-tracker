"""
VitaSense AI - Measurements & Data Quality Engine Module
Implements FR-02 (Measurement Ingestion & History) and FR-03 (Real-time Quality Flags).
Reuses vitasense.quality.trust_score.RuleBasedTrustScorer.
Guarantees per-user data isolation and strictly isolates demo data resets from real data.
"""

import json
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal, Dict, Any
import numpy as np
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, Query, status

from vitasense.api.db import get_db_connection
from vitasense.api.auth import get_current_user
from vitasense.quality.trust_score import RuleBasedTrustScorer

router = APIRouter(prefix="/api/measurements", tags=["measurements"])

# Physiological bounds for server-side validation and plausibility
PHYSIOLOGICAL_LIMITS = {
    "heart_rate": {
        "valid_units": ["bpm"],
        "min_plausible": 35.0,
        "max_plausible": 220.0,
        "max_jump_s": 40.0,
    },
    "spo2": {
        "valid_units": ["%"],
        "min_plausible": 70.0,
        "max_plausible": 100.0,
        "max_jump_s": 15.0,
    },
    "respiratory_rate": {
        "valid_units": ["brpm"],
        "min_plausible": 6.0,
        "max_plausible": 50.0,
        "max_jump_s": 20.0,
    },
    "hrv": {
        "valid_units": ["ms"],
        "min_plausible": 5.0,
        "max_plausible": 250.0,
        "max_jump_s": 100.0,
    },
}

# Shared rule-based trust scorer from vitasense.quality
quality_scorer = RuleBasedTrustScorer(
    hr_min_bpm=35.0,
    hr_max_bpm=220.0,
    max_hr_jump_bpm_s=40.0,
    flatline_variance_eps=1e-6,
    abstention_threshold=0.70,
)


# --- Pydantic Models ---

class MeasurementCreate(BaseModel):
    type: Literal["heart_rate", "spo2", "respiratory_rate", "hrv"]
    value: float
    unit: str
    timestamp: str  # ISO8601 string
    source: Literal["manual", "import", "demo"]

    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Measurement value must be a finite number.")
        if v < 0:
            raise ValueError("Measurement value cannot be negative.")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, ts_str):
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Cannot be more than 2 minutes into the future
            max_future = datetime.now(timezone.utc) + timedelta(minutes=2)
            if dt > max_future:
                raise ValueError("Measurement timestamp cannot be in the future.")
            return dt.isoformat()
        except ValueError as e:
            if "future" in str(e):
                raise
            raise ValueError(f"Invalid ISO timestamp format: {ts_str}")


class ComponentCheck(BaseModel):
    status: Literal["pass", "fail", "warning"]
    score: float
    details: str


class MeasurementUpdate(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[str] = None
    source: Optional[Literal["manual", "import", "demo"]] = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, v):
        if v is not None:
            if math.isnan(v) or math.isinf(v):
                raise ValueError("Measurement value must be a finite number.")
            if v < 0:
                raise ValueError("Measurement value cannot be negative.")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, ts_str):
        if ts_str is not None:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                max_future = datetime.now(timezone.utc) + timedelta(minutes=2)
                if dt > max_future:
                    raise ValueError("Measurement timestamp cannot be in the future.")
                return dt.isoformat()
            except ValueError as e:
                if "future" in str(e):
                    raise
                raise ValueError(f"Invalid ISO timestamp format: {ts_str}")
        return ts_str


class MeasurementResponse(BaseModel):
    id: int
    user_id: int
    type: str
    value: float
    unit: str
    timestamp: str
    source: str
    trust_score: float
    quality_flags: List[str]
    component_checks: Dict[str, ComponentCheck]
    created_at: str
    exclude_from_inference: bool = False
    limitation_note: Optional[str] = None


def determine_inference_exclusion(trust_score: float, flags: List[str]) -> tuple[bool, Optional[str]]:
    """
    FR-04: Determines whether data record must be excluded from downstream
    ML inference or explicitly flagged as a limitation per PRD Section 8.
    """
    if flags:
        reasons = ", ".join(flags)
        return True, f"Excluded from ML inference due to data quality flags: {reasons}."
    if trust_score < 0.70:
        return True, f"Excluded from ML inference due to low trust score ({trust_score:.2f} < 0.70)."
    return False, None


class DemoResetResponse(BaseModel):
    status: str
    demo_deleted_count: int
    demo_reseeded_count: int
    real_records_preserved_count: int
    message: str


# --- Quality Assessment Engine ---

def assess_measurement_quality(
    user_id: int,
    m_type: str,
    value: float,
    unit: str,
    ts_iso: str,
    conn,
) -> tuple[float, List[str], Dict[str, dict]]:
    """
    Evaluates data quality using vitasense.quality.trust_score.RuleBasedTrustScorer.
    Detects flags: missing, stale, duplicate, implausible, sudden_change.
    Returns: (trust_score, quality_flags, component_checks).
    """
    flags: List[str] = []
    checks: Dict[str, dict] = {}
    limits = PHYSIOLOGICAL_LIMITS.get(m_type)

    # 1. Missingness Check
    if value is None or math.isnan(value):
        flags.append("missing")
        checks["missing_check"] = {
            "status": "fail",
            "score": 0.0,
            "details": "Measurement value is missing or NaN.",
        }
    else:
        checks["missing_check"] = {
            "status": "pass",
            "score": 1.0,
            "details": "Valid finite numeric value present.",
        }

    # 2. Duplicate Check (same user, type, and timestamp)
    dup_row = conn.execute(
        """
        SELECT id, value FROM measurements
        WHERE user_id = ? AND type = ? AND timestamp = ?
        LIMIT 1
        """,
        (user_id, m_type, ts_iso),
    ).fetchone()

    if dup_row:
        flags.append("duplicate")
        checks["duplicate_check"] = {
            "status": "fail",
            "score": 0.0,
            "details": f"Duplicate timestamp found matching existing record ID {dup_row['id']}.",
        }
    else:
        checks["duplicate_check"] = {
            "status": "pass",
            "score": 1.0,
            "details": "Timestamp is unique for this series.",
        }

    # 3. Plausibility Check (physiological bounds)
    if limits:
        min_p = limits["min_plausible"]
        max_p = limits["max_plausible"]
        if value < min_p or value > max_p:
            flags.append("implausible")
            checks["plausibility_check"] = {
                "status": "fail",
                "score": 0.0,
                "details": f"Value {value:.1f} {unit} outside physiological range [{min_p:.1f}, {max_p:.1f}].",
            }
        else:
            checks["plausibility_check"] = {
                "status": "pass",
                "score": 1.0,
                "details": f"Value {value:.1f} {unit} within plausible bounds [{min_p:.1f}, {max_p:.1f}].",
            }
    else:
        checks["plausibility_check"] = {
            "status": "pass",
            "score": 1.0,
            "details": "No physiological limits configured for this type.",
        }

    # Retrieve recent historical readings for this user and type
    recent_rows = conn.execute(
        """
        SELECT value, timestamp FROM measurements
        WHERE user_id = ? AND type = ? AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (user_id, m_type, ts_iso),
    ).fetchall()

    recent_values = [row["value"] for row in reversed(recent_rows)]
    all_values = recent_values + [value]

    # 4. Stale / Flatline Check
    # If 4 or more consecutive readings have near-zero variance
    if len(all_values) >= 4:
        sub_window = all_values[-4:]
        sub_var = float(np.var(sub_window))
        if sub_var < 1e-6:
            flags.append("stale")
            checks["stale_check"] = {
                "status": "fail",
                "score": 0.0,
                "details": f"Sensor flatline / locked reading detected (variance = {sub_var:.2e}).",
            }
        else:
            checks["stale_check"] = {
                "status": "pass",
                "score": 1.0,
                "details": f"Dynamic physiological variation present (variance = {sub_var:.3f}).",
            }
    else:
        checks["stale_check"] = {
            "status": "pass",
            "score": 1.0,
            "details": "Insufficient history (<4 samples) for flatline evaluation.",
        }

    # 5. Sudden Change / Rate-of-Change Check
    if recent_rows and limits:
        prev_val = recent_rows[0]["value"]
        try:
            prev_dt = datetime.fromisoformat(recent_rows[0]["timestamp"].replace("Z", "+00:00"))
            curr_dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
            dt_seconds = max(1.0, abs((curr_dt - prev_dt).total_seconds()))
        except Exception:
            dt_seconds = 1.0

        jump = abs(value - prev_val)
        rate = jump / dt_seconds
        max_jump = limits["max_jump_s"]

        if jump > max_jump and dt_seconds <= 5.0:
            flags.append("sudden_change")
            checks["rate_of_change_check"] = {
                "status": "fail",
                "score": max(0.0, 1.0 - (jump - max_jump) / 40.0),
                "details": f"Sudden jump of {jump:.1f} {unit} over {dt_seconds:.1f}s exceeds limit {max_jump:.1f} {unit}/s.",
            }
        else:
            checks["rate_of_change_check"] = {
                "status": "pass",
                "score": 1.0,
                "details": f"Rate of change {jump:.1f} {unit}/{dt_seconds:.1f}s is within normal dynamics.",
            }
    else:
        checks["rate_of_change_check"] = {
            "status": "pass",
            "score": 1.0,
            "details": "No immediate previous reading to evaluate jump rate.",
        }

    # 6. Trust Score Synthesis reusing RuleBasedTrustScorer
    if m_type == "heart_rate" and len(all_values) >= 2:
        hr_arr = np.array(all_values, dtype=float)
        ts_res = quality_scorer.evaluate_window(hr_arr)
        trust_score = float(ts_res.trust_score)
    else:
        # Generic multi-component score
        scores = [chk["score"] for chk in checks.values()]
        trust_score = float(np.prod(scores)) if scores else 1.0

    # Ensure hard zeroing if critical flags fail
    if "implausible" in flags or "missing" in flags or "stale" in flags:
        trust_score = min(trust_score, 0.0)

    trust_score = float(np.clip(trust_score, 0.0, 1.0))
    return trust_score, flags, checks


# --- Measurement Endpoints ---

@router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_measurement(
    payload: MeasurementCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Ingests a physiological measurement with strict server-side validation,
    real-time quality assessment via vitasense.quality, and per-user isolation.
    """
    # Verify unit consistency with type
    type_info = PHYSIOLOGICAL_LIMITS.get(payload.type)
    if type_info and payload.unit not in type_info["valid_units"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid unit '{payload.unit}' for type '{payload.type}'. Expected: {type_info['valid_units']}",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    user_id = current_user["id"]

    with get_db_connection() as conn:
        # Assess quality & component checks
        trust_score, flags, checks = assess_measurement_quality(
            user_id=user_id,
            m_type=payload.type,
            value=payload.value,
            unit=payload.unit,
            ts_iso=payload.timestamp,
            conn=conn,
        )

        cur = conn.execute(
            """
            INSERT INTO measurements (
                user_id, type, value, unit, timestamp, source,
                trust_score, quality_flags, component_checks, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                payload.type,
                payload.value,
                payload.unit,
                payload.timestamp,
                payload.source,
                trust_score,
                json.dumps(flags),
                json.dumps(checks),
                now_iso,
            ),
        )
        record_id = cur.lastrowid

    exclude_inf, limit_note = determine_inference_exclusion(trust_score, flags)

    return MeasurementResponse(
        id=record_id,
        user_id=user_id,
        type=payload.type,
        value=payload.value,
        unit=payload.unit,
        timestamp=payload.timestamp,
        source=payload.source,
        trust_score=trust_score,
        quality_flags=flags,
        component_checks=checks,
        created_at=now_iso,
        exclude_from_inference=exclude_inf,
        limitation_note=limit_note,
    )


class InferenceDatasetResponse(BaseModel):
    total_records: int
    included_for_inference: int
    excluded_records: int
    exclusion_breakdown: Dict[str, int]
    clean_records: List[MeasurementResponse]
    excluded_ids: List[int]
    inference_limitation_statement: str


@router.get("/inference-dataset", response_model=InferenceDatasetResponse)
def get_inference_dataset(
    type: Optional[str] = Query(None, description="Filter by measurement type"),
    limit: int = Query(500, ge=1, le=2000),
    current_user: dict = Depends(get_current_user),
):
    """
    FR-04: Extracts clean dataset for downstream ML model inference/training,
    strictly dropping or flagging any segments with quality defects
    (missing, stale, duplicate, implausible, sudden_change, or trust_score < 0.70).
    """
    user_id = current_user["id"]
    query = "SELECT * FROM measurements WHERE user_id = ?"
    params: List[Any] = [user_id]
    if type:
        query += " AND type = ?"
        params.append(type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    clean_records: List[MeasurementResponse] = []
    excluded_ids: List[int] = []
    breakdown: Dict[str, int] = {
        "missing": 0,
        "stale": 0,
        "duplicate": 0,
        "implausible": 0,
        "sudden_change": 0,
        "low_trust_score": 0,
    }

    for r in rows:
        q_flags = json.loads(r["quality_flags"])
        c_checks = json.loads(r["component_checks"])
        t_score = float(r["trust_score"])
        exclude_inf, limit_note = determine_inference_exclusion(t_score, q_flags)

        resp_item = MeasurementResponse(
            id=r["id"],
            user_id=r["user_id"],
            type=r["type"],
            value=r["value"],
            unit=r["unit"],
            timestamp=r["timestamp"],
            source=r["source"],
            trust_score=t_score,
            quality_flags=q_flags,
            component_checks=c_checks,
            created_at=r["created_at"],
            exclude_from_inference=exclude_inf,
            limitation_note=limit_note,
        )

        if exclude_inf:
            excluded_ids.append(r["id"])
            for f in q_flags:
                if f in breakdown:
                    breakdown[f] += 1
            if not q_flags and t_score < 0.70:
                breakdown["low_trust_score"] += 1
        else:
            clean_records.append(resp_item)

    return InferenceDatasetResponse(
        total_records=len(rows),
        included_for_inference=len(clean_records),
        excluded_records=len(excluded_ids),
        exclusion_breakdown=breakdown,
        clean_records=clean_records,
        excluded_ids=excluded_ids,
        inference_limitation_statement=(
            "Per PRD FR-04, low-quality telemetry (sensor flatlines, missing data, duplicate timestamps, "
            "and physiological bound violations) is quarantined and excluded from model inference."
        ),
    )


@router.get("", response_model=List[MeasurementResponse])
def list_measurements(
    type: Optional[str] = Query(None, description="Filter by measurement type"),
    source: Optional[str] = Query(None, description="Filter by source (manual, import, demo)"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    """
    Lists measurements strictly isolated to the authenticated user.
    """
    user_id = current_user["id"]
    query = "SELECT * FROM measurements WHERE user_id = ?"
    params: List[Any] = [user_id]

    if type:
        query += " AND type = ?"
        params.append(type)
    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    results = []
    for r in rows:
        q_flags = json.loads(r["quality_flags"])
        t_score = float(r["trust_score"])
        exclude_inf, limit_note = determine_inference_exclusion(t_score, q_flags)
        results.append(
            MeasurementResponse(
                id=r["id"],
                user_id=r["user_id"],
                type=r["type"],
                value=r["value"],
                unit=r["unit"],
                timestamp=r["timestamp"],
                source=r["source"],
                trust_score=t_score,
                quality_flags=q_flags,
                component_checks=json.loads(r["component_checks"]),
                created_at=r["created_at"],
                exclude_from_inference=exclude_inf,
                limitation_note=limit_note,
            )
        )
    return results


@router.get("/{measurement_id}", response_model=MeasurementResponse)
def get_measurement_by_id(
    measurement_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Fetches a single measurement by ID.
    Enforces per-user isolation: returns 404 if the record does not belong to the user.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM measurements WHERE id = ? AND user_id = ?",
            (measurement_id, user_id),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Measurement {measurement_id} not found.",
            )

        q_flags = json.loads(row["quality_flags"])
        t_score = float(row["trust_score"])
        exclude_inf, limit_note = determine_inference_exclusion(t_score, q_flags)

        return MeasurementResponse(
            id=row["id"],
            user_id=row["user_id"],
            type=row["type"],
            value=row["value"],
            unit=row["unit"],
            timestamp=row["timestamp"],
            source=row["source"],
            trust_score=t_score,
            quality_flags=q_flags,
            component_checks=json.loads(row["component_checks"]),
            created_at=row["created_at"],
            exclude_from_inference=exclude_inf,
            limitation_note=limit_note,
        )


@router.put("/{measurement_id}", response_model=MeasurementResponse)
@router.patch("/{measurement_id}", response_model=MeasurementResponse)
def update_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-03: Permits authorized users to correct/edit their own measurement entry.
    Enforces strict per-user isolation: returns 404 if record doesn't belong to current user.
    Re-assesses trust score and data quality flags upon modification.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM measurements WHERE id = ? AND user_id = ?",
            (measurement_id, user_id),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Measurement {measurement_id} not found.",
            )

        new_value = payload.value if payload.value is not None else float(row["value"])
        new_unit = payload.unit if payload.unit is not None else row["unit"]
        new_timestamp = payload.timestamp if payload.timestamp is not None else row["timestamp"]
        new_source = payload.source if payload.source is not None else row["source"]
        m_type = row["type"]

        # Validate unit consistency if updated
        type_info = PHYSIOLOGICAL_LIMITS.get(m_type)
        if type_info and new_unit not in type_info["valid_units"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid unit '{new_unit}' for type '{m_type}'. Expected: {type_info['valid_units']}",
            )

        # Re-assess data quality & component checks
        trust_score, flags, checks = assess_measurement_quality(
            user_id=user_id,
            m_type=m_type,
            value=new_value,
            unit=new_unit,
            ts_iso=new_timestamp,
            conn=conn,
        )

        conn.execute(
            """
            UPDATE measurements
            SET value = ?, unit = ?, timestamp = ?, source = ?,
                trust_score = ?, quality_flags = ?, component_checks = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                new_value,
                new_unit,
                new_timestamp,
                new_source,
                trust_score,
                json.dumps(flags),
                json.dumps(checks),
                measurement_id,
                user_id,
            ),
        )

    exclude_inf, limit_note = determine_inference_exclusion(trust_score, flags)

    return MeasurementResponse(
        id=measurement_id,
        user_id=user_id,
        type=m_type,
        value=new_value,
        unit=new_unit,
        timestamp=new_timestamp,
        source=new_source,
        trust_score=trust_score,
        quality_flags=flags,
        component_checks=checks,
        created_at=row["created_at"],
        exclude_from_inference=exclude_inf,
        limitation_note=limit_note,
    )


@router.delete("/{measurement_id}", status_code=status.HTTP_200_OK)
def delete_measurement(
    measurement_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Deletes a single measurement by ID.
    Enforces per-user isolation: returns 404 if the record does not belong to the user.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        cur = conn.execute(
            "DELETE FROM measurements WHERE id = ? AND user_id = ?",
            (measurement_id, user_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Measurement {measurement_id} not found.",
            )
    return {"status": "ok", "message": f"Measurement {measurement_id} deleted."}


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo_data(
    current_user: dict = Depends(get_current_user),
):
    """
    Resets DEMO data for the authenticated user:
    - DELETES only rows where user_id = current_user.id AND source = 'demo'.
    - NEVER touches real data (source = 'manual' or source = 'import').
    - Reseeds a fresh set of realistic baseline demo telemetry readings labelled 'demo'.
    """
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with get_db_connection() as conn:
        # Count existing real records to report preservation
        real_count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM measurements WHERE user_id = ? AND source != 'demo'",
            (user_id,),
        ).fetchone()
        real_count = real_count_row["cnt"] if real_count_row else 0

        # Delete ONLY demo records for this user
        del_cur = conn.execute(
            "DELETE FROM measurements WHERE user_id = ? AND source = 'demo'",
            (user_id,),
        )
        deleted_count = del_cur.rowcount

        # Seed new synthetic demo measurements (e.g., 7 past points for HR and SpO2)
        demo_hr_values = [68.0, 72.0, 70.0, 75.0, 71.0, 74.0, 72.0]
        demo_spo2_values = [98.0, 97.0, 99.0, 98.0, 97.0, 98.0, 98.0]
        reseeded_count = 0

        for i, hr in enumerate(demo_hr_values):
            ts = (now - timedelta(hours=(len(demo_hr_values) - i) * 3)).isoformat()
            checks = {
                "missing_check": {"status": "pass", "score": 1.0, "details": "Nominal signal."},
                "duplicate_check": {"status": "pass", "score": 1.0, "details": "Unique sequence."},
                "plausibility_check": {"status": "pass", "score": 1.0, "details": "Within physiological limits."},
                "stale_check": {"status": "pass", "score": 1.0, "details": "Natural sinus rhythm variation."},
                "rate_of_change_check": {"status": "pass", "score": 1.0, "details": "Normal heart rate transition."},
            }
            conn.execute(
                """
                INSERT INTO measurements (
                    user_id, type, value, unit, timestamp, source,
                    trust_score, quality_flags, component_checks, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "heart_rate",
                    hr,
                    "bpm",
                    ts,
                    "demo",
                    0.96,
                    json.dumps([]),
                    json.dumps(checks),
                    now_iso,
                ),
            )
            reseeded_count += 1

        for i, spo2 in enumerate(demo_spo2_values):
            ts = (now - timedelta(hours=(len(demo_spo2_values) - i) * 3)).isoformat()
            checks = {
                "missing_check": {"status": "pass", "score": 1.0, "details": "Valid photoplethysmogram."},
                "duplicate_check": {"status": "pass", "score": 1.0, "details": "Unique sequence."},
                "plausibility_check": {"status": "pass", "score": 1.0, "details": "Normative arterial saturation."},
                "stale_check": {"status": "pass", "score": 1.0, "details": "Valid SpO2 dynamic range."},
                "rate_of_change_check": {"status": "pass", "score": 1.0, "details": "Stable saturation rate."},
            }
            conn.execute(
                """
                INSERT INTO measurements (
                    user_id, type, value, unit, timestamp, source,
                    trust_score, quality_flags, component_checks, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "spo2",
                    spo2,
                    "%",
                    ts,
                    "demo",
                    0.98,
                    json.dumps([]),
                    json.dumps(checks),
                    now_iso,
                ),
            )
            reseeded_count += 1

    return DemoResetResponse(
        status="ok",
        demo_deleted_count=deleted_count,
        demo_reseeded_count=reseeded_count,
        real_records_preserved_count=real_count,
        message=f"Successfully reset demo data ({reseeded_count} records seeded). {real_count} real user records preserved untouched.",
    )
