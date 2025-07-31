# Enhanced app/core/dependencies.py with better logging

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
        logger.debug(f"Getting user email from token: {credentials.credentials[:20]}...")
        payload = decode_token(credentials.credentials)
        email = payload.get("email")
        
        if not email:
            logger.error("Token payload missing email field")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing email",
            )
        
        logger.debug(f"Extracted email from token: {email}")
        return email
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting email from token: {e}")
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