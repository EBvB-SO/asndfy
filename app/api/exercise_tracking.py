# app/api/exercise_tracking.py - FIXED VERSION

import uuid
import logging
import re
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
    FIXED: Enhanced exercise tracking endpoint with better plan/session creation
    """
    logger.info(f"🔍 [FIXED EXERCISE API] Starting exercise tracking for user: {email}")
    
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
    
    logger.info(f"🔍 [FIXED EXERCISE API] Processing exercise tracking:")
    logger.info(f"  - User: {email} (ID: {user.id})")
    logger.info(f"  - Plan: {planId}")
    logger.info(f"  - Session: {session_id}")
    logger.info(f"  - Exercise: {exercise_id}")
    logger.info(f"  - Record: {record_id}")
    logger.info(f"  - Date: {tracking.date}")
    logger.info(f"  - Notes: {tracking.notes[:200]}...")

    try:
        # FIXED: Better plan creation with more realistic data
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.info(f"📝 [FIXED EXERCISE API] Creating enhanced plan: {planId}")
            
            # Extract route info from planId if possible
            route_parts = planId.replace("_", " ").title().split()
            if len(route_parts) >= 2:
                route_name = " ".join(route_parts[:-1])
                grade = route_parts[-1]
            else:
                route_name = planId.replace("_", " ").title()
                grade = "Unknown"
            
            enhanced_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name=route_name,
                grade=grade,
                route_overview=f"Training plan for {route_name} ({grade}). This plan was auto-created to support exercise tracking and will help you systematically work towards your climbing goals.",
                training_overview=f"Comprehensive training program designed to build the specific strength, technique, and endurance needed for {route_name}. Includes structured progressions and recovery protocols."
            )
            db.add(enhanced_plan)
            try:
                db.flush()
                logger.info(f"✅ [FIXED EXERCISE API] Enhanced plan created successfully: {planId}")
            except Exception as e:
                logger.error(f"❌ [FIXED EXERCISE API] Failed to create plan: {e}")
                db.rollback()
                raise HTTPException(500, f"Failed to create plan: {str(e)}")

        # FIXED: Better session creation with extracted info from notes
        existing_session = db.query(DBSessionTracking).filter(
            DBSessionTracking.id == session_id,
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId
        ).first()
        
        if not existing_session:
            logger.info(f"📝 [FIXED EXERCISE API] Creating enhanced session: {session_id}")
            
            # FIXED: Extract meaningful session data from notes if available
            session_focus = "Training Session"
            week_number = 1
            day_of_week = "Monday"
            
            # Try to extract exercise name from notes for better focus name
            if tracking.notes:
                # Look for [EXERCISE:name] pattern
                exercise_match = re.search(r'\[EXERCISE:([^\]]+)\]', tracking.notes)
                if exercise_match:
                    exercise_name = exercise_match.group(1)
                    session_focus = f"{exercise_name} Session"
                    logger.info(f"🎯 Extracted focus from notes: {session_focus}")
                
                # Try to infer day from session timing or default to current day
                current_day = datetime.now().strftime("%A")
                day_of_week = current_day
                
                # Try to extract week info if available
                week_match = re.search(r'week\s*(\d+)', tracking.notes.lower())
                if week_match:
                    week_number = int(week_match.group(1))
            
            enhanced_session = DBSessionTracking(
                id=session_id,
                user_id=user.id,
                plan_id=planId,
                week_number=week_number,
                day_of_week=day_of_week,
                focus_name=session_focus,
                is_completed=False,
                notes="Auto-created session for exercise tracking",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(enhanced_session)
            try:
                db.flush()
                logger.info(f"✅ [FIXED EXERCISE API] Enhanced session created: {session_id}")
            except Exception as e:
                logger.error(f"❌ [FIXED EXERCISE API] Failed to create session: {e}")
                db.rollback()
                raise HTTPException(500, f"Failed to create session: {str(e)}")

        # Parse and validate date
        try:
            exercise_date = datetime.strptime(tracking.date, '%Y-%m-%d').date()
            logger.info(f"📅 [FIXED EXERCISE API] Parsed date: {exercise_date}")
        except ValueError as e:
            logger.error(f"❌ [FIXED EXERCISE API] Invalid date format: {tracking.date}")
            raise HTTPException(400, f"Invalid date format: {tracking.date}. Expected YYYY-MM-DD")

        # FIXED: Better duplicate handling - check for existing records more thoroughly
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == record_id,
            DBExerciseTracking.user_id == user.id
        ).first()

        # Also check for potential duplicates by session, date, and exercise content
        potential_duplicate = None
        if not existing_record:
            # Look for records with similar content to avoid true duplicates
            similar_records = db.query(DBExerciseTracking).filter(
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.plan_id == planId,
                DBExerciseTracking.session_id == session_id,
                DBExerciseTracking.date == exercise_date
            ).all()
            
            for record in similar_records:
                # Check if the notes contain similar exercise information
                if tracking.notes and record.notes:
                    # Extract exercise names from both
                    new_exercise = re.search(r'\[EXERCISE:([^\]]+)\]', tracking.notes)
                    existing_exercise = re.search(r'\[EXERCISE:([^\]]+)\]', record.notes)
                    
                    if new_exercise and existing_exercise:
                        if new_exercise.group(1) == existing_exercise.group(1):
                            potential_duplicate = record
                            break

        if existing_record:
            # Update existing record
            logger.info(f"🔄 [FIXED EXERCISE API] Updating existing exercise record: {record_id}")
            existing_record.notes = tracking.notes
            existing_record.date = exercise_date
            existing_record.updated_at = datetime.utcnow()
            operation = "updated"
            
        elif potential_duplicate:
            # Update the potential duplicate instead of creating a new one
            logger.info(f"🔄 [FIXED EXERCISE API] Updating potential duplicate: {potential_duplicate.id}")
            potential_duplicate.notes = tracking.notes
            potential_duplicate.date = exercise_date
            potential_duplicate.updated_at = datetime.utcnow()
            operation = "updated"
            record_id = potential_duplicate.id
            
        else:
            # Create new record
            logger.info(f"🆕 [FIXED EXERCISE API] Creating new exercise record: {record_id}")
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

        # Commit the transaction
        try:
            db.commit()
            logger.info(f"✅ [FIXED EXERCISE API] Successfully {operation} exercise tracking: {record_id}")
        except Exception as e:
            logger.error(f"❌ [FIXED EXERCISE API] Commit failed: {e}")
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
                "date": tracking.date,
                "notes_length": len(tracking.notes)
            }
        }

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"❌ [FIXED EXERCISE API] Database integrity error: {e}")
        
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
        logger.error(f"❌ [FIXED EXERCISE API] SQLAlchemy error: {e}")
        raise HTTPException(500, "Database error occurred while saving exercise tracking")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [FIXED EXERCISE API] Unexpected error: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(500, f"An unexpected error occurred: {str(e)}")

# Keep all other existing endpoints unchanged
@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Fetch all exercise tracking records for a given plan"""
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

@router.delete("/exercises/{exercise_id}")
async def delete_exercise_tracking(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Delete an exercise tracking record"""
    logger.info(f"🗑️ [EXERCISE DELETE] Starting deletion for exercise: {exercise_id}")
    
    if email != current_user:
        logger.warning(f"❌ [EXERCISE DELETE] Unauthorized access attempt")
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"❌ [EXERCISE DELETE] User not found: {email}")
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    exercise_id = exercise_id.lower()
    
    logger.info(f"🗑️ [EXERCISE DELETE] Deleting:")
    logger.info(f"  - User: {email} (ID: {user.id})")
    logger.info(f"  - Plan: {planId}")
    logger.info(f"  - Exercise ID: {exercise_id}")

    try:
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == exercise_id,
            DBExerciseTracking.user_id == user.id,
            DBExerciseTracking.plan_id == planId
        ).first()

        if not existing_record:
            logger.warning(f"⚠️ [EXERCISE DELETE] Exercise record not found: {exercise_id}")
            return {
                "success": True,
                "message": "Exercise tracking record not found (already deleted)",
                "record_id": exercise_id
            }

        db.delete(existing_record)
        db.commit()
        
        logger.info(f"✅ [EXERCISE DELETE] Successfully deleted exercise: {exercise_id}")
        
        return {
            "success": True,
            "message": "Exercise tracking deleted successfully",
            "record_id": exercise_id,
            "debug_info": {
                "user_id": user.id,
                "plan_id": planId,
                "exercise_id": exercise_id
            }
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"❌ [EXERCISE DELETE] Database error: {e}")
        raise HTTPException(500, "Database error occurred while deleting exercise tracking")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [EXERCISE DELETE] Unexpected error: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(500, f"An unexpected error occurred: {str(e)}")

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