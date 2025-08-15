# app/api/tests.py
from fastapi import APIRouter, HTTPException, Depends, status, Response
from sqlalchemy.orm import Session
from typing import List
from app.models.test import (
    TestDefinition, TestDefinitionCreate,
    TestResult, TestResultCreate, TestResultUpdate
)
from app.core.dependencies import get_current_user_email
from app.db.models import TestDefinition as DBTestDefinition, TestResult as DBTestResult, User
from app.core.database import get_db

router = APIRouter(prefix="/tests", tags=["Tests"])

@router.get("/", response_model=List[TestDefinition])
def list_tests(db: Session = Depends(get_db)):
    return db.query(DBTestDefinition).all()

@router.post("/", response_model=TestDefinition, status_code=201)
def create_test_definition(payload: TestDefinitionCreate, db: Session = Depends(get_db)):
    db_test = DBTestDefinition(**payload.dict())
    db.add(db_test); db.commit(); db.refresh(db_test)
    return db_test

@router.get("/users/{email}/{test_id}/results", response_model=List[TestResult])
def get_user_test_results(
    email: str,
    test_id: int,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if email.lower() != current_user.lower():
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(404, "User not found")

    rows = (
        db.query(DBTestResult)
        .filter(DBTestResult.user_id == user.id, DBTestResult.test_id == test_id)
        .order_by(DBTestResult.date.asc())
        .all()
    )

    # You can return ORM rows directly because TestResult.Config.orm_mode = True.
    return rows

@router.post("/users/{email}/{test_id}/results", response_model=TestResult, status_code=201)
def create_test_result(
    email: str,
    test_id: int,
    payload: TestResultCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if email.lower() != current_user.lower():
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(404, "User not found")

    db_result = DBTestResult(
        user_id=user.id,
        test_id=test_id,
        date=payload.date,   # DATE column — good
        value=payload.value,
        notes=payload.notes
    )
    db.add(db_result); db.commit(); db.refresh(db_result)
    return db_result         # FastAPI serializes date -> "YYYY-MM-DD"

@router.put("/users/{email}/{test_id}/results/{result_id}", response_model=TestResult)
def update_test_result(
    email: str,
    test_id: int,
    result_id: int,
    payload: TestResultUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Update a user's test result."""
    if email.lower() != current_user.lower():
        raise HTTPException(403, "Unauthorized")

    # Find user
    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Fetch result ensuring it belongs to user and matches test_id
    result = (
        db.query(DBTestResult)
        .filter(DBTestResult.id == result_id,
                DBTestResult.user_id == user.id,
                DBTestResult.test_id == test_id)
        .first()
    )
    if not result:
        raise HTTPException(404, "Test result not found")

    # Update fields if provided
    if payload.date is not None:
        result.date = payload.date
    if payload.value is not None:
        result.value = payload.value
    if payload.notes is not None:
        result.notes = payload.notes

    db.add(result)
    db.commit()
    db.refresh(result)
    return result

@router.delete("/users/{email}/{test_id}/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_result(
    email: str,
    test_id: int,
    result_id: int,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Delete a user's test result."""
    if email.lower() != current_user.lower():
        raise HTTPException(403, "Unauthorized")

    user = db.query(User).filter(User.email == current_user).first()
    if not user:
        raise HTTPException(404, "User not found")

    result = (
        db.query(DBTestResult)
        .filter(
            DBTestResult.id == result_id,
            DBTestResult.user_id == user.id,
            DBTestResult.test_id == test_id
        )
        .first()
    )
    if not result:
        raise HTTPException(404, "Test result not found")

    db.delete(result)
    db.commit()

    # No body returned — just the 204 status
    return Response(status_code=status.HTTP_204_NO_CONTENT)
