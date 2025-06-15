from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class ExerciseTrackingBase(BaseModel):
    session_id: str
    exercise_id: str
    date: date
    notes: str = ""

    class Config:
        orm_mode = True

class ExerciseTrackingCreate(ExerciseTrackingBase):
    id: Optional[str] = None

class ExerciseTrackingUpdate(BaseModel):
    session_id:   Optional[str] = None
    exercise_id:  Optional[str] = None
    date: Optional[datetime.date] = None
    notes:        Optional[str]   = None

    class Config:
        orm_mode = True

class ExerciseTracking(ExerciseTrackingBase):
    id:      str
    plan_id: str


class ExerciseEntryBase(BaseModel):
    user_id: int
    type: str
    duration_minutes: int

class ExerciseEntryCreate(ExerciseEntryBase):
    pass

class ExerciseEntryUpdate(BaseModel):
    type: Optional[str]
    duration_minutes: Optional[int]

class ExerciseEntry(ExerciseEntryBase):
    id: int
    timestamp: datetime
