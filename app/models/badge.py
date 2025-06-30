# models/badge.py
from pydantic import BaseModel
from typing import Optional

class BadgeBase(BaseModel):
    name: str
    description: str
    icon_name: str
    how_to_earn: str
    category_name: str  # 'Climbing Styles', 'Training Plans', etc.

class Badge(BadgeBase):
    id: int
    category_id: int
    earned_at: Optional[str] = None

    class Config:
        orm_mode = True