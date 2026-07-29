"""VaultAlert — Notification Service.

Dispatches alerts via Push (FCM), Email (SMTP), and SMS (Twilio).
"""

import asyncio
from typing import List, Optional
from uuid import UUID

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger

from app.core.config import settings
from app.models.models import Notification, NotificationChannel, AlertSeverity, User
from app.repositories.base import BaseRepository


class NotificationService:
    # ── Email ──────────────────────────────────────────────────────────────────
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
    ) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body_html, "html"))

            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                start_tls=True,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)

            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as exc:
            logger.error(f"Email send failed to {to_email}: {exc}")
            return False

    # ── SMS via Twilio ────────────────────────────────────────────────────────
    async def send_sms(self, to_number: str, message: str) -> bool:
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # Twilio SDK is synchronous — run in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    body=message,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=to_number,
                ),
            )
            logger.info(f"SMS sent to {to_number}")
            return True
        except Exception as exc:
            logger.error(f"SMS send failed to {to_number}: {exc}")
            return False

    # ── Firebase Cloud Messaging (Push) ───────────────────────────────────────
    async def send_push(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> bool:
        try:
            import firebase_admin
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=fcm_token,
                data={str(k): str(v) for k, v in (data or {}).items()},
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: messaging.send(message))
            logger.info(f"Push notification sent to FCM token ending ...{fcm_token[-8:]}")
            return True
        except Exception as exc:
            logger.error(f"Push notification failed: {exc}")
            return False

    # ── Alert dispatcher ──────────────────────────────────────────────────────
    async def dispatch_alert(
        self,
        user: User,
        title: str,
        body: str,
        severity: AlertSeverity = AlertSeverity.info,
        data: Optional[dict] = None,
    ) -> None:
        """Send alert via all available channels for the user."""
        tasks = []
        if user.fcm_token:
            tasks.append(self.send_push(user.fcm_token, title, body, data))
        if user.email:
            html = self._build_alert_email(title, body, severity)
            tasks.append(self.send_email(user.email, f"[VaultAlert] {title}", html))
        if user.phone:
            tasks.append(self.send_sms(user.phone, f"VaultAlert: {title}\n{body}"))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _build_alert_email(self, title: str, body: str, severity: AlertSeverity) -> str:
        color = {
            AlertSeverity.critical: "#ef4444",
            AlertSeverity.warning: "#f59e0b",
            AlertSeverity.info: "#3b82f6",
        }.get(severity, "#3b82f6")

        return f"""
        <html><body style="font-family:Inter,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px">
          <div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:12px;padding:24px;border-left:4px solid {color}">
            <div style="display:flex;align-items:center;margin-bottom:16px">
              <span style="font-size:24px;font-weight:700;color:{color}">⚡ VaultAlert</span>
            </div>
            <h2 style="margin:0 0 8px;color:#f1f5f9">{title}</h2>
            <p style="color:#94a3b8;line-height:1.6">{body}</p>
            <hr style="border-color:#334155;margin:16px 0">
            <p style="font-size:12px;color:#64748b">
              This is an automated alert from VaultAlert Security Platform.<br>
              Log in at <a href="https://app.vaultalert.io" style="color:{color}">app.vaultalert.io</a> to review.
            </p>
          </div>
        </body></html>
        """
