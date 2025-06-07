# app/main.py

import os
import sys
import logging
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env into os.environ
load_dotenv()

# Allow imports from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Routers ---
from app.api.authentication       import router as auth_router
from app.api.users                import router as users_router
from app.api.projects             import router as projects_router
from app.api.training_plans       import router as plans_router
from app.api.daily_notes          import router as notes_router
from app.api.badges               import router as badges_router
from app.api.sessions             import router as sessions_router
from app.api.exercise_tracking    import router as exercise_tracking_router

# --- Configure logging ---
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a")
    ]
)
logger = logging.getLogger("ascendify")

# --- Create FastAPI app ---
app = FastAPI(
    title       = "AscendifyAI API",
    version     = "2.0.0",
    description = "API for personalized climbing training plans"
)

# --- CORS (allow your frontend origin here) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins   = ["*"],
    allow_credentials = True,
    allow_methods   = ["*"],
    allow_headers   = ["*"],
)

# --- Include all routers ---
app.include_router(auth_router,               tags=["Authentication"])
app.include_router(users_router,              tags=["Users"])
app.include_router(projects_router,           tags=["Projects"])
app.include_router(plans_router,              tags=["Training Plans"])
app.include_router(notes_router,              tags=["Daily Notes"])
app.include_router(badges_router,             tags=["Badges"])
app.include_router(sessions_router,           tags=["Session Tracking"])
app.include_router(exercise_tracking_router,  tags=["Exercise Tracking"])


@app.on_event("startup")
async def startup_event():
    """
    On startup, either auto‐create the DB in dev mode or run Alembic migrations in prod.
    """
    logger.info("Starting AscendifyAI API")

    # 1) Check required env vars
    env_ok = {
        "DATABASE_URL":    bool(os.getenv("DATABASE_URL")),
        "OPENAI_API_KEY":  bool(os.getenv("OPENAI_API_KEY")),
        "JWT_SECRET_KEY":  bool(os.getenv("JWT_SECRET_KEY")),
    }
    logger.info(f"Env configuration: {env_ok}")

    if not os.getenv("DATABASE_URL"):
        logger.error("DATABASE_URL is not set → skipping migrations")
        return

    # 2) Run Alembic migrations
    try:
        logger.info("Applying Alembic migrations (upgrade head)")
        from alembic.config import Config
        from alembic import command

        project_root     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        alembic_ini_path = os.path.join(project_root, "alembic.ini")
        alembic_cfg      = Config(alembic_ini_path)

        # override URL if needed:
        # alembic_cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations applied successfully")
    except Exception as e:
        logger.error(f"❌ Failed to run migrations: {e}")

    # 3) Warn if OpenAI key missing
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set → plan generation will fail")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to AscendifyAI API",
        "status":  "online",
        "version": app.version,
        "docs":    "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host     = os.getenv("HOST", "127.0.0.1"),
        port     = int(os.getenv("PORT", 8001)),
        reload   = True
    )
