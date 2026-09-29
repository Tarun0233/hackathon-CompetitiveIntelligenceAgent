"""Offline tests for the DRI scoring logic.

These exercise pure functions only, so the suite runs with no API keys and no
network access. That matters for anyone who clones the repo: `pytest` should
pass on a fresh clone before they have configured Hindsight or Groq.

Tests that need live services live in recall_probe.py, which is a script and is
deliberately not collected by pytest.
"""

import dri
from synthetic_data import HISTORY


def test_outcome_marker_detects_failure() -> None:
    assert dri._has_outcome("Outcome: FAILED. Margin fell from 7.9% to 6.6%.")
    assert dri._has_outcome("The pilot was a failure, so it was cancelled.")
    assert dri._has_outcome("Footfall increased 8% in six weeks.")


def test_outcome_marker_detects_bare_success() -> None:
    # "SUCCESS" is the word the dataset actually uses. It must be caught even
    # though it is neither "successful" nor "successfully".
    assert dri._has_outcome("Outcome: SUCCESS. Footfall rose 8% in six weeks.")


def test_no_outcome_marker_on_plain_event() -> None:
    assert not dri._has_outcome("Sitara Bazaar cut prices on 40 staple items.")
    assert not dri._has_outcome("Sitara Bazaar opened three new stores.")


def test_decision_pattern_detects_inflected_verbs() -> None:
    # Inflected forms, exactly as they appear in the retained history.
    assert dri._has_decision("Dhan Mart matched them on 2026-03-26.")
    assert dri._has_decision("Dhan Mart put 'Price Promise' boards up.")
    assert dri._has_decision("Dhan Mart rushed an in-house 45-minute delivery pilot.")
    assert dri._has_decision("Dhan Mart decided to test a delivery pilot.")
    assert dri._has_decision("Dhan Mart will avoid a capital-intensive warehouse.")


def test_every_real_decision_memory_is_detected() -> None:
    """Regression guard: all four our-response memories must count.

    The scorer previously matched only base verb forms, so 3 of 4 were invisible
    and the Outcome component of the DRI was wrong.
    """
    ours = [m for m in HISTORY if m.kind == "our-response"]
    assert len(ours) == 4
    missed = [m.content[:50] for m in ours if not dri._has_decision(m.content)]
    assert not missed, f"decision memories not detected: {missed}"


def test_all_outcome_memories_are_detected() -> None:
    outcomes = [m for m in HISTORY if m.kind == "outcome"]
    assert len(outcomes) == 4
    missed = [m.content[:50] for m in outcomes if not dri._has_outcome(m.content)]
    assert not missed, f"outcome memories not detected: {missed}"


def test_no_decision_pattern_for_competitor_only_text() -> None:
    assert not dri._has_decision("Sitara Bazaar launched Sitara Express.")
    assert not dri._has_decision("Dhan Mart is a grocery retailer in Hyderabad.")


def test_bank_naming_is_stage_suffixed() -> None:
    assert dri._bank("cold") == f"{dri.BASE_BANK}-cold"
    assert dri._bank("full") == f"{dri.BASE_BANK}-full"
    assert dri._bank("live") == f"{dri.BASE_BANK}-live"


# --- Badge / DRI consistency -------------------------------------------------
# The UI once showed "No direct precedent" beside a DRI of 74, because the badge
# came from the model while the score came from a second, independent recall.
# Both now derive from one measured precedent value, so they cannot disagree.


def test_precedent_threshold_boundary() -> None:
    assert not dri.has_precedent(0.0)
    assert not dri.has_precedent(0.59)
    assert dri.has_precedent(0.60)
    assert dri.has_precedent(0.94)


def test_high_precedent_sets_badge_true() -> None:
    result = dri.score_memories(["Dhan Mart matched them on 2026-03-26."], 0.94)
    assert result["has_direct_precedent"] is True
    assert result["score"] > 0


def test_low_precedent_forces_no_badge_even_with_evidence() -> None:
    result = dri.score_memories(
        ["Dhan Mart matched them on 2026-03-26."],
        0.03,
    )
    assert result["has_direct_precedent"] is False


def test_empty_query_is_fully_zeroed() -> None:
    result = dri.calculate_dri("full", "")
    assert result["score"] == 0
    assert result["precedent"] == 0.0
    assert result["outcome"] == 0.0
    assert result["has_direct_precedent"] is False


def test_score_memories_counts_outcomes_in_text() -> None:
    # Only text that both names a Dhan Mart action and carries outcome evidence
    # counts toward the Outcome component, so the ratio here is 1/2.
    memories = [
        "Dhan Mart matched Sitara's price cuts in March 2026.",
        "Dhan Mart launched a delivery pilot. Outcome: FAILED.",
    ]
    result = dri.score_memories(memories, 0.8)
    assert result["decision_memories"] == 2
    assert result["outcome_memories"] == 1
    assert result["outcome"] == 0.5


def test_bare_outcome_memory_is_not_a_decision() -> None:
    # Outcome records are phrased as "Outcome (...) of matching ..." with no
    # Dhan Mart verb, so they are outcomes without a decision. Documented here
    # because it is the reason the Outcome component stays below 1.0.
    text = "Outcome (2026-05-10) of matching Sitara's price cuts: FAILED."
    assert dri._has_outcome(text)
    assert not dri._has_decision(text)


# --- analyze(): the badge must follow the measured score ---------------------


def _stub_llm(payload: dict) -> object:
    import json

    def llm(_prompt: str) -> str:
        return json.dumps(payload)

    return llm


def _plan_with(precedent: float, memories: list[str]) -> object:
    import agent

    llm = _stub_llm({
        "confidence": "high",
        "recommendation": "Hold prices steady.",
        "evidence": [{"memory": "M1", "why": "margin fell"}],
        "general_reasoning": "general",
        "avoid": "a price war",
    })

    return agent.analyze(
        "full",
        "event",
        recall_fn=lambda *a, **k: memories,
        llm_fn=llm,
        precedent=precedent,
        memories=memories,
    )


def test_analyze_badge_follows_measured_precedent() -> None:
    # A high measured precedent must show the badge even if the model said
    # nothing about it, and a low one must not.
    assert _plan_with(0.94, ["Dhan Mart matched them."]).has_direct_precedent is True
    assert _plan_with(0.03, ["Dhan Mart matched them."]).has_direct_precedent is False


def test_analyze_badge_ignores_model_opinion() -> None:
    # The model previously owned this flag and could contradict the DRI.
    import json

    def llm(_prompt: str) -> str:
        return json.dumps({
            "has_direct_precedent": True,
            "confidence": "medium",
            "recommendation": "r",
            "evidence": [],
            "general_reasoning": "g",
            "avoid": "",
        })

    import agent

    plan = agent.analyze(
        "full",
        "event",
        recall_fn=lambda *a, **k: ["Dhan Mart matched them."],
        llm_fn=llm,
        precedent=0.02,
        memories=["Dhan Mart matched them."],
    )

    assert plan.has_direct_precedent is False


def test_analyze_never_recalls_twice() -> None:
    import agent

    calls = []

    def counting_recall(stage: str, event: str) -> list[str]:
        calls.append((stage, event))
        return ["Dhan Mart matched them."]

    agent.analyze(
        "full",
        "event",
        recall_fn=counting_recall,
        llm_fn=_stub_llm({
            "confidence": "low",
            "recommendation": "r",
            "evidence": [],
            "general_reasoning": "g",
            "avoid": "",
        }),
        precedent=0.5,
        memories=["Dhan Mart matched them."],
    )

    assert calls == []


def test_analyze_confidence_downgraded_without_memories() -> None:
    # Regression: a missing confidence assignment raised
    # "cannot access local variable 'confidence'" and surfaced as a 502.
    import agent

    plan = agent.analyze(
        "cold",
        "event",
        recall_fn=lambda *a, **k: [],
        llm_fn=_stub_llm({
            "confidence": "high",
            "recommendation": "general advice",
            "evidence": [],
            "general_reasoning": "g",
            "avoid": "",
        }),
        precedent=0.0,
        memories=[],
    )

    assert plan.confidence == "low"
    assert plan.has_direct_precedent is False
    assert plan.recommendation == "general advice"
