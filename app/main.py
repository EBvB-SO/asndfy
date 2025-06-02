# app/main.py
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import services
from services import email_service
from db import migrations

# Import refactored routers
from app.api.authentication import router as auth_router
from api.users import router as users_router
from api.projects import router as projects_router
from api.training_plans import router as plans_router
from api.daily_notes import router as notes_router
from api.badges import router as badges_router

# Import existing routers that haven't been migrated yet
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.sessions  import router as session_router
from app.exercises import router as exercise_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
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
    allow_origins=["*"],  # Update with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all refactored routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(users_router, tags=["Users"])
app.include_router(projects_router, tags=["Projects"])
app.include_router(plans_router, tags=["Training Plans"])
app.include_router(notes_router, tags=["Daily Notes"])
app.include_router(badges_router, tags=["Badges"])
app.include_router(session_router, tags=["Sessions"])
app.include_router(exercise_router, tags=["Exercises"])

@app.on_event("startup")
async def startup_event():
    """Run database migrations and startup tasks."""
    logger.info("Starting AscendifyAI API")
    
    # Log environment configuration
    env_config = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
        "SENDGRID_API_KEY": bool(os.getenv("SENDGRID_API_KEY")),
        "JWT_SECRET_KEY": bool(os.getenv("JWT_SECRET_KEY")),
        "AUTO_CREATE_MISSING_RESOURCES": os.getenv("AUTO_CREATE_MISSING_RESOURCES", "False"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "DB_TYPE": "PostgreSQL" if os.getenv("DATABASE_URL") else "SQLite"
    }
    logger.info(f"Environment configuration: {env_config}")
    
    # Initialize database if needed
    if os.getenv("DATABASE_URL"):
        try:
            logger.info("Using PostgreSQL database")
            from scripts.init_database import main as init_db
            init_db()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
    
    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not set - plan generation will not work")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to AscendifyAI API", 
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)