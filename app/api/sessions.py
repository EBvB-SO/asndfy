# app/api/sessions.py

import uuid
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
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
    """
    Update session tracking with proper field mapping
    FIXED: Handles both camelCase (iOS) and snake_case (backend) 
    """
    logger.info(f"📝 [SESSION UPDATE] Starting session update:")
    logger.info(f"  - Email: {email}")
    logger.info(f"  - Plan: {planId}")
    logger.info(f"  - Session: {sessionId}")
    logger.info(f"  - Update: {update.dict()}")
    
    if email != current_user:
        logger.warning(f"❌ [SESSION UPDATE] Unauthorized access attempt")
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"❌ [SESSION UPDATE] User not found: {email}")
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
            # Update existing session
            logger.info(f"🔄 [SESSION UPDATE] Updating existing session: {sessionId}")
            
            # CRITICAL FIX: Handle both camelCase and snake_case from iOS
            completed = getattr(update, 'isCompleted', None) or getattr(update, 'is_completed', False)
            notes = getattr(update, 'notes', '') or ''
            completion_date = getattr(update, 'completionDate', None) or getattr(update, 'completion_date', None)
            
            sess.is_completed    = completed
            sess.notes           = notes
            sess.completion_date = completion_date
            sess.updated_at      = datetime.utcnow()
            
            logger.info(f"✅ [SESSION UPDATE] Updated fields:")
            logger.info(f"  - is_completed: {sess.is_completed}")
            logger.info(f"  - notes: '{sess.notes}'")
            logger.info(f"  - completion_date: {sess.completion_date}")
        else:
            # Create new session
            logger.info(f"🆕 [SESSION UPDATE] Creating new session: {sessionId}")
            
            # ENSURE PLAN EXISTS FIRST
            existing_plan = db.query(TrainingPlan).filter(
                TrainingPlan.id == planId.lower(),
                TrainingPlan.user_id == user.id
            ).first()
            
            if not existing_plan:
                logger.warning(f"📝 [SESSION UPDATE] Plan {planId} not found, creating minimal plan")
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

            # Handle field mapping for new session too
            completed = getattr(update, 'isCompleted', None) or getattr(update, 'is_completed', False)
            notes = getattr(update, 'notes', '') or ''
            completion_date = getattr(update, 'completionDate', None) or getattr(update, 'completion_date', None)

            new_sess = DBSessionTracking(
                id             = sessionId.lower(),
                user_id        = user.id,
                plan_id        = planId.lower(),
                week_number    = 1,                    # Default values
                day_of_week    = "Monday",             # Default values
                focus_name     = "Training Session",   # Default values
                is_completed   = completed,
                notes          = notes,
                completion_date= completion_date,
                created_at     = datetime.utcnow(),
                updated_at     = datetime.utcnow()
            )
            db.add(new_sess)
            
            logger.info(f"✅ [SESSION UPDATE] Created new session with fields:")
            logger.info(f"  - is_completed: {new_sess.is_completed}")
            logger.info(f"  - notes: '{new_sess.notes}'")

        db.commit()
        logger.info(f"✅ [SESSION UPDATE] Session update committed successfully")
        
        return {
            "success": True, 
            "message": "Session updated successfully",
            "debug_info": {
                "session_id": sessionId,
                "plan_id": planId,
                "user_id": user.id,
                "completed": completed,
                "notes_length": len(notes)
            }
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"❌ [SESSION UPDATE] Database error updating session {sessionId}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"❌ [SESSION UPDATE] Unexpected error updating session {sessionId}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

class FlexibleSessionUpdate(BaseModel):
    """Flexible session update model that handles both camelCase and snake_case"""
    
    # Primary fields (snake_case for backend)
    is_completed: Optional[bool] = None
    notes: Optional[str] = None
    completion_date: Optional[datetime] = None
    
    # Alternative fields (camelCase from iOS)
    isCompleted: Optional[bool] = None
    completionDate: Optional[datetime] = None
    
    class Config:
        extra = "allow"  # Allow additional fields
    
    def get_completed(self) -> bool:
        """Get completion status from either field name"""
        return self.is_completed if self.is_completed is not None else (self.isCompleted or False)
    
    def get_notes(self) -> str:
        """Get notes with fallback"""
        return self.notes or ""
    
    def get_completion_date(self) -> Optional[datetime]:
        """Get completion date from either field name"""
        return self.completion_date if self.completion_date is not None else self.completionDate


# Update the route signature to use the flexible model:
# @router.post("/{sessionId}", response_model=Dict[str, Any])
# async def update_session(
#     email: str,
#     planId: str, 
#     sessionId: str,
#     update: FlexibleSessionUpdate,  # <-- Use this instead
#     current_user: str = Depends(get_current_user_email),
#     db: Session = Depends(get_db),
# ):
#     # Then use update.get_completed(), update.get_notes(), etc.

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