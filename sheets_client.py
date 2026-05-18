import os
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

log = structlog.get_logger()


class SheetsClient:
    """Google Sheets API wrapper for outcome logging."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            settings.sheets_credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def append_row(self, sheet_id: str, values: list) -> dict:
        """Append a row to a Google Sheet."""
        try:
            service = self._get_service()
            body = {"values": [values]}
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=sheet_id,
                    range="Sheet1!A:Z",
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )
            log.info("Sheets row appended", sheet_id=sheet_id)
            return result
        except Exception as e:
            log.error("Sheets append failed", error=str(e))
            return {"error": str(e)}

    async def ensure_headers(self, sheet_id: str):
        """Write column headers if the sheet is empty."""
        headers = [
            "Timestamp", "Run ID", "Source", "Intent", "Agent",
            "Actions", "Status", "Duration (ms)", "Tokens Used", "Cost (USD)"
        ]
        try:
            service = self._get_service()
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range="Sheet1!A1:J1")
                .execute()
            )
            if not result.get("values"):
                await self.append_row(sheet_id, headers)
        except Exception as e:
            log.warning("Could not ensure sheet headers", error=str(e))
