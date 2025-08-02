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

@router.get("/debug/auth-test")
def debug_auth_test(
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Debug endpoint to test authentication and list user's projects"""
    logger.info(f"🔍 Auth debug - current user: {current_user}")
    
    # Get user from database
    user = db.query(User).filter(User.email == current_user).first()
    
    # Get user's projects
    projects = db.query(DBProject).filter(DBProject.user_id == (user.id if user else None)).all()
    
    return {
        "success": True,
        "current_user_email": current_user,
        "user_found_in_db": user is not None,
        "user_id": user.id if user else None,
        "user_projects_count": len(projects),
        "project_ids": [p.id for p in projects] if projects else [],
        "message": "Authentication working correctly"
    }

@router.get("/debug/token-info")
def debug_token_info(
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check token contents."""
    # Find user in database
    user = db.query(User).filter(User.email == current_user).first()
    
    return {
        "jwt_email": current_user,
        "jwt_email_length": len(current_user),
        "jwt_email_bytes": current_user.encode(),
        "db_user_found": user is not None,
        "db_user_email": user.email if user else None,
        "db_user_email_length": len(user.email) if user else None,
        "db_user_email_bytes": user.email.encode() if user else None,
        "emails_match": user.email.lower().strip() == current_user.lower().strip() if user else False
    }

@router.get("/detail/{project_id}", response_model=Project)
def get_project_detail(
   project_id: str,
   db: Session = Depends(get_db),
   current_user: str = Depends(get_current_user_email)
):
   """ULTRA DEBUG VERSION"""
   # IMMEDIATE DEBUG - THIS SHOULD ALWAYS PRINT IF THE FUNCTION IS CALLED
   print("🚨🚨🚨 get_project_detail FUNCTION WAS CALLED! 🚨🚨🚨")
   logger.error("🚨🚨🚨 get_project_detail FUNCTION WAS CALLED! 🚨🚨🚨")
   logger.error(f"🚨 project_id parameter: '{project_id}'")
   logger.error(f"🚨 current_user parameter: '{current_user}'")
   
   try:
       logger.info("=== PROJECT DETAIL REQUEST - STEP BY STEP DEBUG ===")
       logger.info(f"🔍 STEP 1: Function called with project_id: '{project_id}'")

     # Check if we even got past the dependency injection
       logger.info(f"🔍 STEP 2: get_current_user_email dependency resolved successfully")
       logger.info(f"🔍 STEP 2a: current_user = '{current_user}'")
       logger.info(f"🔍 STEP 2b: current_user type = {type(current_user)}")
       logger.info(f"🔍 STEP 2c: current_user length = {len(current_user) if current_user else 'None'}")
       
       # Check database dependency
       logger.info(f"🔍 STEP 3: Database session dependency resolved successfully")
       
       # normalize to lowercase so DB lookup always matches
       project_id = project_id.lower()
       logger.info(f"🔍 STEP 4: Normalized project_id to: '{project_id}'")
       
       # Get the project first
       logger.info(f"🔍 STEP 5: Querying database for project...")
       project = db.query(DBProject).filter(DBProject.id == project_id).first()
       if not project:
           logger.error(f"❌ STEP 5 FAILED: Project not found with ID: {project_id}")
           # Let's also check what projects DO exist
           all_projects = db.query(DBProject).all()
           logger.error(f"❌ Available project IDs in database: {[p.id for p in all_projects[:5]]}")  # Show first 5
           raise HTTPException(status_code=404, detail="Project not found")

       logger.info(f"✅ STEP 5 SUCCESS: Found project: '{project.route_name}', user_id: {project.user_id}")

       # Get the user who owns this project
       logger.info(f"🔍 STEP 6: Looking up project owner with user_id: {project.user_id}")
       user = db.query(User).filter(User.id == project.user_id).first()
       if not user:
           logger.error(f"❌ STEP 6 FAILED: Project owner not found with user_id: {project.user_id}")
           raise HTTPException(status_code=404, detail="Project owner not found")

       logger.info(f"✅ STEP 6 SUCCESS: Project owner found: email='{user.email}', name='{user.name}'")
       
       # DETAILED EMAIL COMPARISON DEBUG
       user_email_clean = user.email.strip().lower()
       current_user_clean = current_user.strip().lower()
       
       logger.info(f"🔍 STEP 7: DETAILED EMAIL COMPARISON:")
       logger.info(f"  📧 Project owner email: '{user.email}' (len={len(user.email)})")
       logger.info(f"  🎫 JWT current user:     '{current_user}' (len={len(current_user)})")
       logger.info(f"  🧹 Cleaned owner:       '{user_email_clean}' (len={len(user_email_clean)})")
       logger.info(f"  🧹 Cleaned current:     '{current_user_clean}' (len={len(current_user_clean)})")
       logger.info(f"  ⚖️  Are they equal?      {user_email_clean == current_user_clean}")
       
       if user_email_clean != current_user_clean:
           logger.error(f"❌ STEP 7 FAILED - AUTHORIZATION MISMATCH:")
           logger.error(f"   Owner: '{user_email_clean}'")
           logger.error(f"   Current: '{current_user_clean}'")
           
           # Byte-by-byte comparison for debugging
           owner_bytes = user_email_clean.encode('utf-8')
           current_bytes = current_user_clean.encode('utf-8')
           logger.error(f"   Owner bytes: {list(owner_bytes)}")
           logger.error(f"   Current bytes: {list(current_bytes)}")
           
           # Character by character comparison
           max_len = max(len(user_email_clean), len(current_user_clean))
           logger.error(f"   Character-by-character comparison:")
           for i in range(max_len):
               owner_char = user_email_clean[i] if i < len(user_email_clean) else "END"
               current_char = current_user_clean[i] if i < len(current_user_clean) else "END"
               match = "✓" if owner_char == current_char else "✗"
               logger.error(f"     [{i:2d}]: '{owner_char}' vs '{current_char}' {match}")
           
           raise HTTPException(status_code=403, detail="Unauthorized")

       logger.info("✅ STEP 7 SUCCESS: EMAIL MATCH - Authorization successful!")

       # Convert to response model
       logger.info(f"🔍 STEP 8: Converting to response model...")
       result_project = Project(
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
       
       logger.info("✅ STEP 8 SUCCESS: Returning project details successfully")
       logger.info("=== PROJECT DETAIL REQUEST COMPLETED SUCCESSFULLY ===")
       return result_project

   except HTTPException as http_ex:
       # Re-raise HTTP exceptions but log them
       logger.error(f"❌ HTTP Exception in get_project_detail: {http_ex.status_code} - {http_ex.detail}")
       raise
   except Exception as e:
       logger.error(f"❌ Unexpected error in get_project_detail: {e}", exc_info=True)
       raise HTTPException(status_code=500, detail="Internal server error")

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
        logger.info("Log entry deleted successfully")
        return {"success": True, "message": "Log entry deleted successfully"}
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