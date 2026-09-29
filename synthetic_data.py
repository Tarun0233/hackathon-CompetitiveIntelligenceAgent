"""
Synthetic-but-realistic data for the Competitive Intelligence agent (retail version).

Story: Dhan Mart, a Hyderabad-based everyday-low-price supermarket chain, tracks one
rival, Sitara Bazaar (a larger, app-driven hypermarket chain). Over Mar-Sep 2026
Sitara makes 8 moves. Dhan Mart responded to 4 of them and recorded each outcome:
two failures, two successes. Those lessons are the memory the agent should use.

Two live demo events (DEMO_EVENTS) arrive after the history:
  - DEMO-1: a festival price cut -> has a clear precedent (E1/R1 failed; R2/R4 worked)
  - DEMO-2: an acquisition of a farm-produce startup -> NO direct precedent, so the
            agent must reason from related lessons and say so.

All names, numbers and dates are fictional. Any resemblance to real chains is coincidental.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COMPANY = {
    "name": "Dhan Mart",
    "industry": "Everyday-low-price supermarket chain, Hyderabad region",
    "size": "38 stores, ~6,500 employees, owns most of its store properties",
    "competitor": "Sitara Bazaar",
}


@dataclass(frozen=True)
class Memory:
    id: str
    kind: str          # company-profile | competitor-event | our-response | outcome
    date: str          # ISO date the memory is "written" (fake timestamp)
    context: str       # short label, passed to Hindsight as context
    content: str       # the natural-language fact retained
    source: str = ""   # where a real system would have found it
    meta: dict = field(default_factory=dict)

    @property
    def timestamp(self) -> str:
        return f"{self.date}T09:00:00Z"


# ---------------------------------------------------------------- company profile
PROFILE: list[Memory] = [
    Memory(
        id="PROFILE-1", kind="company-profile", date="2026-03-01",
        context="Dhan Mart strengths",
        content=(
            "Dhan Mart strengths: customers trust it for everyday low prices on staples, most stores "
            "are owned (no rent), and inventory and supplier terms are tight, which keeps costs low. "
            "Shelf availability of top staples is normally above 96%."
        ),
        source="internal strategy doc",
    ),
    Memory(
        id="PROFILE-2", kind="company-profile", date="2026-03-01",
        context="Dhan Mart limits",
        content=(
            "Dhan Mart limits: store operating margin is thin at about 7.9%, staff are lean, and there "
            "is no delivery infrastructure and only a basic app. Capital is committed to opening 12 new "
            "stores this financial year. The most common customer complaint is the freshness of fruit "
            "and vegetables."
        ),
        source="internal strategy doc",
    ),
]

# ------------------------------------------------------ competitor events (public signals)
COMPETITOR_EVENTS: list[Memory] = [
    Memory(
        id="E1", kind="competitor-event", date="2026-03-04",
        context="Sitara Bazaar price cut",
        content=(
            "On 2026-03-04 Sitara Bazaar cut prices on 40 staple items (atta, cooking oil, toor dal, "
            "sugar, rice) by 6-8% across its Hyderabad stores. Found in a weekly in-store price audit "
            "by Dhan Mart's team."
        ),
        source="in-store price audit",
    ),
    Memory(
        id="E2", kind="competitor-event", date="2026-03-19",
        context="Sitara Bazaar hiring signal",
        content=(
            "On 2026-03-19 Sitara Bazaar posted 65 jobs in Hyderabad: 55 delivery riders and dark-store "
            "pickers, plus 10 supply-chain and app-operations roles. Its Hyderabad delivery hiring had "
            "been minimal before."
        ),
        source="job board monitor",
    ),
    Memory(
        id="E3", kind="competitor-event", date="2026-04-09",
        context="Footfall dip after Sitara store opened",
        content=(
            "On 2026-04-09 the Kukatpally store manager (Ramesh K.) reported weekday-evening footfall "
            "down about 6% since a Sitara Bazaar store opened 2 km away. Customers told staff they were "
            "going there for the cashback and the wider range."
        ),
        source="store manager report",
    ),
    Memory(
        id="E4", kind="competitor-event", date="2026-04-28",
        context="Sitara Express delivery launch",
        content=(
            "On 2026-04-28 Sitara Bazaar launched 'Sitara Express', 30-minute grocery delivery in six "
            "Hyderabad pin codes through its app. Announced in a press release and app-store update."
        ),
        source="press release / app store monitor",
    ),
    Memory(
        id="E5", kind="competitor-event", date="2026-05-14",
        context="Sitara loyalty program",
        content=(
            "On 2026-05-14 Sitara Bazaar launched 'Sitara Points', giving members 2% cashback on every "
            "bill, redeemable on the next purchase."
        ),
        source="in-store signage / social media",
    ),
    Memory(
        id="E6", kind="competitor-event", date="2026-06-02",
        context="Sitara new stores",
        content=(
            "On 2026-06-02 Sitara Bazaar opened three new stores in the Hyderabad suburbs (Kompally, "
            "Miyapur and Uppal); one of them is close to a planned Dhan Mart site."
        ),
        source="press coverage / local news",
    ),
    Memory(
        id="E7", kind="competitor-event", date="2026-06-25",
        context="Sitara Express complaints",
        content=(
            "By 2026-06-25 Google Maps reviews and social media posts about Sitara Express mentioned "
            "late deliveries and out-of-stock substitutions, with many reviewers unhappy about missing "
            "items."
        ),
        source="review site monitor",
    ),
    Memory(
        id="E8", kind="competitor-event", date="2026-07-16",
        context="Sitara private label launch",
        content=(
            "On 2026-07-16 Sitara Bazaar launched 'Sitara Select', a private-label range of staples "
            "priced 10-12% below national brands, and opened early festival pre-booking for members."
        ),
        source="in-store audit / social media",
    ),
]

# ------------------------------------------ our responses and their recorded outcomes
RESPONSES: list[Memory] = [
    # R1: matched the price cut -> FAILED
    Memory(
        id="R1", kind="our-response", date="2026-03-26",
        context="Dhan Mart response to price cut",
        content=(
            "In response to Sitara's staple price cuts (E1), Dhan Mart matched them on 2026-03-26, "
            "cutting prices on the same 40 staples by 6-8% in all stores."
        ),
        meta={"responds_to": "E1"},
    ),
    Memory(
        id="R1-OUT", kind="outcome", date="2026-05-10",
        context="Outcome of matching the price cut",
        content=(
            "Outcome (2026-05-10) of matching Sitara's price cuts: FAILED. Store operating margin fell "
            "from 7.9% to 6.6%, while footfall barely changed (up 0.4%). Matching prices cost margin "
            "without bringing shoppers back. Lesson: do not race Sitara on price cuts."
        ),
        meta={"responds_to": "E1", "result": "failure"},
    ),
    # R2: Price Promise boards -> SUCCESS
    Memory(
        id="R2", kind="our-response", date="2026-04-15",
        context="Dhan Mart response to footfall dip",
        content=(
            "After the Kukatpally footfall dip (E3), Dhan Mart put 'Price Promise' boards in the "
            "affected stores from 2026-04-15, showing its own price against the local competitor's "
            "price on the 50 most-bought staples."
        ),
        meta={"responds_to": "E3"},
    ),
    Memory(
        id="R2-OUT", kind="outcome", date="2026-06-10",
        context="Outcome of Price Promise boards",
        content=(
            "Outcome (2026-06-10) of the Price Promise boards: SUCCESS. Weekday-evening footfall in "
            "the affected stores recovered by 9% over 8 weeks, with almost no effect on margin, since "
            "no prices were cut. Lesson: showing existing low prices beats cutting them."
        ),
        meta={"responds_to": "E3", "result": "success"},
    ),
    # R3: rushed in-house delivery -> FAILED
    Memory(
        id="R3", kind="our-response", date="2026-06-02",
        context="Dhan Mart response to delivery launch",
        content=(
            "In response to Sitara Express (E4), Dhan Mart rushed an in-house 45-minute delivery "
            "pilot in three stores, launched on 2026-06-02 after 5 weeks of preparation."
        ),
        meta={"responds_to": "E4"},
    ),
    Memory(
        id="R3-OUT", kind="outcome", date="2026-07-01",
        context="Outcome of the rushed delivery pilot",
        content=(
            "Outcome (2026-07-01) of the in-house delivery pilot: FAILED. Cost per order was Rs 118 "
            "against an average basket of Rs 640, 11% of orders arrived late, and pulling staff off "
            "the shop floor dropped shelf availability in the pilot stores. The pilot was cancelled "
            "after 4 weeks. Lesson: do not copy a competitor's service under time pressure; it strains "
            "a lean operation."
        ),
        meta={"responds_to": "E4", "result": "failure"},
    ),
    # R4: Guaranteed Stock campaign -> SUCCESS
    Memory(
        id="R4", kind="our-response", date="2026-07-02",
        context="Dhan Mart response to competitor stock problems",
        content=(
            "In response to Sitara Express's out-of-stock complaints (E7), Dhan Mart launched a "
            "'Guaranteed Stock' campaign on 2026-07-02 for its top 100 items, with tuned reordering "
            "and in-store signage promising availability."
        ),
        meta={"responds_to": "E7"},
    ),
    Memory(
        id="R4-OUT", kind="outcome", date="2026-08-14",
        context="Outcome of Guaranteed Stock campaign",
        content=(
            "Outcome (2026-08-14) of the Guaranteed Stock campaign: SUCCESS. Footfall rose 8% in six "
            "weeks and average basket size rose 5%, and store staff reported shoppers saying they "
            "came because items were always available. Lesson: Dhan Mart wins when it competes on "
            "low prices and dependable stock, its real strengths."
        ),
        meta={"responds_to": "E7", "result": "success"},
    ),
]

# No response was ever recorded for E2, E5, E6, E8: those are gaps on purpose,
# so the agent can point out Dhan Mart has no plan for Sitara's loyalty push,
# store expansion and private label.

HISTORY: list[Memory] = sorted(
    PROFILE + COMPETITOR_EVENTS + RESPONSES, key=lambda m: (m.date, m.id)
)

# ------------------------------------------------------------------ live demo events
@dataclass(frozen=True)
class DemoEvent:
    id: str
    date: str
    title: str
    description: str
    has_precedent: bool
    expected_behavior: str


DEMO_EVENTS: list[DemoEvent] = [
    DemoEvent(
        id="DEMO-1", date="2026-09-22",
        title="Sitara Bazaar announces a 10% festival price cut on 60 staples",
        description=(
            "On 2026-09-22 Sitara Bazaar announced a 'Festival Fest' with 10% price cuts on 60 "
            "staple items across all Hyderabad stores, running through Diwali."
        ),
        has_precedent=True,
        expected_behavior=(
            "Agent recalls E1/R1 (matching price cuts failed: margin 7.9%->6.6%, footfall flat) and "
            "R2/R4 (Price Promise boards and Guaranteed Stock worked). It should recommend NOT "
            "matching, propose a Price Promise or stock-guarantee play for the festival period, cite "
            "those memories, and show high confidence."
        ),
    ),
    DemoEvent(
        id="DEMO-2", date="2026-09-25",
        title="Sitara Bazaar acquires a farm-produce startup",
        description=(
            "On 2026-09-25 Sitara Bazaar announced it acquired FarmLoop, a Telangana farm-to-store "
            "produce aggregator, and promised fresher fruit and vegetables priced about 15% lower "
            "from Q4."
        ),
        has_precedent=False,
        expected_behavior=(
            "No past acquisition or produce move. Agent should say there is no direct precedent, note "
            "it targets Dhan Mart's known weakness (fruit and vegetable freshness, PROFILE-2), link "
            "it to Sitara's growing push (E5, E6, E8), and reason from lessons: don't copy under "
            "pressure (R3), don't win by price cuts (R1), dependable availability works (R4). Confidence: "
            "medium."
        ),
    ),
]


# ------------------------------------------------------------------------- helpers
STAGES = {
    "cold": None,            # nothing stored: agent gives generic advice
    "early": "2026-05-15",   # a few events, first failed response: partial lessons
    "full": "2026-09-20",    # everything up to just before the demo events
}


def memories_until(cutoff_date: str | None) -> list[Memory]:
    """Memories dated on or before cutoff_date (ISO). None -> no memories (cold start)."""
    if cutoff_date is None:
        return []
    return [m for m in HISTORY if m.date <= cutoff_date]


def to_retain_kwargs(m: Memory) -> dict:
    """Arguments for a Hindsight retain call (bank_id is added by the caller).

    document_id is set to the memory's stable id so re-running the seed
    script upserts instead of duplicating every historical memory.
    """
    metadata = {"id": m.id, "kind": m.kind, "source": m.source or "internal", **m.meta}
    return {
        "content": m.content,
        "context": m.context,
        "timestamp": m.timestamp,
        "document_id": m.id,
        "metadata": {k: str(v) for k, v in metadata.items()},
    }
