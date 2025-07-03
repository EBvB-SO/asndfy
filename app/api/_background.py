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

    This will stream progress to Redis under the key "plan_generation:{task_id}"
    so that clients can poll /plan_status/{task_id}.
    """
    service = PlanGeneratorService()

    def on_progress(current: int, total: int):
        pct = int(current / total * 100)
        logger.info(f"[{task_id}] progress: {pct}% ({current}/{total})")
        # Because redis_client is async, we need to schedule it in the event loop:
        asyncio.get_event_loop().create_task(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "processing", "progress": pct}),
                ex=600
            )
        )

    try:
        logger.info(f"[{task_id}] starting background plan generation for {user_email}")
        # This will invoke on_progress() after each phase
        plan = service.generate_full_plan(request, on_progress=on_progress)

        logger.info(f"[{task_id}] generation complete, saving final result")
        # store the final payload in Redis (or you could persist to DB here)
        asyncio.get_event_loop().run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "complete", "progress": 100, "plan": plan}),
                ex=600
            )
        )

    except Exception as e:
        logger.error(f"[{task_id}] failed to generate plan: {e}", exc_info=True)
        # mark as error
        asyncio.get_event_loop().run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "error", "message": str(e)}),
                ex=600
            )
        )
