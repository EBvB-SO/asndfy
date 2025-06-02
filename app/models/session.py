# models/session.py
from pydantic import BaseModel
from typing import Optional

class SessionTracking(BaseModel):
    id: str
    planId: str
    weekNumber: int
    dayOfWeek: str
    focusName: str
    isCompleted: bool = False
    notes: str = ""
    completionDate: Optional[str] = None

class SessionTrackingUpdate(BaseModel):
    sessionId: str
    isCompleted: bool
    notes: str
    completionDate: Optional[str] = None