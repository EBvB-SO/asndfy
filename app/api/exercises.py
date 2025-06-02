# backend/app/api/exercises.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from core.database import get_db
from sqlalchemy.orm import Session
from db.models import Exercise, ExerciseTarget

router = APIRouter(prefix="/exercises", tags=["Exercises"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_exercises(db: Session = Depends(get_db)):
    """Get all exercises with their details"""
    exercises = db.query(Exercise).all()
    
    result = []
    for exercise in exercises:
        exercise_dict = {
            "id": exercise.id,
            "name": exercise.name,
            "type": exercise.type,
            "description": exercise.description,
            "priority": exercise.priority,
            "time_required": exercise.time_required,
            "required_facilities": exercise.required_facilities,
            "best_for": [target.target for target in exercise.targets]
        }
        result.append(exercise_dict)
    
    return result