# app/main.py

from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your services & routers
from app.services import email_service

from app.api.authentication import router as auth_router
from app.api.users import router as users_router
from app.api.projects import router as projects_router
from app.api.training_plans import router as plans_router
from app.api.daily_notes import router as notes_router
from app.api.badges import router as badges_router
from app.api.exercise_tracking import router as exercise_tracking_router

# Legacy routers (if you still need them)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api.sessions import router as session_router
from app.api.exercises import router as exercise_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a")
    ]
)
logger = logging.getLogger("ascendify")

# Initialize FastAPI app
app = FastAPI(
    title="AscendifyAI API",
    version="2.0.0",
    description="API for personalized climbing training plans"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, lock this down to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(users_router, tags=["Users"])
app.include_router(projects_router, tags=["Projects"])
app.include_router(plans_router, tags=["Training Plans"])
app.include_router(notes_router, tags=["Daily Notes"])
app.include_router(badges_router, tags=["Badges"])
app.include_router(session_router, tags=["Sessions"])
app.include_router(exercise_router, tags=["Exercises"])
app.include_router(exercise_tracking_router, tags=["Exercise Tracking"])


@app.on_event("startup")
async def startup_event():
    """
    On startup, either run the dev “create_all + seed” path
    (if DB_AUTO_CREATE=True) or apply Alembic migrations (production).
    """
    logger.info("Starting AscendifyAI API")

    # 1) Log environment configuration
    env_config = {
        "OPENAI_API_KEY":       bool(os.getenv("OPENAI_API_KEY")),
        "DATABASE_URL":         bool(os.getenv("DATABASE_URL")),
        "SENDGRID_API_KEY":     bool(os.getenv("SENDGRID_API_KEY")),
        "JWT_SECRET_KEY":       bool(os.getenv("JWT_SECRET_KEY")),
        "DB_AUTO_CREATE":       os.getenv("DB_AUTO_CREATE", "False"),
        "LOG_LEVEL":            os.getenv("LOG_LEVEL", "INFO"),
    }
    logger.info(f"Environment configuration: {env_config}")

    # 2) If DATABASE_URL is not set, skip DB work
    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL is not set. Skipping database initialization.")
        return

    # 3) If DB_AUTO_CREATE=True, run scripts/init_database.py (dev mode only)
    # if os.getenv("DB_AUTO_CREATE", "False").lower() in ("1", "true", "yes"):
        # try:
            # logger.info("DEV MODE: creating tables (Base.metadata.create_all) and seeding data")
            # from scripts.init_database import main as init_db
            # init_db()
        # except Exception as e:
            # logger.error(f"❌ Error in DEV auto database creation: {e}")

    # 4) Otherwise, run Alembic migrations (production)
    else:
        try:
            logger.info("PROD MODE: applying Alembic migrations (upgrade head)")
            from alembic.config import Config
            from alembic import command

            # Build path to alembic.ini (one level up from app/)
            project_root     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            alembic_ini_path = os.path.join(project_root, "alembic.ini")
            alembic_cfg      = Config(alembic_ini_path)

            # (Optional) Force‐override the URL if needed:
            # alembic_cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Alembic migrations applied successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to apply Alembic migrations: {e}")

    # 5) Check OpenAI key validity
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set → plan generation will not work")


@app.get("/")
async def root():
    return {
        "message": "Welcome to AscendifyAI API",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
