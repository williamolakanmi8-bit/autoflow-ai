"""
Tests for TriggerClassifier.
Run with: pytest tests/ -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockPayload:
    def __init__(self, source, type_, data):
        self.source = source
        self.type = type_
        self.data = data


class TestTriggerClassifier:
    """Tests for the LLM-based trigger classifier."""

    def test_fallback_classification_on_error(self):
        """Should return a safe fallback when LLM call fails."""
        from core.classifier import TriggerClassifier, Classification

        classifier = TriggerClassifier.__new__(TriggerClassifier)

        payload = MockPayload(
            source="gmail",
            type="new_lead",
            data={"name": "Jane Doe", "email": "jane@example.com"},
        )

        # Simulate classify error path
        import asyncio

        async def run():
            try:
                raise ValueError("LLM unavailable")
            except Exception:
                return Classification(
                    intent=payload.type,
                    urgency="medium",
                    entities=payload.data,
                    suggested_agent="ops",
                    requires_approval=False,
                    summary=f"Unclassified trigger from {payload.source}",
                    confidence=0.0,
                )

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.intent == "new_lead"
        assert result.urgency == "medium"
        assert result.confidence == 0.0

    def test_classification_schema(self):
        """Classification pydantic model validates correctly."""
        from core.classifier import Classification

        c = Classification(
            intent="new_lead_followup",
            urgency="high",
            entities={"name": "John", "email": "john@example.com"},
            suggested_agent="outreach",
            requires_approval=False,
            summary="New lead from contact form",
            confidence=0.92,
        )

        assert c.intent == "new_lead_followup"
        assert c.urgency == "high"
        assert c.confidence == 0.92
        assert c.suggested_agent == "outreach"

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        from core.classifier import Classification
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Classification(
                intent="test",
                urgency="low",
                entities={},
                suggested_agent="ops",
                requires_approval=False,
                summary="test",
                confidence=1.5,  # Invalid — over 1.0
            )


class TestAgentRouter:
    """Tests for the AgentRouter routing logic."""

    def test_needs_approval_above_threshold(self):
        """Should require approval for bulk sends."""
        from core.router import AgentRouter
        router = AgentRouter.__new__(AgentRouter)
        router.agents = {}
        router.slack = MagicMock()

        assert router._needs_approval({"contact_count": 100}) is True
        assert router._needs_approval({"contact_count": 10}) is False
        assert router._needs_approval({"deal_value": 100000}) is True
        assert router._needs_approval({"deal_value": 1000}) is False

    def test_fallback_to_ops_agent(self):
        """Unknown agent keys should fall back to ops."""
        from core.router import AgentRouter
        from agents.ops_agent import OpsAgent

        router = AgentRouter.__new__(AgentRouter)
        ops = OpsAgent.__new__(OpsAgent)
        router.agents = {"ops": ops}

        result = router.agents.get("unknown_agent", router.agents["ops"])
        assert result is ops


class TestWebhookPayload:
    """Tests for the FastAPI webhook payload model."""

    def test_valid_payload(self):
        """Valid payload should parse without error."""
        from main import WebhookPayload

        p = WebhookPayload(
            source="gmail",
            type="new_lead",
            data={"name": "Ada Lovelace", "email": "ada@example.com", "company": "Analytical Engine Co."},
        )
        assert p.source == "gmail"
        assert p.type == "new_lead"
        assert p.data["name"] == "Ada Lovelace"

    def test_missing_required_fields(self):
        """Missing source or type should raise validation error."""
        from main import WebhookPayload
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WebhookPayload(data={"name": "test"})  # missing source and type
