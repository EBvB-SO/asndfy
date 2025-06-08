# db/models.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# User related models
class User(Base):
    __tablename__ = 'users'
    
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile            = relationship("UserProfile",    back_populates="user", cascade="all, delete-orphan", uselist=False)
    projects           = relationship("Project",        back_populates="user", cascade="all, delete-orphan")
    training_plans     = relationship("TrainingPlan",   back_populates="user", cascade="all, delete-orphan")
    daily_notes        = relationship("DailyNote",      back_populates="user", cascade="all, delete-orphan")
    badges             = relationship("UserBadge",      back_populates="user", cascade="all, delete-orphan")
    session_tracking   = relationship("SessionTracking",back_populates="user", cascade="all, delete-orphan")
    exercise_tracking  = relationship("ExerciseTracking", back_populates="user", cascade="all, delete-orphan")
    exercise_entries   = relationship("ExerciseEntry",  back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Profile fields
    current_climbing_grade = Column(String(50))
    max_boulder_grade = Column(String(50))
    goal = Column(Text)
    training_experience = Column(Text)
    perceived_strengths = Column(Text)
    perceived_weaknesses = Column(Text)
    attribute_ratings = Column(Text)
    weeks_to_train = Column(String(50))
    sessions_per_week = Column(String(50))
    time_per_session = Column(String(50))
    training_facilities = Column(Text)
    injury_history = Column(Text)
    general_fitness = Column(String(100))
    height = Column(String(50))
    weight = Column(String(50))
    age = Column(String(50))
    preferred_climbing_style = Column(Text)
    indoor_vs_outdoor = Column(String(50))
    onsight_flash_level = Column(String(50))
    redpointing_experience = Column(Text)
    sleep_recovery = Column(String(50))
    work_life_balance = Column(String(100))
    fear_factors = Column(Text)
    mindfulness_practices = Column(Text)
    motivation_level = Column(String(50))
    access_to_coaches = Column(String(50))
    time_for_cross_training = Column(String(50))
    additional_notes = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

# Project related models
class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    route_name = Column(String(255), nullable=False)
    grade = Column(String(50), nullable=False)
    crag = Column(String(255), nullable=False)
    description = Column(Text)
    route_angle = Column(String(50), nullable=False)  # 'slab', 'vertical', 'overhanging', 'roof'
    route_length = Column(String(50), nullable=False)  # 'long', 'medium', 'short', 'bouldery'
    hold_type = Column(String(50), nullable=False)     # 'crack', 'crimpy', 'slopers', 'jugs', 'pinches'
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="projects")
    logs = relationship("ProjectLog", back_populates="project", cascade="all, delete-orphan")

class ProjectLog(Base):
    __tablename__ = 'project_logs'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    content = Column(Text, nullable=False)
    mood = Column(String(50))  # 'sad', 'neutral', 'happy'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="logs")

# Training plan related models
class TrainingPlan(Base):
    __tablename__ = 'training_plans'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    route_name = Column(String(255), nullable=False)
    grade = Column(String(50), nullable=False)
    route_overview = Column(Text)
    training_overview = Column(Text)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="training_plans")
    phases = relationship("PlanPhase", back_populates="plan", cascade="all, delete-orphan")
    session_tracking = relationship("SessionTracking", back_populates="plan", cascade="all, delete-orphan")
    exercise_tracking = relationship("ExerciseTracking", back_populates="plan", cascade="all, delete-orphan")

class PlanPhase(Base):
    __tablename__ = 'plan_phases'
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(36), ForeignKey('training_plans.id', ondelete='CASCADE'), nullable=False)
    phase_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    phase_order = Column(Integer, nullable=False)
    
    # Relationships
    plan = relationship("TrainingPlan", back_populates="phases")
    sessions = relationship("PlanSession", back_populates="phase", cascade="all, delete-orphan")

class PlanSession(Base):
    __tablename__ = 'plan_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey('plan_phases.id', ondelete='CASCADE'), nullable=False)
    day = Column(String(50), nullable=False)  # 'Monday', 'Tuesday', etc.
    focus = Column(String(255), nullable=False)
    details = Column(Text, nullable=False)
    session_order = Column(Integer, nullable=False)
    
    # Relationships
    phase = relationship("PlanPhase", back_populates="sessions")

# Session tracking models
class SessionTracking(Base):
    __tablename__ = 'session_tracking'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(String(36), ForeignKey('training_plans.id', ondelete='CASCADE'), nullable=False)
    week_number = Column(Integer, nullable=False)
    day_of_week = Column(String(50), nullable=False)
    focus_name = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)
    notes = Column(Text)
    completion_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="session_tracking")
    plan = relationship("TrainingPlan", back_populates="session_tracking")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_tracking_plan_id', 'plan_id'),
        Index('idx_session_tracking_user_id', 'user_id'),
    )

class PendingSessionUpdate(Base):
    __tablename__ = 'pending_session_updates'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(String(36), ForeignKey('training_plans.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('session_tracking.id', ondelete='CASCADE'), nullable=False)
    is_completed = Column(Boolean, nullable=False)
    notes = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_synced = Column(Boolean, default=False)

# Exercise tracking models
class ExerciseTracking(Base):
    __tablename__ = 'exercise_tracking'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(String(36), ForeignKey('training_plans.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('session_tracking.id', ondelete='CASCADE'), nullable=False)
    exercise_id = Column(String(255), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="exercise_tracking")
    plan = relationship("TrainingPlan", back_populates="exercise_tracking")
    
    # Indexes
    __table_args__ = (
        Index('idx_exercise_tracking_plan_id', 'plan_id'),
        Index('idx_exercise_tracking_session_id', 'session_id'),
        Index('idx_exercise_tracking_exercise_id', 'exercise_id'),
        Index('idx_exercise_tracking_user_id', 'user_id'),
    )

class ExerciseEntry(Base):
    __tablename__ = "exercise_entries"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type             = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    timestamp        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="exercise_entries")

# Exercise library models
class Exercise(Base):
    __tablename__ = 'exercises'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    description = Column(Text)
    priority = Column(String(50), default='medium')
    time_required = Column(Integer)
    required_facilities = Column(String(255), default='bouldering_wall')
    
    # Relationships
    targets = relationship("ExerciseTarget", back_populates="exercise", cascade="all, delete-orphan")

class ExerciseTarget(Base):
    __tablename__ = 'exercise_targets'
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id', ondelete='CASCADE'), nullable=False)
    target = Column(String(255), nullable=False)
    
    # Relationships
    exercise = relationship("Exercise", back_populates="targets")

# Badge models
class BadgeCategory(Base):
    __tablename__ = 'badge_categories'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    
    # Relationships
    badges = relationship("Badge", back_populates="category", cascade="all, delete-orphan")

class Badge(Base):
    __tablename__ = 'badges'
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('badge_categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    icon_name = Column(String(100), nullable=False)
    how_to_earn = Column(Text, nullable=False)
    
    # Relationships
    category = relationship("BadgeCategory", back_populates="badges")
    user_badges = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

class UserBadge(Base):
    __tablename__ = 'user_badges'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    badge_id = Column(Integer, ForeignKey('badges.id', ondelete='CASCADE'), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")
    
    # Unique constraint
    __table_args__ = (
        Index('idx_user_badges_unique', 'user_id', 'badge_id', unique=True),
    )

# Daily notes model
class DailyNote(Base):
    __tablename__ = 'daily_notes'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date = Column(String(10), nullable=False)  # ISO format date
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="daily_notes")
    
    # Indexes
    __table_args__ = (
        Index('idx_daily_notes_user_id', 'user_id'),
        Index('idx_daily_notes_date', 'date'),
    )

# Database version tracking
class DBVersion(Base):
    __tablename__ = 'db_version'
    
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    
    __table_args__ = (
        CheckConstraint('id = 1', name='single_row_constraint'),
    )