import hashlib
import hmac
import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any

from config import settings
from core.classifier import TriggerClassifier
from core.router import AgentRouter
from core.logger import OutcomeLogger

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AutoFlow AI starting up")
    app.state.classifier = TriggerClassifier()
    app.state.router = AgentRouter()
    app.state.outcome_logger = OutcomeLogger()
    yield
    log.info("AutoFlow AI shutting down")


app = FastAPI(
    title="AutoFlow AI",
    description="Intelligent Business Workflow Automation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebhookPayload(BaseModel):
    source: str           # gmail | slack | hubspot | form | cron
    type: str             # new_lead | contract_signed | overdue_task | etc.
    data: dict[str, Any]
    timestamp: Optional[float] = None


class WorkflowResult(BaseModel):
    run_id: str
    status: str
    agent: str
    actions_taken: list[str]
    duration_ms: int
    tokens_used: int


def verify_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify HMAC signature on incoming webhooks."""
    expected = hmac.new(
        settings.webhook_secret.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_trigger(
    payload: WebhookPayload,
    classifier: TriggerClassifier,
    router: AgentRouter,
    outcome_logger: OutcomeLogger,
):
    """Core pipeline: classify → route → execute → log."""
    start = time.time()
    run_id = f"run_{int(start * 1000)}"

    try:
        log.info("Processing trigger", run_id=run_id, source=payload.source, type=payload.type)

        # Stage 1: Classify
        classification = await classifier.classify(payload)
        log.info("Classified", run_id=run_id, intent=classification.intent, urgency=classification.urgency)

        # Stage 2: Route & Execute
        result = await router.route_and_execute(run_id, classification, payload.data)

        # Stage 3: Log outcome
        duration_ms = int((time.time() - start) * 1000)
        await outcome_logger.log(
            run_id=run_id,
            source=payload.source,
            intent=classification.intent,
            agent=result.agent_name,
            actions=result.actions_taken,
            status="success",
            duration_ms=duration_ms,
            tokens_used=result.tokens_used,
        )

        log.info("Run complete", run_id=run_id, duration_ms=duration_ms)

    except Exception as e:
        log.error("Run failed", run_id=run_id, error=str(e))
        await outcome_logger.log(
            run_id=run_id,
            source=payload.source,
            intent="unknown",
            agent="none",
            actions=[],
            status=f"error: {str(e)}",
            duration_ms=int((time.time() - start) * 1000),
            tokens_used=0,
        )


@app.post("/webhook", response_model=dict)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive and queue an incoming trigger."""
    body = await request.body()

    # Signature check (skip if no secret configured)
    if settings.webhook_secret:
        sig = request.headers.get("X-AutoFlow-Signature", "")
        if not verify_webhook_signature(body, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        data = json.loads(body)
        payload = WebhookPayload(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    background_tasks.add_task(
        process_trigger,
        payload,
        request.app.state.classifier,
        request.app.state.router,
        request.app.state.outcome_logger,
    )

    return {"status": "queued", "source": payload.source, "type": payload.type}


@app.post("/trigger/manual", response_model=dict)
async def manual_trigger(payload: WebhookPayload, background_tasks: BackgroundTasks, request: Request):
    """Manually fire a workflow (for testing or scheduled runs)."""
    background_tasks.add_task(
        process_trigger,
        payload,
        request.app.state.classifier,
        request.app.state.router,
        request.app.state.outcome_logger,
    )
    return {"status": "queued", "message": "Workflow triggered manually"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": time.time()}


@app.get("/runs/recent")
async def recent_runs(request: Request, limit: int = 20):
    """Fetch recent run history from Supabase."""
    return await request.app.state.outcome_logger.get_recent_runs(limit=limit)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
