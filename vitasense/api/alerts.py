"""
VitaSense AI - Alerts API Router (FR-09)
Supports user-specific alerts, non-destructive acknowledge/dismiss lifecycle,
duplicate suppression refractory window, and strictly informational-only wording.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from vitasense.api.db import get_db_connection
from vitasense.api.auth import get_current_user

logger = logging.getLogger("vitasense.api.alerts")
router = APIRouter(prefix="/alerts", tags=["alerts"])

# Mandatory disclaimer appended to informational health alerts
INFORMATIONAL_DISCLAIMER = (
    "Informational notice only: VitaSense AI generates software estimates from recorded data. "
    "This does not constitute continuous or emergency medical monitoring. "
    "Please consult a qualified healthcare professional for medical concerns."
)


class CreateAlertRequest(BaseModel):
    type: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=3, max_length=1000)
    severity: str = Field(default="info", pattern="^(info|warning|critical)$")
    reason: str = Field(default="", max_length=500)
    recommended_step: str = Field(
        default="Review recent trends and consult a physician if unexpected symptoms persist.",
        max_length=500,
    )
    related_record_id: Optional[int] = None


class AlertResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    severity: str
    status: str
    reason: str
    recommended_step: str
    related_record_id: Optional[int]
    created_at: str
    acknowledged_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    disclaimer: str = INFORMATIONAL_DISCLAIMER


@router.get("", response_model=List[AlertResponse])
def get_user_alerts(
    status_filter: str = Query("all", pattern="^(all|active|acknowledged|dismissed)$"),
    current_user: dict = Depends(get_current_user),
):
    """
    FR-09: Returns the authenticated user's own alerts.
    Isolates records strictly by current_user ID.
    """
    user_id = current_user["id"]
    query = "SELECT * FROM user_alerts WHERE user_id = ?"
    params = [user_id]

    if status_filter != "all":
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"

    with get_db_connection() as conn:
        cursor = conn.execute(query, tuple(params))
        rows = cursor.fetchall()

    return [
        AlertResponse(
            id=row["id"],
            user_id=row["user_id"],
            type=row["type"],
            title=row["title"],
            message=row["message"],
            severity=row["severity"],
            status=row["status"],
            reason=row["reason"],
            recommended_step=row["recommended_step"],
            related_record_id=row["related_record_id"],
            created_at=row["created_at"],
            acknowledged_at=row["acknowledged_at"],
            dismissed_at=row["dismissed_at"],
        )
        for row in rows
    ]


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_user_alert(
    req: CreateAlertRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-09: Generates an alert for the signed-in user's own records.
    Implements 60-second duplicate suppression for matching alert types and titles.
    Enforces informational wording.
    """
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    refractory_cutoff = (now - timedelta(seconds=60)).isoformat()

    with get_db_connection() as conn:
        # Check duplicate suppression within refractory window (60s)
        cur = conn.execute(
            """
            SELECT * FROM user_alerts 
            WHERE user_id = ? AND type = ? AND title = ? AND created_at >= ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, req.type, req.title, refractory_cutoff),
        )
        existing = cur.fetchone()
        if existing:
            logger.info("Duplicate alert suppressed for user_id=%s, type=%s within 60s window", user_id, req.type)
            return AlertResponse(
                id=existing["id"],
                user_id=existing["user_id"],
                type=existing["type"],
                title=existing["title"],
                message=existing["message"],
                severity=existing["severity"],
                status=existing["status"],
                reason=existing["reason"],
                recommended_step=existing["recommended_step"],
                related_record_id=existing["related_record_id"],
                created_at=existing["created_at"],
                acknowledged_at=existing["acknowledged_at"],
                dismissed_at=existing["dismissed_at"],
            )

        # Informational wording verification
        safe_message = req.message
        if "emergency" in safe_message.lower() or "diagnos" in safe_message.lower():
            safe_message = safe_message.replace("emergency", "informational observation").replace("diagnosis", "software estimate")

        cur = conn.execute(
            """
            INSERT INTO user_alerts (
                user_id, type, title, message, severity, status, reason,
                recommended_step, related_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                user_id,
                req.type,
                req.title,
                safe_message,
                req.severity,
                req.reason,
                req.recommended_step,
                req.related_record_id,
                now_iso,
            ),
        )
        alert_id = cur.lastrowid

    return AlertResponse(
        id=alert_id,
        user_id=user_id,
        type=req.type,
        title=req.title,
        message=safe_message,
        severity=req.severity,
        status="active",
        reason=req.reason,
        recommended_step=req.recommended_step,
        related_record_id=req.related_record_id,
        created_at=now_iso,
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_user_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-09: Acknowledges an alert.
    CRITICAL: Updates status to 'acknowledged' and sets acknowledged_at timestamp.
    NEVER deletes the event record.
    """
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM user_alerts WHERE id = ? AND user_id = ?",
            (alert_id, user_id),
        )
        alert = cur.fetchone()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found for this account.",
            )

        conn.execute(
            """
            UPDATE user_alerts 
            SET status = 'acknowledged', acknowledged_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_iso, alert_id, user_id),
        )

        cur = conn.execute("SELECT * FROM user_alerts WHERE id = ?", (alert_id,))
        updated = cur.fetchone()

    return AlertResponse(
        id=updated["id"],
        user_id=updated["user_id"],
        type=updated["type"],
        title=updated["title"],
        message=updated["message"],
        severity=updated["severity"],
        status=updated["status"],
        reason=updated["reason"],
        recommended_step=updated["recommended_step"],
        related_record_id=updated["related_record_id"],
        created_at=updated["created_at"],
        acknowledged_at=updated["acknowledged_at"],
        dismissed_at=updated["dismissed_at"],
    )


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_user_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    FR-09: Dismisses an alert.
    CRITICAL: Updates status to 'dismissed' and sets dismissed_at timestamp.
    NEVER deletes the event record.
    """
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM user_alerts WHERE id = ? AND user_id = ?",
            (alert_id, user_id),
        )
        alert = cur.fetchone()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found for this account.",
            )

        conn.execute(
            """
            UPDATE user_alerts 
            SET status = 'dismissed', dismissed_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_iso, alert_id, user_id),
        )

        cur = conn.execute("SELECT * FROM user_alerts WHERE id = ?", (alert_id,))
        updated = cur.fetchone()

    return AlertResponse(
        id=updated["id"],
        user_id=updated["user_id"],
        type=updated["type"],
        title=updated["title"],
        message=updated["message"],
        severity=updated["severity"],
        status=updated["status"],
        reason=updated["reason"],
        recommended_step=updated["recommended_step"],
        related_record_id=updated["related_record_id"],
        created_at=updated["created_at"],
        acknowledged_at=updated["acknowledged_at"],
        dismissed_at=updated["dismissed_at"],
    )
