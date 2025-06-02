# models/daily_note.py
from pydantic import BaseModel

class DailyNoteBase(BaseModel):
    date: str  # ISO format date
    content: str

class DailyNoteCreate(DailyNoteBase):
    pass

class DailyNoteUpdate(BaseModel):
    content: str

class DailyNote(DailyNoteBase):
    id: str
    created_at: str
    updated_at: str