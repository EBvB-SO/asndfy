# app/api/exercise_tracking.py

import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.exercise import (
    ExerciseTracking,          # Pydantic model for output
    ExerciseTrackingCreate,    # Pydantic model for create payload
    ExerciseTrackingUpdate     # Pydantic model for update payload, if you use it
)
from app.core.dependencies import get_current_user_email
from app.core.database import get_db
from app.db.models import User, ExerciseTracking as DBExerciseTracking

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}",
    tags=["Exercise Tracking"],
)


@router.get("/exercises", response_model=List[ExerciseTracking])
async def get_exercises(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """Fetch all exercise‐tracking records for a given plan."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()
    records = (
        db.query(DBExerciseTracking)
          .filter(
              DBExerciseTracking.user_id   == user.id,
+             DBExerciseTracking.plan_id   == planId,
          )
          .order_by(DBExerciseTracking.date.desc())
          .all()
    )

    return [
        ExerciseTracking(
            id         = rec.id,
            planId     = rec.plan_id,
            sessionId  = rec.session_id,
            exerciseId = rec.exercise_id,
            date       = rec.date.isoformat(),
            notes      = rec.notes or ""
        )
        for rec in records
    ]


@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """Create a new exercise record or update an existing one."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    planId = planId.lower()
    rec_id = (tracking.id or str(uuid.uuid4())).lower()
    existing = db.query(DBExerciseTracking).filter(
        DBExerciseTracking.id      == rec_id,
        DBExerciseTracking.user_id == user.id
    ).first()

    if existing:
        # update
        existing.notes      = tracking.notes
        existing.date       = datetime.fromisoformat(tracking.date)
        existing.updated_at = datetime.utcnow()
    else:
        # create
        new_record = DBExerciseTracking(
            id          = rec_id,
            user_id     = user.id,
            plan_id     = planId,
            session_id  = tracking.sessionId,
            exercise_id = tracking.exerciseId,
            date        = datetime.fromisoformat(tracking.date),
            notes       = tracking.notes
        )
        db.add(new_record)

    db.commit()
    return {"success": True, "message": "Exercise tracking saved"}


@router.get("/exercises/{exercise_id}/history")
async def get_exercise_history(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """Get the full history of a single exercise across all sessions."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId      = planId.lower()
    exercise_id = exercise_id.lower()

    history = (
        db.query(DBExerciseTracking)
          .filter(
              DBExerciseTracking.user_id     == user.id,
              DBExerciseTracking.plan_id     == planId,
              DBExerciseTracking.exercise_id == exercise_id,
          )
          .order_by(DBExerciseTracking.date.desc())
          .all()
    )

    return {
        "history": [
            {
                "id":        rec.id,
                "date":      rec.date.isoformat(),
                "notes":     rec.notes or "",
                "updatedAt": rec.updated_at.isoformat() if rec.updated_at else None
            }
            for rec in history
        ]
    }


@router.delete("/exercises/{exercise_id}")
async def delete_exercise(
    email: str,
    planId: str,
    exercise_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """Delete a single exercise tracking record."""
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId     = planId.lower()
    exercise_id = exercise_id.lower()
    record = (
        db.query(DBExerciseTracking)
          .filter(
              DBExerciseTracking.id      == exercise_id,
              DBExerciseTracking.user_id == user.id,
              DBExerciseTracking.plan_id == planId,
          )
          .first()
    )
    if not record:
        raise HTTPException(404, "Exercise tracking not found")

    db.delete(record)
    db.commit()
    return {"success": True, "message": "Exercise tracking deleted"}
