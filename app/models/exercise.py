# app/models/exercise.py
from __future__ import annotations

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
    session_id:  Optional[str]     = None
    exercise_id: Optional[str]     = None
    date:        Optional[date]    = None
    notes:       Optional[str]     = None

    model_config = {
        "from_attributes": True,
    }

class ExerciseTracking(ExerciseTrackingBase):
    id:      str
    plan_id: str


class ExerciseEntryBase(BaseModel):
    type: str
    duration_minutes: int

class ExerciseEntryCreate(ExerciseEntryBase):
    pass

class ExerciseEntryUpdate(BaseModel):
    """
        Data required to update an existing exercise entry.

        By default only the fields provided by the client will be updated.  To
        support editing the date of an entry we include an optional
        ``timestamp`` field.  If the caller omits ``timestamp`` then the
        original timestamp on the entry is retained.  Without this field
        the backend cannot move an exercise to a different date when the
        user edits the entry via the mobile app.
    """
    type: Optional[str] = None
    duration_minutes: Optional[int] = None
    # Optional new timestamp for the entry.  When supplied the
    # ``update_exercise`` function in ``db_access`` will replace the
    # existing timestamp with this value.
    timestamp: Optional[datetime] = None

class ExerciseEntry(ExerciseEntryBase):
    id: int
    timestamp: datetime
