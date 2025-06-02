# api/users.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

import db.db_access as db

from models.user import UserProfileData
from core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile/{email}")
def get_profile(email: str, current_user: str = Depends(get_current_user_email)):
    """Get user profile by email."""
    # Verify the user is requesting their own profile
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to access this profile")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Get profile data
        profile = db.get_user_profile(user_id)
        
        if not profile:
            # Return empty profile if none exists
            return UserProfileData()
        
        # Convert database fields to API model
        return UserProfileData(**profile)

@router.put("/profile/{email}")
def update_profile(
    email: str, 
    profile_data: UserProfileData,
    current_user: str = Depends(get_current_user_email)
):
    """Update user profile."""
    # Verify the user is updating their own profile
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to update this profile")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Update the profile
        result = db.update_user_profile(user_id, profile_data.dict())
        
        if not result:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {"success": True, "message": "Profile updated successfully"}

@router.get("/stats/{email}")
def get_user_stats(email: str, current_user: str = Depends(get_current_user_email)):
    """Get user statistics."""
    # Verify the user is requesting their own stats
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized to access these stats")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Get statistics
        stats = db.get_user_stats(user_id)
        
        return stats