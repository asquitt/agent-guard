"""Transactional email service using SendGrid."""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_sendgrid_client():  # type: ignore[no-untyped-def]
    """Lazy-load SendGrid client."""
    from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]

    return SendGridAPIClient(settings.SENDGRID_API_KEY)


def _build_message(to_email: str, subject: str, html_content: str, text_content: str):  # type: ignore[no-untyped-def]
    """Build a SendGrid Mail object."""
    from sendgrid.helpers.mail import Content, Email, Mail, To  # type: ignore[import-untyped]

    return Mail(
        from_email=Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME),
        to_emails=To(to_email),
        subject=subject,
        html_content=Content("text/html", html_content),
        plain_text_content=Content("text/plain", text_content),
    )


def send_invite_email(
    to_email: str,
    org_name: str,
    role: str,
    inviter_name: str,
    reset_url: str,
) -> bool:
    """Send a team invitation email.

    Returns True on success, False on failure (non-blocking).
    """
    if not settings.SENDGRID_API_KEY:
        logger.info(
            "Email delivery skipped (SENDGRID_API_KEY not set): invite for %s to %s",
            to_email,
            org_name,
        )
        return False

    subject = f"You've been invited to {org_name} on AgentGuard"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #111; margin-bottom: 16px;">You're invited to {org_name}</h2>
        <p style="color: #444; line-height: 1.6;">
            {inviter_name} has invited you to join <strong>{org_name}</strong> as a <strong>{role}</strong> on AgentGuard.
        </p>
        <p style="color: #444; line-height: 1.6;">
            AgentGuard provides AI agent security monitoring, incident detection, and compliance reporting for your organization.
        </p>
        <div style="margin: 32px 0;">
            <a href="{reset_url}"
               style="display: inline-block; background-color: #6366f1; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 500;">
                Set Up Your Account
            </a>
        </div>
        <p style="color: #888; font-size: 13px; line-height: 1.5;">
            This link will expire in 15 minutes. If you didn't expect this invitation, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
        <p style="color: #aaa; font-size: 12px;">
            AgentGuard &mdash; AI Agent Security Platform
        </p>
    </div>
    """

    text_content = (
        f"{inviter_name} has invited you to join {org_name} as a {role} on AgentGuard.\n\n"
        f"Set up your account: {reset_url}\n\n"
        f"This link expires in 15 minutes.\n"
    )

    try:
        sg = _get_sendgrid_client()
        message = _build_message(to_email, subject, html_content, text_content)
        response = sg.send(message)
        status_code = response.status_code
        if 200 <= status_code < 300:
            logger.info("Invite email sent to %s (status=%d)", to_email, status_code)
            return True
        logger.warning("SendGrid returned status %d for %s", status_code, to_email)
        return False
    except Exception:
        logger.exception("Failed to send invite email to %s", to_email)
        return False


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send a password reset email.

    Returns True on success, False on failure.
    """
    if not settings.SENDGRID_API_KEY:
        logger.info("Email delivery skipped (SENDGRID_API_KEY not set): reset for %s", to_email)
        return False

    subject = "Reset your AgentGuard password"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #111; margin-bottom: 16px;">Reset Your Password</h2>
        <p style="color: #444; line-height: 1.6;">
            We received a request to reset your AgentGuard password. Click the button below to create a new password.
        </p>
        <div style="margin: 32px 0;">
            <a href="{reset_url}"
               style="display: inline-block; background-color: #6366f1; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 500;">
                Reset Password
            </a>
        </div>
        <p style="color: #888; font-size: 13px; line-height: 1.5;">
            This link will expire in 15 minutes. If you didn't request this, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
        <p style="color: #aaa; font-size: 12px;">
            AgentGuard &mdash; AI Agent Security Platform
        </p>
    </div>
    """

    text_content = (
        f"Reset your AgentGuard password: {reset_url}\n\n"
        f"This link expires in 15 minutes.\n"
    )

    try:
        sg = _get_sendgrid_client()
        message = _build_message(to_email, subject, html_content, text_content)
        response = sg.send(message)
        status_code = response.status_code
        if 200 <= status_code < 300:
            logger.info("Password reset email sent to %s (status=%d)", to_email, status_code)
            return True
        logger.warning("SendGrid returned status %d for %s", status_code, to_email)
        return False
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
