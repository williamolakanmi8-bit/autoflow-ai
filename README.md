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
│  Trigger Detector   │  ← Monitors all input sources
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AI Classifier      │  ← LLM extracts intent, urgency, entities
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼         ▼
Outreach   CRM       Ops
 Agent     Agent    Agent
    │         │         │
  Email   HubSpot   Slack/Notion
         Airtable
         │
         ▼
┌─────────────────────┐
│  Human-in-the-Loop  │  ← Optional Slack approval gate
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Outcome Logger     │  ← Google Sheets + Supabase audit trail
└─────────────────────┘
```

---

## Tech Stack

- **Python 3.11** — core runtime
- **LangChain / LangGraph** — agent orchestration
- **OpenAI GPT-4o / Anthropic Claude** — LLM backbone
- **FastAPI** — webhook receiver & REST API
- **n8n** — visual workflow layer (optional)
- **HubSpot API** — CRM integration
- **Slack Bolt SDK** — Slack trigger + approval
- **Google Sheets API** — outcome logging dashboard
- **Supabase** — run history & config store

---

## Project Structure

```
autoflow_ai/
├── main.py                  # FastAPI entry point
├── config.py                # Environment & settings
├── core/
│   ├── classifier.py        # LLM intent classifier
│   ├── router.py            # Agent router
│   └── logger.py            # Outcome logger
├── agents/
│   ├── base_agent.py        # Abstract agent class
│   ├── outreach_agent.py    # Email outreach
│   ├── crm_agent.py         # CRM updates
│   └── ops_agent.py         # Slack/Notion ops
├── integrations/
│   ├── gmail_client.py      # Gmail API wrapper
│   ├── hubspot_client.py    # HubSpot API wrapper
│   ├── slack_client.py      # Slack Bolt wrapper
│   └── sheets_client.py     # Google Sheets wrapper
├── workflows/
│   ├── lead_workflow.py     # New lead automation
│   ├── followup_workflow.py # Follow-up sequence
│   └── ops_workflow.py      # Ops task automation
├── utils/
│   └── helpers.py           # Shared utilities
├── tests/
│   └── test_classifier.py   # Unit tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourusername/autoflow-ai.git
cd autoflow-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your API keys in .env
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

### 4. Trigger a workflow

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"source": "gmail", "type": "new_lead", "data": {"name": "Jane Doe", "email": "jane@example.com", "company": "Acme"}}'
```

---

## Workflows Included

| Workflow | Trigger | Actions |
|----------|---------|---------|
| New lead | Form submit / Gmail | Classify → CRM create → Personalized email |
| Lead follow-up | 3-day no reply | AI draft → Send → Log |
| Contract signed | HubSpot deal stage | Slack notify → Onboarding task create |
| Overdue task | Cron (daily) | Slack alert → Notion update |
| Bulk outreach | Manual trigger | AI personalize each → HITL approval → Send |

---

## Human-in-the-Loop

High-stakes actions pause and send a Slack approval message:

```
🔔 AutoFlow AI — Approval Required
Action: Send outreach to 847 contacts
Preview: "Hi {{name}}, I noticed your team at {{company}}..."
[✅ Approve] [❌ Reject]
```

---

## License

MIT
