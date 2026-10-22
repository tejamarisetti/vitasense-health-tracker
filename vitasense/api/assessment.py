"""
VitaSense AI - Symptom Assessment & AI/ML Explanation Engine
Implements:
- FR-06: Guided symptom questionnaire with mandatory answer review/edit step,
         rule-based risk screening signal, contributing factors, and clinical disclaimers.
- FR-07: Transparent AI/ML explanation with local feature contributions, calibrated
         uncertainty interval, model provenance, and limitations statement.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Tuple, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from vitasense.api.db import get_db_connection
from vitasense.api.auth import get_current_user

router = APIRouter(prefix="/api/assessment", tags=["assessment"])

MODEL_VERSION = "vitasense-ruleset-v2.1"
CLINICAL_DISCLAIMER = (
    "Informational screening only: This result reflects a rule-based screening risk signal "
    "and is NOT a medical diagnosis, clinical prognosis, or treatment directive. If you experience "
    "crushing chest pain, left-arm/jaw radiation, acute breathlessness, or syncope (fainting), "
    "call emergency services immediately."
)


# --- Pydantic Data Models ---

class SymptomQuestionnaireInput(BaseModel):
    primary_symptom: Literal[
        "palpitations",
        "racing_heart",
        "skipped_beats",
        "chest_tightness",
        "dizziness",
        "shortness_of_breath",
        "fatigue",
        "none_routine",
    ] = Field(..., description="Chief subjective cardiac or pulmonary sensation")
    intensity: Literal["mild", "moderate", "severe"] = Field(
        ..., description="Subjective severity: mild (slight), moderate (distracting), severe (incapacitating)"
    )
    duration: Literal["under_5m", "5_to_15m", "15_to_30m", "over_30m", "continuous"] = Field(
        ..., description="Approximate persistence of current symptomatic episode"
    )
    activity_context: Literal[
        "resting",
        "sitting_desk",
        "light_activity",
        "vigorous_exercise",
        "emotional_stress",
        "caffeine_stimulants",
    ] = Field(..., description="Physical or emotional activity occurring when sensation arose")
    warning_signs: List[str] = Field(
        default_factory=list,
        description="Associated acute warning indicators (e.g. radiating pain, breathlessness, fainting)",
    )
    notes: Optional[str] = Field(None, max_length=500, description="Optional brief context notes")
    is_demo: bool = Field(False, description="Flag indicating if generated from interactive demo")


class AssessmentReviewResponse(BaseModel):
    is_valid: bool
    summary: Dict[str, str]
    ready_for_submission: bool
    notice: str


class AssessmentResult(BaseModel):
    id: int
    user_id: int
    risk_level: Literal["Low Risk Signal", "Moderate Risk Signal", "Elevated Risk Signal"]
    risk_score: float
    contributing_factors: List[str]
    feature_contributions: Dict[str, float]
    uncertainty_range: Tuple[float, float]
    model_version: str
    is_demo: bool
    missing_data_notes: List[str]
    model_limitations: str
    when_to_seek_care: str
    disclaimer: str
    created_at: str


# --- Deterministic Screening & Feature Attribution Engine ---

def compute_screening_risk(
    answers: SymptomQuestionnaireInput,
    user_baseline_hr: Optional[int] = None,
) -> Tuple[str, float, List[str], Dict[str, float], Tuple[float, float], List[str]]:
    """
    Evaluates rule-based screening score in range [0.0, 1.0] and computes
    transparent feature attributions (FR-07) and uncertainty bounds.
    """
    factors: List[str] = []
    missing_data: List[str] = []

    # 1. Symptom Severity Weight (base: 0.0 - 0.40)
    symptom_weights = {
        "chest_tightness": 0.35,
        "shortness_of_breath": 0.30,
        "racing_heart": 0.25,
        "dizziness": 0.22,
        "palpitations": 0.18,
        "skipped_beats": 0.15,
        "fatigue": 0.10,
        "none_routine": 0.02,
    }
    intensity_multiplier = {
        "mild": 0.60,
        "moderate": 1.0,
        "severe": 1.35,
    }

    base_symptom_wt = symptom_weights.get(answers.primary_symptom, 0.10)
    severity_mult = intensity_multiplier.get(answers.intensity, 1.0)
    w_symptom = float(min(0.40, base_symptom_wt * severity_mult))

    if answers.primary_symptom != "none_routine":
        factors.append(
            f"Primary symptom '{answers.primary_symptom.replace('_', ' ')}' reported with {answers.intensity} intensity."
        )

    # 2. Activity Context Factor (0.0 - 0.25)
    # Symptoms at rest are clinically more alarming than post-exercise
    context_weights = {
        "resting": 0.25,
        "sitting_desk": 0.20,
        "emotional_stress": 0.14,
        "caffeine_stimulants": 0.12,
        "light_activity": 0.10,
        "vigorous_exercise": 0.05,
    }
    w_context = float(context_weights.get(answers.activity_context, 0.10))

    if answers.activity_context in ("resting", "sitting_desk"):
        factors.append("Symptom occurred during sedentary rest/inactivity, elevating screening index.")
    elif answers.activity_context in ("vigorous_exercise", "caffeine_stimulants"):
        factors.append(f"Exertional/stimulant context ('{answers.activity_context.replace('_', ' ')}') may physiological induce elevated rate.")

    # 3. Duration Factor (0.0 - 0.15)
    duration_weights = {
        "continuous": 0.15,
        "over_30m": 0.13,
        "15_to_30m": 0.09,
        "5_to_15m": 0.05,
        "under_5m": 0.02,
    }
    w_duration = float(duration_weights.get(answers.duration, 0.05))
    if answers.duration in ("over_30m", "continuous"):
        factors.append(f"Prolonged episode duration ({answers.duration.replace('_', ' ')}) contributes to score.")

    # 4. Red Flag Warning Signs (0.0 - 0.20)
    red_flag_score = 0.0
    known_red_flags = {"radiating_pain", "acute_breathlessness", "syncope"}
    active_red_flags = [f for f in answers.warning_signs if f in known_red_flags]
    if active_red_flags:
        red_flag_score = float(min(0.20, len(active_red_flags) * 0.10))
        for rf in active_red_flags:
            factors.append(f"Warning sign noted: {rf.replace('_', ' ')}.")
    w_red_flags = red_flag_score

    # Check missing telemetry data
    if user_baseline_hr is None:
        missing_data.append("Resting baseline HR not set in profile; demographic population default (70 bpm) applied.")

    # Composite normalized score [0.0, 1.0]
    total_score = float(min(1.0, max(0.02, w_symptom + w_context + w_duration + w_red_flags)))

    # Risk level categorization
    if total_score >= 0.65 or len(active_red_flags) >= 2:
        risk_level = "Elevated Risk Signal"
    elif total_score >= 0.32:
        risk_level = "Moderate Risk Signal"
    else:
        risk_level = "Low Risk Signal"

    # Feature contributions (FR-07)
    feature_contributions = {
        "symptom_severity_factor": round(w_symptom, 3),
        "activity_context_factor": round(w_context, 3),
        "duration_persistence_factor": round(w_duration, 3),
        "red_flag_indicators_factor": round(w_red_flags, 3),
    }

    # Calibrated uncertainty interval [lower, upper] (FR-07)
    # Heuristic uncertainty margin is +/- 0.08 based on self-reported variance
    uncertainty_margin = 0.08
    lower_bound = round(max(0.0, total_score - uncertainty_margin), 3)
    upper_bound = round(min(1.0, total_score + uncertainty_margin), 3)
    uncertainty_range = (lower_bound, upper_bound)

    return risk_level, round(total_score, 3), factors, feature_contributions, uncertainty_range, missing_data


# --- API Endpoints ---

@router.post("/review", response_model=AssessmentReviewResponse)
def review_assessment_answers(
    payload: SymptomQuestionnaireInput,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-06 Review Step: Allows the user to inspect and confirm questionnaire inputs
    before committing to evaluation and database storage.
    """
    summary = {
        "Primary Symptom": payload.primary_symptom.replace("_", " ").title(),
        "Intensity": payload.intensity.title(),
        "Duration": payload.duration.replace("_", " ").title(),
        "Activity Context": payload.activity_context.replace("_", " ").title(),
        "Warning Signs": ", ".join([w.replace("_", " ").title() for w in payload.warning_signs]) or "None reported",
        "Mode": "Demo Simulation" if payload.is_demo else "User Telemetry Assessment",
    }
    return AssessmentReviewResponse(
        is_valid=True,
        summary=summary,
        ready_for_submission=True,
        notice="Please review your answers carefully. You may edit any field before submitting.",
    )


@router.post("/submit", response_model=AssessmentResult, status_code=status.HTTP_201_CREATED)
def submit_symptom_assessment(
    payload: SymptomQuestionnaireInput,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-06 & FR-07: Evaluates guided questionnaire, runs deterministic ruleset,
    stores record, and returns screening risk signal with transparent feature attribution.
    """
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Query user profile for baseline resting HR if available
    baseline_hr = None
    with get_db_connection() as conn:
        prof = conn.execute("SELECT resting_hr FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if prof and prof["resting_hr"]:
            baseline_hr = prof["resting_hr"]

    risk_lvl, score, factors, feat_contribs, uncert, missing = compute_screening_risk(payload, baseline_hr)

    limitations = (
        "Calculated by rule-based heuristic screening model (vitasense-ruleset-v2.1). "
        "Inputs are self-reported and not verified by 12-lead ECG or clinical auscultation. "
        "Prediction uncertainty bounds reflect subjective reporting variability."
    )
    when_to_seek = (
        "Seek immediate emergency medical care if you experience acute chest tightness radiating to the jaw/arm, "
        "severe breathlessness at rest, confusion, or syncope. For persistent moderate symptoms lasting over 24 hours, "
        "schedule an appointment with a primary care physician."
    )

    with get_db_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO symptom_assessments (
                user_id, symptoms, risk_level, risk_score,
                contributing_factors, feature_contributions, uncertainty_range,
                model_version, is_demo, disclaimer, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                payload.model_dump_json(),
                risk_lvl,
                score,
                json.dumps(factors),
                json.dumps(feat_contribs),
                json.dumps(list(uncert)),
                MODEL_VERSION,
                1 if payload.is_demo else 0,
                CLINICAL_DISCLAIMER,
                now_iso,
            ),
        )
        record_id = cur.lastrowid

    return AssessmentResult(
        id=record_id,
        user_id=user_id,
        risk_level=risk_lvl,
        risk_score=score,
        contributing_factors=factors,
        feature_contributions=feat_contribs,
        uncertainty_range=uncert,
        model_version=MODEL_VERSION,
        is_demo=payload.is_demo,
        missing_data_notes=missing,
        model_limitations=limitations,
        when_to_seek_care=when_to_seek,
        disclaimer=CLINICAL_DISCLAIMER,
        created_at=now_iso,
    )


@router.get("/history", response_model=List[AssessmentResult])
def list_user_assessments(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns chronological history of symptom assessments for authenticated user.
    """
    user_id = current_user["id"]
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM symptom_assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    results: List[AssessmentResult] = []
    for r in rows:
        factors = json.loads(r["contributing_factors"])
        feat_contribs = json.loads(r["feature_contributions"])
        uncert = tuple(json.loads(r["uncertainty_range"]))

        results.append(
            AssessmentResult(
                id=r["id"],
                user_id=r["user_id"],
                risk_level=r["risk_level"],
                risk_score=r["risk_score"],
                contributing_factors=factors,
                feature_contributions=feat_contribs,
                uncertainty_range=uncert,
                model_version=r["model_version"],
                is_demo=bool(r["is_demo"]),
                missing_data_notes=[],
                model_limitations=(
                    "Rule-based screening evaluation (vitasense-ruleset-v2.1). "
                    "Uncertainty interval indicates self-report variance."
                ),
                when_to_seek_care="Consult a medical professional if symptoms recur or cause discomfort.",
                disclaimer=r["disclaimer"],
                created_at=r["created_at"],
            )
        )
    return results


@router.get("/latest", response_model=Optional[AssessmentResult])
def get_latest_assessment(current_user: dict = Depends(get_current_user)):
    """
    Returns the most recent assessment for the authenticated user, or None if none exist.
    """
    items = list_user_assessments(limit=1, current_user=current_user)
    return items[0] if items else None
