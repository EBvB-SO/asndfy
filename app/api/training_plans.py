# app/api/training_plans.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from models.training_plan import (
    PhasePlanRequest,
    FullPlanRequest,
    TrainingPlan
)

import db.db_access as db
from services.plan_generator import PlanGeneratorService
from core.dependencies import get_current_user_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training_plans", tags=["Training Plans"])

# Initialize the plan generator service
plan_generator = PlanGeneratorService()


@router.post("/generate_preview")
def generate_plan_preview(
    data: PhasePlanRequest,
    current_user: str = Depends(get_current_user_email)  # require valid JWT
):
    """Generate a lightweight preview with route analysis and training approach."""
    try:
        preview = plan_generator.generate_preview(data)
        return preview
    except Exception as e:
        logger.error(f"Error generating plan preview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating preview: {str(e)}"
        )


@router.post("/generate_full")
def generate_full_plan(
    request: FullPlanRequest,
    current_user: str = Depends(get_current_user_email)  # require valid JWT
):
    """Generate a complete training plan with phases."""
    try:
        plan = plan_generator.generate_full_plan(request)
        return plan
    except Exception as e:
        logger.error(f"Error generating plan: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating plan: {str(e)}"
        )


@router.get("/{email}", response_model=List[TrainingPlan])
def get_training_plans(
    email: str,
    current_user: str = Depends(get_current_user_email)
):
    """Get all training plans for a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user["id"]
        plans = db.get_user_training_plans(user_id)
        return plans


@router.get("/{email}/{plan_id}")
def get_training_plan(
    email: str,
    plan_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Get a specific training plan with all phases and sessions."""
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
            "SELECT id FROM training_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Training plan not found")

    plan = db.get_training_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return plan


@router.post("/{email}/save")
def save_training_plan(
    email: str,
    plan_data: dict,
    current_user: str = Depends(get_current_user_email)
):
    """Save a generated training plan."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user["id"]

        # Extract plan info and phases
        plan_info = {
            "route_name": plan_data.get("route_name", ""),
            "grade": plan_data.get("grade", ""),
            "route_overview": plan_data.get("route_overview", ""),
            "training_overview": plan_data.get("training_overview", "")
        }
        phases = plan_data.get("phases", [])

        # Save the plan
        result = db.create_training_plan(user_id, plan_info, phases)
        if not result:
            raise HTTPException(status_code=400, detail=result.message)

        return {
            "success": True,
            "message": "Training plan saved successfully",
            "plan_id": result.id
        }


@router.delete("/{email}/{plan_id}")
def delete_training_plan(
    email: str,
    plan_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Delete a training plan."""
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
            "SELECT id FROM training_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Training plan not found")

    result = db.delete_training_plan(plan_id)
    if not result:
        raise HTTPException(status_code=400, detail=result.message)

    return {"success": True, "message": "Training plan deleted successfully"}
