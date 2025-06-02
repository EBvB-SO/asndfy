# services/email_service.py
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Optional

logger = logging.getLogger(__name__)

def send_password_reset_email(recipient_email: str, reset_code: str) -> bool:
    """
    Send a password reset email with the reset code.
    
    Args:
        recipient_email: The email address to send to
        reset_code: The 6-digit reset code
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get SendGrid API key from environment
        sg_api_key = os.getenv('SENDGRID_API_KEY')
        if not sg_api_key:
            logger.error("SENDGRID_API_KEY not found in environment variables")
            return False
            
        # Create SendGrid client
        sg = SendGridAPIClient(sg_api_key)
        
        # Create the email
        from_email = Email("hello@asndfy.com")  # or use your verified sender email
        to_email = To(recipient_email)
        subject = "Your Ascendify Password Reset Code"
        
        # Create the email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>You requested a password reset for your Ascendify account.</p>
                <p>Your reset code is:</p>
                <h1 style="font-size: 36px; color: #333; letter-spacing: 5px;">{reset_code}</h1>
                <p>This code will expire in 1 hour.</p>
                <p>If you didn't request this reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>The Ascendify Team</p>
            </body>
        </html>
        """
        
        plain_content = f"""
        Password Reset Request
        
        You requested a password reset for your Ascendify account.
        
        Your reset code is: {reset_code}
        
        This code will expire in 1 hour.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        The Ascendify Team
        """
        
        # Create the Mail object
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Send the email
        response = sg.send(message)
        
        logger.info(f"Password reset email sent successfully to {recipient_email}. Status code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {recipient_email}: {str(e)}")
        return False

def send_welcome_email(recipient_email: str, name: str) -> bool:
    """
    Send a welcome email to new users.
    
    Args:
        recipient_email: The email address to send to
        name: The user's name
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get SendGrid API key from environment
        sg_api_key = os.getenv('SENDGRID_API_KEY')
        if not sg_api_key:
            logger.error("SENDGRID_API_KEY not found in environment variables")
            return False
            
        # Create SendGrid client
        sg = SendGridAPIClient(sg_api_key)
        
        # Create the email
        from_email = Email("hello@asndfy.com")  # or use your verified sender email
        to_email = To(recipient_email)
        subject = "Welcome to Ascendify!"
        
        # Create the email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Welcome to Ascendify, {name}!</h2>
                <p>Thank you for joining Ascendify. We're excited to help you on your climbing journey!</p>
                <p>Get started by:</p>
                <ul>
                    <li>Completing your profile</li>
                    <li>Setting up your first climbing project</li>
                    <li>Generating your personalized training plan</li>
                </ul>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <br>
                <p>Happy climbing!<br>The Ascendify Team</p>
            </body>
        </html>
        """
        
        plain_content = f"""
        Welcome to Ascendify, {name}!
        
        Thank you for joining Ascendify. We're excited to help you on your climbing journey!
        
        Get started by:
        - Completing your profile
        - Setting up your first climbing project
        - Generating your personalized training plan
        
        If you have any questions, feel free to reach out to our support team.
        
        Happy climbing!
        The Ascendify Team
        """
        
        # Create the Mail object
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Send the email
        response = sg.send(message)
        
        logger.info(f"Welcome email sent successfully to {recipient_email}. Status code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")
        return False