# api/projects.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
import logging
import sys
import os

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the db_access module as "db" so that db.get_user_projects, db.create_project, etc. are available
import db.db_access as db

from models.project import (
    ProjectCreate, 
    ProjectUpdate, 
    Project,
    ProjectLogCreate,
    ProjectLog
)
from core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/{email}", response_model=List[Project])
def get_projects(email: str, current_user: str = Depends(get_current_user_email)):
    """Get all projects for a user by email."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        user_id = user["id"]
        
        # Get projects for this user
        projects = db.get_user_projects(user_id)
        
        return projects

@router.post("/{email}", response_model=Project)
def create_project(
    email: str, 
    project_data: ProjectCreate,
    current_user: str = Depends(get_current_user_email)
):
    """Create a new project."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Create the project
        project_dict = project_data.dict()
        project_dict["id"] = str(uuid.uuid4())
        
        result = db.create_project(user_id, project_dict)
        
        if not result:
            raise HTTPException(status_code=400, detail=result.message)
        
        # Get the created project
        created_project = db.get_project(result.id)
        return created_project

@router.get("/{email}/{project_id}", response_model=Project)
def get_project(
    email: str, 
    project_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Get a specific project with its logs."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Check if project belongs to user
        cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

@router.put("/{email}/{project_id}")
def update_project(
    email: str, 
    project_id: str, 
    project_data: ProjectUpdate,
    current_user: str = Depends(get_current_user_email)
):
    """Update a project."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Update the project
    update_dict = project_data.dict(exclude_unset=True)
    result = db.update_project(project_id, update_dict)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {"success": True, "message": "Project updated successfully"}

@router.delete("/{email}/{project_id}")
def delete_project(
    email: str, 
    project_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Delete a project."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    result = db.delete_project(project_id)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {"success": True, "message": "Project deleted successfully"}

# Project Log endpoints
@router.post("/{email}/{project_id}/logs", response_model=ProjectLog)
def add_project_log(
    email: str, 
    project_id: str, 
    log_data: ProjectLogCreate,
    current_user: str = Depends(get_current_user_email)
):
    """Add a log entry to a project."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Add the log
    log_dict = log_data.dict()
    log_dict["id"] = str(uuid.uuid4())
    
    result = db.add_project_log(project_id, log_dict)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {
        "id": result.id,
        "project_id": project_id,
        **log_dict
    }

@router.delete("/{email}/{project_id}/logs/{log_id}")
def delete_project_log(
    email: str, 
    project_id: str, 
    log_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Delete a project log entry."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        cursor.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    result = db.delete_project_log(log_id)
    
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {"success": True, "message": "Log entry deleted successfully"}