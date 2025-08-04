# app/models/session.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SessionTracking(BaseModel):
    id: str
    planId: str = Field(..., alias="plan_id")           # Allow both planId and plan_id
    weekNumber: int = Field(..., alias="week_number")   # Allow both weekNumber and week_number
    dayOfWeek: str = Field(..., alias="day_of_week")    # Allow both dayOfWeek and day_of_week
    focusName: str = Field(..., alias="focus_name")     # Allow both focusName and focus_name
    isCompleted: bool = Field(default=False, alias="is_completed")
    notes: str = ""
    completionDate: Optional[datetime] = Field(None, alias="completion_date")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    class Config:
        allow_population_by_field_name = True  # Allow both field names and aliases
        allow_population_by_alias = True

class SessionTrackingUpdateBody(BaseModel):
    isCompleted: bool = Field(..., alias="is_completed")
    notes: str
    completionDate: Optional[datetime] = Field(None, alias="completion_date")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True