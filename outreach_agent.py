import structlog
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from agents.base_agent import BaseAgent, AgentResult
from integrations.gmail_client import GmailClient
from config import settings

log = structlog.get_logger()

EMAIL_PROMPT = """\
You are an expert B2B sales writer. Write a highly personalized, concise outreach email.

Contact details:
- Name: {name}
- Company: {company}
- Role: {role}
- Context: {context}

Intent: {intent}

Rules:
- Subject line: compelling, under 9 words, no spam words
- Body: 3-4 short paragraphs, under 150 words total
- Tone: professional but warm, not salesy
- End with a single low-friction CTA (15-min call, quick question, etc.)
- Do NOT use filler phrases like "I hope this finds you well"

Return ONLY valid JSON in this exact format:
{{
  "subject": "...",
  "body": "..."
}}
"""


class OutreachAgent(BaseAgent):
    """Drafts and sends personalized outreach emails via Gmail."""

    def __init__(self):
        if settings.default_llm_provider == "anthropic":
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                anthropic_api_key=settings.anthropic_api_key,
                temperature=0.7,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                openai_api_key=settings.openai_api_key,
                temperature=0.7,
            )

        self.prompt = ChatPromptTemplate.from_template(EMAIL_PROMPT)
        self.chain = self.prompt | self.llm
        self.gmail = GmailClient()

    async def execute(self, run_id: str, classification, data: dict) -> AgentResult:
        name = data.get("name", "there")
        email = data.get("email", "")
        company = data.get("company", "your company")
        role = data.get("role", "")
        context = data.get("context", classification.summary)

        if not email:
            return AgentResult(
                actions=["Skipped — no email address in payload"],
                tokens_used=0,
            )

        log.info("OutreachAgent drafting email", run_id=run_id, recipient=email)

        # Generate personalized email
        response = await self.chain.ainvoke({
            "name": name,
            "company": company,
            "role": role,
            "context": context,
            "intent": classification.intent,
        })

        raw = response.content.strip()
        tokens = self._count_tokens(raw)

        try:
            import json
            # Strip markdown code fences if present
            clean = raw.replace("```json", "").replace("```", "").strip()
            email_data = json.loads(clean)
            subject = email_data["subject"]
            body = email_data["body"]
        except Exception as e:
            log.warning("Email JSON parse failed, using raw", error=str(e))
            subject = f"Quick note for {name}"
            body = raw

        # Send via Gmail
        send_result = await self.gmail.send_email(
            to=email,
            subject=subject,
            body=body,
        )

        actions = [
            f"Generated personalized email for {name} at {company}",
            f"Subject: '{subject}'",
            f"Sent to {email} — Message ID: {send_result.get('id', 'n/a')}",
        ]

        log.info("OutreachAgent complete", run_id=run_id, actions=actions)
        return AgentResult(actions=actions, tokens_used=tokens, output={"email_id": send_result.get("id")})
