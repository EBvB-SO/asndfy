# services/auth_service.py
import logging
from typing import Optional, Dict, Any
import db.db_access as db
from models.auth_models import SignUpRequest, SignInRequest

logger = logging.getLogger(__name__)

class AuthService:
    """Service layer for authentication operations"""
    
    async def create_user(self, data: SignUpRequest) -> db.DBResult:
        """Create a new user account"""
        return db.create_user(data.name, data.email, data.password)
    
    async def verify_credentials(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user data if valid"""
        result = db.verify_user(email, password)
        if result and result.success:
            return result.data
        return None
    
    async def update_password(self, email: str, new_password: str) -> db.DBResult:
        """Update user password"""
        return db.update_user_password(email, new_password)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data by email"""
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            return dict(user) if user else None