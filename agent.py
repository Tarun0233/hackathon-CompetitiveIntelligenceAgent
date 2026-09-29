"""Competitive-intelligence agent: recall -> reason -> cite evidence -> learn from decisions."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv
from hindsight_client import Hindsight
from openai import OpenAI

from synthetic_data import COMPANY

load_dotenv()

BASE_BANK = os.getenv("HINDSIGHT_BANK_ID", "competitive-intel-demo")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Ordered steps of the learning cycle. Single source of truth for every
# frontend (Streamlit and React both read this) so the console can never drift
# out of sync with what learn_from_decision() actually does.
LEARNING_STEPS = (
    "Saving decision to Hindsight",
    "Decision saved to Live memory",
    "Recalling updated experience",
    "Updated experience recalled from Hindsight",
    "Re-evaluating with Groq",
    "Updated recommendation generated",
    "Learning complete",
)


SYSTEM_PROMPT = f"""You are a strategy advisor for {COMPANY['name']}, a {COMPANY['industry']}, watching its rival {COMPANY['competitor']}.
You receive a NEW competitor event and numbered MEMORIES recalled from the company's own history
(competitor moves, {COMPANY['name']}'s past responses, and their outcomes).

Rules:
- Cite only memories you were given, by id (M1, M2, ...). Never invent past events, numbers or outcomes.
- If no memory is a close precedent for this kind of move, set has_direct_precedent to false and say so plainly.
- Learn from both failed and successful past outcomes.
- Keep general strategy reasoning separate from memory evidence.
- If there are no memories at all, give sensible general advice and set confidence to "low".

Reply with ONLY a JSON object:
{{"has_direct_precedent": true|false,
 "confidence": "high"|"medium"|"low",
 "recommendation": "2-4 sentences",
 "evidence": [{{"memory": "M1", "why": "how it shapes the advice"}}],
 "general_reasoning": "what comes from general strategy, not from memory",
 "avoid": "one thing not to do, or empty string"}}
"""


@dataclass
class Plan:
    has_direct_precedent: bool
    confidence: str
    recommendation: str
    general_reasoning: str
    avoid: str
    memories: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)


def bank_for(stage: str) -> str:
    return f"{BASE_BANK}-{stage}"


_hs: Hindsight | None = None


def hindsight() -> Hindsight:
    global _hs

    if _hs is None:
        _hs = Hindsight(
            base_url=os.getenv(
                "HINDSIGHT_BASE_URL",
                "https://api.hindsight.vectorize.io",
            ),
            api_key=os.environ["HINDSIGHT_API_KEY"],
        )

    return _hs


def _is_missing_bank(err: Exception) -> bool:
    if "404" in str(err) or "not found" in str(err).lower():
        return True

    for attr in ("status_code", "code"):
        if getattr(err, attr, None) == 404:
            return True

    response = getattr(err, "response", None)

    if response is not None and getattr(response, "status_code", None) == 404:
        return True

    return False


def _recall_raw(stage: str, query: str, limit: int) -> list[str]:
    try:
        result = hindsight().recall(
            bank_id=bank_for(stage),
            query=query,
        )

    except Exception as err:
        if _is_missing_bank(err):
            return []

        raise

    return [m.text for m in result.results[:limit]]


def recall(stage: str, query: str, limit: int = 12) -> list[str]:
    """Recall relevant events and Dhan Mart's historical outcomes."""

    primary = _recall_raw(
        stage,
        query,
        limit,
    )

    outcomes_query = (
        f"{COMPANY['name']}'s own past responses to "
        f"{COMPANY['competitor']} and whether each one succeeded or failed"
    )

    secondary = _recall_raw(
        stage,
        outcomes_query,
        limit,
    )

    merged = []
    seen = set()

    for memory in primary + secondary:
        if memory not in seen:
            seen.add(memory)
            merged.append(memory)

    return merged


_groq: OpenAI | None = None

_FATAL_ERROR_MARKERS = (
    "401",
    "403",
    "invalid_api_key",
    "authentication",
)


def _groq_client() -> OpenAI:
    global _groq

    if _groq is None:
        _groq = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )

    return _groq


def ask_llm(user_prompt: str, retries: int = 3) -> str:
    last: Exception | None = None

    for attempt in range(retries):
        try:
            response = _groq_client().chat.completions.create(
                model=MODEL,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            return response.choices[0].message.content or ""

        except Exception as err:
            last = err

            if any(
                marker in str(err).lower()
                for marker in _FATAL_ERROR_MARKERS
            ):
                break

            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError(
        f"Groq failed after {retries} attempts: {last}"
    )


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end < 0:
        raise ValueError("No JSON object in model reply")

    return json.loads(text[start : end + 1])


def analyze(
    stage: str,
    event: str,
    recall_fn=recall,
    llm_fn=ask_llm,
) -> Plan:
    """Recall company memory and generate a counter-plan."""

    memories = recall_fn(stage, event)

    block = (
        "\n".join(
            f"M{i + 1}: {memory}"
            for i, memory in enumerate(memories)
        )
        or "(no memories yet)"
    )

    prompt = (
        f"NEW COMPETITOR EVENT:\n{event}\n\n"
        f"MEMORIES:\n{block}"
    )

    data = None

    for _ in range(2):
        try:
            data = _extract_json(llm_fn(prompt))
            break

        except (ValueError, json.JSONDecodeError):
            continue

    if data is None:
        raise RuntimeError(
            "Model did not return valid JSON twice"
        )

    evidence = []

    for item in data.get("evidence", []):
        memory_match = re.fullmatch(
            r"M(\d+)",
            str(item.get("memory", "")).strip(),
        )

        if (
            memory_match
            and 1 <= int(memory_match.group(1)) <= len(memories)
        ):
            index = int(memory_match.group(1)) - 1

            evidence.append(
                {
                    "id": f"M{memory_match.group(1)}",
                    "text": memories[index],
                    "why": item.get("why", ""),
                }
            )

    precedent = (
        bool(data.get("has_direct_precedent"))
        and bool(evidence)
    )

    confidence = data.get("confidence", "low")

    if not memories:
        confidence = "low"

    elif not evidence and confidence == "high":
        confidence = "medium"

    return Plan(
        precedent,
        confidence,
        data.get("recommendation", ""),
        data.get("general_reasoning", ""),
        data.get("avoid", ""),
        memories,
        evidence,
    )


def record_decision(
    stage: str,
    event_title: str,
    event_date: str,
    plan: Plan,
    decision: str,
    outcome_note: str = "",
) -> dict:
    """
    Save the user's decision to Hindsight.

    Only Live memory is writable.
    """

    if stage != "live":
        raise ValueError(
            "Only Live memory can record decisions. "
            "Cold, Early and Full are read-only."
        )

    text = (
        f"On {event_date}, for the competitor event "
        f"'{event_title}', Dhan Mart {decision} the plan: "
        f"{plan.recommendation}"
    )

    if outcome_note.strip():
        text += f" Outcome: {outcome_note.strip()}"

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        event_title.lower(),
    ).strip("-")

    doc_id = f"decision-{event_date}-{slug}"

    hindsight().retain(
        bank_id=bank_for("live"),
        content=text,
        context="Decision on counter-plan",
        timestamp=f"{event_date}T12:00:00Z",
        document_id=doc_id,
    )

    return {
        "saved_text": text,
        "document_id": doc_id,
        "bank_id": bank_for("live"),
    }


def _normalise_text(text: str) -> str:
    """Normalize text for loose memory matching."""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s%'-]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def _important_terms(text: str) -> set[str]:
    """
    Extract useful terms for verifying that Hindsight recalled
    the newly saved experience.

    This intentionally does NOT require an exact sentence match
    because Hindsight may rephrase retained memories.
    """

    normalized = _normalise_text(text)

    words = normalized.split()

    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "for",
        "on",
        "in",
        "with",
        "from",
        "that",
        "this",
        "is",
        "was",
        "are",
        "were",
        "their",
        "they",
        "it",
        "as",
        "by",
        "at",
        "be",
        "has",
        "have",
        "had",
        "our",
        "we",
        "dhan",
        "mart",
        "plan",
        "event",
    }

    return {
        word
        for word in words
        if len(word) >= 4
        and word not in stop_words
    }


def _memory_represents_saved_decision(
    saved_text: str,
    memory: str,
) -> bool:
    """
    Determine whether a recalled Hindsight memory represents
    the newly saved decision.

    Hindsight can rewrite/rephrase retained memories, so this
    uses meaningful term overlap rather than exact text matching.
    """

    saved_terms = _important_terms(saved_text)
    memory_terms = _important_terms(memory)

    if not saved_terms or not memory_terms:
        return False

    overlap = saved_terms.intersection(memory_terms)

    # Strong match:
    # at least 3 meaningful terms and at least 30% of the
    # saved decision's meaningful vocabulary is represented.
    if len(overlap) >= 3 and (
        len(overlap) / len(saved_terms)
    ) >= 0.30:
        return True

    # Date + competitor/event signal is also strong evidence.
    saved_normalized = _normalise_text(saved_text)
    memory_normalized = _normalise_text(memory)

    date_match = re.search(
        r"\b20\d{2}-\d{2}-\d{2}\b",
        saved_normalized,
    )

    if date_match and date_match.group(0) in memory_normalized:
        if len(overlap) >= 2:
            return True

    return False


def _wait_for_memory(
    stage: str,
    query: str,
    saved_text: str,
    attempts: int = 5,
    delay: float = 0.8,
) -> tuple[list[str], bool]:
    """
    Poll Hindsight briefly until the newly saved experience
    becomes available to recall.

    Returns:
        (recalled_memories, saved_memory_recalled)
    """

    latest_memories: list[str] = []

    for attempt in range(attempts):
        latest_memories = recall(
            stage,
            query,
            limit=12,
        )

        for memory in latest_memories:
            if _memory_represents_saved_decision(
                saved_text,
                memory,
            ):
                return latest_memories, True

        if attempt < attempts - 1:
            time.sleep(delay)

    return latest_memories, False


def learn_from_decision(
    event_title: str,
    event_date: str,
    request_text: str,
    plan: Plan,
    decision: str,
    outcome_note: str = "",
) -> dict:
    """
    Complete the real learning cycle:

        1. Save the user's decision to Live Hindsight.
        2. Recall the updated experience.
        3. Re-run the strategy analysis using updated memory.
        4. Return before/after plans and learning evidence.
    """

    # ------------------------------------------------------------
    # STEP 1 — SAVE DECISION
    # ------------------------------------------------------------

    saved = record_decision(
        stage="live",
        event_title=event_title,
        event_date=event_date,
        plan=plan,
        decision=decision,
        outcome_note=outcome_note,
    )

    # ------------------------------------------------------------
    # STEP 2 — RECALL UPDATED MEMORY
    # ------------------------------------------------------------

    updated_memories, saved_memory_recalled = _wait_for_memory(
        stage="live",
        query=request_text,
        saved_text=saved["saved_text"],
    )

    # ------------------------------------------------------------
    # STEP 3 — RE-EVALUATE WITH GROQ
    # ------------------------------------------------------------

    updated_plan = analyze(
        stage="live",
        event=request_text,
    )

    # ------------------------------------------------------------
    # STEP 4 — COMPARE RECOMMENDATIONS
    # ------------------------------------------------------------

    before_recommendation = (
        plan.recommendation.strip()
    )

    after_recommendation = (
        updated_plan.recommendation.strip()
    )

    recommendation_changed = (
        before_recommendation.lower()
        != after_recommendation.lower()
    )

    # ------------------------------------------------------------
    # STEP 5 — CHECK WHETHER UPDATED PLAN HAS MEMORY EVIDENCE
    # ------------------------------------------------------------

    memory_evidence_used = len(
        updated_plan.evidence
    ) > 0

    return {
        "saved": saved,

        "before": plan,

        "after": updated_plan,

        "updated_memories": updated_memories,

        "saved_memory_recalled": saved_memory_recalled,

        "memory_evidence_used": memory_evidence_used,

        "recommendation_changed": recommendation_changed,

        "learning_complete": (
            saved_memory_recalled
            and memory_evidence_used
        ),
    }


def reflect_patterns(stage: str) -> str:
    try:
        return hindsight().reflect(
            bank_id=bank_for(stage),
            query=(
                "What has worked and what has failed for Dhan Mart "
                "when responding to Sitara Bazaar?"
            ),
        ).text

    except Exception as err:
        return f"(reflect unavailable: {err})"