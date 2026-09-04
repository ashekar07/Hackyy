"""SMTP notifications for approved surplus redistribution."""
import asyncio
import smtplib
from email.message import EmailMessage

from config import (
    MANAGER_EMAIL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)


def _send_message(subject: str, body: str) -> None:
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, MANAGER_EMAIL)):
        raise RuntimeError("SMTP configuration is incomplete in .env")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = MANAGER_EMAIL
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        try:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "SMTP authentication failed. For Gmail, use a 16-character "
                "Google App Password for SMTP_PASSWORD."
            ) from exc
        smtp.send_message(message)


async def send_surplus_notification(route: str, portions: int) -> None:
    """Send mail without blocking FastAPI's event loop."""
    await asyncio.to_thread(
        _send_message,
        f"FoodWise surplus redistribution: {route}",
        (
            "A surplus redistribution request was approved in FoodWise AI.\n\n"
            f"Route: {route}\n"
            f"Meals available: {portions}\n"
        ),
    )