# app/api/users.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict
import logging
import json
import re

from app.models.user import UserProfileData
from app.core.database import get_db
from app.core.dependencies import get_current_user_email
from app.models.auth_models import BaseResponse
from sqlalchemy.orm import Session
from app.db.models import (
    User,
    UserProfile,
    PendingSessionUpdate,
    UserAttributeRatingsHistory,  # <-- NEW
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

# -------------------- helpers: parse + normalize ratings --------------------

AXES_6 = [
    "Finger Strength",
    "Power",
    "Power Endurance",
    "Endurance",
    "Core Strength",
    "Flexibility",
]

_KEYS = {
    "crimp strength": "crimp",
    "crimp": "crimp",
    "pinch strength": "pinch",
    "pinch": "pinch",
    "pocket strength": "pocket",
    "pocket": "pocket",
    "finger strength": "finger_strength",  # explicit finger score (if present)

    "power": "power",
    "power endurance": "power_endurance",
    "endurance": "endurance",
    "core strength": "core_strength",
    "flexibility": "flexibility",

    # not part of the 6-axis radar but may appear
    "upper body strength": "upper_body_strength",
    "strength": "strength",
    "mental strength": "mental_strength",
}

_PAIR_RE = re.compile(r"\s*([A-Za-z ]+?)\s*:\s*([0-9]+)\s*")

def _parse_attribute_ratings_text(s: str) -> Dict[str, float]:
    """
    Accepts either:
      - Free text: "Crimp Strength: 4, Power: 5, ..."
      - JSON dict string: {"Crimp Strength": 4, "Power": 5, ...}
    Returns canonical key->float dict.
    """
    if not s:
        return {}

    # JSON dict path
    try:
        parsed = json.loads(s)
        if isinstance(parsed, dict):
            out: Dict[str, float] = {}
            for k, v in parsed.items():
                kk = _KEYS.get(k.strip().lower(), k.strip().lower())
                try:
                    out[kk] = float(v)
                except Exception:
                    pass
            return out
    except Exception:
        pass

    # Free-text path
    out: Dict[str, float] = {}
    for m in _PAIR_RE.finditer(s):
        label = m.group(1).strip().lower()
        try:
            val = float(m.group(2))
        except Exception:
            continue
        canon = _KEYS.get(label)
        if canon:
            out[canon] = val
    return out

def _six_axis_from_parsed(parsed: Dict[str, float]) -> Dict[str, float]:
    """
    Convert canonical parsed dict into the 6-axis payload we store in JSON.
    Finger Strength = explicit 'finger_strength' if present, else avg(crimp, pinch, pocket).
    Missing values become 0.0.
    """
    fingers: List[float] = []
    if "finger_strength" in parsed:
        fingers.append(parsed["finger_strength"])
    for part in ("crimp", "pinch", "pocket"):
        if part in parsed:
            fingers.append(parsed[part])
    finger_strength = sum(fingers) / len(fingers) if fingers else 0.0

    return {
        "Finger Strength": finger_strength,
        "Power":           float(parsed.get("power", 0.0)),
        "Power Endurance": float(parsed.get("power_endurance", 0.0)),
        "Endurance":       float(parsed.get("endurance", 0.0)),
        "Core Strength":   float(parsed.get("core_strength", 0.0)),
        "Flexibility":     float(parsed.get("flexibility", 0.0)),
    }

def _same_six(a: Dict[str, float] | None, b: Dict[str, float] | None) -> bool:
    """Loose equality with rounding so tiny float diffs don't spam history."""
    a = a or {}
    b = b or {}
    for k in AXES_6:
        if round(float(a.get(k, 0.0)), 3) != round(float(b.get(k, 0.0)), 3):
            return False
    return True

# ------------------------------ routes --------------------------------------

@router.get("/profile/{email}")
def get_profile(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    logger.info(f"Profile request - URL email: '{email}', Token email: '{current_user}'")
    if email.lower() != current_user.lower():
        logger.error(f"Email mismatch: URL='{email}', Token='{current_user}'")
        raise HTTPException(status_code=403, detail="Unauthorized to access this profile")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        return UserProfileData(name=user.name)
    
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
    """Update user profile (and keep ability ratings JSON + history in sync)."""
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized to update this profile")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    
    data = profile_data.dict(exclude_unset=True)

    # Normalize training facilities (accept list or CSV; de-dupe + sorted)
    if 'training_facilities' in data and data['training_facilities'] is not None:
        tf = data['training_facilities']
        if isinstance(tf, list):
            names = [str(x).strip() for x in tf if str(x).strip()]
        else:
            names = [p.strip() for p in str(tf).split(',') if p.strip()]
        data['training_facilities'] = ", ".join(sorted(set(names)))

    # Update User.name if provided
    if 'name' in data:
        user.name = data.pop('name')

    # Track whether attribute_ratings changed and compute 6-axis if present
    six_from_update: Dict[str, float] | None = None
    if 'attribute_ratings' in data:
        # keep legacy text field in the profile
        incoming_text = data['attribute_ratings'] or ""
        parsed = _parse_attribute_ratings_text(incoming_text)
        six_from_update = _six_axis_from_parsed(parsed)

    # Apply remaining fields to UserProfile
    for field, value in data.items():
        setattr(profile, field, value)

    # If ratings provided, update JSON columns + history
    if six_from_update is not None:
        current_before = user.attribute_ratings_current or {}
        # Seed "initial" the very first time
        if not user.attribute_ratings_initial:
            user.attribute_ratings_initial = six_from_update

        user.attribute_ratings_current = six_from_update

        # Only add a history row if different from the previous "current"
        if not _same_six(current_before, six_from_update):
            db.add(UserAttributeRatingsHistory(
                user_id=user.id,
                ratings=six_from_update,
                source="profile_update"
            ))

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
    if email.lower() != current_user.lower():
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
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized to access these stats")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "total_sessions": 0,
        "completed_sessions": 0,
        "active_projects": 0,
        "completed_projects": 0
    }

@router.delete("/profile/{email}", response_model=BaseResponse)
async def delete_profile(email: str, current_user: str = Depends(get_current_user_email)):
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # assuming db.delete_user exists in your db_access
        from app.db import db_access as dbx
        dbx.delete_user(email)
        return BaseResponse(success=True, message="User deleted.", data=None)
    except Exception as e:
        logger.error(f"Error deleting user {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

# Legacy compatibility
@router.get("/user_profile/{email}")
async def get_profile_legacy(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    return get_profile(email, current_user, db)

@router.post("/update_user_profile/{email}")
async def update_profile_legacy(
    email: str, 
    profile_data: UserProfileData,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    return update_profile(email, profile_data, current_user, db)
