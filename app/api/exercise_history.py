# app/api/exercise_history.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from app.core.security import get_current_user
from app.models.exercise import (
    ExerciseEntry, ExerciseEntryCreate, ExerciseEntryUpdate
)
from app.db.db_access import (
    get_all_exercises, get_exercise_by_id,
    create_exercise, update_exercise, delete_exercise
)
from app.models.auth_models import DataResponse, BaseResponse

router = APIRouter(prefix="/exercise-history", tags=["ExerciseHistory"])

@router.get("/", response_model=DataResponse[List[ExerciseEntry]])
def list_history(
    current_user = Depends(get_current_user),
):
    """
    Returns only the exercise‐history entries belonging to the logged‐in user.
    """
    entries = get_all_exercises(user_id=current_user.id)
    return DataResponse(success=True, message="Fetched history", data=entries)

@router.get("/{entry_id}", response_model=DataResponse[ExerciseEntry])
def get_entry(
    entry_id: int,
    current_user=Depends(get_current_user),
):
    entry = get_exercise_by_id(entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(404, "Not found")
    return DataResponse(success=True, message="Fetched entry", data=entry)

@router.post("/", response_model=DataResponse[ExerciseEntry])
def create_entry(
    payload: ExerciseEntryCreate,
    current_user=Depends(get_current_user),
):
    try:
        # ensure the payload is associated with the current user
        entry = create_exercise(payload, user_id=current_user.id)
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
    current_user=Depends(get_current_user),
):
    try:
        updated = update_exercise(entry_id, payload, user_id=current_user.id)
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
    current_user=Depends(get_current_user),
):
    # delete_exercise should be scoped by user_id
    if not delete_exercise(entry_id, user_id=current_user.id):
        raise HTTPException(404, "Not found")
    return BaseResponse(success=True, message="Deleted entry")
