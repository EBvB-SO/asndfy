# app/api/exercise_history.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from app.core.dependencies import get_current_user_email
from app.models.exercise import (
    ExerciseEntry, ExerciseEntryCreate, ExerciseEntryUpdate
)
from app.db.db_access import (
    get_all_exercises, get_exercise_by_id,
    create_exercise, update_exercise, delete_exercise
)
from app.models.auth_models import DataResponse, BaseResponse
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.db.models import User

router = APIRouter(prefix="/exercise-history", tags=["ExerciseHistory"])

@router.get("/", response_model=DataResponse[List[ExerciseEntry]])
def list_history(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Returns only the exercise‐history entries belonging to the logged‐in user.
    """
    # Get user ID from email
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    entries = get_all_exercises(user_id=user.id)
    return DataResponse(success=True, message="Fetched history", data=entries)

@router.get("/{entry_id}", response_model=DataResponse[ExerciseEntry])
def get_entry(
    entry_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    # Get user ID from email
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    entry = get_exercise_by_id(entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Not found")
    return DataResponse(success=True, message="Fetched entry", data=entry)

@router.post("/", response_model=DataResponse[ExerciseEntry])
def create_entry(
    payload: ExerciseEntryCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    # Get user ID from email
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    try:
        # ensure the payload is associated with the current user
        entry = create_exercise(payload, user_id=user.id)
        return DataResponse(success=True, message="Created entry", data=entry)
    except SQLAlchemyError as e:
        # optionally log e here
        raise HTTPException(
            status_code=500,
            detail="Failed to create entry, please try again later."
        )

@router.put("/{entry_id}", response_model=DataResponse[ExerciseEntry])
def edit_entry(
    entry_id: int,
    payload: ExerciseEntryUpdate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    # Get user ID from email
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    try:
        updated = update_exercise(entry_id, payload, user_id=user.id)
        if not updated:
            raise HTTPException(status_code=404, detail="Entry not found")
        return DataResponse(success=True, message="Updated entry", data=updated)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to update entry, please try again later."
        )

@router.delete("/{entry_id}", response_model=BaseResponse)
def remove_entry(
    entry_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    # Get user ID from email
    user = db.query(User).filter(User.email == current_user_email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # delete_exercise should be scoped by user_id
    if not delete_exercise(entry_id, user_id=user.id):
        raise HTTPException(404, "Not found")
    return BaseResponse(success=True, message="Deleted entry")