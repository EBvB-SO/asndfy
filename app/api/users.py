# api/users.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
import logging

from app.models.user import UserProfileData
from app.core.database import get_db
from app.core.dependencies import get_current_user_email
from app.models.auth_models import BaseResponse
from sqlalchemy.orm import Session
from app.db.models import User, UserProfile, PendingSessionUpdate
from app.db import db_access as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile/{email}")
def get_profile(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    logger.info(f"Profile request - URL email: '{email}', Token email: '{current_user}'")
    # Normalize both to lowercase
    if email.lower() != current_user.lower():
        logger.error(f"Email mismatch: URL='{email}', Token='{current_user}'")
        raise HTTPException(status_code=403, detail="Unauthorized to access this profile")
    """Get user profile by email."""
    # Verify the user is requesting their own profile
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to access this profile")
    
    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get profile data
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    
    if not profile:
        # No profile row yet, but still return their name from User
        return UserProfileData(name=user.name)
    
    # Convert database fields to API model - handle None values by converting to empty strings
    return UserProfileData(
        name=user.name,
        current_climbing_grade=profile.current_climbing_grade or "",
        max_boulder_grade=profile.max_boulder_grade or "",
        goal=profile.goal or "",
        training_experience=profile.training_experience or "",
        perceived_strengths=profile.perceived_strengths or "",
        perceived_weaknesses=profile.perceived_weaknesses or "",
        attribute_ratings=profile.attribute_ratings or "",
        weeks_to_train=profile.weeks_to_train or "",
        sessions_per_week=profile.sessions_per_week or "",
        time_per_session=profile.time_per_session or "",
        training_facilities=profile.training_facilities or "",
        injury_history=profile.injury_history or "",
        general_fitness=profile.general_fitness or "",
        height=profile.height or "",
        weight=profile.weight or "",
        age=profile.age or "",
        preferred_climbing_style=profile.preferred_climbing_style or "",
        indoor_vs_outdoor=profile.indoor_vs_outdoor or "",
        onsight_flash_level=profile.onsight_flash_level or "",
        redpointing_experience=profile.redpointing_experience or "",
        sleep_recovery=profile.sleep_recovery or "",
        work_life_balance=profile.work_life_balance or "",
        fear_factors=profile.fear_factors or "",
        mindfulness_practices=profile.mindfulness_practices or "",
        motivation_level=profile.motivation_level or "",
        access_to_coaches=profile.access_to_coaches or "",
        time_for_cross_training=profile.time_for_cross_training or "",
        additional_notes=profile.additional_notes or ""
    )

@router.put("/profile/{email}")
def update_profile(
    email: str, 
    profile_data: UserProfileData,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    # Verify the user is updating their own profile
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to update this profile")
    
    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    
    # Pull out exactly what the client sent
    data = profile_data.dict(exclude_unset=True)

    # If they sent a name, save it to the User record (not UserProfile)
    if 'name' in data:
        user.name = data.pop('name')

    # Now update the remaining attributes on the UserProfile
    for field, value in data.items():
        setattr(profile, field, value)
    
    try:
        db.commit()
        return {"success": True, "message": "Profile updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=400, detail="Failed to update profile")

@router.get("/{email}/pending_updates")
async def get_pending_updates(
    email: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all pending updates for a user"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = db.query(PendingSessionUpdate).filter(
        PendingSessionUpdate.user_id == user.id,
        PendingSessionUpdate.is_synced == False
    ).all()
    
    return {
        "success": True,
        "updates": [
            {
                "id": update.id,
                "planId": update.plan_id,
                "sessionId": update.session_id,
                "isCompleted": update.is_completed,
                "notes": update.notes or "",
                "timestamp": update.timestamp.isoformat()
            }
            for update in updates
        ]
    }

@router.post("/{email}/sync_pending_updates")
async def sync_pending_updates(
    email: str,
    update_ids: List[int],
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Mark pending updates as synced"""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mark each update as synced
    synced_count = 0
    for update_id in update_ids:
        update = db.query(PendingSessionUpdate).filter(
            PendingSessionUpdate.id == update_id,
            PendingSessionUpdate.user_id == user.id
        ).first()
        
        if update:
            update.is_synced = True
            synced_count += 1
    
    try:
        db.commit()
        return {
            "success": True,
            "message": f"Marked {synced_count} updates as synced"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing updates: {e}")
        raise HTTPException(status_code=400, detail="Failed to sync updates")

@router.get("/stats/{email}")
def get_user_stats(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get user statistics."""
    # Verify the user is requesting their own stats
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to access these stats")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # TODO: Implement actual stats logic using SQLAlchemy ORM
    # For now, return a placeholder
    return {
        "total_sessions": 0,
        "completed_sessions": 0,
        "active_projects": 0,
        "completed_projects": 0
    }

@router.delete("/profile/{email}", response_model=BaseResponse)
async def delete_profile(email: str, current_user: str = Depends(get_current_user_email)):
    # Authorize: only allow the user to delete their own profile
    if email != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        db.delete_user(email)    # implement this in db_access
        return BaseResponse(success=True, message="User deleted.", data=None)
    except Exception as e:
        # Log the error and return a 500 if something goes wrong
        logger.error(f"Error deleting user {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

# Add backward compatibility routes if needed
@router.get("/user_profile/{email}")
async def get_profile_legacy(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Legacy route for backward compatibility"""
    return get_profile(email, current_user, db)

@router.post("/update_user_profile/{email}")
async def update_profile_legacy(
    email: str, 
    profile_data: UserProfileData,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Legacy route for backward compatibility"""
    return update_profile(email, profile_data, current_user, db)