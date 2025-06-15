# Fixed app/api/badges.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, Badge, UserBadge
from app.core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/badges", tags=["Badges"])

@router.get("/", response_model=List[Badge])
def get_all_badges(
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Get all available badges."""
    badges = db.query(Badge).all()
    return badges


@router.get("/{email}", response_model=List[Badge])
def get_user_badges(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all badges earned by a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Use SQLAlchemy ORM query instead of cursor
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get badges through the relationship or with a join
    user_badges = (
        db.query(Badge)
        .join(UserBadge)
        .filter(UserBadge.user_id == user.id)
        .all()
    )
    
    return user_badges


@router.post("/{email}/award/{badge_id}")
def award_badge(
    email: str, 
    badge_id: int, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Award a badge to a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Use SQLAlchemy ORM query
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if badge exists
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    # Check if user already has this badge
    existing = (
        db.query(UserBadge)
        .filter(UserBadge.user_id == user.id, UserBadge.badge_id == badge_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already has this badge")
    
    # Award the badge
    user_badge = UserBadge(user_id=user.id, badge_id=badge_id)
    db.add(user_badge)
    
    try:
        db.commit()
        return {"success": True, "message": "Badge awarded successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error awarding badge: {e}")
        raise HTTPException(status_code=400, detail="Failed to award badge")
