# app/api/exercise_tracking.py

import uuid
import logging
import re
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, validator

from app.models.exercise import ExerciseTracking
from app.core.dependencies import get_current_user_email
from app.core.database import get_db
from app.db.models import User, ExerciseTracking as DBExerciseTracking, TrainingPlan

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}",
    tags=["Exercise Tracking"],
)

class ExerciseTrackingCreateEnhanced(BaseModel):
    id: Optional[str] = None
    session_id: str
    exercise_id: str
    date: str
    notes: str = ""

    @validator("session_id", "exercise_id", "id", pre=True, always=True)
    def ensure_lowercase_ids(cls, v):
        return str(v).lower() if v is not None else None

    @validator("date", pre=True)
    def validate_date_format(cls, v):
        if not v:
            return datetime.now().strftime("%Y-%m-%d")
        try:
            datetime.strptime(str(v), "%Y-%m-%d")
            return str(v)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

    @validator("notes", pre=True, always=True)
    def validate_notes(cls, v):
        return str(v) if v is not None else ""

def extract_exact_exercise_title_from_notes(notes: str) -> str:
    match = re.search(r"\[EXERCISE:([^\]]+)\]", notes)
    if match:
        return match.group(1).strip()
    return notes.strip()

def generate_unique_exercise_key(plan_id: str, session_id: str, exercise_title: str) -> str:
    timestamp = int(datetime.now().timestamp())
    safe_title = exercise_title.strip().replace(" ", "-").replace("_", "-").lower()
    hash_input = f"{plan_id}-{session_id}-{safe_title}-{timestamp}"
    hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"{plan_id.lower()}_{session_id.lower()}_{safe_title}_{hash_hex}"

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreateEnhanced,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Track an exercise — requires an existing session."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    session_id = tracking.session_id.lower()
    exercise_id = tracking.exercise_id.lower()

    # Ensure plan exists
    existing_plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == planId,
        TrainingPlan.user_id == user.id,
    ).first()
    if not existing_plan:
        raise HTTPException(404, "Plan not found — please create or initialize first")

    # Ensure session exists
    existing_session = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.session_id == session_id,
        DBExerciseTracking.user_id == user.id,
        DBExerciseTracking.plan_id == planId,
    ).first()
    if not existing_session:
        raise HTTPException(404, "Session not found — please initialize sessions first")

    exercise_title = extract_exact_exercise_title_from_notes(tracking.notes)
    if not exercise_title or exercise_title == tracking.notes:
        clean_title = tracking.notes.split("]")[-1].strip()
        if clean_title.endswith(" completed") or clean_title.endswith(" Completed"):
            clean_title = clean_title.rsplit(" ", 1)[0]
        exercise_title = clean_title or "Unknown Exercise"

    record_id = (
        tracking.id.lower()
        if tracking.id and re.fullmatch(r"[0-9a-fA-F-]{36}", tracking.id)
        else str(uuid.uuid4())
    )

    legacy_key = generate_unique_exercise_key(planId, session_id, exercise_title)
    try:
        exercise_date = datetime.strptime(tracking.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, f"Invalid date format: {tracking.date}")

    enhanced_notes = f"[EXERCISE:{exercise_title}][KEY:{legacy_key}] {tracking.notes}"

    existing_record = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.id == record_id,
        DBExerciseTracking.user_id == user.id,
    ).first()

    if existing_record:
        existing_record.notes = enhanced_notes
        existing_record.date = exercise_date
        existing_record.updated_at = datetime.utcnow()
        operation = "updated"
    else:
        new_record = DBExerciseTracking(
            id=record_id,
            user_id=user.id,
            plan_id=planId,
            session_id=session_id,
            exercise_id=exercise_id,
            date=exercise_date,
            notes=enhanced_notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_record)
        operation = "created"

    db.commit()
    return {
        "success": True,
        "message": f"Exercise tracking {operation} successfully",
        "record_id": record_id,
        "operation": operation,
        "exercise_title": exercise_title,
    }

@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Get exercises for a plan."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    records = (
        db.query(DBExerciseTracking)
        .filter(
            DBExerciseTracking.user_id == user.id,
            DBExerciseTracking.plan_id == planId,
        )
        .order_by(DBExerciseTracking.date.desc())
        .all()
    )

    return [
        ExerciseTracking(
            id=rec.id,
            plan_id=rec.plan_id,
            session_id=rec.session_id,
            exercise_id=rec.exercise_id,
            date=rec.date,
            notes=rec.notes or "",
        )
        for rec in records
    ]
