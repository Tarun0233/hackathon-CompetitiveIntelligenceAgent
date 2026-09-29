"""
FastAPI backend for the Competitive Intelligence Agent.

This is a thin HTTP layer over the *existing* agent.py / dri.py. It does not
reimplement any memory logic - the agent and DRI modules remain the single
source of truth, so the Streamlit UI (app.py) and this API stay in lockstep.

The reason this layer exists: Streamlit cannot stream incremental progress
from a single button click, so the original 7-step learning cycle painted all
its steps at once. Here each step is emitted over SSE the moment the real
backend call it represents finishes.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from datetime import date
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import agent
import dri
from synthetic_data import DEMO_EVENTS

load_dotenv()

app = FastAPI(
    title="Competitive Intelligence Agent API",
    version="1.0.0",
    description="Hindsight-backed competitive intelligence with a live learning cycle.",
)

# The Vite dev server runs on 5173; allow it during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_STAGES = ("cold", "early", "full", "live")


# ============================================================
# EVENT-LOOP PINNING  (important)
# ============================================================
#
# agent.py caches one global Hindsight client, whose aiohttp connection pool
# binds itself to the first event loop that uses it. Its sync methods bridge
# async->sync via loop.run_until_complete() on asyncio.get_event_loop().
#
# FastAPI runs *sync* endpoints in a worker THREAD POOL, and each thread gets
# its own event loop. So a second request would reuse a pool attached to a
# different loop and aiohttp raises:
#
#     RuntimeError: Timeout context manager should be used inside a task
#
# Pinning every agent call to ONE dedicated thread guarantees a single event
# loop for the process, so the cached client stays valid. Do not "fix" this by
# removing the executor - it would reintroduce the intermittent 500s.

_AGENT_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="hindsight-loop",
)


async def call_agent(fn, *args, **kwargs) -> Any:
    """Run a blocking agent/dri call on the pinned single-thread executor."""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _AGENT_EXECUTOR,
        functools.partial(fn, *args, **kwargs),
    )


# ============================================================
# SERIALISATION
# ============================================================

def _event_field(event: Any, field: str, default: Any = "") -> Any:
    """Events may be dicts or objects depending on the source module."""

    if isinstance(event, dict):
        return event.get(field, default)

    return getattr(event, field, default)


def _to_jsonable(value: Any) -> Any:
    """Convert Plan dataclasses (and nested containers) into plain JSON types."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)

    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]

    return str(value)


def _safe_dri(stage: str, query: str) -> dict[str, Any]:
    """DRI must never break a response - degrade to an 'unavailable' card."""

    try:
        return dri.calculate_dri(stage=stage, query=query)

    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as a note
        return {"score": None, "precedent": 0.0, "outcome": 0.0, "error": str(exc)}


async def _analyze_with_dri(stage: str, question: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the plan and its DRI from a single recall.

    These used to be two independent Hindsight retrievals for the same query, so
    the precedent badge and the reliability score could contradict each other
    (e.g. "No direct precedent" beside a DRI of 74). One recall now feeds both.
    """

    memories, precedent = await call_agent(
        agent.recall_with_precedent,
        stage,
        question,
    )

    plan = await call_agent(
        agent.analyze,
        stage,
        question,
        precedent=precedent,
        memories=memories,
    )
    scored = await call_agent(dri.score_memories, memories, precedent)

    return _to_jsonable(plan), scored


# ============================================================
# REQUEST MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    stage: str = Field(default="full")
    question: str = Field(min_length=1)


class LearnRequest(AnalyzeRequest):
    event_title: str
    event_date: str
    decision: str
    outcome_note: str = ""
    has_direct_precedent: bool = False
    confidence: str = "low"
    recommendation: str = ""
    general_reasoning: str = ""
    avoid: str = ""
    memories: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class PatternsRequest(BaseModel):
    stage: str = Field(default="full")


# ============================================================
# CREDENTIAL PREFLIGHT
# ============================================================
# Anyone who clones this repo gets no .env (it is gitignored on purpose), so the
# first thing a fresh clone does is fail on a bare KeyError. Translate the two
# required keys into one actionable message before the agent is ever called.
REQUIRED_ENV = {
    "HINDSIGHT_API_KEY": "Hindsight Cloud key - https://ui.hindsight.vectorize.io",
    "GROQ_API_KEY": "Groq key - https://groq.com/ (free tier)",
}


def missing_env() -> list[str]:
    """Names of required credentials that are absent or blank."""
    return [key for key in REQUIRED_ENV if not os.getenv(key)]


def require_env() -> None:
    """Fail fast with setup instructions when credentials are missing."""
    missing = missing_env()

    if not missing:
        return

    lines = [
        f"- {key}: {REQUIRED_ENV[key]}" for key in missing
    ]
    raise HTTPException(
        status_code=503,
        detail=(
            "Missing credentials: "
            + ", ".join(missing)
            + ". Copy .env.example to .env, fill in the keys, then restart "
            "the server. Full walkthrough in GUIDE.md."
        ),
    )


# ============================================================
# READ ENDPOINTS
# ============================================================

@app.get("/api/health")
def health() -> dict[str, Any]:
    """Liveness probe that also reports whether credentials are configured."""

    return {
        "status": "ok",
        "hindsight_configured": bool(os.getenv("HINDSIGHT_API_KEY")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "bank": os.getenv("HINDSIGHT_BANK_ID", "competitive-intel-demo"),
        "stages": list(VALID_STAGES),
    }


@app.get("/api/events")
def list_events() -> list[dict[str, Any]]:
    """Competitor events powering the sidebar picker."""

    events = []

    for event in DEMO_EVENTS:
        title = _event_field(event, "title", "")

        if not title:
            continue

        events.append(
            {
                "title": title,
                "date": str(
                    _event_field(event, "date", date.today().isoformat())
                ),
                "description": _event_field(event, "description", ""),
            }
        )

    return events


async def get_dri(stage: str, query: str) -> dict[str, Any]:
    require_env()
    return await call_agent(_safe_dri, stage, query)


@app.post("/api/patterns")
async def patterns(body: PatternsRequest) -> dict[str, str]:
    require_env()
    text = await call_agent(agent.reflect_patterns, body.stage)
    return {"patterns": text}


@app.post("/api/analyze")
async def analyze(body: AnalyzeRequest) -> dict[str, Any]:
    """Recall memory, generate a counter-plan, and score its reliability."""
    require_env()
    stage = body.stage if body.stage in VALID_STAGES else "full"
    question = body.question.strip()

    try:
        plan, scored = await _analyze_with_dri(stage, question)

    except Exception as exc:  # noqa: BLE001 - returned to the UI as a message
        raise HTTPException(
            status_code=502,
            detail=f"Analysis failed: {exc}",
        ) from exc

    return {
        "stage": stage,
        "question": question,
        "plan": plan,
        "dri": scored,
    }


# ============================================================
# LEARNING CYCLE — real per-step Server-Sent Events
# ============================================================

# Step labels come from agent.py so the Streamlit UI, this API, and the React
# console all describe the same cycle.
LEARNING_STEPS = list(agent.LEARNING_STEPS)


@app.get("/api/learning-steps")
def learning_steps() -> dict[str, list[str]]:
    return {"steps": LEARNING_STEPS}


def _sse(event: str, data: Any) -> str:
    """Format one SSE frame."""

    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/learn")
async def learn(body: LearnRequest) -> StreamingResponse:
    """
    Run the full learning cycle, emitting each step as it genuinely completes.

    Mirrors agent.learn_from_decision, but decomposed so the UI can show real
    progress instead of a single blocking call. agent.py remains the source of
    truth for *what* each step does.
    """

    stage = "live"
    request_text = body.question.strip()

    plan = agent.Plan(
        has_direct_precedent=body.has_direct_precedent,
        confidence=body.confidence,
        recommendation=body.recommendation,
        general_reasoning=body.general_reasoning,
        avoid=body.avoid,
        memories=body.memories,
        evidence=body.evidence,
    )

    async def stream() -> AsyncIterator[str]:
        yield _sse("steps", {"steps": LEARNING_STEPS})
        yield _sse("status", {"step": 0, "state": "active"})

        try:
            # DRI "before" MUST be measured before the decision is written,
            # otherwise both figures include the new memory and the before/after
            # comparison always shows a zero delta.
            dri_before = await call_agent(_safe_dri, stage, request_text)

            # --- STEP 0/1: persist the decision to Live memory -----------
            saved = await call_agent(
                agent.record_decision,
                stage=stage,
                event_title=body.event_title,
                event_date=body.event_date,
                plan=plan,
                decision=body.decision,
                outcome_note=body.outcome_note,
            )

            yield _sse("status", {"step": 0, "state": "completed"})
            yield _sse("status", {"step": 1, "state": "completed"})
            yield _sse("saved", _to_jsonable(saved))
            yield _sse("status", {"step": 2, "state": "active"})

            # --- STEP 2/3: confirm the new memory is recallable ---------
            updated_memories, was_recalled = await call_agent(
                agent._wait_for_memory,
                stage=stage,
                query=request_text,
                saved_text=saved["saved_text"],
            )

            yield _sse("status", {"step": 2, "state": "completed"})
            yield _sse("status", {"step": 3, "state": "completed"})
            yield _sse("status", {"step": 4, "state": "active"})

            # --- STEP 4/5: re-run the analysis on the updated memory ----
            updated_memories, updated_precedent = await call_agent(
                agent.recall_with_precedent,
                stage,
                request_text,
            )

            updated_plan = await call_agent(
                agent.analyze,
                stage,
                request_text,
                precedent=updated_precedent,
                memories=updated_memories,
            )

            yield _sse("status", {"step": 4, "state": "completed"})
            yield _sse("status", {"step": 5, "state": "completed"})

            after_text = updated_plan.recommendation.strip()
            before_text = plan.recommendation.strip()

            recommendation_changed = before_text.lower() != after_text.lower()
            memory_evidence_used = len(updated_plan.evidence) > 0

            dri_after = await call_agent(_safe_dri, stage, request_text)

            learning_complete = was_recalled and memory_evidence_used

            yield _sse("result", {
                "saved": _to_jsonable(saved),
                "before": _to_jsonable(plan),
                "after": _to_jsonable(updated_plan),
                "updated_memories": updated_memories,
                "saved_memory_recalled": was_recalled,
                "memory_evidence_used": memory_evidence_used,
                "recommendation_changed": recommendation_changed,
                "learning_complete": learning_complete,
                "dri_before": dri_before,
                "dri_after": dri_after,
            })

            yield _sse(
                "status",
                {
                    "step": 6,
                    "state": "completed" if learning_complete else "active",
                },
            )
            yield _sse("done", {"ok": True})

        except Exception as exc:  # noqa: BLE001 - reported to the UI
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {"ok": False})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
