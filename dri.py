"""Decision Reliability Index (DRI) for the Competitive Intelligence Agent."""
from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BASE_BANK = os.getenv("HINDSIGHT_BANK_ID", "competitive-intel-demo")

# Verbs are listed in base form and given an optional inflection suffix, because
# recalled memory is natural language: the dataset says "Dhan Mart matched
# them", "Dhan Mart put 'Price Promise' boards", "Dhan Mart rushed an in-house
# pilot". Matching only base forms silently missed 3 of the 4 real decisions and
# made the Outcome component of the DRI wrong.
_VERB = (
    r"(?:decided|chose|chosen|selected|adopted|rejected|rejects?|"
    r"implement(?:ed|s)?|test(?:ed|s)?|piloted|pilot(?:ed|s)?|"
    r"launch(?:ed|es)?|introduc(?:ed|es)|respond(?:ed|s)?|counter(?:ed|s)?|"
    r"investigat(?:ed|es)|opted|match(?:ed|es)?|match(?:ing)?|"
    r"put|puts|rush(?:ed|es)?|countering)"
)

_DECISION_PATTERNS = (
    rf"\bdhan mart\s+{_VERB}",
    r"\bdhan mart\s+(?:will|would|did)\s+"
    r"(?:run|test|pilot|match|target|focus|use|offer|launch|continue|expand|avoid|maintain|investigate)",
)

# Substring markers, so a base form covers its inflections: "success" matches
# "SUCCESS"/"successful"/"successfully", "fail" matches "FAILED"/"failure".
_OUTCOME_MARKERS = (
    "outcome:",
    "resulted in",
    "result:",
    "success",
    "fail",
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


# One threshold decides both the headline badge and the score. Previously the
# badge came from the model's opinion while the score came from the measured
# reranker score, so the UI could show "No direct precedent" next to a DRI of
# 74. Deriving both from the same measured value makes them impossible to
# disagree.
PRECEDENT_THRESHOLD = 0.60


def has_precedent(precedent: float) -> bool:
    """Whether a measured precedent score counts as a direct precedent."""
    return precedent >= PRECEDENT_THRESHOLD


def _precedent(results: list[Any]) -> float:
    """Highest reranker score in the recall set, clamped to 0..1."""
    scores = [s for s in (_score(r, "reranker") for r in results) if s is not None]
    return max(0.0, min(1.0, max(scores, default=0.0)))


def _outcome(results: list[Any]) -> tuple[float, int, int]:
    """Fraction of decision-bearing memories that also carry outcome evidence."""
    decision_count = 0
    outcome_count = 0

    for result in results:
        text = _text(result)

        if not text or not _has_decision(text):
            continue

        decision_count += 1

        if _has_outcome(text):
            outcome_count += 1

    ratio = (outcome_count / decision_count) if decision_count else 0.0

    return max(0.0, min(1.0, ratio)), decision_count, outcome_count


def _build(
    precedent: float, outcome: float, decision_count: int, outcome_count: int
) -> dict[str, Any]:
    return {
        "score": round(100 * (0.6 * precedent + 0.4 * outcome)),
        "precedent": precedent,
        "outcome": outcome,
        "has_direct_precedent": has_precedent(precedent),
        "decision_memories": decision_count,
        "outcome_memories": outcome_count,
    }


def score_memories(memories: list[str], precedent: float) -> dict[str, Any]:
    """Score an already-recalled memory set.

    The agent and the DRI used to recall the same query twice and reach different
    conclusions. Now the plan hands over the memories it actually reasoned
    from, together with the precedent measured on that same recall, so the badge
    and the score are guaranteed to describe the same evidence.
    """
    decision_count = 0
    outcome_count = 0

    for text in memories:
        if not _has_decision(text):
            continue

        decision_count += 1

        if _has_outcome(text):
            outcome_count += 1

    outcome = (outcome_count / decision_count) if decision_count else 0.0
    outcome = max(0.0, min(1.0, outcome))

    return _build(
        max(0.0, min(1.0, precedent)),
        outcome,
        decision_count,
        outcome_count,
    )


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
        return _build(0.0, 0.0, 0, 0)

    client = _client()
    try:
        response = client.recall(
            bank_id=_bank(stage),
            query=query,
            budget="mid",
        )

        results = list(getattr(response, "results", []) or [])

        return _build(
            _precedent(results),
            *_outcome(results),
        )
    finally:
        client.close()
