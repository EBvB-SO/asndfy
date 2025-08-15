# app/api/sessions.py

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    User,
    SessionTracking as DBSessionTracking,
    TrainingPlan,
)
from app.models.session import SessionTracking
from app.core.dependencies import get_current_user_email
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}/sessions",
    tags=["Session Tracking"],
)

@router.get("", response_model=List[SessionTracking])
async def get_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> List[SessionTracking]:
    """Retrieve all tracking sessions for a given user & plan."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    planId = planId.lower()

    sessions = (
        db.query(DBSessionTracking)
        .filter(
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId,
        )
        .order_by(DBSessionTracking.week_number, DBSessionTracking.day_of_week)
        .all()
    )

    return [
        SessionTracking(
            id=s.id,
            planId=s.plan_id,
            weekNumber=s.week_number,
            dayOfWeek=s.day_of_week,
            focusName=s.focus_name,
            isCompleted=s.is_completed,
            notes=s.notes or "",
            completionDate=s.completion_date,
            updatedAt=s.updated_at,
        )
        for s in sessions
    ]

# app/api/sessions.py

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create server-side SessionTracking rows for a plan from the plan's weekly_schedule.
    Idempotent: if rows already exist for this user+plan, it returns a 'already initialised' message.
    """
    # 1) AuthN/AuthZ
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 2) Resolve user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_id = planId.lower()

    # 3) Find the plan (must belong to this user)
    plan = (
        db.query(TrainingPlan)
        .filter(
            TrainingPlan.id == plan_id,
            TrainingPlan.user_id == user.id,
        )
        .first()
    )
    if not plan or not plan.phases:
        raise HTTPException(status_code=404, detail="Training plan not found or has no phases")

    # 4) If we already have sessions for this user+plan, do nothing
    existing_count = (
        db.query(DBSessionTracking)
        .filter(
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == plan_id,
        )
        .count()
    )
    if existing_count > 0:
        return {"success": True, "message": "Sessions already initialised", "created": 0}

    # 5) Create sessions from weekly_schedule
    created_rows: list[DBSessionTracking] = []
    now = datetime.utcnow()

    # Each plan.phase is expected to expose:
    #   phase.week_start (int), phase.week_end (int), phase.weekly_schedule (list of {"day","focus"})
    # If your DB stores JSON strings, ensure .phases is already a parsed structure (your codebase suggests it is).
    for phase in plan.phases:
        # Defensive checks in case of malformed data
        week_start = getattr(phase, "week_start", None)
        week_end = getattr(phase, "week_end", None)
        schedule = getattr(phase, "weekly_schedule", None)
        if not isinstance(week_start, int) or not isinstance(week_end, int) or not isinstance(schedule, list):
            continue  # skip bad phase safely

        for week_num in range(week_start, week_end + 1):
            for day in schedule:
                day_name = (day.get("day") or "").strip()
                focus = (day.get("focus") or "").strip()
                if not day_name or not focus:
                    continue

                created_rows.append(
                    DBSessionTracking(
                        id=str(uuid.uuid4()).lower(),
                        user_id=user.id,
                        plan_id=plan_id,
                        week_number=week_num,
                        day_of_week=day_name,           # e.g. "Monday"
                        focus_name=focus,               # e.g. "Max Boulder Sessions + Density Hangs"
                        is_completed=False,
                        notes="",
                        created_at=now,
                        updated_at=now,
                    )
                )

    # 6) Persist
    if not created_rows:
        # Nothing to create — better to tell the client the plan contained no valid schedule
        raise HTTPException(status_code=422, detail="Plan has no valid weekly schedule to create sessions from")

    db.add_all(created_rows)
    db.commit()

    return {
        "success": True,
        "message": f"Created {len(created_rows)} sessions",
        "created": len(created_rows),
    }

class SessionUpdate(BaseModel):
    is_completed: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("is_completed", "isCompleted"),
    )
    notes: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("notes",),
    )
    completion_date: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("completion_date", "completionDate"),
    )
    model_config = ConfigDict(extra="ignore")

@router.post("/{sessionId}", response_model=Dict[str, Any])
async def update_session(
    email: str,
    planId: str,
    sessionId: str,
    update: SessionUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update session tracking — only modifies existing sessions."""
    logger.info(f"📝 [SESSION UPDATE] {email} / {planId} / {sessionId}")

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_id = planId.lower()
    sess_id = sessionId.lower()

    sess = (
        db.query(DBSessionTracking)
        .filter(
            DBSessionTracking.id == sess_id,
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == plan_id,
        )
        .first()
    )

    if not sess:
        raise HTTPException(
            status_code=404,
            detail="Session not found — please initialize sessions first",
        )

    try:
        if update.is_completed is not None:
            sess.is_completed = update.is_completed
        if update.notes is not None:
            sess.notes = update.notes
        if update.completion_date is not None:
            sess.completion_date = update.completion_date

        sess.updated_at = datetime.utcnow()

        db.commit()

        return {
            "success": True,
            "message": "Session updated successfully",
            "debug_info": {
                "session_id": sess_id,
                "plan_id": plan_id,
                "user_id": user.id,
                "completed": sess.is_completed,
                "notes_length": len(sess.notes or ""),
            },
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"DB error for session {sess_id}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
