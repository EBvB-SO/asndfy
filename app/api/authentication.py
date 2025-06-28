# app/api/authentication.py

import logging
import random
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.redis import redis_client
from app.db.db_access import create_user, verify_user, update_user_password
from app.services.email_service import send_welcome_email, send_password_reset_email
from app.core.security import create_access_token, create_refresh_token
from app.models.auth_models import (
    SignUpRequest,
    SignInRequest,
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest,
    BaseResponse,
    DataResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# How long (in seconds) reset codes live in Redis
RESET_CODE_TTL = 3600


class TestEmailDeliverabilityRequest(BaseModel):
    email: EmailStr


@router.post("/signup", response_model=BaseResponse)
async def signup(data: SignUpRequest):
    """Create a new user record and send welcome email."""
    result = create_user(data.name, data.email, data.password)
    if not result:
        raise HTTPException(status_code=400, detail=result.message)

    send_welcome_email(data.email, data.name)
    return BaseResponse(success=True, message="User created.")


@router.post("/signin", response_model=DataResponse[dict])
async def signin(data: SignInRequest):
    """Authenticate and return JWT token."""
    result = verify_user(data.email, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token({
        "email": data.email,
        "user_id": result.data["id"]
    })

    token_data = {
        "email": data.email,
        "user_id": result.data["id"]
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return DataResponse(
        success=True,
        message="Signed in successfully.",
        data={
            "access_token": token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "email": data.email,
            "user_id": result.data["id"],
        },
    )


@router.post("/forgot-password", response_model=BaseResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """Generate a 6-digit reset code, store in Redis, and email it."""
    code = "".join(random.choices(string.digits, k=6))
    await redis_client.set(f"pwdreset:{request.email}", code, ex=RESET_CODE_TTL)
    send_password_reset_email(request.email, code)
    return BaseResponse(
        success=True,
        message="If an account exists, you’ll receive a reset code shortly."
    )


@router.post("/verify-reset-code", response_model=BaseResponse)
async def verify_reset_code(request: VerifyResetCodeRequest):
    """Check the submitted code against Redis entry."""
    key = f"pwdreset:{request.email}"
    stored = await redis_client.get(key)
    if stored is None:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    if stored != request.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    return BaseResponse(success=True, message="Code verified")


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(request: ResetPasswordRequest):
    """Validate code, update password, and clear the code."""
    key = f"pwdreset:{request.email}"
    stored = await redis_client.get(key)
    if stored is None or stored != request.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    result = update_user_password(request.email, request.new_password)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update password")

    await redis_client.delete(key)
    return BaseResponse(success=True, message="Password reset successfully")


@router.post(
    "/test-email-deliverability",
    response_model=DataResponse[dict],
    summary="Diagnostic endpoint for email deliverability"
)
async def test_email_deliverability(request: TestEmailDeliverabilityRequest):
    """Send a test reset email and return diagnostics."""
    test_email = request.email
    test_code = "TEST123"
    success = send_password_reset_email(test_email, test_code)

    domain = test_email.split('@')[1]
    problematic = {
        'hotmail.com', 'outlook.com', 'live.com', 'msn.com',
        'yahoo.com', 'aol.com'
    }
    is_problematic = domain in problematic

    recommendations = []
    if is_problematic:
        recommendations.extend([
            f"Add noreply@em7572.asndfy.com to your safe senders",
            "Check Spam/Junk folder",
            "Check 'Other' or 'Promotions' tab in Outlook",
            "Wait 2-5 minutes for delivery"
        ])
    if not success:
        recommendations.extend([
            "Verify SendGrid API key",
            "Check SendGrid bounces/blocks",
            "Ensure email address is valid"
        ])

    next_steps = [
        "1. Check inbox (incl. spam/junk)",
        "2. Add sender to contacts if found in spam",
        "3. If not received in 5 minutes, check SendGrid logs",
        "4. Report back with results"
    ]

    return DataResponse(
        success=success,
        message="Deliverability test completed",
        data={
            "test_email": test_email,
            "domain": domain,
            "is_problematic_domain": is_problematic,
            "recommendations": recommendations,
            "next_steps": next_steps,
        }
    )
