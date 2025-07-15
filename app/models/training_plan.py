# models/training_plan.py
from pydantic import BaseModel
from typing import List, Optional

class PlanSessionBase(BaseModel):
    day: str
    focus: str
    details: str

class PlanPhaseBase(BaseModel):
    phase_name: str
    description: str
    weekly_schedule: List[PlanSessionBase]

class TrainingPlanBase(BaseModel):
    route_name: str
    grade: str
    route_overview: str
    training_overview: str
    phases: List[PlanPhaseBase]

class PhasePlanRequest(BaseModel):
    route: str
    grade: str
    crag: str
    
    # Route characteristic fields
    route_angles: str = ""  # Comma-separated values (e.g. "Slab, Vertical")
    route_lengths: str = ""  # Comma-separated values (e.g. "Short, Medium")
    hold_types: str = ""     # Comma-separated values (e.g. "Crimpy, Jugs")
    route_style: str = ""    # Single value (e.g. "Pumpy", "Bouldery", etc.)
    route_description: str = ""  # Free-form text about the route
    
    # These fields are now primarily defined in GeneratePlanView instead of profile
    # The backend logic stays the same since it still receives the values
    weeks_to_train: str
    sessions_per_week: str
    time_per_session: str

    current_climbing_grade: str
    max_boulder_grade: str
    training_experience: str
    perceived_strengths: str
    perceived_weaknesses: str
    attribute_ratings: str = ""
    years_experience: Optional[float] = None
    age: Optional[int] = None
    training_facilities: str
    injury_history: str
    general_fitness: str
    height: str
    weight: str
    preferred_climbing_style: str
    indoor_vs_outdoor: str
    onsight_flash_level: str
    redpointing_experience: str
    sleep_recovery: str
    work_life_balance: str
    fear_factors: str
    mindfulness_practices: str
    motivation_level: str
    access_to_coaches: str
    time_for_cross_training: str
    additional_notes: str
    
class FullPlanRequest(BaseModel):
    plan_data: PhasePlanRequest
    weeks_to_train: int
    sessions_per_week: int
    previous_analysis: Optional[str] = None

class TrainingPlanCreate(TrainingPlanBase):
    pass

class TrainingPlan(TrainingPlanBase):
    id: str
    user_id: str
    purchased_at: str