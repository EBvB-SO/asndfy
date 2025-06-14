# app/api/projects.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
import logging
import sys
import os

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the db_access module as "db" so that db.get_user_projects, db.create_project, etc. are available
import app.db.db_access as db

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
        project_dict = project_data.dict()
        project_dict["id"] = str(uuid.uuid4())
        result = db.create_project(user_id, project_dict)
        if not result:
            raise HTTPException(status_code=400, detail=result.message)

        created_project = db.get_project(result.id)
        return created_project


@router.get("/{email}/{project_id}", response_model=Project)
def get_project(
    email: str,
    project_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Get a specific project with its logs."""
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

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
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

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
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

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
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

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
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()
    log_id     = log_id.lower()

    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

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


# --- New endpoints to match Swift client calls ---

@router.get("/detail/{project_id}", response_model=Project)
def get_project_detail(
    project_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get a project (with logs) by its ID, without the email in the path.
    """
    # normalize to lowercase so DB lookup always matches
    project_id = project_id.lower()

    # 1) Lookup owner
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM projects WHERE id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    owner_id = row["user_id"]

    # 2) Verify ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (current_user,)
        )
        user = cursor.fetchone()
    if not user or user["id"] != owner_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 3) Return the project
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/logs/{log_id}")
def delete_log_entry(
    log_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """
    Delete a log entry by its ID, without needing the project/email in the path.
    """
    # normalize to lowercase so DB lookup always matches
    log_id = log_id.lower()

    # 1) Find its project
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT project_id FROM project_logs WHERE id = ?",
            (log_id,)
        )
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Log entry not found")
    project_id = row["project_id"]

    # 2) Verify project ownership
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT p.id FROM projects p "
            "JOIN users u ON u.id = p.user_id "
            "WHERE p.id = ? AND u.email = ?",
            (project_id, current_user)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Unauthorized")

    # 3) Delete
    result = db.delete_project_log(log_id)
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "message": "Log entry deleted successfully"}
