# scripts/backfill_attribute_ratings.py
import json
import re
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.db.models import User, UserProfile, UserAttributeRatingsHistory

_KEYS = {
    "crimp strength": "crimp", "crimp": "crimp",
    "pinch strength": "pinch", "pinch": "pinch",
    "pocket strength": "pocket", "pocket": "pocket",
    "finger strength": "finger_strength",
    "power": "power",
    "power endurance": "power_endurance",
    "endurance": "endurance",
    "core strength": "core_strength",
    "flexibility": "flexibility",
}
_PAIR_RE = re.compile(r"\s*([A-Za-z ]+?)\s*:\s*([0-9]+)\s*")
AXES_6 = ["Finger Strength","Power","Power Endurance","Endurance","Core Strength","Flexibility"]

def parse_text(s: str):
    if not s: return {}
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return { _KEYS.get(k.strip().lower(), k.strip().lower()): float(v) for k,v in obj.items() }
    except Exception:
        pass
    out = {}
    for m in _PAIR_RE.finditer(s):
        k = _KEYS.get(m.group(1).strip().lower())
        if not k: continue
        try: out[k] = float(m.group(2))
        except: pass
    return out

def to_six(parsed: dict):
    fingers = []
    if "finger_strength" in parsed: fingers.append(parsed["finger_strength"])
    for k in ("crimp","pinch","pocket"):
        if k in parsed: fingers.append(parsed[k])
    finger = sum(fingers)/len(fingers) if fingers else 0.0
    return {
        "Finger Strength": finger,
        "Power": float(parsed.get("power",0.0)),
        "Power Endurance": float(parsed.get("power_endurance",0.0)),
        "Endurance": float(parsed.get("endurance",0.0)),
        "Core Strength": float(parsed.get("core_strength",0.0)),
        "Flexibility": float(parsed.get("flexibility",0.0)),
    }

def run():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for u in users:
            prof = db.query(UserProfile).filter(UserProfile.user_id==u.id).first()
            if not prof or not prof.attribute_ratings:
                continue
            six = to_six(parse_text(prof.attribute_ratings))
            if not six: 
                continue
            changed = False
            if not u.attribute_ratings_initial:
                u.attribute_ratings_initial = six
                changed = True
            if not u.attribute_ratings_current:
                u.attribute_ratings_current = six
                changed = True
            if changed:
                db.add(UserAttributeRatingsHistory(user_id=u.id, ratings=six, source="backfill"))
        db.commit()
        print("Backfill complete.")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run()
