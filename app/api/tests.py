# app/api/tests.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.models.test import (
    TestDefinition, TestDefinitionCreate,
    TestResult, TestResultCreate
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
        return []                    # <- never an empty body

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
