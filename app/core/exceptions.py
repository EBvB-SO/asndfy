# core/dependencies.py
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
from datetime import datetime
import os

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token from Authorization header"""
    token = credentials.credentials
    
    try:
        # Use the SECRET_KEY from environment or auth.py
        SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        if not SECRET_KEY:
            raise RuntimeError("Missing JWT_SECRET_KEY environment variable")

        
        payload = jwt.decode(
            token, 
            SECRET_KEY,
            algorithms=["HS256"]
        )
        
        # Check expiration
        if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
            raise HTTPException(status_code=401, detail="Token expired")
            
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_email(token_payload: dict = Depends(verify_token)) -> str:
    """Extract user email from verified token"""
    email = token_payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return email

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[str]:
    """Get current user email if token is provided, None otherwise"""
    if not credentials:
        return None
    
    try:
        token_payload = verify_token(credentials)
        return token_payload.get("email")
    except:
        return None