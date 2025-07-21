# app/api/_background.py
"""
Background task module for generating full training plans without circular imports.
"""
import logging
import json
import asyncio

from app.services.plan_generator import PlanGeneratorService
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
    import logging
    file_handler = logging.FileHandler('background_task.log')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    logger.info(f"[{task_id}] Background task started")
   
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
   
    try:
        # Create new DB session for this thread
        from app.core.database import SessionLocal
        from contextlib import contextmanager
       
        @contextmanager
        def get_thread_db_session():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
       
        # Monkey-patch the session getter for this thread
        import app.db.db_access
        app.db.db_access.get_db_session = get_thread_db_session
       
        # Initialize service with proper context for background thread
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
       
        from app.services.plan_generator import PlanGeneratorService
        service = PlanGeneratorService()
       
        def update_progress(current: int, total: int):
            pct = int(current / total * 100)
            logger.info(f"[{task_id}] progress: {pct}% ({current}/{total})")
           
            loop.run_until_complete(
                redis_client.set(
                    f"plan_generation:{task_id}",
                    json.dumps({"status": "processing", "progress": pct}),
                    ex=600
                )
            )
       
        logger.info(f"[{task_id}] starting background plan generation for {user_email}")
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
        logger.error(f"[{task_id}] Plan generation failed: {str(e)}", exc_info=True)
        loop.run_until_complete(
            redis_client.set(
                f"plan_generation:{task_id}",
                json.dumps({"status": "error", "message": str(e)}),
                ex=600
            )
        )
    finally:
        loop.close()