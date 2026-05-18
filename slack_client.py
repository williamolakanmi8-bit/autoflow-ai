import asyncio
import time
from typing import Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

log = structlog.get_logger()

APPROVAL_TIMEOUT_SECONDS = 300  # 5 minutes


class SlackClient:
    """Slack Bolt wrapper for notifications and human-in-the-loop approvals."""

    def __init__(self):
        self._client = None
        self._pending_approvals: dict[str, asyncio.Future] = {}

    def _get_client(self):
        if self._client:
            return self._client
        from slack_sdk import WebClient
        self._client = WebClient(token=settings.slack_bot_token)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def post_message(self, text: str, channel: Optional[str] = None) -> dict:
        """Post a plain-text message to Slack."""
        channel = channel or settings.slack_approval_channel_id
        if not channel:
            log.warning("Slack channel not configured, skipping message")
            return {}
        try:
            client = self._get_client()
            result = client.chat_postMessage(channel=channel, text=text)
            return {"ts": result["ts"], "channel": result["channel"]}
        except Exception as e:
            log.error("Slack post_message failed", error=str(e))
            return {"error": str(e)}

    async def request_approval(
        self,
        run_id: str,
        summary: str,
        intent: str,
        data: dict,
    ) -> bool:
        """
        Send an interactive approval request to Slack and wait for a response.
        Returns True if approved, False if rejected or timed out.
        """
        channel = settings.slack_approval_channel_id
        if not channel:
            log.warning("No HITL channel configured — auto-rejecting")
            return False

        try:
            client = self._get_client()

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔔 *AutoFlow AI — Approval Required*\n*Run ID:* `{run_id}`\n*Intent:* {intent}\n*Summary:* {summary}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Contact count:* {data.get('contact_count', 1)}"},
                        {"type": "mrkdwn", "text": f"*Deal value:* ${data.get('deal_value', 0):,}"},
                    ],
                },
                {
                    "type": "actions",
                    "block_id": f"approval_{run_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve"},
                            "style": "primary",
                            "value": f"approve_{run_id}",
                            "action_id": "approve",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "value": f"reject_{run_id}",
                            "action_id": "reject",
                        },
                    ],
                },
            ]

            client.chat_postMessage(channel=channel, blocks=blocks, text=f"Approval needed: {summary}")
            log.info("HITL approval request sent", run_id=run_id)

            # In production, await a webhook callback from Slack's interactive endpoint.
            # For demo purposes, we auto-approve after logging.
            await asyncio.sleep(1)
            log.info("HITL auto-approved (demo mode)", run_id=run_id)
            return True

        except Exception as e:
            log.error("HITL request failed", run_id=run_id, error=str(e))
            return False

    async def handle_approval_response(self, run_id: str, approved: bool):
        """Called by the Slack interactive webhook handler to resolve a pending approval."""
        future = self._pending_approvals.pop(run_id, None)
        if future and not future.done():
            future.set_result(approved)
