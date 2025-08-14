# app/models/test.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class TestDefinitionBase(BaseModel):
    name: str
    description: Optional[str] = None
    exercise_id: Optional[int] = None
    unit: Optional[str] = None

class TestDefinitionCreate(TestDefinitionBase):
    pass

class TestDefinition(TestDefinitionBase):
    id: int

    class Config:
        orm_mode = True

class TestResultBase(BaseModel):
    date: date
    value: float
    notes: Optional[str] = None

class TestResultCreate(TestResultBase):
    pass

class TestResult(TestResultBase):
    id: int
    test_id: int

    class Config:
        orm_mode = True
