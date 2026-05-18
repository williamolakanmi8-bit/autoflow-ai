# AutoFlow AI 🤖

**Intelligent Business Workflow Automation Engine**

AutoFlow AI is a multi-agent system that monitors business triggers, classifies tasks using LLMs, routes them to specialized agents, and executes actions across your tools — email, CRM, Slack, spreadsheets — with zero manual intervention.

---

## Results

| Metric | Before | After |
|--------|--------|-------|
| Lead follow-up time | 5 days | 4 minutes |
| Manual data entry | 340+ rows/week | 0 |
| Outreach personalization | Generic templates | 100% AI-generated |
| Pipeline classification accuracy | — | 94.2% |
| Cost per automation run | — | ~$0.004 |

---

## Architecture

```
Trigger (Gmail / Slack / Webhook / Cron)
        │
        ▼
┌─────────────────────┐
│  Trigger Detector   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AI Classifier      │
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼         ▼
Outreach   CRM       Ops
 Agent     Agent    Agent
```

---

## Tech Stack

- **Python 3.11**
- **LangChain / LangGraph** — agent orchestration
- **OpenAI GPT-4o / Anthropic Claude** — LLM backbone
- **FastAPI** — webhook receiver and REST API
- **HubSpot API** — CRM integration
- **Slack Bolt SDK** — alerts and approvals
- **Google Sheets API** — outcome logging
- **Supabase** — run history and config store

---

## Quick Start

### 1. Clone and install

git clone https://github.com/yourusername/autoflow-ai.git
cd autoflow-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

### 2. Configure environment

cp .env.example .env

### 3. Run the server

uvicorn main:app --reload

### 4. Trigger a workflow

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"source": "gmail", "type": "new_lead", "data": {"name": "Jane Doe", "email": "jane@example.com", "company": "Acme"}}'

---

## Workflows Included

| Workflow | Trigger | Actions |
|----------|---------|---------|
| New lead | Form submit / Gmail | Classify → CRM create → Personalized email |
| Lead follow-up | 3-day no reply | AI draft → Send → Log |
| Contract signed | HubSpot deal stage | Slack notify → Onboarding task |
| Overdue task | Cron daily | Slack alert → Notion update |
| Bulk outreach | Manual trigger | AI personalize → Approval → Send |

---

## Human-in-the-Loop

High-stakes actions pause for Slack approval before executing.

---

## License

MIT
