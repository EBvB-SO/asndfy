# api/badges.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
import sys
import os

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the db_access module as "db" so that db.get_badges, db.get_user_badges, etc. are available
import db.db_access as db

from models.badge import Badge
from core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/badges", tags=["Badges"])

@router.get("/", response_model=List[Badge])
def get_all_badges():
    """Get all available badges."""
    badges = db.get_badges()
    return badges


@router.get("/{email}", response_model=List[Badge])
def get_user_badges(email: str, current_user: str = Depends(get_current_user_email)):
    """Get all badges earned by a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        badges = db.get_user_badges(user_id)
        
        return badges

@router.post("/{email}/award/{badge_id}")
def award_badge(email: str, badge_id: int, current_user: str = Depends(get_current_user_email)):
    """Award a badge to a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        result = db.award_badge_to_user(user_id, badge_id)
        
        if not result:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {"success": True, "message": result.message}