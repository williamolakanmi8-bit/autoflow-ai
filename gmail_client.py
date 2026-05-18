import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

log = structlog.get_logger()


class GmailClient:
    """Gmail API wrapper for sending emails."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
        creds = None

        if os.path.exists(settings.gmail_token_path):
            creds = Credentials.from_authorized_user_file(settings.gmail_token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(settings.gmail_token_path, "w") as token:
                token.write(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _build_message(self, to: str, subject: str, body: str) -> dict:
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["from"] = settings.gmail_sender_email
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {"raw": raw}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send an email via Gmail API."""
        try:
            service = self._get_service()
            message = self._build_message(to, subject, body)
            result = service.users().messages().send(userId="me", body=message).execute()
            log.info("Email sent", to=to, subject=subject, message_id=result.get("id"))
            return result
        except Exception as e:
            log.error("Gmail send failed", to=to, error=str(e))
            # Return mock for dev/test environments
            return {"id": f"mock_{to[:8]}", "error": str(e)}
