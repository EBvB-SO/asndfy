# app/api/exercise_tracking.py

import uuid
from uuid import uuid4, uuid5, NAMESPACE_DNS
import logging
import re
import hashlib
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

class ExerciseTrackingCreateEnhanced(BaseModel):
    id: Optional[str] = None
    session_id: str
    exercise_id: str
    date: str  # YYYY-MM-DD format
    notes: str = ""
    
    @validator('session_id', 'exercise_id', 'id', pre=True, always=True)
    def ensure_lowercase_ids(cls, v):
        if v is None:
            return None
        return str(v).lower()
    
    @validator('date', pre=True)
    def validate_date_format(cls, v):
        if not v:
            return datetime.now().strftime('%Y-%m-%d')
        try:
            datetime.strptime(str(v), '%Y-%m-%d')
            return str(v)
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('notes', pre=True, always=True)
    def validate_notes(cls, v):
        if v is None:
            return ""
        return str(v)

def extract_exact_exercise_title_from_notes(notes: str) -> str:
    """FIXED: Extract exact exercise title from notes with precise pattern matching"""
    # Look for [EXERCISE:title] pattern
    exercise_match = re.search(r'\[EXERCISE:([^\]]+)\]', notes)
    if exercise_match:
        return exercise_match.group(1).strip()
    
    # Fallback: no fuzzy matching, return original note text
    return notes.strip()

def generate_unique_exercise_key(plan_id: str, session_id: str, exercise_title: str) -> str:
    """FIXED: Generate truly unique exercise keys with hash"""
    timestamp = int(datetime.now().timestamp())
    safe_title = exercise_title.strip().replace(" ", "-").replace("_", "-").lower()
    
    # Create hash for uniqueness
    hash_input = f"{plan_id}-{session_id}-{safe_title}-{timestamp}"
    hash_obj = hashlib.md5(hash_input.encode())
    hash_hex = hash_obj.hexdigest()[:8]
    
    return f"{plan_id.lower()}_{session_id.lower()}_{safe_title}_{hash_hex}"

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreateEnhanced,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Enhanced exercise tracking: UUID PK for new records, legacy key for compatibility."""
    logger.info(f"🔍 [FIXED EXERCISE API] Processing exercise for: {email}")

    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Normalize IDs
    planId = planId.lower()
    session_id = tracking.session_id.lower()
    exercise_id = tracking.exercise_id.lower()

    # Extract exact exercise title from notes
    exercise_title = extract_exact_exercise_title_from_notes(tracking.notes)
    if not exercise_title or exercise_title == tracking.notes:
        clean_title = tracking.notes.split("]")[-1].strip()
        if clean_title.endswith(" completed") or clean_title.endswith(" Completed"):
            clean_title = clean_title.rsplit(" ", 1)[0]
        exercise_title = clean_title or "Unknown Exercise"

    # Decide primary key (UUID) and legacy key
    if tracking.id and re.fullmatch(r"[0-9a-fA-F-]{36}", tracking.id):
        record_id = tracking.id.lower()
    else:
        record_id = str(uuid4())  # New proper UUID for DB PK

    legacy_key = generate_unique_exercise_key(planId, session_id, exercise_title)

    logger.info(f"🔍 [FIXED] Tracking details:")
    logger.info(f"  - Exercise Title: '{exercise_title}'")
    logger.info(f"  - UUID PK: {record_id}")
    logger.info(f"  - Legacy Key: {legacy_key}")
    logger.info(f"  - Session: {session_id}")

    try:
        # Ensure plan exists
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        if not existing_plan:
            logger.info(f"📝 Creating plan: {planId}")
            route_parts = planId.replace("_", " ").title().split()
            route_name = " ".join(route_parts[:-1]) if len(route_parts) >= 2 else planId.replace("_", " ").title()
            grade = route_parts[-1] if len(route_parts) >= 2 else "Unknown"
            new_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name=route_name,
                grade=grade,
                route_overview=f"Training plan for {route_name} ({grade})",
                training_overview="Auto-created plan for exercise tracking"
            )
            db.add(new_plan)
            db.flush()

        # Ensure session exists
        existing_session = db.query(DBSessionTracking).filter(
            DBSessionTracking.id == session_id,
            DBSessionTracking.user_id == user.id,
            DBSessionTracking.plan_id == planId
        ).first()
        if not existing_session:
            logger.info(f"📝 Creating session: {session_id}")
            new_session = DBSessionTracking(
                id=session_id,
                user_id=user.id,
                plan_id=planId,
                week_number=1,
                day_of_week=datetime.now().strftime("%A"),
                focus_name=f"{exercise_title} Session",
                is_completed=False,
                notes="Auto-created for exercise tracking",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_session)
            db.flush()

        # Parse date
        try:
            exercise_date = datetime.strptime(tracking.date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {tracking.date}")

        # Prepare notes with legacy key
        enhanced_notes = f"[EXERCISE:{exercise_title}][KEY:{legacy_key}] {tracking.notes}"

        # Try to find existing record by UUID PK
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == record_id,
            DBExerciseTracking.user_id == user.id
        ).first()

        # If not found and client sent old non-UUID id, try fallback search by legacy key
        if not existing_record and tracking.id and not re.fullmatch(r"[0-9a-fA-F-]{36}", tracking.id):
            existing_record = db.query(DBExerciseTracking).filter(
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.notes.ilike(f"%[KEY:{tracking.id}]%")
            ).first()

        if existing_record:
            logger.info(f"🔄 Updating existing record: {existing_record.id}")
            existing_record.notes = enhanced_notes
            existing_record.date = exercise_date
            existing_record.updated_at = datetime.utcnow()
            operation = "updated"
        else:
            logger.info(f"🆕 Creating new record with UUID PK: {record_id}")
            new_record = DBExerciseTracking(
                id=record_id,
                user_id=user.id,
                plan_id=planId,
                session_id=session_id,
                exercise_id=exercise_id,
                date=exercise_date,
                notes=enhanced_notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_record)
            operation = "created"

        db.commit()
        logger.info(f"✅ Successfully {operation} exercise: {record_id}")

        return {
            "success": True,
            "message": f"Exercise tracking {operation} successfully",
            "record_id": record_id,
            "operation": operation,
            "exercise_title": exercise_title
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")


@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """FIXED: Get exercises with exact matching"""
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
        
        logger.info(f"✅ Retrieved {len(records)} exercise records")

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
        logger.error(f"❌ Database error: {e}")
        raise HTTPException(500, "Database error occurred")

@router.put("/exercises/{exercise_id}")
async def update_exercise_tracking(
    email: str,
    planId: str,
    exercise_id: str,
    tracking: ExerciseTrackingCreateEnhanced,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Update an existing exercise tracking record while preserving legacy key."""
    logger.info(f"🔄 [UPDATE EXERCISE] Processing update for: {exercise_id}")
    
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Normalize IDs
    planId = planId.lower()
    exercise_id = exercise_id.lower()
    
    try:
        # Find existing record by UUID PK first
        existing_record = (
            db.query(DBExerciseTracking)
            .filter(
                DBExerciseTracking.id == exercise_id,
                DBExerciseTracking.user_id == user.id,
                DBExerciseTracking.plan_id == planId
            )
            .first()
        )

        # If not found, try legacy key match in notes
        if not existing_record:
            key_marker = f"[KEY:{exercise_id}]"
            existing_record = (
                db.query(DBExerciseTracking)
                .filter(
                    DBExerciseTracking.user_id == user.id,
                    DBExerciseTracking.plan_id == planId,
                    DBExerciseTracking.notes.ilike(f"%{key_marker}%")
                )
                .first()
            )

        if not existing_record:
            raise HTTPException(404, "Exercise record not found")

        # Extract existing legacy key from notes if present
        legacy_key_match = re.search(r"\[KEY:([^\]]+)\]", existing_record.notes or "")
        if legacy_key_match:
            legacy_key = legacy_key_match.group(1).strip()
        else:
            # No existing legacy key, generate one
            exercise_title_for_key = extract_exact_exercise_title_from_notes(tracking.notes) or "Unknown Exercise"
            legacy_key = generate_unique_exercise_key(planId, existing_record.session_id, exercise_title_for_key)

        # Extract exercise title from updated notes
        exercise_title = extract_exact_exercise_title_from_notes(tracking.notes)
        if not exercise_title or exercise_title == tracking.notes:
            clean_title = tracking.notes.split("]")[-1].strip()
            if clean_title.endswith(" completed") or clean_title.endswith(" Completed"):
                clean_title = clean_title.rsplit(" ", 1)[0]
            exercise_title = clean_title or "Unknown Exercise"

        # Parse and validate date
        try:
            exercise_date = datetime.strptime(tracking.date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {tracking.date}")

        # Preserve the same legacy key in notes
        enhanced_notes = f"[EXERCISE:{exercise_title}][KEY:{legacy_key}] {tracking.notes}"
        
        # Apply updates
        existing_record.date = exercise_date
        existing_record.notes = enhanced_notes
        existing_record.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"✅ Successfully updated exercise: {existing_record.id}")
        logger.info(f"  - New date: {exercise_date}")
        logger.info(f"  - Legacy Key preserved: {legacy_key}")
        
        return {
            "success": True, 
            "message": "Exercise tracking updated successfully",
            "exercise_id": existing_record.id,
            "new_date": exercise_date.isoformat(),
            "exercise_title": exercise_title,
            "legacy_key": legacy_key
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error updating exercise: {e}")
        raise HTTPException(500, f"Database error: {str(e)}")

# Keep delete endpoint unchanged
@router.delete("/exercises/{exercise_id}")
async def delete_exercise_tracking(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Delete an exercise tracking record"""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    try:
        existing_record = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id == exercise_id.lower(),
            DBExerciseTracking.user_id == user.id,
            DBExerciseTracking.plan_id == planId.lower()
        ).first()

        if not existing_record:
            return {
                "success": True,
                "message": "Exercise tracking record not found (already deleted)"
            }

        db.delete(existing_record)
        db.commit()
        
        return {
            "success": True,
            "message": "Exercise tracking deleted successfully"
        }

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"❌ Database error: {e}")
        raise HTTPException(500, "Database error occurred")
    
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