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

# --- Configure logging FIRST ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s:%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log", mode="a")
    ]
)

# Create main logger
logger = logging.getLogger("ascendify")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Set uvicorn loggers to same level
uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_error.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
uvicorn_access.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Also ensure FastAPI gets proper logging
fastapi_logger = logging.getLogger("fastapi")
fastapi_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

logger.info(f"Logging configured at {LOG_LEVEL} level")

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
    logger.info(f"📥 Incoming request: {request.method} {request.url.path}")
    
    # Only log headers in DEBUG mode to avoid spam
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Headers: {dict(request.headers)}")
    
    # Handle body logging carefully
    body = await request.body()
    if body and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Body size: {len(body)} bytes")
        # Only log first 500 chars of body to avoid huge logs
        if len(body) < 500:
            try:
                logger.debug(f"Body: {body.decode('utf-8')}")
            except UnicodeDecodeError:
                logger.debug("Body: <binary data>")

    # Reset body for the actual handler
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"✅ Request completed in {process_time:.3f}s with status {response.status_code}")
    
    return response

# --- Validation‐error handler (logs raw body + errors) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = await request.body()
    logger.error(
        f"\n❗️ Validation error for {request.url.path}\n"
        f"Raw JSON was:\n{raw_body.decode('utf-8') if raw_body else 'No body'}\n"
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
# Replace your entire startup_event function with this improved version:

# Replace your startup_event with this minimal version to test:

# Now that logging works, let's restore the full startup:

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting AscendifyAI API")

    # 1) Check required env vars
    env_ok = {
        "DATABASE_URL":    bool(os.getenv("DATABASE_URL")),
        "OPENAI_API_KEY":  bool(os.getenv("OPENAI_API_KEY")),
        "JWT_SECRET_KEY":  bool(os.getenv("JWT_SECRET_KEY")),
    }
    logger.info(f"📋 Env configuration: {env_ok}")

    # 3) Check Redis connectivity with timeout
    try:
        import asyncio
        logger.info("🔄 Testing Redis connection...")
        
        await asyncio.wait_for(redis_client.ping(), timeout=5.0)
        logger.info("✅ Redis connection OK")
    except asyncio.TimeoutError:
        logger.warning("⚠️  Redis connection timeout - continuing without Redis")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e} - continuing without Redis")

    # 4) Check OpenAI key
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️  OPENAI_API_KEY not set → plan generation will fail")
    else:
        logger.info("✅ OpenAI API key is configured")

    logger.info("🎉 Application startup complete!")
    logger.info("📚 API docs available at: http://127.0.0.1:8001/docs")

@app.get("/debug-logs", tags=["Debug"])
async def debug_logs():
    """Test endpoint to verify logging is working"""
    import logging
    
    # Test different logger types
    main_logger = logging.getLogger("ascendify")
    uvicorn_logger = logging.getLogger("uvicorn.error")
    root_logger = logging.getLogger()
    
    # Force log messages at different levels
    main_logger.debug("🐛 DEBUG: This is a debug message from main_logger")
    main_logger.info("ℹ️  INFO: This is an info message from main_logger")
    main_logger.warning("⚠️  WARNING: This is a warning message from main_logger")
    
    uvicorn_logger.info("ℹ️  INFO: This is from uvicorn_logger")
    root_logger.info("ℹ️  INFO: This is from root_logger")
    
    # Also test print (should always work)
    print("🖨️  PRINT: This should always appear in console", flush=True)
    
    return {
        "message": "Debug logs sent - check your console!",
        "loggers_tested": ["ascendify", "uvicorn.error", "root"],
        "log_levels": ["DEBUG", "INFO", "WARNING"]
    }

# --- Root & health endpoints ---
@app.get("/", tags=["Root"])
async def root():
    logger.info("📍 Root endpoint accessed")
    return {
        "message": "Welcome to AscendifyAI API",
        "status":  "online",
        "version": app.version,
        "docs":    "/docs"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    logger.info("🏥 Health check endpoint accessed")
    return {"status": "healthy"}