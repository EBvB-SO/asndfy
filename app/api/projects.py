# app/api/projects.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
import logging
from datetime import datetime

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, Project as DBProject, ProjectLog as DBProjectLog
from app.models.project import (
    ProjectCreate,
    ProjectUpdate,
    Project,
    ProjectLogCreate,
    ProjectLog
)
from app.core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/{email}", response_model=List[Project])
def get_projects(
    email: str, 
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all projects for a user by email."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Use SQLAlchemy ORM
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get projects with their logs (logs are loaded via relationship)
    projects = db.query(DBProject).filter(DBProject.user_id == user.id).all()
    
    # Convert to response model
    result = []
    for project in projects:
        project_dict = Project(
            id=project.id,
            user_id=project.user_id,
            route_name=project.route_name,
            grade=project.grade,
            crag=project.crag,
            description=project.description or "",
            route_angle=project.route_angle,
            route_length=project.route_length,
            hold_type=project.hold_type,
            is_completed=project.is_completed,
            completion_date=project.completion_date.isoformat() if project.completion_date else None,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            logs=[ProjectLog(
                id=log.id,
                project_id=log.project_id,
                date=log.date.isoformat(),
                content=log.content,
                mood=log.mood,
                created_at=log.created_at.isoformat()
            ) for log in project.logs]
        )
        result.append(project_dict)
    
    return result


@router.post("/{email}", response_model=Project)
def create_project(
    email: str,
    project_data: ProjectCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Create a new project."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create project
    new_project = DBProject(
        id=str(uuid.uuid4()),
        user_id=user.id,
        **project_data.dict()
    )
    db.add(new_project)
    
    try:
        db.commit()
        db.refresh(new_project)
        
        # Convert to response model
        return Project(
            id=new_project.id,
            user_id=new_project.user_id,
            route_name=new_project.route_name,
            grade=new_project.grade,
            crag=new_project.crag,
            description=new_project.description or "",
            route_angle=new_project.route_angle,
            route_length=new_project.route_length,
            hold_type=new_project.hold_type,
            is_completed=new_project.is_completed,
            completion_date=None,
            created_at=new_project.created_at.isoformat(),
            updated_at=new_project.updated_at.isoformat(),
            logs=[]
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=400, detail="Failed to create project")


@router.get("/{email}/{project_id}", response_model=Project)
def get_project(
    email: str,
    project_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get a specific project with its logs."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get project and verify ownership
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert to response model
    return Project(
        id=project.id,
        user_id=project.user_id,
        route_name=project.route_name,
        grade=project.grade,
        crag=project.crag,
        description=project.description or "",
        route_angle=project.route_angle,
        route_length=project.route_length,
        hold_type=project.hold_type,
        is_completed=project.is_completed,
        completion_date=project.completion_date.isoformat() if project.completion_date else None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        logs=[ProjectLog(
            id=log.id,
            project_id=log.project_id,
            date=log.date.isoformat(),
            content=log.content,
            mood=log.mood,
            created_at=log.created_at.isoformat()
        ) for log in project.logs]
    )


@router.put("/{email}/{project_id}")
def update_project(
    email: str,
    project_id: str,
    project_data: ProjectUpdate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Update a project."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get project and verify ownership
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update project fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    # Update the updated_at timestamp
    project.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"success": True, "message": "Project updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=400, detail="Failed to update project")


@router.delete("/{email}/{project_id}")
def delete_project(
    email: str,
    project_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Delete a project."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get project and verify ownership
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete the project (logs will be cascade deleted)
    db.delete(project)
    
    try:
        db.commit()
        return {"success": True, "message": "Project deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete project")


# Project Log endpoints

@router.post("/{email}/{project_id}/logs", response_model=ProjectLog)
def add_project_log(
    email: str,
    project_id: str,
    log_data: ProjectLogCreate,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Add a log entry to a project."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify project ownership
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create log entry
    new_log = DBProjectLog(
        id=str(uuid.uuid4()),
        project_id=project_id,
        date=datetime.fromisoformat(log_data.date.replace('Z', '+00:00')),
        content=log_data.content,
        mood=log_data.mood
    )
    db.add(new_log)
    
    try:
        db.commit()
        db.refresh(new_log)
        
        return ProjectLog(
            id=new_log.id,
            project_id=new_log.project_id,
            date=new_log.date.isoformat(),
            content=new_log.content,
            mood=new_log.mood,
            created_at=new_log.created_at.isoformat()
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding project log: {e}")
        raise HTTPException(status_code=400, detail="Failed to add log entry")


@router.delete("/{email}/{project_id}/logs/{log_id}")
def delete_project_log(
    email: str,
    project_id: str,
    log_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Delete a project log entry."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()
    log_id = log_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify project ownership
    project = (
        db.query(DBProject)
        .filter(DBProject.id == project_id, DBProject.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get and delete the log
    log = db.query(DBProjectLog).filter(DBProjectLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    db.delete(log)
    
    try:
        db.commit()
        return {"success": True, "message": "Log entry deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting log entry: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete log entry")


# --- New endpoints to match Swift client calls ---

@router.get("/detail/{project_id}", response_model=Project)
def get_project_detail(
    project_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Get a project (with logs) by its ID, without the email in the path.
    """
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    # Get the project
    project = db.query(DBProject).filter(DBProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify ownership
    user = db.query(User).filter(User.email == current_user).first()
    if not user or project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Convert to response model
    return Project(
        id=project.id,
        user_id=project.user_id,
        route_name=project.route_name,
        grade=project.grade,
        crag=project.crag,
        description=project.description or "",
        route_angle=project.route_angle,
        route_length=project.route_length,
        hold_type=project.hold_type,
        is_completed=project.is_completed,
        completion_date=project.completion_date.isoformat() if project.completion_date else None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        logs=[ProjectLog(
            id=log.id,
            project_id=log.project_id,
            date=log.date.isoformat(),
            content=log.content,
            mood=log.mood,
            created_at=log.created_at.isoformat()
        ) for log in project.logs]
    )


@router.delete("/logs/{log_id}")
def delete_log_entry(
    log_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Delete a log entry by its ID, without needing the project/email in the path.
    """
    # normalize to lowercase so DB lookup always matches
    log_id = log_id.lower()

    # Get the log entry
    log = db.query(DBProjectLog).filter(DBProjectLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")

    # Get the project to verify ownership
    project = db.query(DBProject).filter(DBProject.id == log.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Associated project not found")

    # Verify user owns the project
    user = db.query(User).filter(User.email == current_user).first()
    if not user or project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Delete the log
    db.delete(log)
    
    try:
        db.commit()
        return {"success": True, "message": "Log entry deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting log entry: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete log entry")