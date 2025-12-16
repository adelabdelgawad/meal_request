"""
Celery Email Tasks.

Handles email notification sending with automatic retry logic.
Replaces fire-and-forget FastAPI BackgroundTasks for email operations.
"""

import logging
import os
import traceback
from typing import List, Optional

from celery import shared_task
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


def _generate_template(data: dict, file_name: str) -> str:
    """
    Generate HTML content from a Jinja2 template.

    Args:
        data: Template context data
        file_name: Template file name

    Returns:
        Rendered HTML string
    """
    templates_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates"
    )
    env = Environment(loader=FileSystemLoader(templates_path))
    template = env.get_template(file_name)
    return template.render(data)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_notification_task(
    self,
    request_id: int,
    request_lines: int,
    to_recipient: str,
    cc_recipients: Optional[List[str]] = None,
) -> dict:
    """
    Send email notification for a meal request.

    This task replaces the BackgroundTasks version with Celery's
    automatic retry logic and dead-letter queue support.

    Args:
        request_id: Meal request ID for email subject
        request_lines: Number of request lines for email body
        to_recipient: Primary recipient email address
        cc_recipients: Optional list of CC email addresses

    Returns:
        dict with status and message

    Raises:
        Retries automatically on failure up to max_retries times
    """
    try:
        # Import here to avoid circular imports and ensure fresh connection
        from utils.mail_sender import EmailSender

        logger.info(f"Sending notification email for request #{request_id} to {to_recipient}")

        # Generate email content
        body_html = _generate_template(
            {"request_lines": request_lines},
            "request.html"
        )
        subject = f"Meal Request Submitted #{request_id} - Confirmation Pending"

        # Create sender and send
        email_sender = EmailSender()
        message = email_sender.create_message(
            subject=subject,
            body=body_html,
            to_recipient=to_recipient,
            cc_recipients=cc_recipients,
        )
        message.send()

        logger.info(f"Email sent successfully to {to_recipient} for request #{request_id}")

        return {
            "status": "success",
            "request_id": request_id,
            "recipient": to_recipient,
        }

    except Exception as e:
        logger.error(
            f"Failed to send email to {to_recipient} for request #{request_id}: {e}"
        )
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Re-raise to trigger Celery retry
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_status_update_task(
    self,
    request_id: int,
    status: str,
    to_recipient: str,
    cc_recipients: Optional[List[str]] = None,
) -> dict:
    """
    Send email notification for meal request status change.

    Args:
        request_id: Meal request ID
        status: New status (e.g., "approved", "rejected")
        to_recipient: Primary recipient email address
        cc_recipients: Optional list of CC email addresses

    Returns:
        dict with status and message
    """
    try:
        from utils.mail_sender import EmailSender

        logger.info(f"Sending status update email for request #{request_id} ({status})")

        # Generate email content
        body_html = _generate_template(
            {"request_id": request_id, "status": status},
            "status_update.html"
        )
        subject = f"Meal Request #{request_id} - Status: {status.upper()}"

        email_sender = EmailSender()
        message = email_sender.create_message(
            subject=subject,
            body=body_html,
            to_recipient=to_recipient,
            cc_recipients=cc_recipients,
        )
        message.send()

        logger.info(f"Status update email sent to {to_recipient}")

        return {
            "status": "success",
            "request_id": request_id,
            "new_status": status,
        }

    except Exception as e:
        logger.error(f"Failed to send status update email: {e}")
        raise
