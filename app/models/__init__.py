# models/__init__.py
"""
Pydantic models for request/response validation
"""

from .auth_models import (
    SignUpRequest,
    SignInRequest,
    ForgotRequest,
    ForgotPasswordResponse,
    VerifyResetCodeRequest,
    ResetPasswordRequest
)

from .user import UserProfileData

from .project import (
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    Project,
    ProjectLogBase,
    ProjectLogCreate,
    ProjectLog
)

from .training_plan import (
    PlanSessionBase,
    PlanPhaseBase,
    TrainingPlanBase,
    PhasePlanRequest,
    FullPlanRequest,
    TrainingPlanCreate,
    TrainingPlan
)

from .session import (
    SessionTracking,
    SessionTrackingUpdateBody
)

from .daily_note import (
    DailyNoteBase,
    DailyNoteCreate,
    DailyNoteUpdate,
    DailyNote
)

from .exercise import (
    ExerciseTracking,
    ExerciseTrackingCreate,
    ExerciseTrackingUpdate
)

__all__ = [
    # Auth
    "SignUpRequest",
    "SignInRequest", 
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "VerifyResetCodeRequest",
    "ResetPasswordRequest",
    
    # User
    "UserProfileData",
    
    # Project
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "Project",
    "ProjectLogBase",
    "ProjectLogCreate",
    "ProjectLog",
    
    # Training Plan
    "PlanSessionBase",
    "PlanPhaseBase",
    "TrainingPlanBase",
    "PhasePlanRequest",
    "FullPlanRequest",
    "TrainingPlanCreate",
    "TrainingPlan",
    
    # Session
    "SessionTracking",
    "SessionTrackingUpdate",
    
    # Daily Note
    "DailyNoteBase",
    "DailyNoteCreate",
    "DailyNoteUpdate",
    "DailyNote",

    # Exercise Tracking
    "ExerciseTracking",
    "ExerciseTrackingCreate",
    "ExerciseTrackingUpdate"
]