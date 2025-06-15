# core/dependencies.py
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.core.security import (
    decode_token,
    get_current_user_email as _get_current_user_email,
    get_current_user_optional as _get_current_user_optional,
)

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency: decode and return full token payload."""
    return decode_token(credentials.credentials)

def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI dependency: return the `email` claim from a Bearer token."""
    return _get_current_user_email(credentials)

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """FastAPI dependency: `email` if token present and valid, else None."""
    return _get_current_user_optional(credentials)