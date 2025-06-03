# api/authentication.py
from fastapi import APIRouter, HTTPException
from typing import Dict
import random
import string
from datetime import datetime, timedelta
import logging
import sys
import os

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the db_access module as "db" so that db.create_user, db.verify_user, etc. are available
import db.db_access as db

from models.auth_models import (
    SignUpRequest, 
    SignInRequest, 
    ForgotPasswordRequest, 
    ForgotPasswordResponse,
    VerifyResetCodeRequest,
    ResetPasswordRequest
)
from services.email_service import send_welcome_email, send_password_reset_email
from core.security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Temporary storage for reset codes - should be Redis in production
reset_codes: Dict[str, Dict] = {}

@router.post("/signup")
def signup(data: SignUpRequest):
    result = db.create_user(data.name, data.email, data.password)
    if not result:
        raise HTTPException(status_code=400, detail=result.message)
    
    # Send welcome email
    send_welcome_email(data.email, data.name)
    
    return {"success": True, "message": "User created."}


@router.post("/signin")
def signin(data: SignInRequest):
    result = db.verify_user(data.email, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    # Create JWT token
    access_token = create_access_token(
        data={"email": data.email, "user_id": result.data["id"]}
    )
    
    return {
        "success": True,
        "message": "Signed in successfully.",
        "access_token": access_token,
        "token_type": "bearer",
        "email": data.email,
        "user_id": result.data["id"]
    }

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """Handle forgot password request."""
    try:
        # Generate a random 6-digit reset code
        reset_code = ''.join(random.choices(string.digits, k=6))
        
        # Store the code with expiration (1 hour)
        reset_codes[request.email] = {
            'code': reset_code,
            'expires': datetime.now() + timedelta(hours=1)
        }
        
        # Send the email with the reset code
        success = send_password_reset_email(request.email, reset_code)
        
        if success:
            return ForgotPasswordResponse(
                message="Password reset code sent to your email",
                success=True
            )
        else:
            # Still return success to avoid email enumeration
            return ForgotPasswordResponse(
                message="If an account exists with this email, you will receive a reset code",
                success=True
            )
            
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        # Don't expose internal errors
        return ForgotPasswordResponse(
            message="If an account exists with this email, you will receive a reset code",
            success=True
        )

@router.post("/verify-reset-code")
async def verify_reset_code(request: VerifyResetCodeRequest):
    """Verify the reset code is valid."""
    if request.email not in reset_codes:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    stored = reset_codes[request.email]
    
    # Check expiration
    if datetime.now() > stored['expires']:
        del reset_codes[request.email]
        raise HTTPException(status_code=400, detail="Code has expired")
    
    # Check code
    if stored['code'] != request.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    return {"message": "Code verified", "valid": True}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset the password with a valid code."""
    # First verify the code
    if request.email not in reset_codes:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    stored = reset_codes[request.email]
    
    if datetime.now() > stored['expires'] or stored['code'] != request.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    # Update the user's password in database
    result = db.update_user_password(request.email, request.new_password)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    # Clear the used code
    del reset_codes[request.email]
    
    return {"message": "Password reset successfully", "success": True}

@router.post("/test-email-deliverability")
async def test_email_deliverability(request: dict):
    """Test email deliverability with detailed diagnostics."""
    
    test_email = request.get("email")
    
    # Send test email
    test_code = "TEST123"
    success = send_password_reset_email(test_email, test_code)
    
    # Get domain info
    domain = test_email.split('@')[1] if '@' in test_email else 'unknown'
    
    # Check if it's a problematic domain
    problematic_domains = {
        'hotmail.com', 'outlook.com', 'live.com', 'msn.com',
        'yahoo.com', 'aol.com'
    }
    
    is_problematic = domain in problematic_domains
    
    recommendations = []
    
    if is_problematic:
        recommendations.extend([
            f"Add noreply@em7572.asndfy.com to your contacts/safe sender list",
            "Check your Spam/Junk folder",
            "Check 'Other' or 'Promotions' tab if using Outlook",
            "Wait 2-5 minutes for delivery (some providers delay new senders)"
        ])
    
    if not success:
        recommendations.extend([
            "Verify SendGrid API key is correct",
            "Check SendGrid dashboard for bounce/block notifications",
            "Ensure the email address is valid"
        ])
    
    return {
        "success": success,
        "test_email": test_email,
        "domain": domain,
        "is_problematic_domain": is_problematic,
        "recommendations": recommendations,
        "next_steps": [
            "1. Check inbox (including spam/junk)",
            "2. Add sender to contacts if found in spam",
            "3. If not received in 5 minutes, check SendGrid Activity Feed",
            "4. Report back with results"
        ]
    }