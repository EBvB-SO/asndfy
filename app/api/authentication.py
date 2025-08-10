# app/api/authentication.py

import logging
import random
import string

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.core.redis import redis_client
from app.db.db_access import create_user, verify_user, update_user_password
from app.services.email_service import send_welcome_email, send_password_reset_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.auth_models import (
    SignUpRequest,
    SignInRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest,
    BaseResponse,
    DataResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_CODE_TTL = 3600  # seconds

@router.post("/signup", response_model=BaseResponse)
async def signup(data: SignUpRequest):
    result = create_user(data.name, data.email, data.password)
    if not result:
        # Duplicate email or other create failure becomes a 400 (shown nicely in the app)
        raise HTTPException(status_code=400, detail=result.message)

    # Try to send the welcome email, but do NOT fail signup if it errors
    try:
        send_welcome_email(data.email, data.name)
    except Exception as e:
        logger.warning(f"Welcome email failed for {data.email}: {e}")

    return BaseResponse(success=True, message="User created.", data=None)

@router.post("/signin", response_model=DataResponse[dict])
async def signin(data: SignInRequest):
    result = verify_user(data.email, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token_data = {"email": data.email, "user_id": result.data["id"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return DataResponse(
        success=True,
        message="Signed in successfully.",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "email": data.email,
            "user_id": result.data["id"],
        },
    )


@router.post("/refresh", response_model=DataResponse[dict])
async def refresh_token(request: RefreshTokenRequest):
    try:
        payload = decode_token(request.refresh_token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token.")

    token_data = {"email": payload.get("email"), "user_id": payload.get("user_id")}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)
    return DataResponse(
        success=True,
        message="Token refreshed successfully.",
        data={
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        },
    )


@router.post("/forgot-password", response_model=BaseResponse)
async def forgot_password(request: ForgotPasswordRequest):
    try:
        code = "".join(random.choices(string.digits, k=6))
        await redis_client.set(f"pwdreset:{request.email}", code, ex=RESET_CODE_TTL)
        send_password_reset_email(request.email, code)
        return BaseResponse(
            success=True,
            message="If an account exists, you'll receive a reset code shortly."
        )
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-reset-code", response_model=BaseResponse)
async def verify_reset_code(request: VerifyResetCodeRequest):
    key = f"pwdreset:{request.email}"
    stored = await redis_client.get(key)
    if stored is None or stored != request.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return BaseResponse(success=True, message="Code verified")


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(request: ResetPasswordRequest):
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
async def test_email_deliverability(request: BaseModel):
    test_email = request.email
    test_code = "TEST123"
    success = send_password_reset_email(test_email, test_code)
    domain = test_email.split('@')[1]
    problematic = {'hotmail.com', 'outlook.com', 'live.com', 'msn.com', 'yahoo.com', 'aol.com'}
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
