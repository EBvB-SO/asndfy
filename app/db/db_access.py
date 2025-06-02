# backend/app/db/db_access.py
"""
Database access adapter to maintain compatibility with original code
while using SQLAlchemy ORM
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, TypeVar, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid
from contextlib import contextmanager

from core.database import get_db_session, SessionLocal
from core.security import get_password_hash, verify_password
from db.models import (
    User, UserProfile, Project, ProjectLog, TrainingPlan,
    PlanPhase, PlanSession, SessionTracking, ExerciseTracking,
    Exercise, ExerciseTarget, Badge, BadgeCategory, UserBadge,
    DailyNote, PendingSessionUpdate
)

logger = logging.getLogger(__name__)

T = TypeVar('T')

class DBResult:
    """Standardized result object for database operations."""
    
    def __init__(self, success: bool, message: str, data: Optional[T] = None):
        self.success = success
        self.message = message
        self.data = data
    
    @property
    def id(self) -> Optional[str]:
        """Helper to get ID for create operations."""
        if isinstance(self.data, str):
            return self.data
        elif isinstance(self.data, dict) and 'id' in self.data:
            return self.data['id']
        elif hasattr(self.data, 'id'):
            return str(self.data.id)
        return None
    
    def __bool__(self) -> bool:
        """Allow direct boolean evaluation of results."""
        return self.success

# For backward compatibility
get_db_connection = get_db_session
get_connection = SessionLocal

# User Management Functions
def create_user(name: str, email: str, password: str) -> DBResult:
    """Create a new user with hashed password."""
    with get_db_session() as db:
        try:
            # Check if email already exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return DBResult(False, "Email already registered")
            
            # Create new user
            user = User(
                name=name,
                email=email,
                password_hash=get_password_hash(password)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return DBResult(True, "User created successfully", user.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return DBResult(False, f"Error creating user: {str(e)}")

def verify_user(email: str, password: str) -> DBResult:
    """Verify user credentials and return user data if valid."""
    with get_db_session() as db:
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user or not verify_password(password, user.password_hash):
                return DBResult(False, "Invalid credentials")
            
            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
            return DBResult(True, "User authenticated successfully", user_data)
        except Exception as e:
            logger.error(f"Error verifying user: {str(e)}")
            return DBResult(False, "Authentication error")

def update_user_password(email: str, new_password: str) -> DBResult:
    """Update a user's password."""
    with get_db_session() as db:
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return DBResult(False, "User not found")
            
            user.password_hash = get_password_hash(new_password)
            db.commit()
            
            return DBResult(True, "Password updated successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating password: {str(e)}")
            return DBResult(False, f"Database error: {str(e)}")

# User Profile Functions
def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Get a user's profile by user ID."""
    with get_db_session() as db:
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                return None
            
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "current_climbing_grade": profile.current_climbing_grade,
                "max_boulder_grade": profile.max_boulder_grade,
                "goal": profile.goal,
                "training_experience": profile.training_experience,
                "perceived_strengths": profile.perceived_strengths,
                "perceived_weaknesses": profile.perceived_weaknesses,
                "attribute_ratings": profile.attribute_ratings,
                "training_facilities": profile.training_facilities,
                "injury_history": profile.injury_history,
                # Add all other profile fields...
            }
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None

def update_user_profile(user_id: int, profile_data: Dict[str, Any]) -> DBResult:
    """Update a user profile."""
    with get_db_session() as db:
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            
            if profile:
                # Update existing profile
                for key, value in profile_data.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
            else:
                # Create new profile
                profile = UserProfile(user_id=user_id, **profile_data)
                db.add(profile)
            
            db.commit()
            return DBResult(True, "Profile updated successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            return DBResult(False, f"Error updating profile: {str(e)}")

# Exercise Management Functions
def get_exercises() -> List[Dict[str, Any]]:
    """Get all exercises with their required facilities and time requirements."""
    with get_db_session() as db:
        exercises = db.query(Exercise).all()
        
        result = []
        for exercise in exercises:
            exercise_dict = {
                "id": exercise.id,
                "name": exercise.name,
                "type": exercise.type,
                "description": exercise.description,
                "priority": exercise.priority,
                "time_required": exercise.time_required,
                "required_facilities": exercise.required_facilities,
                "best_for": [target.target for target in exercise.targets]
            }
            result.append(exercise_dict)
        
        return result

# Project Management Functions
def create_project(user_id: int, project_data: Dict[str, Any]) -> DBResult:
    """Create a new project."""
    with get_db_session() as db:
        try:
            project = Project(
                id=project_data.get("id", str(uuid.uuid4())),
                user_id=user_id,
                **{k: v for k, v in project_data.items() if k != "id"}
            )
            db.add(project)
            db.commit()
            
            return DBResult(True, "Project created successfully", project.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating project: {str(e)}")
            return DBResult(False, f"Error creating project: {str(e)}")

def get_user_projects(user_id: int) -> List[Dict[str, Any]]:
    """Get all projects for a user with log counts."""
    with get_db_session() as db:
        projects = db.query(Project).filter(Project.user_id == user_id).all()
        
        result = []
        for project in projects:
            project_dict = {
                "id": project.id,
                "user_id": project.user_id,
                "route_name": project.route_name,
                "grade": project.grade,
                "crag": project.crag,
                "description": project.description,
                "route_angle": project.route_angle,
                "route_length": project.route_length,
                "hold_type": project.hold_type,
                "is_completed": project.is_completed,
                "completion_date": project.completion_date.isoformat() if project.completion_date else None,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "log_count": len(project.logs)
            }
            result.append(project_dict)
        
        return result

# Add remaining functions following the same pattern...
# This is a partial implementation showing the structure
# You would need to implement all functions from the original db_access.py