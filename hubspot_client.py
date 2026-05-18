import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

log = structlog.get_logger()


class HubSpotClient:
    """HubSpot CRM API wrapper."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        from hubspot import HubSpot
        self._client = HubSpot(access_token=settings.hubspot_access_token)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def upsert_contact(self, contact_data: dict) -> dict:
        """Create or update a contact. Returns the contact object."""
        try:
            from hubspot.crm.contacts import SimplePublicObjectInputForCreate, ApiException
            client = self._get_client()

            properties = {k: str(v) for k, v in contact_data.items() if v}
            email = properties.pop("email", "")

            # Search for existing contact
            try:
                existing = client.crm.contacts.basic_api.get_by_id(
                    email, id_property="email", properties=list(properties.keys())
                )
                # Update existing
                from hubspot.crm.contacts import SimplePublicObjectInput
                update_input = SimplePublicObjectInput(properties=properties)
                result = client.crm.contacts.basic_api.update(existing.id, update_input)
                log.info("HubSpot contact updated", contact_id=existing.id, email=email)
                return {"id": existing.id, "action": "updated"}
            except Exception:
                # Create new
                properties["email"] = email
                create_input = SimplePublicObjectInputForCreate(properties=properties, associations=[])
                result = client.crm.contacts.basic_api.create(create_input)
                log.info("HubSpot contact created", contact_id=result.id, email=email)
                return {"id": result.id, "action": "created"}

        except Exception as e:
            log.error("HubSpot upsert_contact failed", error=str(e))
            return {"id": "mock", "error": str(e)}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def create_or_update_deal(self, deal_data: dict) -> dict:
        """Create a new deal in HubSpot."""
        try:
            from hubspot.crm.deals import SimplePublicObjectInputForCreate
            client = self._get_client()
            properties = {k: str(v) for k, v in deal_data.items() if v}
            create_input = SimplePublicObjectInputForCreate(properties=properties, associations=[])
            result = client.crm.deals.basic_api.create(create_input)
            log.info("HubSpot deal created", deal_id=result.id)
            return {"id": result.id}
        except Exception as e:
            log.error("HubSpot create_deal failed", error=str(e))
            return {"id": "mock", "error": str(e)}

    async def update_deal_stage(self, deal_id: str, new_stage: str) -> dict:
        """Move a deal to a new pipeline stage."""
        try:
            from hubspot.crm.deals import SimplePublicObjectInput
            client = self._get_client()
            update_input = SimplePublicObjectInput(properties={"dealstage": new_stage})
            result = client.crm.deals.basic_api.update(deal_id, update_input)
            log.info("HubSpot deal stage updated", deal_id=deal_id, new_stage=new_stage)
            return {"id": result.id}
        except Exception as e:
            log.error("HubSpot update_deal_stage failed", error=str(e))
            return {"error": str(e)}
