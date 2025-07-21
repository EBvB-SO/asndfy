# app/api/training_plans.py

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import logging
import uuid
import json

from app.models.training_plan import (
    PhasePlanRequest,
    FullPlanRequest,
    TrainingPlan
)

import app.db.db_access as db
from app.services.plan_generator import PlanGeneratorService
from app.core.dependencies import get_current_user_email
from app.core.redis import redis_client
from app.api._background import generate_plan_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training_plans", tags=["Training Plans"])

@router.get("/test")
def test_endpoint():
    logger.info("Test endpoint hit!")
    return {"status": "ok", "message": "Backend is reachable"}

@router.get("/test_background")
async def test_background():
    try:
        from app.api._background import generate_plan_background
        return {"status": "import successful"}
    except Exception as e:
        return {"status": "import failed", "error": str(e)}

# Initialize the plan generator service
plan_generator = PlanGeneratorService()


@router.post("/generate_preview")
def generate_plan_preview(
    data: PhasePlanRequest,
    current_user: str = Depends(get_current_user_email)  # require valid JWT
):
    """Generate a lightweight preview with route analysis and training approach."""
    logger.info(f"Received preview request from {current_user}")
    logger.info(f"Route: {data.route}, Grade: {data.grade}, Crag: {data.crag}")
    try:
        preview = plan_generator.generate_preview(data)
        logger.info("Preview generated successfully")
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

@router.post("/generate_full_async")
async def generate_full_plan_async(
    request: FullPlanRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user_email)
):
    """Start plan generation and return immediately with a task ID"""
    logger.info(f"Received full plan request from {current_user}")
    logger.info(f"Request data: {request.dict()}")
    logger.info(f"Weeks: {request.weeks_to_train}, Sessions: {request.sessions_per_week}")
    
    task_id = str(uuid.uuid4())
    
    # Initialize status in Redis
    await redis_client.set(
        f"plan_generation:{task_id}",
        json.dumps({"status": "processing", "progress": 0}),
        ex=600  # expire in 10 minutes
    )

    try:
        # Test that we can create the service
        test_service = PlanGeneratorService()
        logger.info(f"PlanGeneratorService created successfully")
    except Exception as e:
        logger.error(f"Failed to create PlanGeneratorService: {e}")
        await redis_client.set(
            f"plan_generation:{task_id}",
            json.dumps({"status": "error", "message": str(e)}),
            ex=600
        )
        return {"task_id": task_id, "error": "Service initialization failed"}

    # Queue the actual generation in the background
    background_tasks.add_task(
        generate_plan_background,
        task_id,
        request,
        current_user
    )

    return {"task_id": task_id}


@router.get("/plan_status/{task_id}")
async def get_plan_status(
    task_id: str,
    current_user: str = Depends(get_current_user_email)
):
    """Check the status of a plan generation task"""
    status_data = await redis_client.get(f"plan_generation:{task_id}")
    if not status_data:
        raise HTTPException(404, "Task not found")

    return json.loads(status_data)

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