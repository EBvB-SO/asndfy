# app/models/session.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class SessionTracking(BaseModel):
    id: str
    planId: str       # do not default to "unknown_plan"
    weekNumber: int   # must be provided
    dayOfWeek: str    # require a day name, do not default to Monday
    focusName: str    # require the focus (e.g. "Max Boulder Sessions + Density Hangs")
    isCompleted: bool = Field(default=False, alias="is_completed")
    notes: str = ""
    completionDate: Optional[datetime] = Field(None, alias="completion_date")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True

class SessionTrackingUpdateBody(BaseModel):
    isCompleted: bool = Field(..., alias="is_completed")
    notes: str = ""
    completionDate: Optional[datetime] = Field(None, alias="completion_date")

    # Add validators for the update body too
    @validator('notes', pre=True)
    def validate_notes(cls, v):
        if v is None:
            return ""
        return str(v)

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True