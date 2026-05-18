import time
import uuid
from typing import Optional

import structlog

from config import settings

log = structlog.get_logger()


class OutcomeLogger:
    """Logs automation run outcomes to Google Sheets and Supabase."""

    def __init__(self):
        self._sheets = None
        self._supabase = None
        self._init_clients()

    def _init_clients(self):
        try:
            from integrations.sheets_client import SheetsClient
            self._sheets = SheetsClient()
        except Exception as e:
            log.warning("Google Sheets logger unavailable", error=str(e))

        try:
            from supabase import create_client
            if settings.supabase_url and settings.supabase_key:
                self._supabase = create_client(settings.supabase_url, settings.supabase_key)
        except Exception as e:
            log.warning("Supabase logger unavailable", error=str(e))

    async def log(
        self,
        run_id: str,
        source: str,
        intent: str,
        agent: str,
        actions: list[str],
        status: str,
        duration_ms: int,
        tokens_used: int,
    ):
        record = {
            "run_id": run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "source": source,
            "intent": intent,
            "agent": agent,
            "actions": " | ".join(actions),
            "status": status,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "cost_usd": round(tokens_used * 0.000004, 6),  # gpt-4o-mini rate
        }

        # Log to Supabase
        if self._supabase:
            try:
                self._supabase.table("automation_runs").insert(record).execute()
            except Exception as e:
                log.warning("Supabase insert failed", error=str(e))

        # Log to Google Sheets
        if self._sheets:
            try:
                row = [
                    record["timestamp"],
                    record["run_id"],
                    record["source"],
                    record["intent"],
                    record["agent"],
                    record["actions"],
                    record["status"],
                    record["duration_ms"],
                    record["tokens_used"],
                    record["cost_usd"],
                ]
                await self._sheets.append_row(settings.outcome_sheet_id, row)
            except Exception as e:
                log.warning("Sheets append failed", error=str(e))

        # Always log to console
        log.info("Run logged", **record)

    async def get_recent_runs(self, limit: int = 20) -> list[dict]:
        if self._supabase:
            try:
                res = (
                    self._supabase.table("automation_runs")
                    .select("*")
                    .order("timestamp", desc=True)
                    .limit(limit)
                    .execute()
                )
                return res.data
            except Exception as e:
                log.warning("Failed to fetch recent runs", error=str(e))
        return []
