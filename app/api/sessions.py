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

    return [
        SessionTracking(
            id             = s.id,
            planId         = s.plan_id,
            weekNumber     = s.week_number,
            dayOfWeek      = s.day_of_week,
            focusName      = s.focus_name,
            isCompleted    = s.is_completed,
            notes          = s.notes or "",
            completionDate = s.completion_date,
            updatedAt      = s.updated_at
        )
        for s in sessions
    ]

from sqlalchemy.exc import SQLAlchemyError

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
                  DBSessionTracking.id      == sessionId,
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
            # create new
            new_sess = DBSessionTracking(
                id             = sessionId.lower(),
                user_id        = user.id,
                plan_id        = planId.lower(),
                week_number    = 1,
                day_of_week    = "Monday",
                focus_name     = "Unknown",
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


from sqlalchemy.exc import SQLAlchemyError

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
) -> Dict[str, Any]:
    """
    Bootstrap tracking sessions for each week/day in a plan,
    based on PlanPhase → PlanSession templates.
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
        return {"success": True, "message": "Sessions already initialized"}

    try:
        # ENSURE PLAN EXISTS - create minimal plan if needed
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.warning(f"Plan {planId} not found, creating minimal plan for session tracking")
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Local Training Plan",
                grade="Unknown",
                route_overview="Auto-created for session tracking",
                training_overview="This plan was auto-created from local session data."
            )
            db.add(minimal_plan)
            db.flush()

        # Try to find phases, but if none exist, create basic sessions
        phases = (
            db.query(PlanPhase)
              .filter(PlanPhase.plan_id == planId)
              .order_by(PlanPhase.phase_order)
              .all()
        )

        created: List[Dict[str, Any]] = []
        
        if phases:
            # Use existing logic with phases
            for phase in phases:
                match = re.search(r"weeks?\s+(\d+)-(\d+)", phase.phase_name.lower())
                if not match:
                    continue
                start, end = int(match.group(1)), int(match.group(2)) + 1

                templates = (
                    db.query(PlanSession)
                      .filter(PlanSession.phase_id == phase.id)
                      .order_by(PlanSession.session_order)
                      .all()
                )

                for week in range(start, end):
                    for tmpl in templates:
                        new_s = DBSessionTracking(
                            id             = str(uuid.uuid4()).lower(),
                            user_id        = user.id,
                            plan_id        = planId,
                            week_number    = week,
                            day_of_week    = tmpl.day,
                            focus_name     = tmpl.focus,
                            is_completed   = False,
                            notes          = "",
                        )
                        db.add(new_s)
                        created.append({
                            "id":           new_s.id,
                            "planId":       planId,
                            "weekNumber":   week,
                            "dayOfWeek":    tmpl.day,
                            "focusName":    tmpl.focus,
                            "isCompleted":  False,
                            "notes":        ""
                        })
        else:
            # No phases found - create basic weekly structure
            logger.info(f"No phases found for plan {planId}, creating basic structure")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            
            for week in range(1, 9):  # 8 week default
                for i, day in enumerate(days):
                    if i < 3:  # Only 3 sessions per week
                        new_s = DBSessionTracking(
                            id             = str(uuid.uuid4()).lower(),
                            user_id        = user.id,
                            plan_id        = planId,
                            week_number    = week,
                            day_of_week    = day,
                            focus_name     = f"Training Session {i+1}",
                            is_completed   = False,
                            notes          = "",
                        )
                        db.add(new_s)
                        created.append({
                            "id":           new_s.id,
                            "planId":       planId,
                            "weekNumber":   week,
                            "dayOfWeek":    day,
                            "focusName":    f"Training Session {i+1}",
                            "isCompleted":  False,
                            "notes":        ""
                        })

        db.commit()
        return {
            "success":  True,
            "message":  f"Created {len(created)} sessions",
            "sessions": created
        }

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed initializing sessions for %s", email)
        raise HTTPException(
            status_code=500,
            detail="Could not initialize sessions, please try again later."
        )
