# app/api/_background.py
"""
Background task module for generating full training plans without circular imports.
"""
import logging
import json
import asyncio

from services.plan_generator import PlanGeneratorService
from app.models.training_plan import FullPlanRequest
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

def generate_plan_background(
    task_id: str,
    request: FullPlanRequest,
    user_email: str
) -> None:
    """
    Background task to generate a complete training plan.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    service = PlanGeneratorService()
    
    def update_progress(current: int, total: int):
        pct = int(current / total * 100)
        logger.info(f"[{task_id}] progress: {pct}% ({current}/{total})")
        
        # Use run_coroutine_threadsafe for thread-safe async operations
        loop.run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "processing", "progress": pct}),
                ex=600
            )
        )
    
    try:
        logger.info(f"[{task_id}] starting background plan generation for {user_email}")
        logger.info(f"[{task_id}] Starting background generation")
        logger.info(f"[{task_id}] Request data: {request.dict()}")
        
        # Generate the plan
        plan = service.generate_full_plan(request, on_progress=update_progress)
        
        logger.info(f"[{task_id}] generation complete, saving final result")
        
        # Store the final result
        loop.run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "complete", "progress": 100, "plan": plan}),
                ex=600
            )
        )
        
    except Exception as e:
        logger.error(f"[{task_id}] Background task failed: {str(e)}", exc_info=True)
        logger.error(f"[{task_id}] failed to generate plan: {e}", exc_info=True)
        loop.run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "error", "message": str(e)}),
                ex=600
            )
        )
    finally:
        loop.close()
