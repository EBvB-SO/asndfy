# backend/app/api/sessions.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from db.models import PlanPhase, PlanSession
import uuid
import logging
import re

from models.session import SessionTracking, SessionTrackingUpdate
from core.dependencies import get_current_user_email
from core.database import get_db
from sqlalchemy.orm import Session
from db.models import User, SessionTracking as DBSessionTracking, TrainingPlan
from db.models import PendingSessionUpdate

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

@router.get("/user/{email}/pending_updates")
async def get_pending_updates(
    email: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all pending updates for a user"""
    # Implementation needed
    pass

@router.post("/user/{email}/sync_pending_updates")
async def sync_pending_updates(
    email: str,
    update_ids: List[int],
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Mark pending updates as synced"""
    # Implementation needed
    pass

@router.get("/user/{email}/pending_updates")
async def get_pending_updates(
    email: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all pending updates for a user"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = db.query(PendingSessionUpdate).filter(
        PendingSessionUpdate.user_id == user.id,
        PendingSessionUpdate.is_synced == False
    ).all()
    
    return {
        "success": True,
        "updates": [
            {
                "id": update.id,
                "planId": update.plan_id,
                "sessionId": update.session_id,
                "isCompleted": update.is_completed,
                "notes": update.notes or "",
                "timestamp": update.timestamp.isoformat()
            }
            for update in updates
        ]
    }

@router.post("/user/{email}/sync_pending_updates")
async def sync_pending_updates(
    email: str,
    update_ids: List[int],
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Mark pending updates as synced"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mark each update as synced
    synced_count = 0
    for update_id in update_ids:
        update = db.query(PendingSessionUpdate).filter(
            PendingSessionUpdate.id == update_id,
            PendingSessionUpdate.user_id == user.id
        ).first()
        
        if update:
            update.is_synced = True
            synced_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Marked {synced_count} updates as synced"
    }

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
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if sessions already exist
    existing_count = db.query(DBSessionTracking).filter(
        DBSessionTracking.user_id == user.id,
        DBSessionTracking.plan_id == plan_id
    ).count()
    
    if existing_count > 0:
        return {"success": True, "message": "Sessions already initialized"}
    
    # Get plan phases
    phases = db.query(PlanPhase).filter(
        PlanPhase.plan_id == plan_id
    ).order_by(PlanPhase.phase_order).all()
    
    created_sessions = []
    
    for phase in phases:
        # Extract week range from phase name
        week_match = re.search(r'weeks?\s+(\d+)-(\d+)', phase.phase_name.lower())
        if week_match:
            start_week = int(week_match.group(1))
            end_week = int(week_match.group(2)) + 1
            
            # Get sessions for this phase
            sessions = db.query(PlanSession).filter(
                PlanSession.phase_id == phase.id
            ).order_by(PlanSession.session_order).all()
            
            # Create tracking sessions for each week
            for week_num in range(start_week, end_week):
                for session in sessions:
                    new_session = DBSessionTracking(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        plan_id=plan_id,
                        week_number=week_num,
                        day_of_week=session.day,
                        focus_name=session.focus,
                        is_completed=False,
                        notes=""
                    )
                    db.add(new_session)
                    created_sessions.append({
                        "id": new_session.id,
                        "planId": plan_id,
                        "weekNumber": week_num,
                        "dayOfWeek": session.day,
                        "focusName": session.focus,
                        "isCompleted": False,
                        "notes": ""
                    })
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Created {len(created_sessions)} sessions",
        "sessions": created_sessions
    }