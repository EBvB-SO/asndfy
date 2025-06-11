# app/models/daily_note.py
from datetime import date, datetime
from typing   import Optional
from pydantic import BaseModel, Field
from uuid     import UUID

class DailyNoteBase(BaseModel):
    date: date
    content: str

class DailyNoteCreate(DailyNoteBase):
    pass

class DailyNoteUpdate(BaseModel):
    content: str

class DailyNote(DailyNoteBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True