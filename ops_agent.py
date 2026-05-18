import structlog

from agents.base_agent import BaseAgent, AgentResult
from integrations.slack_client import SlackClient

log = structlog.get_logger()

URGENCY_EMOJI = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


class OpsAgent(BaseAgent):
    """Handles operational tasks: Slack alerts, Notion tasks, internal notifications."""

    def __init__(self):
        self.slack = SlackClient()

    async def execute(self, run_id: str, classification, data: dict) -> AgentResult:
        intent = classification.intent
        urgency = classification.urgency
        actions = []

        log.info("OpsAgent executing", run_id=run_id, intent=intent, urgency=urgency)

        # Slack alert for high-urgency or ops-type triggers
        if urgency == "high" or "alert" in intent or "overdue" in intent:
            actions += await self._send_slack_alert(run_id, classification, data)

        # Task creation (Notion or internal)
        if "task" in intent or "followup" in intent or "action" in intent:
            actions += await self._create_task(run_id, classification, data)

        # Onboarding trigger
        if "onboarding" in intent or "welcome" in intent:
            actions += await self._trigger_onboarding(data)

        if not actions:
            actions.append(f"Ops: logged trigger '{intent}' with urgency '{urgency}'")

        log.info("OpsAgent complete", run_id=run_id, actions=actions)
        return AgentResult(actions=actions, tokens_used=0)

    async def _send_slack_alert(self, run_id: str, classification, data: dict) -> list[str]:
        """Post a formatted Slack alert to the ops channel."""
        emoji = URGENCY_EMOJI.get(classification.urgency, "⚪")
        name = data.get("name", "Unknown")
        company = data.get("company", "")

        message = (
            f"{emoji} *AutoFlow Alert* — `{run_id}`\n"
            f"*Intent:* {classification.intent}\n"
            f"*Summary:* {classification.summary}\n"
            f"*Contact:* {name}{' @ ' + company if company else ''}\n"
            f"*Urgency:* {classification.urgency.upper()}"
        )

        result = await self.slack.post_message(message)
        return [f"Slack alert sent to ops channel (ts: {result.get('ts', 'n/a')})"]

    async def _create_task(self, run_id: str, classification, data: dict) -> list[str]:
        """Create an internal task record in Supabase (Notion integration optional)."""
        try:
            from supabase import create_client
            from config import settings

            if not settings.supabase_url:
                return ["Task creation skipped — Supabase not configured"]

            client = create_client(settings.supabase_url, settings.supabase_key)
            task = {
                "run_id": run_id,
                "title": f"Follow up: {classification.summary}",
                "intent": classification.intent,
                "urgency": classification.urgency,
                "assignee": data.get("owner", "unassigned"),
                "due_date": data.get("due_date", ""),
                "status": "open",
                "metadata": data,
            }
            client.table("tasks").insert(task).execute()
            return [f"Task created: '{task['title']}' (urgency: {classification.urgency})"]
        except Exception as e:
            return [f"Task creation failed: {str(e)}"]

    async def _trigger_onboarding(self, data: dict) -> list[str]:
        """Send onboarding welcome message via Slack."""
        name = data.get("name", "new customer")
        company = data.get("company", "")
        message = (
            f"🎉 *New customer onboarding started!*\n"
            f"*Name:* {name}\n"
            f"*Company:* {company}\n"
            "Please assign an onboarding specialist and send the welcome kit."
        )
        await self.slack.post_message(message)
        return [f"Onboarding triggered for {name} @ {company}"]
