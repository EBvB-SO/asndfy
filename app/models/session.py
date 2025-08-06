# app/models/session.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class SessionTracking(BaseModel):
    id: str
    planId: str = Field(alias="plan_id")
    weekNumber: int = Field(alias="week_number")
    dayOfWeek: str = Field(alias="day_of_week") 
    focusName: str = Field(alias="focus_name")
    isCompleted: bool = Field(default=False, alias="is_completed")
    notes: str = ""
    completionDate: Optional[datetime] = Field(None, alias="completion_date")
    updatedAt: Optional[datetime] = Field(None, alias="updated_at")

    # Validators to ensure proper data types
    @validator('id', pre=True)
    def validate_id(cls, v):
        if v is None:
            raise ValueError('id cannot be None')
        return str(v).lower()
    
    @validator('planId', pre=True)
    def validate_plan_id(cls, v):
        if v is None:
            raise ValueError('plan_id cannot be None')
        return str(v).lower()
    
    @validator('weekNumber', pre=True)
    def validate_week_number(cls, v):
        if v is None:
            return 1  # Default value
        try:
            return int(v)
        except (ValueError, TypeError):
            return 1
    
    @validator('dayOfWeek', pre=True)
    def validate_day_of_week(cls, v):
        if v is None:
            return "Monday"  # Default value
        return str(v)
    
    @validator('focusName', pre=True)
    def validate_focus_name(cls, v):
        if v is None:
            return "Training Session"  # Default value
        return str(v)

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