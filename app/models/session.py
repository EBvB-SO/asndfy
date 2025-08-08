# app/models/session.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class SessionTracking(BaseModel):
    id: str
    planId: Optional[str] = Field(None, alias="plan_id")
    weekNumber: Optional[int] = Field(None, alias="week_number")
    dayOfWeek: Optional[str] = Field(None, alias="day_of_week") 
    focusName: Optional[str] = Field(None, alias="focus_name")
    isCompleted: bool = Field(default=False, alias="is_completed")
    notes: str = ""
    completionDate: Optional[datetime] = Field(None, alias="completion_date")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    # Make fields optional with defaults for validation
    @validator('planId', pre=True, always=True)
    def set_plan_id(cls, v):
        return v or "unknown_plan"
    
    @validator('weekNumber', pre=True, always=True)
    def set_week_number(cls, v):
        return v if v is not None else 1
    
    @validator('dayOfWeek', pre=True, always=True)
    def set_day_of_week(cls, v):
        return v or "Monday"
    
    @validator('focusName', pre=True, always=True)
    def set_focus_name(cls, v):
        return v or "Training Session"

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