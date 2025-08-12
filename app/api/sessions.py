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

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Bootstrap tracking sessions for each week/day in a plan."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    planId = planId.lower()

    already = (
        db.query(DBSessionTracking)
        .filter(
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId,
        )
        .count()
    )
    if already > 0:
        logger.info(f"Sessions already exist for plan {planId} ({already} sessions)")
        return {"success": True, "message": "Sessions already initialized"}

    try:
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id,
        ).first()

        if not existing_plan:
            logger.warning(f"Plan {planId} not found, creating minimal plan")
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Local Training Plan",
                grade="Unknown",
                route_overview="Auto-created for session tracking",
                training_overview="This plan was auto-created from iOS app session data.",
            )
            db.add(minimal_plan)
            db.flush()

        created: List[Dict[str, Any]] = []

        weeks_data = [
            (1, 4, "Base Building"),
            (5, 8, "Strength Focus"),
            (9, 12, "Power Development"),
        ]

        for start_week, end_week, phase_name in weeks_data:
            session_templates = [
                ("Monday", "Strength Training"),
                ("Wednesday", "Technique Work"),
                ("Friday", "Power Development"),
            ]
            for week in range(start_week, end_week + 1):
                for day, focus in session_templates:
                    new_s = DBSessionTracking(
                        id=str(uuid.uuid4()).lower(),
                        user_id=user.id,
                        plan_id=planId,
                        week_number=week,
                        day_of_week=day,
                        focus_name=f"{focus} - {phase_name}",
                        is_completed=False,
                        notes="",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(new_s)
                    created.append(
                        {
                            "id": new_s.id,
                            "planId": planId,
                            "weekNumber": week,
                            "dayOfWeek": day,
                            "focusName": f"{focus} - {phase_name}",
                            "isCompleted": False,
                            "notes": "",
                        }
                    )

        db.commit()
        logger.info(f"Created {len(created)} sessions for plan {planId}")
        return {
            "success": True,
            "message": f"Created {len(created)} sessions",
            "sessions": created,
        }

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed initializing sessions")
        raise HTTPException(status_code=500, detail="Could not initialize sessions")

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
