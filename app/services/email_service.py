"""Email service for sending notifications."""
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email or settings.smtp_user
        self.from_name = settings.smtp_from_name
        self.use_tls = settings.smtp_use_tls

    def _is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.host and self.user and self.password)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body of the email
            text_content: Plain text alternative (optional)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.warning("Email not configured. Skipping email send.")
            return False

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add plain text version
            if text_content:
                message.attach(MIMEText(text_content, "plain"))

            # Add HTML version
            message.attach(MIMEText(html_content, "html"))

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_admin_credentials(
        self,
        to_email: str,
        admin_name: str,
        username: str,
        password: str,
        attraction_name: str,
        login_url: str | None = None,
    ) -> bool:
        """
        Send admin credentials email to newly created attraction admin.

        Args:
            to_email: Admin's email address
            admin_name: Admin's full name
            username: Admin's username for login
            password: Admin's password (plain text, before hashing)
            attraction_name: Name of the attraction
            login_url: URL to the login page

        Returns:
            True if email was sent successfully, False otherwise
        """
        # Use frontend_url if set, otherwise fall back to base_url
        frontend_base = settings.frontend_url or settings.base_url
        login_url = login_url or f"{frontend_base}/login"

        subject = f"Welcome to InSite Survey - Your Admin Credentials for {attraction_name}"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to InSite Survey</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to InSite Survey</h1>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
        <h2 style="color: #333; margin-top: 0;">Hello {admin_name},</h2>

        <p>Your admin account has been created for <strong>{attraction_name}</strong>. You can now access the InSite Survey portal to manage your surveys and view responses.</p>

        <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin: 25px 0;">
            <h3 style="margin-top: 0; color: #667eea;">Your Login Credentials</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Email:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{to_email}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee; font-weight: bold;">Username:</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #eee;">{username}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold;">Password:</td>
                    <td style="padding: 10px 0;"><code style="background: #f0f0f0; padding: 5px 10px; border-radius: 4px; font-size: 14px;">{password}</code></td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{login_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Login to Your Account</a>
        </div>

        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin-top: 25px;">
            <strong style="color: #856404;">Important Security Notice:</strong>
            <p style="margin: 10px 0 0 0; color: #856404;">For security purposes, we recommend changing your password after your first login.</p>
        </div>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #666; font-size: 14px; margin-bottom: 0;">
            If you have any questions or need assistance, please contact our support team.<br>
            <br>
            Best regards,<br>
            <strong>The InSite Survey Team</strong>
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
        <p>This is an automated message from InSite Survey. Please do not reply to this email.</p>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome to InSite Survey

Hello {admin_name},

Your admin account has been created for {attraction_name}. You can now access the InSite Survey portal to manage your surveys and view responses.

Your Login Credentials:
- Email: {to_email}
- Username: {username}
- Password: {password}

Login URL: {login_url}

IMPORTANT: For security purposes, we recommend changing your password after your first login.

If you have any questions or need assistance, please contact our support team.

Best regards,
The InSite Survey Team
"""

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_link: str,
    ) -> bool:
        """
        Send password reset email with reset link.

        Args:
            to_email: User's email address
            user_name: User's full name
            reset_link: Password reset link with token

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.warning(
                f"Email not configured. Password reset link for {to_email}: {reset_link}"
            )
            # For development: just log the reset link
            logger.info(f"PASSWORD RESET LINK FOR {to_email}: {reset_link}")
            return True

        subject = "Password Reset Request - InSite Survey Platform"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset Request</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Password Reset Request</h1>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
        <h2 style="color: #333; margin-top: 0;">Hello {user_name},</h2>

        <p>We received a request to reset your password for your InSite Survey Platform account.</p>

        <p>Click the button below to reset your password:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Reset Password</a>
        </div>

        <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #667eea; font-size: 14px; background: white; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">{reset_link}</p>

        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin-top: 25px;">
            <strong style="color: #856404;">Important:</strong>
            <p style="margin: 10px 0 0 0; color: #856404;">This link will expire in 1 hour for security reasons.</p>
        </div>

        <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; border-left: 4px solid #2196F3; margin-top: 15px;">
            <strong style="color: #0d47a1;">Didn't request this?</strong>
            <p style="margin: 10px 0 0 0; color: #0d47a1;">If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
        </div>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #666; font-size: 14px; margin-bottom: 0;">
            Best regards,<br>
            <strong>The InSite Survey Team</strong>
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
        <p>This is an automated message from InSite Survey. Please do not reply to this email.</p>
        <p>© 2025 InSite Survey Platform. All rights reserved.</p>
    </div>
</body>
</html>
"""

        text_content = f"""
Password Reset Request

Hello {user_name},

We received a request to reset your password for your InSite Survey Platform account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
The InSite Survey Team

---
This is an automated message from InSite Survey. Please do not reply to this email.
© 2025 InSite Survey Platform. All rights reserved.
"""

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Singleton instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the email service instance."""
    return email_service
