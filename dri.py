"""Decision Reliability Index (DRI) for the Competitive Intelligence Agent."""
from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BASE_BANK = os.getenv("HINDSIGHT_BANK_ID", "competitive-intel-demo")

_DECISION_PATTERNS = (
    r"\bdhan mart\s+(?:decided|chose|selected|adopted|rejected|implemented|tested|piloted|launched|introduced|responded|countered|investigated|opted)\b",
    r"\bdhan mart\s+(?:will|would|did)\s+(?:run|test|pilot|match|target|focus|use|offer|launch|continue|expand|avoid|maintain|investigate)\b",
    r"\bdhan mart\s+(?:implemented|tested|piloted|introduced|launched)\b",
)

_OUTCOME_MARKERS = (
    "outcome:",
    "resulted in",
    "result:",
    "successful",
    "successfully",
    "failed",
    "failure",
    "profit",
    "profitable",
    "loss",
    "revenue",
    "margin",
    "retention",
    "repeat purchases",
    "conversion",
    "average order value",
    "incremental purchases",
    "customer response",
    "increased",
    "decreased",
    "improved",
    "reduced",
    "grew",
    "declined",
    "generated",
    "achieved",
    "impact",
)


def _bank(stage: str) -> str:
    return f"{BASE_BANK}-{stage}"


def _client() -> Hindsight:
    return Hindsight(
        base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
        api_key=os.environ["HINDSIGHT_API_KEY"],
    )


def _score(result: Any, field: str) -> float | None:
    scores = getattr(result, "scores", None)
    if scores is None:
        return None
    value = getattr(scores, field, None)
    if value is None and isinstance(scores, dict):
        value = scores.get(field)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _text(result: Any) -> str:
    return str(getattr(result, "text", "") or "").strip()


def _has_decision(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in _DECISION_PATTERNS)


def _has_outcome(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _OUTCOME_MARKERS)


def calculate_dri(stage: str, query: str) -> dict[str, Any]:
    """Calculate DRI = 100 * (0.6 * P + 0.4 * O).

    P: highest Hindsight reranker score returned for the current query.
    O: fraction of recalled Dhan Mart decision-bearing memories that also contain
       explicit outcome evidence.

    The component values are returned for debugging/validation, while the UI can
    display only the final score.
    """
    query = (query or "").strip()
    if not query:
        return {"score": 0, "precedent": 0.0, "outcome": 0.0, "decision_memories": 0, "outcome_memories": 0}

    client = _client()
    try:
        response = client.recall(
            bank_id=_bank(stage),
            query=query,
            budget="mid",
        )

        results = list(getattr(response, "results", []) or [])

        rerankers = [s for s in (_score(r, "reranker") for r in results) if s is not None]
        precedent = max(rerankers, default=0.0)
        precedent = max(0.0, min(1.0, precedent))

        decision_count = 0
        outcome_count = 0
        for result in results:
            text = _text(result)
            if not text or not _has_decision(text):
                continue
            decision_count += 1
            if _has_outcome(text):
                outcome_count += 1

        outcome = (outcome_count / decision_count) if decision_count else 0.0
        outcome = max(0.0, min(1.0, outcome))

        score = round(100 * (0.6 * precedent + 0.4 * outcome))

        return {
            "score": score,
            "precedent": precedent,
            "outcome": outcome,
            "decision_memories": decision_count,
            "outcome_memories": outcome_count,
        }
    finally:
        client.close()
