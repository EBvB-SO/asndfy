# models/user.py
from pydantic import BaseModel

class UserProfileData(BaseModel):
    name: str = ""
    current_climbing_grade: str = ""
    max_boulder_grade: str = ""
    goal: str = ""
    training_experience: str = ""
    perceived_strengths: str = ""
    perceived_weaknesses: str = ""
    attribute_ratings: str = ""
    
    # Keep these fields for backward compatibility
    weeks_to_train: str = ""
    sessions_per_week: str = ""
    time_per_session: str = ""
    
    training_facilities: str = ""
    injury_history: str = ""
    general_fitness: str = ""
    height: str = ""
    weight: str = ""
    age: str = ""
    preferred_climbing_style: str = ""
    indoor_vs_outdoor: str = ""
    onsight_flash_level: str = ""
    redpointing_experience: str = ""
    sleep_recovery: str = ""
    work_life_balance: str = ""
    fear_factors: str = ""
    mindfulness_practices: str = ""
    motivation_level: str = ""
    access_to_coaches: str = ""
    time_for_cross_training: str = ""
    additional_notes: str = ""