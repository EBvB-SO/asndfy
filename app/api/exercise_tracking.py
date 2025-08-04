# app/api/exercise_tracking.py - Enhanced version with better error handling

import uuid
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import BaseModel, validator

from app.models.exercise import (
    ExerciseTracking,          
    ExerciseTrackingCreate,    
    ExerciseTrackingUpdate     
)
from app.core.dependencies import get_current_user_email
from app.core.database import get_db
from app.db.models import User, ExerciseTracking as DBExerciseTracking, TrainingPlan, SessionTracking as DBSessionTracking

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}",
    tags=["Exercise Tracking"],
)

# Enhanced request model with validation
class ExerciseTrackingCreateEnhanced(BaseModel):
    id: Optional[str] = None
    session_id: str
    exercise_id: str
    date: str  # YYYY-MM-DD format
    notes: str = ""
    
    @validator('session_id', 'exercise_id', 'id', pre=True)
    def ensure_lowercase_ids(cls, v):
        """Ensure all IDs are lowercase for consistency"""
        if v:
            return str(v).lower()
        return v
    
    @validator('date')
    def validate_date_format(cls, v):
        """Validate date is in YYYY-MM-DD format"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreateEnhanced,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Enhanced exercise tracking endpoint with better error handling and logging
    """
    if email != current_user:
        logger.warning(f"Unauthorized access attempt: {current_user} trying to access {email}")
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"User not found: {email}")
        raise HTTPException(404, "User not found")

    # Ensure consistent lowercase IDs
    planId = planId.lower()
    session_id = tracking.session_id.lower()
    exercise_id = tracking.exercise_id.lower()
    record_id = (tracking.id or str(uuid.uuid4())).lower()
    
    logger.info(f"Processing exercise tracking: user={email}, plan={planId}, session={session_id}, exercise={exercise_id}")

    try:
        # Ensure plan exists - create minimal one if needed
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.info(f"Creating minimal plan for exercise tracking: {planId}")
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Local Training Plan",
                grade="Unknown Grade",
                route_overview="Auto-created for exercise tracking",
                training_overview="This plan was auto-created to support exercise tracking."
            )
            db.add(minimal_plan)
            db.flush()  # Ensure plan exists before continuing

        # Ensure session exists - create minimal one if needed
        existing_session = db.query(DBSessionTracking).filter(
            DBSessionTracking.id == session_id,
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId
        ).first()
        
        if not existing_session:
            logger.info(f"Creating minimal session for exercise tracking: {session_id}")
            minimal_session = DBSessionTracking(
                id=session_id,
                user_id=user.id,
                plan_id=planId,
                week_number=1,
                day_of_week="Monday",
                focus_name="Auto-created session",
                is_completed=False,
                notes=""
            )
            db.add(minimal_session)
            db.flush()  # Ensure session exists before continuing

        # Check if exercise tracking record already exists
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == record_id,
            DBExerciseTracking.user_id == user.id
        ).first()

        # Parse date
        try:
            exercise_date = datetime.strptime(tracking.date, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Invalid date format: {tracking.date}")
            raise HTTPException(400, f"Invalid date format: {tracking.date}. Expected YYYY-MM-DD")

        if existing_record:
            # Update existing record
            logger.info(f"Updating existing exercise record: {record_id}")
            existing_record.notes = tracking.notes
            existing_record.date = exercise_date
            existing_record.updated_at = datetime.utcnow()
        else:
            # Create new record
            logger.info(f"Creating new exercise record: {record_id}")
            new_record = DBExerciseTracking(
                id=record_id,
                user_id=user.id,
                plan_id=planId,
                session_id=session_id,
                exercise_id=exercise_id,
                date=exercise_date,
                notes=tracking.notes
            )
            db.add(new_record)

        db.commit()
        logger.info(f"Successfully saved exercise tracking: {record_id}")
        
        return {
            "success": True, 
            "message": "Exercise tracking saved successfully",
            "record_id": record_id
        }

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error for user {email}: {e}")
        
        # Check specific constraint violations
        error_detail = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'foreign key constraint' in error_detail.lower():
            if 'session_id' in error_detail.lower():
                raise HTTPException(400, f"Session {session_id} does not exist for this plan")
            elif 'plan_id' in error_detail.lower():
                raise HTTPException(400, f"Plan {planId} does not exist")
            else:
                raise HTTPException(400, "Database constraint violation")
        else:
            raise HTTPException(400, f"Database error: {error_detail}")
            
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"Database error saving exercise for user {email}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred while saving exercise tracking"
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error saving exercise for user {email}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while saving exercise tracking"
        )

@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Fetch all exercise tracking records for a given plan with enhanced error handling"""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    
    try:
        records = (
            db.query(DBExerciseTracking)
            .filter(
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.plan_id == planId,
            )
            .order_by(DBExerciseTracking.date.desc())
            .all()
        )
        
        logger.info(f"Retrieved {len(records)} exercise records for plan {planId}")

        return [
            ExerciseTracking(
                id=rec.id,
                plan_id=rec.plan_id,
                session_id=rec.session_id,
                exercise_id=rec.exercise_id,
                date=rec.date,
                notes=rec.notes or ""
            )
            for rec in records
        ]
        
    except SQLAlchemyError as e:
        logger.exception(f"Database error retrieving exercises for plan {planId}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred while retrieving exercises"
        )

@router.get("/exercises/{exercise_id}/history")
async def get_exercise_history(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Get the full history of a single exercise across all sessions with enhanced logging"""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    exercise_id = exercise_id.lower()
    
    try:
        history = (
            db.query(DBExerciseTracking)
            .filter(
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.plan_id == planId,
                DBExerciseTracking.exercise_id == exercise_id,
            )
            .order_by(DBExerciseTracking.date.desc())
            .all()
        )
        
        logger.info(f"Retrieved {len(history)} history records for exercise {exercise_id}")

        return {
            "exercise_id": exercise_id,
            "plan_id": planId,
            "total_records": len(history),
            "history": [
                {
                    "id": rec.id,
                    "date": rec.date.isoformat(),
                    "notes": rec.notes or "",
                    "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
                    "session_id": rec.session_id
                }
                for rec in history
            ]
        }
        
    except SQLAlchemyError as e:
        logger.exception(f"Database error retrieving exercise history for {exercise_id}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred while retrieving exercise history"
        )

@router.delete("/exercises/{exercise_id}")
async def delete_exercise(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Delete exercise tracking record with enhanced error handling"""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    exercise_id = exercise_id.lower()
    
    try:
        record = (
            db.query(DBExerciseTracking)
            .filter(
                DBExerciseTracking.id == exercise_id,
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.plan_id == planId,
            )
            .first()
        )
        
        if not record:
            logger.warning(f"Exercise tracking not found for deletion: {exercise_id}")
            raise HTTPException(404, "Exercise tracking record not found")

        db.delete(record)
        db.commit()
        
        logger.info(f"Successfully deleted exercise tracking: {exercise_id}")
        
        return {
            "success": True, 
            "message": "Exercise tracking deleted successfully",
            "deleted_id": exercise_id
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"Database error deleting exercise {exercise_id} for user {email}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred while deleting exercise tracking"
        )

# Health check endpoint for debugging
@router.get("/exercises/health")
async def health_check(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Health check endpoint for debugging sync issues"""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    
    # Check plan exists
    plan_exists = db.query(TrainingPlan).filter(
        TrainingPlan.id == planId,
        TrainingPlan.user_id == user.id
    ).first() is not None
    
    # Count sessions
    session_count = db.query(DBSessionTracking).filter(
        DBSessionTracking.plan_id == planId,
        DBSessionTracking.user_id == user.id
    ).count()
    
    # Count exercises
    exercise_count = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.plan_id == planId,
        DBExerciseTracking.user_id == user.id
    ).count()
    
    return {
        "user_id": user.id,
        "plan_id": planId,
        "plan_exists": plan_exists,
        "session_count": session_count,
        "exercise_count": exercise_count,
        "timestamp": datetime.utcnow().isoformat()
    }