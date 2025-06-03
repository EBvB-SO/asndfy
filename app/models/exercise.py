# app/models/exercise.py
from pydantic import BaseModel
from typing import Optional

class ExerciseTrackingBase(BaseModel):
    sessionId: str
    exerciseId: str
    date: str
    notes: str = ""

class ExerciseTrackingCreate(ExerciseTrackingBase):
    id: Optional[str] = None

class ExerciseTrackingUpdate(BaseModel):
    notes: str = ""
    date: Optional[str] = None

class ExerciseTracking(ExerciseTrackingBase):
    id: str
    planId: str