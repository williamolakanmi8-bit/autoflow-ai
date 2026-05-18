from dataclasses import dataclass
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from config import settings

log = structlog.get_logger()

CLASSIFICATION_PROMPT = """\
You are an AI classifier for a business workflow automation system.

Given an incoming trigger, extract:
1. intent — the primary business action required
2. urgency — how quickly this must be handled (high/medium/low)
3. entities — key data extracted (name, email, company, deal_value, etc.)
4. suggested_agent — which agent should handle this (outreach|crm|ops)
5. requires_approval — true if this action is high-stakes (bulk send, large deal, financial change)
6. summary — one sentence describing what happened

Incoming trigger:
Source: {source}
Type: {type}
Data: {data}

{format_instructions}
"""


class Classification(BaseModel):
    intent: str = Field(description="Primary business intent, e.g. 'new_lead_followup'")
    urgency: str = Field(description="high | medium | low")
    entities: dict = Field(description="Extracted entities from the trigger data")
    suggested_agent: str = Field(description="outreach | crm | ops")
    requires_approval: bool = Field(description="Whether human approval is needed")
    summary: str = Field(description="One-sentence summary of the trigger")
    confidence: float = Field(description="Classifier confidence 0.0-1.0", ge=0.0, le=1.0)


class TriggerClassifier:
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=Classification)

        if settings.default_llm_provider == "anthropic":
            self.llm = ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                anthropic_api_key=settings.anthropic_api_key,
                temperature=0,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=settings.openai_api_key,
                temperature=0,
            )

        self.prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
        self.chain = self.prompt | self.llm | self.parser

    async def classify(self, payload) -> Classification:
        """Classify an incoming trigger using the LLM."""
        try:
            result = await self.chain.ainvoke({
                "source": payload.source,
                "type": payload.type,
                "data": str(payload.data),
                "format_instructions": self.parser.get_format_instructions(),
            })
            log.info(
                "Classification complete",
                intent=result.intent,
                urgency=result.urgency,
                agent=result.suggested_agent,
                confidence=result.confidence,
            )
            return result
        except Exception as e:
            log.error("Classification failed", error=str(e))
            # Fallback classification
            return Classification(
                intent=payload.type,
                urgency="medium",
                entities=payload.data,
                suggested_agent="ops",
                requires_approval=False,
                summary=f"Unclassified trigger from {payload.source}",
                confidence=0.0,
            )
