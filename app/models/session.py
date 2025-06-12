# models/session.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

def _to_snake(s: str) -> str:
    # helper to turn CamelCase → snake_case
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

class SessionTracking(BaseModel):
    id: str
    planId: str
    weekNumber: int
    dayOfWeek: str
    focusName: str
    isCompleted: bool = False
    notes: str = ""
    completionDate: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        allow_population_by_alias = True
        alias_generator = _to_snake

class SessionTrackingUpdateBody(BaseModel):
    isCompleted: bool       = Field(..., alias="is_completed")
    notes:        str
    completionDate: Optional[datetime] = Field(None, alias="completion_date")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True
        alias_generator = _to_snake

