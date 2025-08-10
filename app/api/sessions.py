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
    db: Session   = Depends(get_db),
) -> List[SessionTracking]:
    """
    Retrieve all tracking sessions for a given user & plan.
    """
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # normalize planId
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

    # FIXED: Proper field mapping from DB model to API model
    return [
        SessionTracking(
            id             = s.id,
            planId         = s.plan_id,           # DB field -> API field
            weekNumber     = s.week_number,       # DB field -> API field  
            dayOfWeek      = s.day_of_week,       # DB field -> API field
            focusName      = s.focus_name,        # DB field -> API field
            isCompleted    = s.is_completed,      # DB field -> API field
            notes          = s.notes or "",
            completionDate = s.completion_date,   # DB field -> API field
            updatedAt      = s.updated_at         # DB field -> API field
        )
        for s in sessions
    ]

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
) -> Dict[str, Any]:
    """
    Bootstrap tracking sessions for each week/day in a plan.
    """
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    planId = planId.lower()
    
    # Check if sessions already exist
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
        # ENSURE PLAN EXISTS - create minimal plan if needed
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.warning(f"Plan {planId} not found, creating minimal plan for session initialization")
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Local Training Plan",
                grade="Unknown",
                route_overview="Auto-created for session tracking",
                training_overview="This plan was auto-created from iOS app session data."
            )
            db.add(minimal_plan)
            db.flush()

        created: List[Dict[str, Any]] = []
        
        # Create basic weekly structure for climbing training
        weeks_data = [
            (1, 4, "Base Building"),     # Weeks 1-4
            (5, 8, "Strength Focus"),    # Weeks 5-8
            (9, 12, "Power Development"), # Weeks 9-12
        ]
        
        for start_week, end_week, phase_name in weeks_data:
            # Create sessions per week
            session_templates = [
                ("Monday", "Strength Training"),
                ("Wednesday", "Technique Work"),
                ("Friday", "Power Development"),
            ]
            
            for week in range(start_week, end_week + 1):
                for day, focus in session_templates:
                    new_s = DBSessionTracking(
                        id             = str(uuid.uuid4()).lower(),
                        user_id        = user.id,
                        plan_id        = planId,
                        week_number    = week,
                        day_of_week    = day,
                        focus_name     = f"{focus} - {phase_name}",
                        is_completed   = False,
                        notes          = "",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(), 
                    )
                    db.add(new_s)
                    created.append({
                        "id":           new_s.id,
                        "planId":       planId,
                        "weekNumber":   week,
                        "dayOfWeek":    day,
                        "focusName":    f"{focus} - {phase_name}",
                        "isCompleted":  False,
                        "notes":        ""
                    })

        db.commit()
        logger.info(f"Created {len(created)} sessions for plan {planId}")
        return {
            "success":  True,
            "message":  f"Created {len(created)} sessions",
            "sessions": created
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed initializing sessions for %s", email)
        raise HTTPException(
            status_code=500,
            detail="Could not initialize sessions, please try again later."
        )
    
class SessionUpdate(BaseModel):
    # Accept both is_completed and isCompleted
    is_completed: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("is_completed", "isCompleted")
    )
    # Accept notes
    notes: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("notes",)
    )
    # Accept both completion_date and completionDate
    completion_date: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("completion_date", "completionDate")
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
    """
    Update session tracking. Accepts both camelCase and snake_case fields via Pydantic aliases.
    """
    logger.info("📝 [SESSION UPDATE] Start")
    logger.info(f"  - Email: {email}")
    logger.info(f"  - Plan: {planId}")
    logger.info(f"  - Session: {sessionId}")
    logger.info(f"  - Update: {update.model_dump(exclude_none=True)}")

    if email != current_user:
        logger.warning("❌ [SESSION UPDATE] Unauthorized")
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"❌ [SESSION UPDATE] User not found: {email}")
        raise HTTPException(status_code=404, detail="User not found")

    plan_id = planId.lower()
    sess_id = sessionId.lower()

    # Extract final values once
    completed: bool = update.is_completed if update.is_completed is not None else False
    notes: str = (update.notes or "")
    completion_date: Optional[datetime] = update.completion_date

    try:
        sess = (
            db.query(DBSessionTracking)
              .filter(
                  DBSessionTracking.id == sess_id,
                  DBSessionTracking.user_id == user.id,
                  DBSessionTracking.plan_id == plan_id,
              )
              .first()
        )

        if sess:
            logger.info(f"🔄 [SESSION UPDATE] Updating existing session: {sess_id}")

            # Only apply fields that were provided in the request
            if update.is_completed is not None:
                sess.is_completed = update.is_completed
            if update.notes is not None:
                sess.notes = update.notes
            if update.completion_date is not None:
                sess.completion_date = update.completion_date

            sess.updated_at = datetime.utcnow()

            # Reflect final values for the response/debug payload
            completed = sess.is_completed
            notes = sess.notes or ""
            completion_date = sess.completion_date
        else:
            logger.info(f"🆕 [SESSION UPDATE] Creating new session: {sess_id}")

            # Ensure plan exists
            existing_plan = db.query(TrainingPlan).filter(
                TrainingPlan.id == plan_id,
                TrainingPlan.user_id == user.id
            ).first()
            if not existing_plan:
                logger.warning(f"📝 [SESSION UPDATE] Plan {plan_id} not found, creating minimal plan")
                minimal_plan = TrainingPlan(
                    id=plan_id,
                    user_id=user.id,
                    route_name="Local Training Plan",
                    grade="Unknown",
                    route_overview="Auto-created for session tracking",
                    training_overview="This plan was auto-created from session data."
                )
                db.add(minimal_plan)
                db.flush()

            new_sess = DBSessionTracking(
                id             = sess_id,
                user_id        = user.id,
                plan_id        = plan_id,
                week_number    = 1,
                day_of_week    = "Monday",
                focus_name     = "Training Session",
                is_completed   = completed,
                notes          = notes,
                completion_date= completion_date,
                created_at     = datetime.utcnow(),
                updated_at     = datetime.utcnow()
            )
            db.add(new_sess)

        db.commit()
        logger.info("✅ [SESSION UPDATE] Commit OK")

        return {
            "success": True,
            "message": "Session updated successfully",
            "debug_info": {
                "session_id": sess_id,
                "plan_id": plan_id,
                "user_id": user.id,
                "completed": completed,
                "notes_length": len(notes)
            }
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"❌ [SESSION UPDATE] DB error for session {sess_id}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.exception(f"❌ [SESSION UPDATE] Unexpected error for session {sess_id}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")