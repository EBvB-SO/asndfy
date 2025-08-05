# app/api/exercise_tracking.py

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

# Enhanced request model with better validation
class ExerciseTrackingCreateEnhanced(BaseModel):
    id: Optional[str] = None
    session_id: str
    exercise_id: str
    date: str  # YYYY-MM-DD format
    notes: str = ""
    
    @validator('session_id', 'exercise_id', 'id', pre=True, always=True)
    def ensure_lowercase_ids(cls, v):
        """Ensure all IDs are lowercase for consistency"""
        if v is None:
            return None
        return str(v).lower()
    
    @validator('date', pre=True)
    def validate_date_format(cls, v):
        """Validate date is in YYYY-MM-DD format"""
        if not v:
            # Use current date if none provided
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            datetime.strptime(str(v), '%Y-%m-%d')
            return str(v)
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('notes', pre=True, always=True)
    def validate_notes(cls, v):
        """Ensure notes is always a string"""
        if v is None:
            return ""
        return str(v)

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreateEnhanced,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Enhanced exercise tracking endpoint with comprehensive error handling and logging
    """
    logger.info(f"🔍 [EXERCISE API] Starting exercise tracking for user: {email}")
    
    if email != current_user:
        logger.warning(f"❌ [EXERCISE API] Unauthorized access attempt: {current_user} trying to access {email}")
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"❌ [EXERCISE API] User not found: {email}")
        raise HTTPException(404, "User not found")

    # Ensure consistent lowercase IDs
    planId = planId.lower()
    session_id = tracking.session_id.lower()
    exercise_id = tracking.exercise_id.lower()
    record_id = (tracking.id or str(uuid.uuid4())).lower()
    
    logger.info(f"🔍 [EXERCISE API] Processing exercise tracking:")
    logger.info(f"  - User: {email} (ID: {user.id})")
    logger.info(f"  - Plan: {planId}")
    logger.info(f"  - Session: {session_id}")
    logger.info(f"  - Exercise: {exercise_id}")
    logger.info(f"  - Record: {record_id}")
    logger.info(f"  - Date: {tracking.date}")
    logger.info(f"  - Notes: {tracking.notes[:100]}...")

    try:
        # Step 1: Ensure plan exists
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.info(f"📝 [EXERCISE API] Creating minimal plan: {planId}")
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Auto-created Plan",
                grade="Unknown",
                route_overview="This plan was auto-created to support exercise tracking.",
                training_overview="Auto-generated training plan for exercise tracking."
            )
            db.add(minimal_plan)
            try:
                db.flush()
                logger.info(f"✅ [EXERCISE API] Plan created successfully: {planId}")
            except Exception as e:
                logger.error(f"❌ [EXERCISE API] Failed to create plan: {e}")
                db.rollback()
                raise HTTPException(500, f"Failed to create plan: {str(e)}")

        # Step 2: Ensure session exists
        existing_session = db.query(DBSessionTracking).filter(
            DBSessionTracking.id == session_id,
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId
        ).first()
        
        if not existing_session:
            logger.info(f"📝 [EXERCISE API] Creating minimal session: {session_id}")
            
            # Try to parse meaningful session data from the session ID or use defaults
            minimal_session = DBSessionTracking(
                id=session_id,
                user_id=user.id,
                plan_id=planId,
                week_number=1,
                day_of_week="Monday",
                focus_name="Auto-created Session",
                is_completed=False,
                notes="",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(minimal_session)
            try:
                db.flush()
                logger.info(f"✅ [EXERCISE API] Session created successfully: {session_id}")
            except Exception as e:
                logger.error(f"❌ [EXERCISE API] Failed to create session: {e}")
                db.rollback()
                raise HTTPException(500, f"Failed to create session: {str(e)}")

        # Step 3: Parse and validate date
        try:
            exercise_date = datetime.strptime(tracking.date, '%Y-%m-%d').date()
            logger.info(f"📅 [EXERCISE API] Parsed date: {exercise_date}")
        except ValueError as e:
            logger.error(f"❌ [EXERCISE API] Invalid date format: {tracking.date}")
            raise HTTPException(400, f"Invalid date format: {tracking.date}. Expected YYYY-MM-DD")

        # Step 4: Check if exercise tracking record already exists
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == record_id,
            DBExerciseTracking.user_id == user.id
        ).first()

        if existing_record:
            # Update existing record
            logger.info(f"🔄 [EXERCISE API] Updating existing exercise record: {record_id}")
            existing_record.notes = tracking.notes
            existing_record.date = exercise_date
            existing_record.updated_at = datetime.utcnow()
            
            operation = "updated"
        else:
            # Create new record
            logger.info(f"🆕 [EXERCISE API] Creating new exercise record: {record_id}")
            new_record = DBExerciseTracking(
                id=record_id,
                user_id=user.id,
                plan_id=planId,
                session_id=session_id,
                exercise_id=exercise_id,
                date=exercise_date,
                notes=tracking.notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_record)
            operation = "created"

        # Step 5: Commit the transaction
        try:
            db.commit()
            logger.info(f"✅ [EXERCISE API] Successfully {operation} exercise tracking: {record_id}")
        except Exception as e:
            logger.error(f"❌ [EXERCISE API] Commit failed: {e}")
            db.rollback()
            raise HTTPException(500, f"Failed to save exercise tracking: {str(e)}")
        
        return {
            "success": True, 
            "message": f"Exercise tracking {operation} successfully",
            "record_id": record_id,
            "operation": operation,
            "debug_info": {
                "user_id": user.id,
                "plan_id": planId,
                "session_id": session_id,
                "exercise_id": exercise_id,
                "date": tracking.date
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"❌ [EXERCISE API] Database integrity error: {e}")
        
        # Check specific constraint violations
        error_detail = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'foreign key' in error_detail.lower():
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
        logger.error(f"❌ [EXERCISE API] SQLAlchemy error: {e}")
        raise HTTPException(500, "Database error occurred while saving exercise tracking")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [EXERCISE API] Unexpected error: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(500, f"An unexpected error occurred: {str(e)}")

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
    
    logger.info(f"🔍 [EXERCISE API] Fetching exercises for plan: {planId}")
    
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
        
        logger.info(f"✅ [EXERCISE API] Retrieved {len(records)} exercise records for plan {planId}")

        result = []
        for rec in records:
            result.append(ExerciseTracking(
                id=rec.id,
                plan_id=rec.plan_id,
                session_id=rec.session_id,
                exercise_id=rec.exercise_id,
                date=rec.date,
                notes=rec.notes or ""
            ))
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"❌ [EXERCISE API] Database error retrieving exercises for plan {planId}: {e}")
        raise HTTPException(500, "Database error occurred while retrieving exercises")

# Add debugging endpoint
@router.get("/exercises/debug")
async def debug_exercise_tracking(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Debug endpoint to check exercise tracking status"""
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
    
    # Get recent exercises
    recent_exercises = (
        db.query(DBExerciseTracking)
        .filter(
            DBExerciseTracking.plan_id == planId,
            DBExerciseTracking.user_id == user.id
        )
        .order_by(DBExerciseTracking.created_at.desc())
        .limit(5)
        .all()
    )
    
    return {
        "user_id": user.id,
        "user_email": email,
        "plan_id": planId,
        "plan_exists": plan_exists,
        "session_count": session_count,
        "exercise_count": exercise_count,
        "recent_exercises": [
            {
                "id": ex.id,
                "session_id": ex.session_id,
                "exercise_id": ex.exercise_id, 
                "date": ex.date.isoformat(),
                "notes": ex.notes[:100] + "..." if len(ex.notes) > 100 else ex.notes,
                "created_at": ex.created_at.isoformat() if ex.created_at else None
            }
            for ex in recent_exercises
        ],
        "timestamp": datetime.utcnow().isoformat()
    }