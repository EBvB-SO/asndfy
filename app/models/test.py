# app/models/test.py
from datetime import date
from typing import Optional
from pydantic import BaseModel


# ----------------------------
# Test definitions
# ----------------------------
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
        orm_mode = True  # Pydantic v1; for v2 use: model_config = ConfigDict(from_attributes=True)


# ----------------------------
# Test results
# ----------------------------
class TestResultBase(BaseModel):
    date: date           # "yyyy-mm-dd"
    value: float
    notes: Optional[str] = None

class TestResultCreate(TestResultBase):
    pass

class TestResult(TestResultBase):
    id: int
    test_id: int

    class Config:
        orm_mode = True
