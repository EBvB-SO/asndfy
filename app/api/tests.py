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

# List all available tests
@router.get("/", response_model=List[TestDefinition])
def list_tests(db: Session = Depends(get_db)):
    return db.query(DBTestDefinition).all()

# (Optional) create a new test definition – could be restricted to admin
@router.post("/", response_model=TestDefinition)
def create_test_definition(
    payload: TestDefinitionCreate,
    db: Session = Depends(get_db)
):
    db_test = DBTestDefinition(**payload.dict())
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test

# Get all results for a particular user and test
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
    return [
        TestResult(
            id=res.id,
            test_id=res.test_id,
            date=res.date,
            value=res.value,
            notes=res.notes
        )
        for res in db.query(DBTestResult).filter(
            DBTestResult.user_id == user.id,
            DBTestResult.test_id == test_id
        ).order_by(DBTestResult.date.asc()).all()
    ]

# Record a new test result
@router.post("/users/{email}/{test_id}/results", response_model=TestResult)
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
    db_result = DBTestResult(
        user_id=user.id,
        test_id=test_id,
        date=payload.date,
        value=payload.value,
        notes=payload.notes
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return TestResult(
        id=db_result.id,
        test_id=db_result.test_id,
        date=db_result.date,
        value=db_result.value,
        notes=db_result.notes
    )
