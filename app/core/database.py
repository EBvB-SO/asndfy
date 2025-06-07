# app/core/database.py

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# DATABASE URL & ENGINE SETUP
# ---------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Environment variable DATABASE_URL is not set. "
        "Please add a .env file with:\n"
        "    DATABASE_URL=postgresql://<your_user>@localhost:5432/asndfy_db"
    )

# Convert old‐style “postgres://” URIs if necessary:
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ---------------------------------------------------
# SESSION FACTORY & BASE CLASS
# ---------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ---------------------------------------------------
# CONTEXT MANAGER FOR SESSIONS
# ---------------------------------------------------

@contextmanager
def get_db_session():
    """
    Context‐manager for SQLAlchemy sessions.
    Use like:
        with get_db_session() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------
# FASTAPI DEPENDENCY (if you’re using FastAPI)
# ---------------------------------------------------

def get_db():
    """
    FastAPI dependency to yield a SQLAlchemy session.
    Use in your route functions as:
        def some_route(..., db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
