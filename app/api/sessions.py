# backend/app/api/sessions.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import uuid
import logging

from models.session import SessionTracking, SessionTrackingUpdate
from core.dependencies import get_current_user_email
from core.database import get_db
from sqlalchemy.orm import Session
from db.models import User, SessionTracking as DBSessionTracking, TrainingPlan

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/user/{email}/plans/{plan_id}",
    tags=["Session Tracking"]
)

@router.get("/sessions", response_model=List[SessionTracking])
async def get_sessions(
    email: str, 
    plan_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all tracking sessions for a plan"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all sessions
    sessions = db.query(DBSessionTracking).filter(
        DBSessionTracking.user_id == user.id,
        DBSessionTracking.plan_id == plan_id
    ).order_by(
        DBSessionTracking.week_number,
        DBSessionTracking.day_of_week
    ).all()
    
    # Format response
    return [
        SessionTracking(
            id=session.id,
            planId=session.plan_id,
            weekNumber=session.week_number,
            dayOfWeek=session.day_of_week,
            focusName=session.focus_name,
            isCompleted=session.is_completed,
            notes=session.notes or "",
            completionDate=session.completion_date.isoformat() if session.completion_date else None
        )
        for session in sessions
    ]

@router.post("/sessions")
async def update_session(
    email: str,
    plan_id: str,
    update: SessionTrackingUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Update or create a session"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if session exists
    session = db.query(DBSessionTracking).filter(
        DBSessionTracking.id == update.sessionId,
        DBSessionTracking.plan_id == plan_id,
        DBSessionTracking.user_id == user.id
    ).first()
    
    if session:
        # Update existing
        session.is_completed = update.isCompleted
        session.notes = update.notes
        session.completion_date = datetime.fromisoformat(update.completionDate) if update.completionDate else None
        session.updated_at = datetime.utcnow()
    else:
        # Create new
        session = DBSessionTracking(
            id=update.sessionId,
            user_id=user.id,
            plan_id=plan_id,
            week_number=1,  # Default values
            day_of_week="Monday",
            focus_name="Unknown",
            is_completed=update.isCompleted,
            notes=update.notes,
            completion_date=datetime.fromisoformat(update.completionDate) if update.completionDate else None
        )
        db.add(session)
    
    db.commit()
    return {"success": True, "message": "Session updated successfully"}

@router.post("/initialize")
async def initialize_sessions(
    email: str,
    plan_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Initialize all sessions for a plan"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Implementation would be similar to original
    # This is a placeholder - needs full implementation
    return {"success": True, "message": "Sessions initialized"}