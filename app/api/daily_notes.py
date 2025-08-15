# Fixed app/api/daily_notes.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, date
import logging
import uuid

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, DailyNote as DBDailyNote
from app.models.daily_note import DailyNoteCreate, DailyNoteUpdate, DailyNote
from app.core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/daily_notes", tags=["Daily Notes"])


@router.get("/{email}", response_model=List[DailyNote])
def get_daily_notes(
    email: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Get daily notes for a user, optionally filtered by date range."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user using SQLAlchemy ORM
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(DBDailyNote).filter(DBDailyNote.user_id == user.id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(DBDailyNote.date >= start_date)
    if end_date:
        query = query.filter(DBDailyNote.date <= end_date)
    
    # Execute query and return results
    notes = query.order_by(DBDailyNote.date).all()
    return notes


@router.post("/{email}", response_model=DailyNote)
def create_daily_note(
    email: str,
    note: DailyNoteCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Create a new daily note."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user using SQLAlchemy ORM
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new note
    new_note = DBDailyNote(
        id=str(uuid.uuid4()),
        user_id=user.id,
        date=note.date,
        content=note.content
    )
    db.add(new_note)
    
    try:
        db.commit()
        db.refresh(new_note)
        return new_note
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating daily note: {e}")
        raise HTTPException(status_code=400, detail="Failed to create daily note")


@router.put("/{email}/{note_id}")
def update_daily_note(
    email: str,
    note_id: str,
    update: DailyNoteUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """Update an existing daily note."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get and verify ownership of the note
    note = (
        db.query(DBDailyNote)
        .filter(DBDailyNote.id == note_id, DBDailyNote.user_id == user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Daily note not found")

    # Update the note
    note.content = update.content
    note.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"success": True, "message": "Daily note updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating daily note: {e}")
        raise HTTPException(status_code=400, detail="Failed to update daily note")


@router.delete("/{email}/{note_id}")
def delete_daily_note(
    email: str,
    note_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete a daily note for the authenticated user.

    Both the path email and the email extracted from the JWT are normalised
    to lower‑case before comparison.  The route then verifies that a user
    exists for the given email and that the specified note belongs to that
    user before deleting it.

    A 403 is returned if the token email does not match the path email.
    A 404 is returned if either the user or the note cannot be found.
    """
    # Normalise e‑mails (handles tokens in lower‑case and mixed‑case paths)
    email_lower = email.strip().lower()
    current_lower = current_user.strip().lower() if current_user else None
    if not current_lower or email_lower != current_lower:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Look up the user using a case‑insensitive search
    user = db.query(User).filter(User.email.ilike(email_lower)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch the note, ensuring it belongs to this user
    note = (
        db.query(DBDailyNote)
        .filter(DBDailyNote.id == note_id, DBDailyNote.user_id == user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Daily note not found")

    # Delete and commit
    db.delete(note)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting daily note: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete daily note")

    return {"success": True, "message": "Daily note deleted successfully"}
