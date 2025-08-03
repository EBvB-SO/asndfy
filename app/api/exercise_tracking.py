# app/api/exercise_tracking.py

import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.exercise import (
    ExerciseTracking,          
    ExerciseTrackingCreate,    
    ExerciseTrackingUpdate     
)
from app.core.dependencies import get_current_user_email
from app.core.database import get_db
from app.db.models import User, ExerciseTracking as DBExerciseTracking, TrainingPlan

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}",
    tags=["Exercise Tracking"],
)

@router.post("/exercises")
async def add_or_update_exercise(
    email: str,
    planId: str,
    tracking: ExerciseTrackingCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    planId = planId.lower()

    try:
        # CHECK IF PLAN EXISTS - if not, create a minimal one
        existing_plan = db.query(TrainingPlan).filter(
            TrainingPlan.id == planId,
            TrainingPlan.user_id == user.id
        ).first()
        
        if not existing_plan:
            logger.warning(f"Plan {planId} not found, creating minimal plan for exercise tracking")
            # Create a minimal plan to satisfy foreign key constraint
            minimal_plan = TrainingPlan(
                id=planId,
                user_id=user.id,
                route_name="Unknown Route",
                grade="Unknown Grade",
                route_overview="Auto-created for exercise tracking",
                training_overview="This plan was auto-created to allow exercise tracking."
            )
            db.add(minimal_plan)
            db.flush()  # Ensure the plan is created before continuing

        rec_id = (tracking.id or str(uuid.uuid4())).lower()
        existing = db.query(DBExerciseTracking).filter(
            DBExerciseTracking.id      == rec_id,
            DBExerciseTracking.user_id == user.id
        ).first()

        if existing:
            existing.notes      = tracking.notes
            existing.date       = tracking.date
            existing.updated_at = datetime.utcnow()
        else:
            new_record = DBExerciseTracking(
                id          = rec_id,
                user_id     = user.id,
                plan_id     = planId,
                session_id  = tracking.session_id,
                exercise_id = tracking.exercise_id,
                date        = tracking.date,
                notes       = tracking.notes
            )
            db.add(new_record)

        db.commit()
        return {"success": True, "message": "Exercise tracking saved"}

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed saving exercise for user %s", email)
        raise HTTPException(
            status_code=500,
            detail="Could not save exercise, please try again later."
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
              DBExerciseTracking.plan_id   == planId,
          )
          .order_by(DBExerciseTracking.date.desc())
          .all()
    )

    return [
        ExerciseTracking(
            id          = rec.id,
            plan_id     = rec.plan_id,
            session_id  = rec.session_id,
            exercise_id = rec.exercise_id,
            date        = rec.date,
            notes       = rec.notes or ""
        )
        for rec in records
    ]

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
            "id":         rec.id,
            "date":       rec.date.isoformat(),
            "notes":      rec.notes or "",
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None
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
    if email != current_user:
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    try:
        record = (
            db.query(DBExerciseTracking)
              .filter(
                  DBExerciseTracking.id      == exercise_id.lower(),
                  DBExerciseTracking.user_id == user.id,
                  DBExerciseTracking.plan_id == planId.lower(),
              )
              .first()
        )
        if not record:
            raise HTTPException(404, "Exercise tracking not found")

        db.delete(record)
        db.commit()
        return {"success": True, "message": "Exercise tracking deleted"}

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed deleting exercise %s for user %s", exercise_id, email)
        raise HTTPException(
            status_code=500,
            detail="Could not delete exercise, please try again later."
        )

