# app/main.py

import os
import sys
import logging
import time
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.redis import redis_client

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
from app.api.exercise_history     import router as history_router

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO) 

# --- Configure logging ---
# logging.basicConfig(
    # level    = logging.DEBUG,
    # format   = "%(asctime)s %(name)s %(levelname)s %(message)s",
    # handlers = [
        # logging.StreamHandler(),
        # logging.FileHandler("app.log", mode="a")
    # ]
# )
# logger = logging.getLogger("ascendify")

# === Hook root handlers into Uvicorn’s loggers ===
# root_logger    = logging.getLogger()
# uvicorn_error  = logging.getLogger("uvicorn.error")
# uvicorn_access = logging.getLogger("uvicorn.access")

# Attach every handler the root logger has, into uvicorn.error & uvicorn.access
# for handler in root_logger.handlers:
    # uvicorn_error.addHandler(handler)
    # uvicorn_access.addHandler(handler)

# Make sure both Uvicorn loggers show DEBUG+ messages
# uvicorn_error.setLevel(logging.DEBUG)
# uvicorn_access.setLevel(logging.DEBUG)

# --- Create FastAPI app ---
app = FastAPI(
    title       = "AscendifyAI API",
    version     = "2.0.0",
    description = "API for personalized climbing training plans"
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    # Log the incoming request
    body = await request.body()
    logger.info(f"📥 Incoming request: {request.method} {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    if body:
        logger.info(f"Body size: {len(body)} bytes")

    # Reset body for the actual handler
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Request completed in {process_time:.3f}s with status {response.status_code}")
    
    return response

# --- Validation‐error handler (logs raw body + errors) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = await request.body()
    logger.error(
        f"\n❗️ Validation error for {request.url.path}\n"
        f"Raw JSON was:\n{raw_body.decode('utf-8')}\n"
        f"Errors:\n{exc.errors()!r}"
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# --- CORS (allow your frontend origin here) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
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
app.include_router(history_router,            tags=["Exercise History"])

# --- Startup event: migrations, Redis, env var checks ---
@app.on_event("startup")
async def startup_event():
    logger.info("Starting AscendifyAI API")

    # 1) Check required env vars
    env_ok = {
        "DATABASE_URL":    bool(os.getenv("DATABASE_URL")),
        "OPENAI_API_KEY":  bool(os.getenv("OPENAI_API_KEY")),
        "JWT_SECRET_KEY":  bool(os.getenv("JWT_SECRET_KEY")),
    }
    logger.info(f"Env configuration: {env_ok}")

    # 2) Run Alembic migrations if DATABASE_URL is set
    if os.getenv("DATABASE_URL"):
        try:
            logger.info("Applying Alembic migrations (upgrade head)")
            from alembic.config import Config
            from alembic import command

            project_root     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            alembic_ini_path = os.path.join(project_root, "alembic.ini")
            alembic_cfg      = Config(alembic_ini_path)
            # alembic_cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Migrations applied successfully")
        except Exception as e:
            logger.error(f"❌ Failed to run migrations: {e}")
    else:
        logger.error("DATABASE_URL is not set → skipping migrations")

    # 3) Check Redis connectivity
    try:
        await redis_client.ping()
        logger.info("✅ Redis connection OK")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")

    # 4) Warn if OpenAI key is missing
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set → plan generation will fail")

# --- Root & health endpoints ---
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