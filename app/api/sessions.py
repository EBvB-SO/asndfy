# app/api/sessions.py

import uuid
import logging
import re
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    User,
    SessionTracking as DBSessionTracking,
    PlanPhase,
    PlanSession,
    TrainingPlan,
)
from app.models.session import SessionTracking, SessionTrackingUpdateBody
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

@router.post("/{sessionId}", response_model=Dict[str, Any])
async def update_session(
    email: str,
    planId: str,
    sessionId: str,
    update: SessionTrackingUpdateBody,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
) -> Dict[str, Any]:
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    try:
        sess = (
            db.query(DBSessionTracking)
              .filter(
                  DBSessionTracking.id      == sessionId.lower(),
                  DBSessionTracking.user_id == user.id,
                  DBSessionTracking.plan_id == planId.lower(),
              )
              .first()
        )

        if sess:
            # update existing
            sess.is_completed    = update.isCompleted
            sess.notes           = update.notes
            sess.completion_date = update.completionDate
            sess.updated_at      = datetime.utcnow()
        else:
            # create new - ENSURE PLAN EXISTS FIRST
            existing_plan = db.query(TrainingPlan).filter(
                TrainingPlan.id == planId.lower(),
                TrainingPlan.user_id == user.id
            ).first()
            
            if not existing_plan:
                logger.warning(f"Plan {planId} not found, creating minimal plan")
                minimal_plan = TrainingPlan(
                    id=planId.lower(),
                    user_id=user.id,
                    route_name="Local Training Plan",
                    grade="Unknown",
                    route_overview="Auto-created for session tracking",
                    training_overview="This plan was auto-created from session data."
                )
                db.add(minimal_plan)
                db.flush()

            new_sess = DBSessionTracking(
                id             = sessionId.lower(),
                user_id        = user.id,
                plan_id        = planId.lower(),
                week_number    = 1,                    # Default values
                day_of_week    = "Monday",             # Default values
                focus_name     = "Training Session",   # Default values
                is_completed   = update.isCompleted,
                notes          = update.notes,
                completion_date=update.completionDate
            )
            db.add(new_sess)

        db.commit()
        return {"success": True, "message": "Session updated successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Error updating session %s for user %s", sessionId, email)
        raise HTTPException(
            status_code=500,
            detail="Could not update session, please try again later."
        )


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