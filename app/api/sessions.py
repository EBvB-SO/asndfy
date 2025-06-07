# app/api/sessions.py

import uuid
import logging
import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from db.models import (
    User,
    SessionTracking as DBSessionTracking,
    PlanPhase,
    PlanSession,
)
from models.session import SessionTracking, SessionTrackingUpdate
from core.dependencies import get_current_user_email
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user/{email}/plans/{planId}",
    tags=["Session Tracking"],
)


@router.get("/sessions", response_model=List[SessionTracking])
async def get_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """
    Retrieve all tracking sessions for a given user & plan.
    """
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = (
        db.query(DBSessionTracking)
          .filter(
              DBSessionTracking.user_id == user.id,
              DBSessionTracking.plan_id == planId,
          )
          .order_by(DBSessionTracking.week_number, DBSessionTracking.day_of_week)
          .all()
    )

    return [
        SessionTracking(
            id             = s.id,
            planId         = s.plan_id,
            weekNumber     = s.week_number,
            dayOfWeek      = s.day_of_week,
            focusName      = s.focus_name,
            isCompleted    = s.is_completed,
            notes          = s.notes or "",
            completionDate = s.completion_date.isoformat() if s.completion_date else None
        )
        for s in sessions
    ]


@router.post("/sessions")
async def update_session(
    email: str,
    planId: str,
    update: SessionTrackingUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """
    Update an existing session or create a new one if it doesn't exist.
    """
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sess = (
        db.query(DBSessionTracking)
          .filter(
              DBSessionTracking.id      == update.sessionId,
              DBSessionTracking.user_id == user.id,
              DBSessionTracking.plan_id == planId,
          )
          .first()
    )

    if sess:
        # update existing
        sess.is_completed    = update.isCompleted
        sess.notes           = update.notes
        sess.completion_date = (
            datetime.fromisoformat(update.completionDate)
            if update.completionDate else None
        )
        sess.updated_at      = datetime.utcnow()
    else:
        # create new
        new_sess = DBSessionTracking(
            id             = update.sessionId,
            user_id        = user.id,
            plan_id        = planId,
            week_number    = 1,            # you may choose to infer week/day from payload
            day_of_week    = "Monday",
            focus_name     = "Unknown",
            is_completed   = update.isCompleted,
            notes          = update.notes,
            completion_date= (
                datetime.fromisoformat(update.completionDate)
                if update.completionDate else None
            ),
        )
        db.add(new_sess)

    db.commit()
    return {"success": True, "message": "Session updated successfully"}


@router.post("/initialize")
async def initialize_sessions(
    email: str,
    planId: str,
    current_user: str = Depends(get_current_user_email),
    db: Session   = Depends(get_db),
):
    """
    Bootstrap tracking sessions for each week/day in a plan,
    based on PlanPhase → PlanSession templates.
    """
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    already = (
        db.query(DBSessionTracking)
          .filter(
              DBSessionTracking.user_id == user.id,
              DBSessionTracking.plan_id == planId,
          )
          .count()
    )
    if already > 0:
        return {"success": True, "message": "Sessions already initialized"}

    phases = (
        db.query(PlanPhase)
          .filter(PlanPhase.plan_id == planId)
          .order_by(PlanPhase.phase_order)
          .all()
    )

    created = []
    for phase in phases:
        match = re.search(r"weeks?\s+(\d+)-(\d+)", phase.phase_name.lower())
        if not match:
            continue
        start, end = int(match.group(1)), int(match.group(2)) + 1

        templates = (
            db.query(PlanSession)
              .filter(PlanSession.phase_id == phase.id)
              .order_by(PlanSession.session_order)
              .all()
        )

        for week in range(start, end):
            for tmpl in templates:
                new_s = DBSessionTracking(
                    id           = str(uuid.uuid4()),
                    user_id      = user.id,
                    plan_id      = planId,
                    week_number  = week,
                    day_of_week  = tmpl.day,
                    focus_name   = tmpl.focus,
                    is_completed = False,
                    notes        = "",
                )
                db.add(new_s)
                created.append({
                    "id":           new_s.id,
                    "planId":       planId,
                    "weekNumber":   week,
                    "dayOfWeek":    tmpl.day,
                    "focusName":    tmpl.focus,
                    "isCompleted":  False,
                    "notes":        ""
                })

    db.commit()
    return {
        "success":  True,
        "message":  f"Created {len(created)} sessions",
        "sessions": created
    }
