# app/api/analytics.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
import re
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

# --------------------------- helpers: sessions ------------------------------

def _extract_session_date(s: DBSessionTracking) -> Optional[date]:
    """Prefer completion_date; else updated_at/created_at -> date(); else None."""
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


# ----------------------- helpers: exercise bucketing ------------------------

_BUCKETS: Dict[str, List[str]] = {
    "finger strength": ["finger", "hangboard", "fingerboard", "max hang", "half crimp", "open hand"],
    "strength": ["strength", "weighted pull", "one arm", "lockoff"],
    "power": ["power", "campus", "dyno"],
    "cap": ["cap ", "anaerobic capacity", "power endurance", "4x4"],
    "aero cap": ["aero cap", "aerobic capacity", "laps", "endurance circuits"],
    "bouldering": ["boulder", "bouldering", "problems"],
    "endurance": ["endurance", "arc", "continuous"],
    "technique": ["technique", "footwork", "drill"],
    "core": ["core", "plank", "leg raise", "hollow"],
}


def _bucket_for(title_or_notes: str) -> str:
    text = (title_or_notes or "").lower()
    for bucket, needles in _BUCKETS.items():
        if any(n in text for n in needles):
            return bucket
    return "other"


# -------------------- helpers: abilities (free-text parsing) ----------------

AXES_6 = [
    "Finger Strength",
    "Power",
    "Power Endurance",
    "Endurance",
    "Core Strength",
    "Flexibility",
]

# map common labels -> canonical keys we expect from questionnaire
KEYS = {
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
    # occasionally present; not part of radar but kept for completeness
    "upper body strength": "upper_body_strength",
    "strength": "strength",
    "mental strength": "mental_strength",
}

PAIR_RE = re.compile(r"\s*([A-Za-z ]+?)\s*:\s*([0-9]+)\s*")


def _parse_attribute_ratings_text(s: str) -> Dict[str, float]:
    """
    Accept a free-text string like:
    "Crimp Strength: 2, Pinch Strength: 2, Pocket Strength: 2, Power: 2, Power Endurance: 4, Endurance: 5, Core Strength: 4, Flexibility: 5"
    or a JSON dict string like:
    {"Crimp Strength": 4, "Power": 5, ...}
    and return a dict of normalized numeric values by canonical key in KEYS.
    """
    result: Dict[str, float] = {}
    if not s:
        return result

    # If it happens to be valid JSON, just parse it straight away
    try:
        parsed = json.loads(s)
        if isinstance(parsed, dict):
            out: Dict[str, float] = {}
            for k, v in parsed.items():
                kk = KEYS.get(k.strip().lower(), k.strip().lower())
                try:
                    out[kk] = float(v)
                except Exception:
                    pass
            return out
    except Exception:
        pass  # fall back to regex parsing

    # Free text pairs: "Label: number"
    for m in PAIR_RE.finditer(s):
        raw_key = m.group(1).strip().lower()
        try:
            val = float(m.group(2))
        except Exception:
            continue
        canon = KEYS.get(raw_key)
        if not canon:
            continue
        result[canon] = val
    return result


def _six_axis_from_user_fields(user: User) -> Dict[str, Dict[str, float]]:
    """
    Build our 6-axis values from either:
    - JSON columns attribute_ratings_initial/current if present, else
    - free-text attribute_ratings on User or user.profile (UserProfile), else
    - individual numeric columns on User (power, endurance, etc.), else zeros.
    Returns:
      {"initial": {...6 keys...}, "current": {...6 keys...}}
    """
    # 1) If JSON columns exist on the User (or attached profile) use them directly
    abilities_initial = getattr(user, "attribute_ratings_initial", None) or {}
    abilities_current = getattr(user, "attribute_ratings_current", None) or {}

    # 2) If empty, try attribute_ratings (free text) on User or on the attached profile
    if not abilities_current:
        raw = getattr(user, "attribute_ratings", None)
        if not raw:
            profile = getattr(user, "profile", None)
            raw = getattr(profile, "attribute_ratings", None) if profile else None

        parsed = _parse_attribute_ratings_text(raw or "")
        if parsed:
            # Finger Strength = explicit 'finger_strength' if present, else average of crimp/pinch/pocket
            fingers: List[float] = []
            if "finger_strength" in parsed:
                fingers.append(parsed["finger_strength"])
            for part in ("crimp", "pinch", "pocket"):
                if part in parsed:
                    fingers.append(parsed[part])
            finger_strength = sum(fingers) / len(fingers) if fingers else 0.0

            out = {
                "Finger Strength": finger_strength,
                "Power": float(parsed.get("power", 0.0)),
                "Power Endurance": float(parsed.get("power_endurance", 0.0)),
                "Endurance": float(parsed.get("endurance", 0.0)),
                "Core Strength": float(parsed.get("core_strength", 0.0)),
                "Flexibility": float(parsed.get("flexibility", 0.0)),
            }
            abilities_current = out
            if not abilities_initial:
                abilities_initial = out

    # 3) Align and return
    def _align6(d: Dict[str, float]) -> Dict[str, float]:
        return {k: float(d.get(k, 0.0)) for k in AXES_6}

    return {
        "initial": _align6(abilities_initial or {}),
        "current": _align6(abilities_current or {}),
    }


# --------------------------------- route ------------------------------------


@router.get("/{email}", summary="Return dashboard data for a user")
async def get_dashboard(
    email: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    if email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure the helper can see attribute_ratings even if profile isn't eagerly loaded
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if profile is not None and not getattr(user, "attribute_ratings", None):
            # only attach if the model actually supports arbitrary attrs or has relationship
            # this is safe: SQLAlchemy models can hold transient attributes
            setattr(user, "profile", profile)
    except Exception:
        # non-fatal; continue without profile
        pass

    today = datetime.utcnow().date()
    start_date = today - timedelta(weeks=8)

    # 1) Session completion by week (last 8 weeks)
    sessions_q = db.query(DBSessionTracking).filter(DBSessionTracking.user_id == user.id).all()
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
                "weekLabel": f"Week {i+1}",
                "completedSessions": completed,
                "completionRate": round(rate, 2),
            }
        )

    # 2) Abilities (6-axis)
    six = _six_axis_from_user_fields(user)
    abilities_initial = six["initial"]
    abilities_current = six["current"]

    # 3) Exercise distribution (simple bucketing over all tracking rows)
    ex_rows = db.query(DBExerciseTracking).filter(DBExerciseTracking.user_id == user.id).all()
    buckets: Dict[str, int] = {}
    for ex in ex_rows:
        ex_type = getattr(ex, "exercise_type", None)
        if not ex_type:
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

    return {
        "sessionCompletion": completion_by_week,
        "abilities": {
            "initial": abilities_initial,
            "current": abilities_current,
        },
        "exerciseDistribution": exercise_distribution,
    }
