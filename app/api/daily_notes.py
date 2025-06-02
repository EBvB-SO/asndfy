# api/daily_notes.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the db_access module as "db" so that db.get_db_connection, db.get_daily_notes_for_user, etc. are available
import db.db_access as db

from models.daily_note import DailyNoteCreate, DailyNoteUpdate, DailyNote
from core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/daily_notes", tags=["Daily Notes"])


@router.get("/{email}", response_model=List[DailyNote])
def get_daily_notes(
    email: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """Get daily notes for a user, optionally filtered by date range."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Get notes based on date range if provided
        if start_date and end_date:
            notes = db.get_daily_notes_for_date_range(user_id, start_date, end_date)
        else:
            notes = db.get_daily_notes_for_user(user_id)
        
        return notes

@router.post("/{email}", response_model=DailyNote)
def create_daily_note(
    email: str, 
    note: DailyNoteCreate,
    current_user: str = Depends(get_current_user_email)
):
    """Create a new daily note."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Create the note
        note_data = note.dict()
        result = db.create_daily_note(user_id, note_data)
        
        if not result:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "id": result.id,
            **note_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

@router.put("/{email}/{note_id}")
def update_daily_note(
    email: str, 
    note_id: str, 
    update: DailyNoteUpdate,
    current_user: str = Depends(get_current_user_email)
):
    """Update an existing daily note."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # First verify the user owns this note
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Verify ownership
        cursor.execute("""
            SELECT id FROM daily_notes 
            WHERE id = ? AND user_id = ?
        """, (note_id, user_id))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Daily note not found")
    
    # Update the note
    result = db.update_daily_note(note_id, update.content)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {"success": True, "message": "Daily note updated successfully"}

@router.delete("/{email}/{note_id}")
def delete_daily_note(
    email: str, 
    note_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Delete a daily note."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # First verify the user owns this note
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Verify ownership
        cursor.execute("""
            SELECT id FROM daily_notes 
            WHERE id = ? AND user_id = ?
        """, (note_id, user_id))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Daily note not found")
    
    # Delete the note
    result = db.delete_daily_note(note_id)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {"success": True, "message": "Daily note deleted successfully"}