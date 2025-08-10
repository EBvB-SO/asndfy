# app/db/db_access.py

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager

from app.core.database import get_db_session, SessionLocal
from app.models.exercise import ExerciseEntry, ExerciseEntryCreate, ExerciseEntryUpdate
from app.core.security import get_password_hash, verify_password
from .models import ExerciseEntry as DBExerciseEntry
from .models import (
    User,
    UserProfile,
    Project,
    ProjectLog,
    TrainingPlan,
    PlanPhase,
    PlanSession,
    SessionTracking,
    ExerciseTracking,
    Exercise,
    ExerciseTarget,
    Badge,
    BadgeCategory,
    UserBadge,
    DailyNote,
    PendingSessionUpdate,
)

logger = logging.getLogger(__name__)


class DBResult:
    """Standardized result object for database operations."""

    def __init__(self, success: bool, message: str, data: Optional[Any] = None):
        self.success = success
        self.message = message
        self.data = data

    @property
    def id(self) -> Optional[str]:
        if isinstance(self.data, str):
            return self.data
        if isinstance(self.data, dict) and "id" in self.data:
            return self.data["id"]
        if hasattr(self.data, "id"):
            return str(self.data.id)
        return None

    def __bool__(self) -> bool:
        return self.success


# ------------------------------------------------------------------
# Backward compatibility helpers
# ------------------------------------------------------------------

class ConnectionWrapper:
    """Wrapper to provide cursor-like interface for SQLAlchemy session."""
    
    def __init__(self, session):
        self.session = session
        self._results = []
        self._current_row = None
    
    def cursor(self):
        """Return self as the cursor."""
        return self
    
    def execute(self, query, params=None):
        """Execute a raw SQL query."""
        from sqlalchemy import text
        
        if params:
            # Convert ? to :param for SQLAlchemy
            # Count the number of ? and replace with :param0, :param1, etc.
            if '?' in query:
                for i, param in enumerate(params):
                    query = query.replace('?', f':param{i}', 1)
                params = {f'param{i}': p for i, p in enumerate(params)}
            
            result = self.session.execute(text(query), params)
        else:
            result = self.session.execute(text(query))
        
        if result.returns_rows:
            self._results = result.fetchall()
        else:
            self._results = []
        return self
    
    def fetchone(self):
        """Fetch one row as a dict."""
        if self._results:
            row = self._results.pop(0)
            # Convert Row object to dict
            if hasattr(row, '_mapping'):
                return dict(row._mapping)
            elif hasattr(row, '_asdict'):
                return row._asdict()
            else:
                # For older SQLAlchemy versions
                return dict(row)
        return None
    
    def fetchall(self):
        """Fetch all rows as list of dicts."""
        results = []
        while self._results:
            row = self.fetchone()
            if row:
                results.append(row)
        return results
    
    def commit(self):
        """Commit the transaction."""
        self.session.commit()
    
    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()
    
    def close(self):
        """Close the session."""
        self.session.close()


@contextmanager
def get_db_connection():
    """
    Context manager that provides a connection-like interface.
    This is for backward compatibility with code expecting cursor() method.
    """
    session = SessionLocal()
    wrapper = ConnectionWrapper(session)
    try:
        yield wrapper
    finally:
        session.close()


def get_connection():
    """
    Returns a connection wrapper for backward compatibility.
    Note: Caller is responsible for closing this!
    """
    session = SessionLocal()
    return ConnectionWrapper(session)


# ------------------------------------------------------------------
# USER MANAGEMENT FUNCTIONS
# ------------------------------------------------------------------

def create_user(name: str, email: str, password: str) -> DBResult:
    """Create a new user with a hashed password."""
    with get_db_session() as db:
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return DBResult(False, "Email already registered")

            user = User(
                name=name,
                email=email,
                password_hash=get_password_hash(password),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return DBResult(True, "User created successfully", user.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            return DBResult(False, f"Error creating user: {e}")


def verify_user(email: str, password: str) -> DBResult:
    """Verify user credentials and return user data if valid."""
    with get_db_session() as db:
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user or not verify_password(password, user.password_hash):
                return DBResult(False, "Invalid credentials")

            user_data = {"id": user.id, "name": user.name, "email": user.email}
            return DBResult(True, "User authenticated successfully", user_data)
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
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
            logger.error(f"Error updating password: {e}")
            return DBResult(False, f"Database error: {e}")

def delete_user(email: str):
    with get_db_session() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return
        # Delete related entities (or configure cascade on foreign keys)
        db.query(TrainingPlan).filter(TrainingPlan.user_id == user.id).delete()
        db.query(Project).filter(Project.user_id == user.id).delete()
        db.query(DailyNote).filter(DailyNote.user_id == user.id).delete()
        db.delete(user)
        db.commit()

# ------------------------------------------------------------------
# USER PROFILE FUNCTIONS
# ------------------------------------------------------------------

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user's profile by user ID."""
    with get_db_session() as db:
        try:
            user = db.query(User).get(user_id)
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

            # If no profile row yet, still return the user's name
            if not profile:
                return {"user_id": user_id, "name": user.name}
            
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "name": user.name,
                "current_climbing_grade": profile.current_climbing_grade,
                "max_boulder_grade": profile.max_boulder_grade,
                "goal": profile.goal,
                "training_experience": profile.training_experience,
                "perceived_strengths": profile.perceived_strengths,
                "perceived_weaknesses": profile.perceived_weaknesses,
                "attribute_ratings": profile.attribute_ratings,
                "weeks_to_train": profile.weeks_to_train,
                "sessions_per_week": profile.sessions_per_week,
                "time_per_session": profile.time_per_session,
                "training_facilities": profile.training_facilities,
                "injury_history": profile.injury_history,
                "general_fitness": profile.general_fitness,
                "height": profile.height,
                "weight": profile.weight,
                "age": profile.age,
                "preferred_climbing_style": profile.preferred_climbing_style,
                "indoor_vs_outdoor": profile.indoor_vs_outdoor,
                "onsight_flash_level": profile.onsight_flash_level,
                "redpointing_experience": profile.redpointing_experience,
                "sleep_recovery": profile.sleep_recovery,
                "work_life_balance": profile.work_life_balance,
                "fear_factors": profile.fear_factors,
                "mindfulness_practices": profile.mindfulness_practices,
                "motivation_level": profile.motivation_level,
                "access_to_coaches": profile.access_to_coaches,
                "time_for_cross_training": profile.time_for_cross_training,
                "additional_notes": profile.additional_notes,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None


def update_user_profile(user_id: str, profile_data: Dict[str, Any]) -> DBResult:
    """Update a user profile."""
    with get_db_session() as db:
        try:
            # 1) update User.name if present
            user = db.query(User).get(user_id)
            if "name" in profile_data:
                user.name = profile_data.pop("name")

            # 2) update or create UserProfile
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile:
                for key, value in profile_data.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
            else:
                profile = UserProfile(user_id=user.id, **profile_data)
                db.add(profile)

            # 3) commit everything
            db.commit()
            return DBResult(True, "Profile updated successfully")

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating profile: {e}")
            return DBResult(False, f"Error updating profile: {e}")
        

# ------------------------------------------------------------------
# EXERCISE MANAGEMENT FUNCTIONS
# ------------------------------------------------------------------

def get_exercises() -> List[Dict[str, Any]]:
    """Get all exercises with their required facilities and time requirements."""
    with get_db_session() as db:
        try:
            exercises = db.query(Exercise).all()
            result: List[Dict[str, Any]] = []
            for exercise in exercises:
                result.append({
                    "id": exercise.id,
                    "name": exercise.name,
                    "type": exercise.type,
                    "description": exercise.description,
                    "priority": exercise.priority,
                    "time_required": exercise.time_required,
                    "required_facilities": exercise.required_facilities,
                    "best_for": [t.target for t in exercise.targets],
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching exercises: {e}")
            return []


def add_exercise_target(exercise_id: int, target: str) -> DBResult:
    """Add a target/attribute to an existing exercise."""
    with get_db_session() as db:
        try:
            et = ExerciseTarget(exercise_id=exercise_id, target=target)
            db.add(et)
            db.commit()
            return DBResult(True, "Exercise target added", et.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding exercise target: {e}")
            return DBResult(False, f"Error adding exercise target: {e}")

def get_all_exercises(user_id: str) -> List[ExerciseEntry]:
    with get_db_session() as db:
        rows = (
            db.query(DBExerciseEntry)
              .filter(DBExerciseEntry.user_id == user_id)
              .all()
        )
        return [ExerciseEntry(
            id               = r.id,
            user_id          = r.user_id,
            type             = r.type,
            duration_minutes = r.duration_minutes,
            timestamp        = r.timestamp,
        ) for r in rows]

def get_exercise_by_id(entry_id: int) -> Optional[ExerciseEntry]:
    with get_db_session() as db:
        r = db.query(DBExerciseEntry).get(entry_id)
        if not r:
            return None
        return ExerciseEntry(
            id    = r.id,
            user_id = r.user_id,
            type  = r.type,
            duration_minutes = r.duration_minutes,
            timestamp = r.timestamp,
        )

def create_exercise(data: ExerciseEntryCreate, user_id: str) -> ExerciseEntry:
    with get_db_session() as db:
        new = DBExerciseEntry(
            user_id          = user_id,
            type             = data.type,
            duration_minutes = data.duration_minutes,
            timestamp        = datetime.utcnow(),  # use the datetime import above
        )
        db.add(new)
        db.commit()
        db.refresh(new)
        return ExerciseEntry(
            id    = new.id,
            user_id = new.user_id,
            type  = new.type,
            duration_minutes = new.duration_minutes,
            timestamp = new.timestamp,
        )

def update_exercise(entry_id: int, data: ExerciseEntryUpdate, user_id: str) -> Optional[ExerciseEntry]:
    with get_db_session() as db:
        existing = db.query(DBExerciseEntry).filter(
            DBExerciseEntry.id == entry_id,
            DBExerciseEntry.user_id == user_id
        ).first()
        if not existing:
            return None
        if data.type is not None:
            existing.type = data.type
        if data.duration_minutes is not None:
            existing.duration_minutes = data.duration_minutes
        # Allow editing the timestamp: if a new timestamp is provided,
        # update the entry’s timestamp to that value.  Without this,
        # date edits from the client are silently ignored.
        if data.timestamp is not None:
            ts = data.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            existing.timestamp = ts

        db.commit()
        db.refresh(existing)
        return ExerciseEntry(
            id    = existing.id,
            user_id = existing.user_id,
            type  = existing.type,
            duration_minutes = existing.duration_minutes,
            timestamp = existing.timestamp,
        )

def delete_exercise(entry_id: int, user_id: str) -> bool:
    with get_db_session() as db:
        existing = db.query(DBExerciseEntry).filter(
            DBExerciseEntry.id == entry_id,
            DBExerciseEntry.user_id == user_id
        ).first()
        if not existing:
            return False
        db.delete(existing)
        db.commit()
        return True

# ------------------------------------------------------------------
# PROJECT MANAGEMENT FUNCTIONS
# ------------------------------------------------------------------

def create_project(user_id: str, project_data: Dict[str, Any]) -> DBResult:
    """Create a new project."""
    with get_db_session() as db:
        try:
            proj = Project(
                id=project_data.get("id", str(uuid.uuid4())),
                user_id=user_id,
                **{k: v for k, v in project_data.items() if k != "id"},
            )
            db.add(proj)
            db.commit()
            return DBResult(True, "Project created successfully", proj.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating project: {e}")
            return DBResult(False, f"Error creating project: {e}")


def get_user_projects(user_id: str) -> List[Dict[str, Any]]:
    """Get all projects for a user with log counts."""
    with get_db_session() as db:
        try:
            projects = db.query(Project).filter(Project.user_id == user_id).all()
            result: List[Dict[str, Any]] = []
            for project in projects:
                result.append({
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
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    "log_count": len(project.logs),
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching user projects: {e}")
            return []


def add_project_log(project_id: str, date: str, content: str, mood: Optional[str] = None) -> DBResult:
    """Add a log entry to a project."""
    with get_db_session() as db:
        try:
            log = ProjectLog(
                id=str(uuid.uuid4()),
                project_id=project_id,
                date=date,
                content=content,
                mood=mood,
            )
            db.add(log)
            db.commit()
            return DBResult(True, "Project log added", log.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding project log: {e}")
            return DBResult(False, f"Error adding project log: {e}")


def get_project_logs(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve all logs for a project."""
    with get_db_session() as db:
        try:
            logs = db.query(ProjectLog).filter(ProjectLog.project_id == project_id).all()
            result: List[Dict[str, Any]] = []
            for log in logs:
                result.append({
                    "id": log.id,
                    "project_id": log.project_id,
                    "date": log.date.isoformat(),
                    "content": log.content,
                    "mood": log.mood,
                    "created_at": log.created_at.isoformat(),
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching project logs: {e}")
            return []


# ------------------------------------------------------------------
# TRAINING PLAN / SESSION FUNCTIONS
# ------------------------------------------------------------------

def get_sessions_for_plan(user_id: str, plan_id: str) -> List[Dict[str, Any]]:
    """Get all tracking sessions for a specific user & plan."""
    with get_db_session() as db:
        try:
            sessions = (
                db.query(SessionTracking)
                .filter(SessionTracking.user_id == user_id, SessionTracking.plan_id == plan_id)
                .all()
            )
            result: List[Dict[str, Any]] = []
            for s in sessions:
                result.append({
                    "id": s.id,
                    "plan_id": s.plan_id,
                    "week_number": s.week_number,
                    "day_of_week": s.day_of_week,
                    "focus_name": s.focus_name,
                    "is_completed": s.is_completed,
                    "notes": s.notes,
                    "completion_date": s.completion_date.isoformat() if s.completion_date else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching sessions for plan {plan_id}: {e}")
            return []


def create_sessions_for_plan(user_id: str, plan_id: str) -> DBResult:
    """
    Initialize tracking sessions for a plan based on PlanPhase → PlanSession hierarchy.
    Each PlanPhase.phase_order becomes week_number.
    """
    with get_db_session() as db:
        try:
            phases = (
                db.query(PlanPhase)
                .filter(PlanPhase.plan_id == plan_id)
                .order_by(PlanPhase.phase_order)
                .all()
            )
            created_sessions: List[Dict[str, Any]] = []

            for phase in phases:
                plan_sessions = (
                    db.query(PlanSession)
                    .filter(PlanSession.phase_id == phase.id)
                    .order_by(PlanSession.session_order)
                    .all()
                )
                for ps in plan_sessions:
                    new_session = SessionTracking(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        plan_id=plan_id,
                        week_number=phase.phase_order,
                        day_of_week=ps.day,
                        focus_name=ps.focus,
                        is_completed=False,
                        notes="",
                        completion_date=None,
                    )
                    db.add(new_session)
                    db.flush()
                    created_sessions.append({
                        "id": new_session.id,
                        "plan_id": new_session.plan_id,
                        "week_number": new_session.week_number,
                        "day_of_week": new_session.day_of_week,
                        "focus_name": new_session.focus_name,
                        "is_completed": new_session.is_completed,
                        "notes": new_session.notes,
                        "completion_date": None,
                    })

            db.commit()
            return DBResult(True, "Sessions initialized", created_sessions)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating sessions for plan {plan_id}: {e}")
            return DBResult(False, f"Error creating sessions: {e}")


# ------------------------------------------------------------------
# PENDING SESSION UPDATES (Offline Sync)
# ------------------------------------------------------------------

def get_pending_updates(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all pending session updates (is_synced == False) for a user.
    """
    with get_db_session() as db:
        try:
            updates = (
                db.query(PendingSessionUpdate)
                .filter(PendingSessionUpdate.user_id == user_id, PendingSessionUpdate.is_synced == False)
                .all()
            )
            result: List[Dict[str, Any]] = []
            for u in updates:
                result.append({
                    "id": u.id,
                    "plan_id": u.plan_id,
                    "session_id": u.session_id,
                    "is_completed": u.is_completed,
                    "notes": u.notes,
                    "timestamp": u.timestamp.isoformat() if u.timestamp else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching pending updates for user {user_id}: {e}")
            return []


def mark_update_synced(update_id: int) -> DBResult:
    """
    Mark a PendingSessionUpdate as synced (is_synced = True).
    """
    with get_db_session() as db:
        try:
            upd = db.query(PendingSessionUpdate).filter(PendingSessionUpdate.id == update_id).first()
            if not upd:
                return DBResult(False, "Pending update not found")

            upd.is_synced = True
            db.commit()
            return DBResult(True, "Update marked as synced")
        except Exception as e:
            db.rollback()
            logger.error(f"Error marking update {update_id} as synced: {e}")
            return DBResult(False, f"Error updating sync status: {e}")


# ------------------------------------------------------------------
# DAILY NOTES FUNCTIONS
# ------------------------------------------------------------------

def get_daily_notes_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Get all daily notes for a user."""
    with get_db_session() as db:
        try:
            notes = (
                db.query(DailyNote)
                .filter(DailyNote.user_id == user_id)
                .order_by(DailyNote.date)
                .all()
            )
            result: List[Dict[str, Any]] = []
            for note in notes:
                result.append({
                    "id": note.id,
                    "date": note.date,
                    "content": note.content,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                    "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching daily notes for user {user_id}: {e}")
            return []


def get_daily_notes_for_date_range(
    user_id:    str,
    start_date: date,
    end_date:   date
) -> List[Dict[str, Any]]:
    """Get all daily notes for a user within a given date range (inclusive)."""
    with get_db_session() as db:
        try:
            notes = (
                db.query(DailyNote)
                .filter(
                    DailyNote.user_id == user_id,
                    DailyNote.date >= start_date,
                    DailyNote.date <= end_date,
                )
                .order_by(DailyNote.date)
                .all()
            )
            result: List[Dict[str, Any]] = []
            for note in notes:
                result.append({
                    "id": note.id,
                    "date": note.date,
                    "content": note.content,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                    "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching daily notes for user {user_id} between {start_date} and {end_date}: {e}")
            return []


def create_daily_note(user_id: str, note_data: Dict[str, Any]) -> DBResult:
    """
    Create a new daily note.
    note_data should at least contain 'date' and 'content'.
    """
    with get_db_session() as db:
        try:
            new_note = DailyNote(
                id=str(uuid.uuid4()),
                user_id=user_id,
                date=note_data.get("date"),
                content=note_data.get("content"),
            )
            db.add(new_note)
            db.commit()
            return DBResult(True, "Daily note created successfully", new_note.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating daily note for user {user_id}: {e}")
            return DBResult(False, f"Error creating daily note: {e}")


def update_daily_note(note_id: str, content: str) -> DBResult:
    """Update the content of an existing daily note."""
    with get_db_session() as db:
        try:
            note = db.query(DailyNote).filter(DailyNote.id == note_id).first()
            if not note:
                return DBResult(False, "Daily note not found")

            note.content = content
            db.commit()
            return DBResult(True, "Daily note updated successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating daily note {note_id}: {e}")
            return DBResult(False, f"Error updating daily note: {e}")


def delete_daily_note(note_id: str) -> DBResult:
    """Delete a daily note by its ID."""
    with get_db_session() as db:
        try:
            note = db.query(DailyNote).filter(DailyNote.id == note_id).first()
            if not note:
                return DBResult(False, "Daily note not found")

            db.delete(note)
            db.commit()
            return DBResult(True, "Daily note deleted successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting daily note {note_id}: {e}")
            return DBResult(False, f"Error deleting daily note: {e}")


# ------------------------------------------------------------------
# BADGE / ACHIEVEMENT FUNCTIONS
# ------------------------------------------------------------------

def get_badge_categories() -> List[Dict[str, Any]]:
    """Retrieve all badge categories."""
    with get_db_session() as db:
        try:
            cats = db.query(BadgeCategory).all()
            return [{"id": c.id, "name": c.name} for c in cats]
        except Exception as e:
            logger.error(f"Error fetching badge categories: {e}")
            return []


def get_badges_for_category(category_id: int) -> List[Dict[str, Any]]:
    """Retrieve all badges under a specific category."""
    with get_db_session() as db:
        try:
            badges = db.query(Badge).filter(Badge.category_id == category_id).all()
            result: List[Dict[str, Any]] = []
            for b in badges:
                result.append({
                    "id": b.id,
                    "name": b.name,
                    "description": b.description,
                    "icon_name": b.icon_name,
                    "how_to_earn": b.how_to_earn,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching badges for category {category_id}: {e}")
            return []


def award_badge_to_user(user_id: str, badge_id: int) -> DBResult:
    """Award a badge to a user (if not already earned)."""
    with get_db_session() as db:
        try:
            existing = (
                db.query(UserBadge)
                .filter(UserBadge.user_id == user_id, UserBadge.badge_id == badge_id)
                .first()
            )
            if existing:
                return DBResult(False, "User already has this badge")

            ub = UserBadge(user_id=user_id, badge_id=badge_id)
            db.add(ub)
            db.commit()
            return DBResult(True, "Badge awarded", ub.id)
        except IntegrityError:
            db.rollback()
            return DBResult(False, "Badge or user not found")
        except Exception as e:
            db.rollback()
            logger.error(f"Error awarding badge {badge_id} to user {user_id}: {e}")
            return DBResult(False, f"Error awarding badge: {e}")


# ------------------------------------------------------------------
# EXERCISE TRACKING FUNCTIONS
# ------------------------------------------------------------------

def track_exercise(
    user_id: str,
    plan_id: str,
    session_id: str,
    exercise_id: str,
    date: str,
    notes: Optional[str] = None,
) -> DBResult:
    """Record an exercise tracking entry."""
    with get_db_session() as db:
        try:
            et = ExerciseTracking(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=plan_id,
                session_id=session_id,
                exercise_id=exercise_id,
                date=date,
                notes=notes or "",
            )
            db.add(et)
            db.commit()
            return DBResult(True, "Exercise tracked successfully", et.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error tracking exercise for session {session_id}: {e}")
            return DBResult(False, f"Error tracking exercise: {e}")


def get_exercise_tracking_for_session(session_id: str) -> List[Dict[str, Any]]:
    """Get all exercise tracking entries for a given session."""
    with get_db_session() as db:
        try:
            entries = (
                db.query(ExerciseTracking)
                .filter(ExerciseTracking.session_id == session_id)
                .all()
            )
            result: List[Dict[str, Any]] = []
            for e in entries:
                result.append({
                    "id": e.id,
                    "user_id": e.user_id,
                    "plan_id": e.plan_id,
                    "session_id": e.session_id,
                    "exercise_id": e.exercise_id,
                    "date": e.date.isoformat(),
                    "notes": e.notes,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching exercise tracking for session {session_id}: {e}")
            return []


# ------------------------------------------------------------------
# TRAINING PLAN CRUD
# ------------------------------------------------------------------

def delete_training_plan(plan_id: str) -> DBResult:
    """
    Permanently delete a training plan and all associated phases/sessions.
    Due to the cascade configuration on the relationships, deleting the
    TrainingPlan row will cascade to PlanPhase, PlanSession, session_tracking
    and exercise_tracking.
    """
    with get_db_session() as db:
        try:
            plan = db.query(TrainingPlan).filter(TrainingPlan.id == plan_id).first()
            if not plan:
                return DBResult(False, "Training plan not found")
            db.delete(plan)
            db.commit()
            return DBResult(True, "Training plan deleted", plan_id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting training plan: {e}")
            return DBResult(False, f"Error deleting training plan: {e}")

def create_training_plan(user_id: str, plan_data: Dict[str, Any]) -> DBResult:
    """
    Create a new TrainingPlan with nested phases & sessions.
    plan_data must include 'id', 'route_name', 'grade', and arrays of 'phases'.
    Each phase should have phase_name, description, phase_order, and a 'sessions' array.
    """
    with get_db_session() as db:
        try:
            plan = TrainingPlan(
                id=plan_data.get("id", str(uuid.uuid4())),
                user_id=user_id,
                route_name=plan_data["route_name"],
                grade=plan_data["grade"],
                route_overview=plan_data.get("route_overview"),
                training_overview=plan_data.get("training_overview"),
                purchased_at=plan_data.get("purchased_at", datetime.now(timezone.utc)),
            )
            db.add(plan)
            db.flush()

            # Insert phases
            for p in plan_data.get("phases", []):
                phase = PlanPhase(
                    plan_id=plan.id,
                    phase_name=p["phase_name"],
                    description=p["description"],
                    phase_order=p["phase_order"],
                )
                db.add(phase)
                db.flush()
                # Insert sessions for this phase
                for s in p.get("sessions", []):
                    ps = PlanSession(
                        phase_id=phase.id,
                        day=s["day"],
                        focus=s["focus"],
                        details=s["details"],
                        session_order=s["session_order"],
                    )
                    db.add(ps)

            db.commit()
            return DBResult(True, "Training plan created", plan.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating training plan: {e}")
            return DBResult(False, f"Error creating training plan: {e}")

def get_user_training_plans(user_id: str) -> List[Dict[str, Any]]:
    """Return a simple list of training plans for a user."""
    with get_db_session() as db:
        try:
            plans = db.query(TrainingPlan).filter(TrainingPlan.user_id == user_id).all()
            out: List[Dict[str, Any]] = []
            for p in plans:
                out.append({
                    "id": p.id,
                    "user_id": p.user_id,
                    "route_name": p.route_name,
                    "grade": p.grade,
                    "route_overview": p.route_overview,
                    "training_overview": p.training_overview,
                    # Return datetime directly, let FastAPI/Pydantic handle serialization
                    "purchased_at": p.purchased_at if p.purchased_at else None,
                })
            return out
        except Exception as e:
            logger.error(f"Error fetching plans for user {user_id}: {e}")
            return []

def get_training_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a full training plan (with phases & sessions) by its ID.
    """
    with get_db_session() as db:
        try:
            plan = db.query(TrainingPlan).filter(TrainingPlan.id == plan_id).first()
            if not plan:
                return None

            result: Dict[str, Any] = {
                "id": plan.id,
                "user_id": plan.user_id,
                "route_name": plan.route_name,
                "grade": plan.grade,
                "route_overview": plan.route_overview,
                "training_overview": plan.training_overview,
                "purchased_at": plan.purchased_at,
                "phases": [],
            }

            phases = (
                db.query(PlanPhase)
                .filter(PlanPhase.plan_id == plan.id)
                .order_by(PlanPhase.phase_order)
                .all()
            )
            for phase in phases:
                p_dict: Dict[str, Any] = {
                    "id": phase.id,
                    "phase_name": phase.phase_name,
                    "description": phase.description,
                    "phase_order": phase.phase_order,
                    "sessions": [],
                }
                sessions = (
                    db.query(PlanSession)
                    .filter(PlanSession.phase_id == phase.id)
                    .order_by(PlanSession.session_order)
                    .all()
                )
                for s in sessions:
                    p_dict["sessions"].append({
                        "id": s.id,
                        "day": s.day,
                        "focus": s.focus,
                        "details": s.details,
                        "session_order": s.session_order,
                    })
                result["phases"].append(p_dict)

            return result
        except Exception as e:
            logger.error(f"Error fetching training plan {plan_id}: {e}")
            return None