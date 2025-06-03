# scripts/setup_database.py
#!/usr/bin/env python
"""
Simple database setup script for fresh PostgreSQL database
Run this to create all tables and initialize data
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine, Base
from app.db.models import *
from scripts.init_database import init_exercises, init_badges
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Create all tables and initialize with default data"""
    try:
        logger.info("Creating database tables...")
        # This creates all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        
        logger.info("Initializing exercises...")
        init_exercises()
        
        logger.info("Initializing badges...")
        init_badges()
        
        logger.info("\n✅ Database setup complete!")
        logger.info("You can now start the application with: uvicorn app.main:app --reload")
        
    except Exception as e:
        logger.error(f"❌ Error setting up database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()