"""
VitaSense AI - Unified User History API (FR-10)
Provides chronological record of the authenticated user's own measurements,
alerts, and assessments with date/type filters and pagination.
"""

from typing import Optional, List, Dict, Any
import json
import math
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from vitasense.api.db import get_db_connection
from vitasense.api.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


class HistoryItem(BaseModel):
    id: str
    category: str  # "measurement" | "alert" | "assessment"
    type: str
    title: str
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: str
    source: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    quality_flags: List[str] = []
    trust_score: Optional[float] = None
    component_checks: Dict[str, Any] = {}
    details: Dict[str, Any] = {}


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    pagination: PaginationMetadata


@router.get("", response_model=HistoryResponse)
def get_user_history(
    category: str = Query("all", pattern="^(all|measurements|alerts|assessments)$"),
    type_filter: Optional[str] = Query(None, description="Specific measurement or alert type (e.g. heart_rate)"),
    start_date: Optional[str] = Query(None, description="ISO timestamp start cutoff"),
    end_date: Optional[str] = Query(None, description="ISO timestamp end cutoff"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    FR-10: Unified history of the authenticated user's own records.
    Strictly isolated to current_user.
    """
    user_id = current_user["id"]
    combined_items: List[HistoryItem] = []

    with get_db_connection() as conn:
        # 1. Fetch user's measurements if category is "all" or "measurements"
        if category in ("all", "measurements"):
            m_query = "SELECT * FROM measurements WHERE user_id = ?"
            m_params: List[Any] = [user_id]

            if type_filter:
                m_query += " AND type = ?"
                m_params.append(type_filter)
            if start_date:
                m_query += " AND timestamp >= ?"
                m_params.append(start_date)
            if end_date:
                m_query += " AND timestamp <= ?"
                m_params.append(end_date)

            cur = conn.execute(m_query, tuple(m_params))
            for row in cur.fetchall():
                flags = []
                checks = {}
                try:
                    flags = json.loads(row["quality_flags"]) if row["quality_flags"] else []
                except Exception:
                    flags = []
                try:
                    checks = json.loads(row["component_checks"]) if row["component_checks"] else {}
                except Exception:
                    checks = {}

                combined_items.append(
                    HistoryItem(
                        id=f"meas_{row['id']}",
                        category="measurement",
                        type=row["type"],
                        title=f"{row['type'].replace('_', ' ').title()} Reading",
                        value=row["value"],
                        unit=row["unit"],
                        timestamp=row["timestamp"],
                        source=row["source"],
                        quality_flags=flags,
                        trust_score=row["trust_score"],
                        component_checks=checks,
                        details={
                            "record_id": row["id"],
                            "created_at": row["created_at"],
                        },
                    )
                )

        # 2. Fetch user's alerts if category is "all" or "alerts"
        if category in ("all", "alerts"):
            a_query = "SELECT * FROM user_alerts WHERE user_id = ?"
            a_params: List[Any] = [user_id]

            if type_filter:
                a_query += " AND type = ?"
                a_params.append(type_filter)
            if start_date:
                a_query += " AND created_at >= ?"
                a_params.append(start_date)
            if end_date:
                a_query += " AND created_at <= ?"
                a_params.append(end_date)

            cur = conn.execute(a_query, tuple(a_params))
            for row in cur.fetchall():
                combined_items.append(
                    HistoryItem(
                        id=f"alert_{row['id']}",
                        category="alert",
                        type=row["type"],
                        title=row["title"],
                        timestamp=row["created_at"],
                        status=row["status"],
                        severity=row["severity"],
                        details={
                            "reason": row["reason"],
                            "recommended_step": row["recommended_step"],
                            "related_record_id": row["related_record_id"],
                            "acknowledged_at": row["acknowledged_at"],
                            "dismissed_at": row["dismissed_at"],
                        },
                    )
                )

    # Sort descending by timestamp
    combined_items.sort(key=lambda x: x.timestamp, reverse=True)

    # Calculate pagination
    total_items = len(combined_items)
    total_pages = max(1, math.ceil(total_items / page_size))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = combined_items[start_idx:end_idx]

    return HistoryResponse(
        items=paginated_items,
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
