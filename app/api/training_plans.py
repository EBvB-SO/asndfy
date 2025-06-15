# app/api/training_plans.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
import uuid

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User, TrainingPlan as DBTrainingPlan, PlanPhase, PlanSession
from app.models.training_plan import (
    PhasePlanRequest,
    FullPlanRequest,
    TrainingPlan,
    PlanPhaseBase,
    PlanSessionBase
)
from app.services.plan_generator import PlanGeneratorService
from app.core.dependencies import get_current_user_email

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
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get all training plans for a user."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user using SQLAlchemy ORM
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all training plans for the user
    plans = db.query(DBTrainingPlan).filter(DBTrainingPlan.user_id == user.id).all()
    
    # Convert to response models
    result = []
    for plan in plans:
        # Get phases for this plan
        phases = []
        db_phases = (
            db.query(PlanPhase)
            .filter(PlanPhase.plan_id == plan.id)
            .order_by(PlanPhase.phase_order)
            .all()
        )
        
        for phase in db_phases:
            # Get sessions for this phase
            sessions = (
                db.query(PlanSession)
                .filter(PlanSession.phase_id == phase.id)
                .order_by(PlanSession.session_order)
                .all()
            )
            
            weekly_schedule = [
                PlanSessionBase(
                    day=session.day,
                    focus=session.focus,
                    details=session.details
                )
                for session in sessions
            ]
            
            phases.append(PlanPhaseBase(
                phase_name=phase.phase_name,
                description=phase.description,
                weekly_schedule=weekly_schedule
            ))
        
        result.append(TrainingPlan(
            id=plan.id,
            user_id=plan.user_id,
            route_name=plan.route_name,
            grade=plan.grade,
            route_overview=plan.route_overview or "",
            training_overview=plan.training_overview or "",
            purchased_at=plan.purchased_at.isoformat(),
            phases=phases
        ))
    
    return result


@router.get("/{email}/{plan_id}")
def get_training_plan(
    email: str,
    plan_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Get a specific training plan with all phases and sessions."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get plan and verify ownership
    plan = (
        db.query(DBTrainingPlan)
        .filter(DBTrainingPlan.id == plan_id, DBTrainingPlan.user_id == user.id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    # Get phases and sessions
    phases = []
    db_phases = (
        db.query(PlanPhase)
        .filter(PlanPhase.plan_id == plan.id)
        .order_by(PlanPhase.phase_order)
        .all()
    )
    
    for phase in db_phases:
        sessions = (
            db.query(PlanSession)
            .filter(PlanSession.phase_id == phase.id)
            .order_by(PlanSession.session_order)
            .all()
        )
        
        phase_dict = {
            "id": phase.id,
            "phase_name": phase.phase_name,
            "description": phase.description,
            "phase_order": phase.phase_order,
            "sessions": [
                {
                    "id": session.id,
                    "day": session.day,
                    "focus": session.focus,
                    "details": session.details,
                    "session_order": session.session_order
                }
                for session in sessions
            ]
        }
        phases.append(phase_dict)
    
    # Return full plan structure
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "route_name": plan.route_name,
        "grade": plan.grade,
        "route_overview": plan.route_overview,
        "training_overview": plan.training_overview,
        "purchased_at": plan.purchased_at.isoformat(),
        "phases": phases
    }


@router.post("/{email}/save")
def save_training_plan(
    email: str,
    plan_data: Dict[str, Any],
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Save a generated training plan."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create the training plan
    new_plan = DBTrainingPlan(
        id=str(uuid.uuid4()),
        user_id=user.id,
        route_name=plan_data.get("route_name", ""),
        grade=plan_data.get("grade", ""),
        route_overview=plan_data.get("route_overview", ""),
        training_overview=plan_data.get("training_overview", "")
    )
    db.add(new_plan)
    db.flush()  # Flush to get the plan ID before adding phases

    # Add phases and sessions
    for phase_order, phase_data in enumerate(plan_data.get("phases", []), start=1):
        new_phase = PlanPhase(
            plan_id=new_plan.id,
            phase_name=phase_data.get("phase_name", ""),
            description=phase_data.get("description", ""),
            phase_order=phase_order
        )
        db.add(new_phase)
        db.flush()  # Flush to get the phase ID

        # Add sessions for this phase
        for session_order, session_data in enumerate(phase_data.get("weekly_schedule", []), start=1):
            new_session = PlanSession(
                phase_id=new_phase.id,
                day=session_data.get("day", ""),
                focus=session_data.get("focus", ""),
                details=session_data.get("details", ""),
                session_order=session_order
            )
            db.add(new_session)

    try:
        db.commit()
        return {
            "success": True,
            "message": "Training plan saved successfully",
            "plan_id": new_plan.id
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving training plan: {e}")
        raise HTTPException(status_code=400, detail="Failed to save training plan")


@router.delete("/{email}/{plan_id}")
def delete_training_plan(
    email: str,
    plan_id: str,
    current_user: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Delete a training plan."""
    if email != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get plan and verify ownership
    plan = (
        db.query(DBTrainingPlan)
        .filter(DBTrainingPlan.id == plan_id, DBTrainingPlan.user_id == user.id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    # Delete the plan (phases and sessions will be cascade deleted)
    db.delete(plan)
    
    try:
        db.commit()
        return {"success": True, "message": "Training plan deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting training plan: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete training plan")