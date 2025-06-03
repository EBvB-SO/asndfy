# app/api/exercise_tracking.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import uuid
import logging

from models.exercise import ExerciseTracking, ExerciseTrackingCreate, ExerciseTrackingUpdate
from core.dependencies import get_current_user_email
from core.database import get_db
from sqlalchemy.orm import Session
from db.models import User, ExerciseTracking as DBExerciseTracking, SessionTracking, Exercise

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/user/{email}/plans/{plan_id}",
    tags=["Exercise Tracking"]
)

@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str, 
    plan_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all exercise tracking records for a plan"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    exercises = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.user_id == user.id,
        DBExerciseTracking.plan_id == plan_id
    ).order_by(DBExerciseTracking.date.desc()).all()
    
    return [
        ExerciseTracking(
            id=ex.id,
            planId=ex.plan_id,
            sessionId=ex.session_id,
            exerciseId=ex.exercise_id,
            date=ex.date.isoformat(),
            notes=ex.notes or ""
        )
        for ex in exercises
    ]

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    plan_id: str,
    tracking: ExerciseTrackingCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Add or update exercise tracking"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if tracking already exists
    existing = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.id == tracking.id,
        DBExerciseTracking.user_id == user.id
    ).first()
    
    if existing:
        # Update existing
        existing.notes = tracking.notes
        existing.date = datetime.fromisoformat(tracking.date)
        existing.updated_at = datetime.utcnow()
    else:
        # Create new
        new_tracking = DBExerciseTracking(
            id=tracking.id or str(uuid.uuid4()),
            user_id=user.id,
            plan_id=plan_id,
            session_id=tracking.sessionId,
            exercise_id=tracking.exerciseId,
            date=datetime.fromisoformat(tracking.date),
            notes=tracking.notes
        )
        db.add(new_tracking)
    
    db.commit()
    return {"success": True, "message": "Exercise tracking saved"}

@router.get("/exercises/{exercise_id}/history")
async def get_exercise_history(
    email: str,
    plan_id: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get history of a specific exercise across all sessions"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    history = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.user_id == user.id,
        DBExerciseTracking.plan_id == plan_id,
        DBExerciseTracking.exercise_id == exercise_id
    ).order_by(DBExerciseTracking.date.desc()).all()
    
    return {
        "history": [
            {
                "id": h.id,
                "date": h.date.isoformat(),
                "notes": h.notes or "",
                "updatedAt": h.updated_at.isoformat() if h.updated_at else None
            }
            for h in history
        ]
    }

@router.delete("/exercises/{exercise_id}")
async def delete_exercise(
    email: str,
    plan_id: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Delete an exercise tracking record"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tracking = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.id == exercise_id,
        DBExerciseTracking.user_id == user.id,
        DBExerciseTracking.plan_id == plan_id
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Exercise tracking not found")
    
    db.delete(tracking)
    db.commit()
    
    return {"success": True, "message": "Exercise tracking deleted"}