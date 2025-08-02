# app/core/dependencies.py

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.core.security import (
    decode_token,
    get_current_user_email as _get_current_user_email,
    get_current_user_optional as _get_current_user_optional,
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency: decode and return full token payload."""
    try:
        logger.debug(f"Verifying token: {credentials.credentials[:20]}...")
        payload = decode_token(credentials.credentials)
        logger.debug(f"Token payload: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI dependency: return the `email` claim from a Bearer token."""
    try:
        logger.debug(f"🔍 AUTH DEPENDENCY: Starting token validation")
        logger.debug(f"🔍 AUTH DEPENDENCY: Token present: {credentials.credentials[:20] if credentials else 'None'}...")
        
        payload = decode_token(credentials.credentials)
        logger.debug(f"🔍 AUTH DEPENDENCY: Token decoded successfully")
        logger.debug(f"🔍 AUTH DEPENDENCY: Payload keys: {list(payload.keys())}")
        
        email = payload.get("email")
        
        if not email:
            logger.error("❌ AUTH DEPENDENCY: Token payload missing email field")
            logger.error(f"❌ AUTH DEPENDENCY: Full payload: {payload}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing email",
            )
        
        logger.debug(f"✅ AUTH DEPENDENCY: Successfully extracted email: '{email}'")
        return email
        
    except HTTPException as http_ex:
        logger.error(f"❌ AUTH DEPENDENCY: HTTP Exception: {http_ex.status_code} - {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ AUTH DEPENDENCY: Unexpected error: {e}")
        logger.error(f"❌ AUTH DEPENDENCY: Credentials: {credentials}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """FastAPI dependency: `email` if token present and valid, else None."""
    if not credentials:
        return None
        
    try:
        payload = decode_token(credentials.credentials)
        return payload.get("email")
    except Exception as e:
        logger.warning(f"Optional token validation failed: {e}")
        return None