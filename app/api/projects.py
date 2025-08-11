# app/api/projects.py

from fastapi import APIRouter, HTTPException, Depends, Body, Response
from typing import List
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, Project as DBProject, ProjectLog as DBProjectLog
from app.models.project import (
    ProjectCreate,
    ProjectUpdate,
    Project,
    ProjectLogCreate,
    ProjectLog,
    ProjectLogUpdate,
)
from app.core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/detail/{project_id}", response_model=Project)
def get_project_detail(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user_email)
):
    """
    Get detailed information for a single project by its ID.
    Includes all associated logs.
    """
    try:
        # Normalize to lowercase so DB lookup always matches
        project_id = project_id.lower()

        # Get the project
        project = db.query(DBProject).filter(DBProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get the user who owns this project
        user = db.query(User).filter(User.id == project.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Project owner not found")

        # Verify ownership
        if user.email.strip().lower() != current_user.strip().lower():
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Build response model
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
            logs=[
                ProjectLog(
                    id=log.id,
                    project_id=log.project_id,
                    date=log.date.isoformat(),
                    content=log.content,
                    mood=log.mood,
                    created_at=log.created_at.isoformat()
                )
                for log in sorted(project.logs, key=lambda l: l.date, reverse=True)
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_project_detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/logs/{log_id}", response_model=ProjectLog)
def update_log_entry(
    log_id: str,
    log_data: ProjectLogUpdate = Body(...),
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Update a project log.  Only the owner of the project can edit its logs.
    """
    log_id = log_id.lower()

    # Find the log and its project
    log = db.query(DBProjectLog).filter(DBProjectLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")

    project = db.query(DBProject).filter(DBProject.id == log.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Associated project not found")

    user = db.query(User).filter(User.id == project.user_id).first()
    if not user or user.email.lower() != current_user.lower():
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Update fields if provided
    if log_data.date is not None:
        try:
            log.date = datetime.fromisoformat(log_data.date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format; use ISO8601")
    if log_data.content is not None:
        log.content = log_data.content
    if log_data.mood is not None:
        log.mood = log_data.mood

    db.add(log)
    try:
        db.commit()
        db.refresh(log)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update log entry")

    return ProjectLog(
        id=log.id,
        project_id=log.project_id,
        date=log.date.isoformat(),
        content=log.content,
        mood=log.mood,
        created_at=log.created_at.isoformat(),
    )

@router.delete("/logs/{log_id}", status_code=204)
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
    
    logger.info(f"Looking for log entry with ID: {log_id}")
    logger.info(f"Current user: {current_user}")

    # Get the log entry
    log = db.query(DBProjectLog).filter(DBProjectLog.id == log_id).first()
    if not log:
        logger.error(f"Log entry not found with ID: {log_id}")
        raise HTTPException(status_code=404, detail="Log entry not found")

    logger.info(f"Found log entry for project_id: {log.project_id}")

    # Get the project to verify ownership
    project = db.query(DBProject).filter(DBProject.id == log.project_id).first()
    if not project:
        logger.error(f"Associated project not found with ID: {log.project_id}")
        raise HTTPException(status_code=404, detail="Associated project not found")

    logger.info(f"Found project: {project.route_name}, user_id: {project.user_id}")

    # Get the user who owns this project
    user = db.query(User).filter(User.id == project.user_id).first()
    if not user:
        logger.error(f"Project owner not found with user_id: {project.user_id}")
        raise HTTPException(status_code=404, detail="Project owner not found")

    logger.info(f"Project owner email: {user.email}")

    # DEBUG LOGGING - ADD THIS
    logger.info(f"🔍 AUTH DEBUG:")
    logger.info(f"🔍 JWT email (current_user): '{current_user}'")
    logger.info(f"🔍 Project owner email: '{user.email}'")
    logger.info(f"🔍 Project user_id: {project.user_id}")
    logger.info(f"🔍 Found user id: {user.id}")

    # Verify ownership - compare emails (both normalized to lowercase)
    if user.email.lower() != current_user.lower():
        logger.warning(f"Authorization failed: project owner email '{user.email}' != current user '{current_user}'")
        raise HTTPException(status_code=403, detail="Unauthorized")

    logger.info("Authorization successful - deleting log entry")

    # Delete the log
    db.delete(log)
    try:
        db.commit()
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting log entry: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete log entry")

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
            logs=[
                ProjectLog(
                    id=log.id,
                    project_id=log.project_id,
                    date=log.date.isoformat(),
                    content=log.content,
                    mood=log.mood,
                    created_at=log.created_at.isoformat()
                )
                for log in sorted(project.logs, key=lambda l: l.date, reverse=True)
            ]
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
        logs=[
            ProjectLog(
                id=log.id,
                project_id=log.project_id,
                date=log.date.isoformat(),
                content=log.content,
                mood=log.mood,
                created_at=log.created_at.isoformat()
            )
            for log in sorted(project.logs, key=lambda l: l.date, reverse=True)
        ]
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
    project.updated_at = datetime.now(timezone.utc)
    
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