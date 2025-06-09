# models/session.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SessionTracking(BaseModel):
    id: str
    planId: str
    weekNumber: int
    dayOfWeek: str
    focusName: str
    isCompleted: bool = False
    notes: str = ""
    completionDate: Optional[datetime] = None

class SessionTrackingUpdateBody(BaseModel):
    isCompleted:  bool
    notes:        str
    completionDate: Optional[datetime]
