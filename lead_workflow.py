"""
Lead Workflow
-------------
Triggered by: new form submission, Gmail new lead email, or HubSpot webhook.
Pipeline:
  1. Classify lead intent and urgency
  2. Create/update contact in HubSpot
  3. Send personalized outreach email
  4. Log outcome
"""

import structlog

log = structlog.get_logger()


async def run_lead_workflow(run_id: str, data: dict, classifier, router):
    """
    Convenience wrapper for the new-lead workflow.
    Can be called directly from cron or the webhook handler.
    """
    from main import WebhookPayload

    payload = WebhookPayload(
        source=data.get("source", "form"),
        type="new_lead",
        data=data,
    )

    log.info("Lead workflow starting", run_id=run_id, email=data.get("email"))

    # Step 1: Classify
    classification = await classifier.classify(payload)

    # Step 2: CRM first
    from agents.crm_agent import CRMAgent
    crm = CRMAgent()
    crm_result = await crm.execute(run_id=run_id, classification=classification, data=data)
    log.info("CRM step complete", actions=crm_result.actions)

    # Step 3: Outreach
    from agents.outreach_agent import OutreachAgent
    outreach = OutreachAgent()
    outreach_result = await outreach.execute(run_id=run_id, classification=classification, data=data)
    log.info("Outreach step complete", actions=outreach_result.actions)

    return {
        "run_id": run_id,
        "crm_actions": crm_result.actions,
        "outreach_actions": outreach_result.actions,
        "total_tokens": crm_result.tokens_used + outreach_result.tokens_used,
    }
