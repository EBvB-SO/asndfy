# app/api/analytics.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
import json

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_email
from app.db.models import (
    User,
    UserProfile,
    SessionTracking as DBSessionTracking,
    ExerciseTracking as DBExerciseTracking,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# ---------------------------- helpers --------------------------------- #

def _extract_session_date(s: DBSessionTracking) -> date | None:
    """
    Prefer completion_date; else updated_at/created_at -> date(); else None.
    Handles both datetime and date objects defensively.
    """
    try:
        if getattr(s, "completion_date", None):
            cd = s.completion_date
            return cd.date() if hasattr(cd, "date") else cd
        if getattr(s, "updated_at", None):
            return s.updated_at.date()
        if getattr(s, "created_at", None):
            return s.created_at.date()
    except Exception:
        pass
    return None


# If you do not persist an exercise "type", map from title/notes keywords.
_BUCKETS: Dict[str, List[str]] = {
    "finger strength": ["finger", "hangboard", "fingerboard", "max hang", "half crimp", "open hand"],
    "strength":        ["strength", "weighted pull", "one arm", "lockoff"],
    "power":           ["power", "campus", "dyno"],
    "cap":             ["cap ", "anaerobic capacity", "power endurance", "4x4"],
    "aero cap":        ["aero cap", "aerobic capacity", "laps", "endurance circuits"],
    "bouldering":      ["boulder", "bouldering", "problems"],
    "endurance":       ["endurance", "arc", "continuous"],
    "technique":       ["technique", "footwork", "drill"],
    "core":            ["core", "plank", "leg raise", "hollow"],
}

def _bucket_for(title_or_notes: str) -> str:
    text = (title_or_notes or "").lower()
    for bucket, needles in _BUCKETS.items():
        if any(n in text for n in needles):
            return bucket
    return "other"


# ----------------------------- route ---------------------------------- #

@router.get("/{email}", summary="Return dashboard data for a user")
async def get_dashboard(
    email: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    # ---- auth ---------------------------------------------------------- #
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized")

    user: User | None = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ---- 1) Session completion (last 8 weeks) ------------------------- #
    today = datetime.utcnow().date()
    start_date = today - timedelta(weeks=8)

    sessions_q: List[DBSessionTracking] = (
        db.query(DBSessionTracking)
        .filter(DBSessionTracking.user_id == user.id)
        .all()
    )

    sessions_window: List[Tuple[DBSessionTracking, date]] = []
    for s in sessions_q:
        d = _extract_session_date(s)
        if d and start_date <= d <= today:
            sessions_window.append((s, d))

    completion_by_week: List[Dict[str, float | int | str]] = []
    for i in range(8):
        wk_start = start_date + timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        wk_sessions = [s for (s, d) in sessions_window if wk_start <= d <= wk_end]

        total = len(wk_sessions)
        completed = sum(1 for (s, _) in wk_sessions if getattr(s, "is_completed", False))
        rate = (completed / total * 100.0) if total else 0.0

        completion_by_week.append(
            {
                "weekLabel": f"Week {i + 1}",
                "completedSessions": completed,
                "completionRate": round(rate, 2),
            }
        )

    # ---- 2) Abilities (6-axis radar) ---------------------------------- #
    ORDERED_ABILITY_LABELS = [
        "Finger Strength",
        "Power",
        "Power Endurance",
        "Endurance",
        "Core Strength",
        "Flexibility",
    ]

    def _num(v) -> float | None:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except Exception:
                return None
        return None

    # Pull questionnaire from UserProfile.attribute_ratings (JSON string)
    profile: UserProfile | None = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    current_from_profile: Dict[str, float] = {}

    if profile and profile.attribute_ratings:
        try:
            raw = json.loads(profile.attribute_ratings)  # keys from your questionnaire
        except Exception:
            raw = {}

        # Components for finger strength
        crimp  = _num(raw.get("crimp_strength"))   or 0.0
        pinch  = _num(raw.get("pinch_strength"))   or 0.0
        pocket = _num(raw.get("pocket_strength"))  or 0.0
        denom = max(1, sum(x > 0 for x in (crimp, pinch, pocket)))
        finger_strength = (crimp + pinch + pocket) / denom

        current_from_profile = {
            "Finger Strength":  finger_strength,
            "Power":            _num(raw.get("power"))            or 0.0,
            "Power Endurance":  _num(raw.get("power_endurance"))  or 0.0,
            "Endurance":        _num(raw.get("endurance"))        or 0.0,
            "Core Strength":    _num(raw.get("core_strength"))    or 0.0,
            "Flexibility":      _num(raw.get("flexibility"))      or 0.0,
        }

    # Prefer first-class JSON columns on User if you added them; otherwise use profile values
    abilities_initial: Dict[str, float] = getattr(user, "attribute_ratings_initial", None) or {}
    abilities_current: Dict[str, float] = getattr(user, "attribute_ratings_current", None) or current_from_profile

    # If still empty, return zeros (no hard-coded demo values)
    if not abilities_current:
        abilities_current = {k: 0.0 for k in ORDERED_ABILITY_LABELS}
    if not abilities_initial:
        abilities_initial = abilities_current  # until you snapshot an "initial" baseline

    # Ensure exact order and float values
    abilities_initial = {k: float(abilities_initial.get(k, 0.0)) for k in ORDERED_ABILITY_LABELS}
    abilities_current = {k: float(abilities_current.get(k, 0.0)) for k in ORDERED_ABILITY_LABELS}

    # ---- 3) Exercise distribution ------------------------------------- #
    ex_rows: List[DBExerciseTracking] = (
        db.query(DBExerciseTracking)
        .filter(DBExerciseTracking.user_id == user.id)
        .all()
    )

    buckets: Dict[str, int] = {}
    for ex in ex_rows:
        ex_type = getattr(ex, "exercise_type", None)
        if not ex_type:
            # derive from title/notes if no explicit type field exists
            text = ""
            for attr in ("exercise_title", "title", "notes"):
                val = getattr(ex, attr, None)
                if val:
                    text = str(val)
                    break
            ex_type = _bucket_for(text)
        buckets[ex_type] = buckets.get(ex_type, 0) + 1

    total_sessions = sum(buckets.values())
    exercise_distribution = [
        {
            "type": k,
            "count": v,
            "percentage": round((v / total_sessions * 100.0), 2) if total_sessions else 0.0,
        }
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])
    ]

    # ---- response ------------------------------------------------------ #
    return {
        "sessionCompletion": completion_by_week,
        "abilities": {"initial": abilities_initial, "current": abilities_current},
        "exerciseDistribution": exercise_distribution,
    }
