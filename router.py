from dataclasses import dataclass, field

import structlog

from agents.outreach_agent import OutreachAgent
from agents.crm_agent import CRMAgent
from agents.ops_agent import OpsAgent
from core.classifier import Classification
from integrations.slack_client import SlackClient
from config import settings

log = structlog.get_logger()


@dataclass
class ExecutionResult:
    agent_name: str
    actions_taken: list[str]
    tokens_used: int
    approved: bool = True
    error: str | None = None


class AgentRouter:
    """Routes classified triggers to the correct agent and handles HITL approval."""

    def __init__(self):
        self.agents = {
            "outreach": OutreachAgent(),
            "crm": CRMAgent(),
            "ops": OpsAgent(),
        }
        self.slack = SlackClient()

    async def route_and_execute(
        self,
        run_id: str,
        classification: Classification,
        data: dict,
    ) -> ExecutionResult:
        agent_key = classification.suggested_agent
        agent = self.agents.get(agent_key, self.agents["ops"])

        log.info("Routing to agent", run_id=run_id, agent=agent_key)

        # Human-in-the-loop gate
        if classification.requires_approval or self._needs_approval(data):
            approved = await self._request_approval(run_id, classification, data)
            if not approved:
                log.info("Action rejected by human", run_id=run_id)
                return ExecutionResult(
                    agent_name=agent_key,
                    actions_taken=["Rejected by human reviewer"],
                    tokens_used=0,
                    approved=False,
                )

        try:
            result = await agent.execute(run_id=run_id, classification=classification, data=data)
            return ExecutionResult(
                agent_name=agent_key,
                actions_taken=result.actions,
                tokens_used=result.tokens_used,
                approved=True,
            )
        except Exception as e:
            log.error("Agent execution failed", run_id=run_id, agent=agent_key, error=str(e))
            return ExecutionResult(
                agent_name=agent_key,
                actions_taken=[],
                tokens_used=0,
                error=str(e),
            )

    def _needs_approval(self, data: dict) -> bool:
        """Check if data volume or value requires human approval."""
        contact_count = data.get("contact_count", 1)
        deal_value = data.get("deal_value", 0)
        return (
            contact_count > settings.hitl_threshold_contacts
            or deal_value > 50000
        )

    async def _request_approval(
        self,
        run_id: str,
        classification: Classification,
        data: dict,
    ) -> bool:
        """Send Slack approval request and wait for response."""
        try:
            approved = await self.slack.request_approval(
                run_id=run_id,
                summary=classification.summary,
                intent=classification.intent,
                data=data,
            )
            return approved
        except Exception as e:
            log.warning("HITL approval failed, defaulting to reject", error=str(e))
            return False
