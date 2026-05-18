import structlog

from agents.base_agent import BaseAgent, AgentResult
from integrations.hubspot_client import HubSpotClient

log = structlog.get_logger()


class CRMAgent(BaseAgent):
    """Creates/updates contacts and deals in HubSpot based on trigger data."""

    def __init__(self):
        self.hubspot = HubSpotClient()

    async def execute(self, run_id: str, classification, data: dict) -> AgentResult:
        intent = classification.intent
        actions = []
        tokens = 0

        log.info("CRMAgent executing", run_id=run_id, intent=intent)

        if "lead" in intent or "contact" in intent:
            actions += await self._handle_new_contact(data)

        if "deal" in intent or "contract" in intent or "signed" in intent:
            actions += await self._handle_deal_update(data)

        if "stage" in intent or "pipeline" in intent:
            actions += await self._handle_pipeline_update(data)

        if not actions:
            actions.append(f"CRM: no specific action mapped for intent '{intent}', data logged.")

        log.info("CRMAgent complete", run_id=run_id, actions=actions)
        return AgentResult(actions=actions, tokens_used=tokens)

    async def _handle_new_contact(self, data: dict) -> list[str]:
        """Create or update a contact in HubSpot."""
        email = data.get("email", "")
        if not email:
            return ["CRM: skipped contact creation — no email"]

        contact_data = {
            "email": email,
            "firstname": data.get("name", "").split()[0] if data.get("name") else "",
            "lastname": " ".join(data.get("name", "").split()[1:]),
            "company": data.get("company", ""),
            "jobtitle": data.get("role", ""),
            "phone": data.get("phone", ""),
            "hs_lead_status": "NEW",
        }

        result = await self.hubspot.upsert_contact(contact_data)
        return [f"HubSpot contact upserted: {email} (ID: {result.get('id', 'n/a')})"]

    async def _handle_deal_update(self, data: dict) -> list[str]:
        """Create or advance a deal in HubSpot."""
        deal_name = data.get("deal_name", data.get("company", "New Deal"))
        deal_value = data.get("deal_value", 0)
        stage = data.get("stage", "contractsent")

        result = await self.hubspot.create_or_update_deal({
            "dealname": deal_name,
            "amount": deal_value,
            "dealstage": stage,
            "pipeline": "default",
        })
        return [
            f"HubSpot deal updated: '{deal_name}' — stage: {stage}, value: ${deal_value:,}",
            f"Deal ID: {result.get('id', 'n/a')}",
        ]

    async def _handle_pipeline_update(self, data: dict) -> list[str]:
        """Move a deal to a new pipeline stage."""
        deal_id = data.get("deal_id", "")
        new_stage = data.get("new_stage", "")
        if not deal_id or not new_stage:
            return ["CRM: pipeline update skipped — missing deal_id or new_stage"]

        await self.hubspot.update_deal_stage(deal_id, new_stage)
        return [f"HubSpot deal {deal_id} moved to stage: {new_stage}"]
