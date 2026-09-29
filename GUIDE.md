# Competitive Intelligence Agent — Build & Test Guide

Working reference for the team: what this is, how it's wired, what to click
through, and what output to expect. Everything under "Verified Output" below
is copy-pasted from a real run against Hindsight Cloud + Groq, not a guess.

---

## 1. What we built

An agent that recommends counter-plans against a competitor's moves — and
gets better at it because it remembers **its own company's past decisions
and whether they worked.**

Scenario: **Dhan Mart** (fictional Hyderabad supermarket chain) watching
**Sitara Bazaar** (fictional rival). Full backstory and all data lives in
[`synthetic_data.py`](synthetic_data.py).

The core loop:

1. A new competitor move comes in.
2. The agent recalls similar past competitor moves, *and* what Dhan Mart did
   about similar situations before, *and* whether that worked.
3. It proposes a counter-plan, showing exactly which memories it used.
4. The user marks the plan adopted or rejected, optionally records the
   outcome. That gets retained — the next plan can learn from it.

Most competitive-intelligence tools stop at step 1 (watch the rival). The
point of this build is steps 2–4: memory of **our own trial and error**, not
just the competitor's activity.

### Two frontends, one brain

The memory logic lives in `agent.py` and `dri.py` only. Both UIs call into it,
so neither can drift from the other:

| Frontend | Run it with | Use when |
|---|---|---|
| **React + Vite** (recommended) | `python -m uvicorn server:app` + `npm run dev` | Live demo — steps stream as they happen |
| **Streamlit** | `python -m streamlit run app.py` | Quick checks, single-file fallback |

**Why the React build exists.** Streamlit cannot emit incremental progress
from one button click — on rerun it painted all seven learning-cycle steps at
once, which read as a canned animation. `server.py` emits each step over
Server-Sent Events the instant the real backend call it represents finishes,
so the console shows genuine progress (0% → 29% → 57% → 86% → 100%) rather
than a timer.

See section 9 for the full React setup.

### How Live differs from the read-only stages

Live is the only **writable** stage, and it drops the explicit buttons in favour
of the chat input:

- **Cold / Early / Full** — sidebar shows *Get counter-plan* and *Show learned
  patterns*, plus a *Generate counter-plan* button under the input. The event
  dropdown is the primary way to ask.
- **Live** — no sidebar buttons and no generate button at all. You ask **only**
  via the chat input: **Enter** sends, **Shift+Enter** inserts a newline. A
  hint under the input shows the current state (idle hint, or a live
  "Thinking…" indicator while Groq is running).

Once a plan exists in Live, the **Decision** panel appears with
Adopted/Rejected, an optional outcome note, and **Save decision**.

---

## 2. How it works

```
Streamlit UI (app.py)  OR  React UI (frontend/) -> FastAPI (server.py)
        |                                                |
        '-----------------------> agent.py <------------'
                                    |--- recall() ----> Hindsight Cloud (memory bank)
                                    |--- reflect() -->        "
                                    |--- retain() ---->       "
                                    |
                                    '--- ask_llm() ----> Groq (openai/gpt-oss-120b)
```

Hindsight and Groq do different jobs and never talk to each other directly:

| | Hindsight Cloud | Groq |
|---|---|---|
| Job | Store and retrieve facts (`retain`/`recall`/`reflect`) | Turn recalled facts into a recommendation |
| Paid via | Your `$50` Cloud credit | Free tier |

### The three-stage memory design

Three separate banks simulate three points in time, so the "memory makes it
better" claim is something you can click through and see, not just assert:

| Stage | Bank | What's known |
|---|---|---|
| `cold` | never created | Nothing. Pure LLM general knowledge. |
| `early` | `competitive-intel-demo-early` | First 10 memories — the price-cut failure is known, the later successes aren't yet. |
| `full` | `competitive-intel-demo-full` | All 18 seed memories — failures **and** successes. |

Re-seed with `python seed_hindsight.py <stage>`. Safe to re-run — every
memory has a stable `document_id`, so re-running upserts instead of
duplicating.

### The evidence guard

The LLM is told to cite memories by id (`M1`, `M2`, ...). `agent.analyze()`
then validates every citation against the memories actually recalled — an
id the model invents, or a citation for a memory that wasn't returned, gets
silently dropped. If a plan claims a direct precedent but ends up with zero
valid citations, `has_direct_precedent` is forced to `False` and confidence
is capped. **The agent cannot claim evidence it doesn't have.**

### The dual-query recall

`agent.recall()` runs two Hindsight recalls, not one:

1. The new event's own description (surfaces comparable competitor moves)
2. A fixed query: *"Dhan Mart's own past responses to Sitara Bazaar and
   whether each one succeeded or failed"*

Results are merged and de-duplicated. This exists because we found, testing
live, that a single query ranks other competitor-move facts above our own
outcome facts — "we launched a stock-guarantee campaign" isn't semantically
close to "competitor cut prices," even though it's the fact that matters
most. Without the second query, the agent's best evidence (the successes)
routinely got buried and never cited.

---

## 3. Test plan — walk through this in the UI

Run `streamlit run app.py`. Check each of these in order:

- [ ] **Cold, DEMO-1** — sidebar: stage = `cold`, event = the Festival Fest
  price cut. Click **Get counter-plan**. Expect a generic, sensible-sounding
  answer with `⚠️ No direct precedent`, confidence `low`, and a low DRI.
- [ ] **Full, DEMO-1, same event** — switch stage to `full`, click **Get
  counter-plan** again. Expect `✅ Direct precedent found`, confidence
  `high`, a memory panel full of real recalled facts, and evidence citations
  pinned in the list. **This is the single most important moment in the
  demo — the same event, dramatically different answer, because of memory.**
- [ ] **Early, DEMO-1** — switch to `early`. Precedent should still show
  (the failure is already known at this cutoff), but check whether the
  recommendation differs subtly from `full` — `full` should read as more
  confident/specific since it also knows the successes.
- [ ] **Full, DEMO-2** (the acquisition/no-precedent event) — expect
  `⚠️ No direct precedent`, confidence `medium` (not `low` — there's related
  context even without a direct match), and reasoning that references the
  produce-freshness weakness.
- [ ] **Show learned patterns** button (either stage) — expect a formatted
  markdown report (headers, bold, a table) summarizing what worked and what
  failed. If it renders as raw `##` text instead of a formatted heading,
  the `st.markdown` fix didn't take — check `app.py` line ~38.
- [ ] **Save decision (Live stage only)** — switching the stage to `live`
  is what enables writing: the sidebar badge changes to *"🟢 learning
  enabled"* and the **Decision** panel appears with Adopted/Rejected plus
  an optional outcome note. Click **Save decision**. Expect the *Live
  Learning Cycle* console to step through all seven stages, then a
  **Learning result** section with Before/After recommendations and
  Before/After DRI. Saving is blocked on `cold`/`early`/`full` by design.
- [ ] **DRI responds to memory** — compare the DRI card at `cold` (no
  precedent → low) against `full` for the same event. After saving a Live
  decision, the After DRI should rise, since the decision you just saved
  is now part of the recall it is measured against.
- [ ] **Custom event** — try something *not* in `synthetic_data.py`
  entirely (e.g. "Sitara Bazaar cuts store hours"). This is the real
  stress test: does the agent degrade gracefully to general reasoning
  with low confidence, or does it hallucinate a precedent?

---

## 4. Sample prompts and verified outcomes

These are real, not invented — captured from live runs against Hindsight
Cloud during this build.

### DEMO-1: "Sitara Bazaar announces a 10% festival price cut on 60 staples"

> On 2026-09-22 Sitara Bazaar announced a 'Festival Fest' with 10% price
> cuts on 60 staple items across all Hyderabad stores, running through
> Diwali.

| Stage | precedent | confidence | recommendation |
|---|---|---|---|
| **cold** | False | low | *"Introduce a targeted Diwali promotion... 5-8% discount and bundle offers (buy-one-get-one-half-price)..."* — reasonable-sounding, but this is close to repeating the exact price-cut approach that already failed. The agent has no way to know that. |
| **early** | True | high | *"Do not match the 10% cuts... use targeted price-promise signage... loyalty incentives..."* — correctly avoids the price war, cites the 2026-03-26 failed price-match and its outcome. |
| **full** | True | high | *"Do not match the 10% cuts... reinforce the 'Price Promise' boards and loyalty incentives. Emphasize guaranteed stock..."* — same correct avoidance, but now names the two actual playbook tactics that are proven to work, citing both the failure and the Price Promise success. |

### DEMO-2: "Sitara Bazaar acquires a farm-produce startup"

> On 2026-09-25 Sitara Bazaar announced it acquired FarmLoop... promising
> fresher fruit and vegetables priced about 15% lower from Q4.

| Stage | precedent | confidence | recommendation |
|---|---|---|---|
| **cold** | False | low | *"Accelerate Dhan Mart's own fresh produce sourcing by partnering with local farmer cooperatives..."* — plausible generic advice. |
| **full** | False | **medium** | *"Rather than matching the 15% lower produce prices, double down on reliable, high-quality fresh-produce sourcing... communicate its price advantage..."* — correctly identifies there's no direct precedent, but confidence is `medium` not `low`, because memory supplies real context: this targets Dhan Mart's known freshness weakness, and past lessons (don't race on price, don't copy under pressure) still apply. |

The DEMO-2 contrast is the subtler but arguably more important one: it
proves the agent doesn't just pattern-match on identical past events — it
reasons with memory as context even when there's no direct precedent, and
is honest about the confidence difference between "I've seen this exact
thing before" and "I haven't, but here's what I know that's relevant."

---

## 5. Known limitations

Be upfront about these in the pitch — judges respond better to honesty here
than to overclaiming:

- **All data is synthetic and pre-seeded.** Outcomes that would take months
  in reality are known instantly in the demo. Say so directly.
- **Single fictional company, single fictional competitor.** No live
  scraping, no multi-competitor tracking — explicitly out of scope per the
  build plan.
- **LLM output is stochastic.** Temperature is `0.2`, not `0`, so re-running
  the identical event can change the exact wording and which valid citations
  get chosen, though the structural facts (precedent True/False, confidence
  tier) have been consistent across our test runs.
- **Retrieval ranking is still relevance-based, not guaranteed-complete.**
  The dual-query fix solved the specific failure we found (successes buried
  under price-cut facts), but a sufically novel custom event could still
  surface a thin or skewed memory set. The evidence-validation guard limits
  the damage — the agent can't cite what it wasn't given — but it can't
  invent evidence that should exist but didn't get recalled.
- **Three banks-per-stage is a demo device, not a production design.** A
  real deployment would have one bank that grows continuously, not three
  artificially frozen snapshots.
- **No decay or forgetting.** Hindsight doesn't document a decay/importance
  mechanism — memory only accumulates. Fine for a hackathon timeline,
  something to watch at real scale.
- **`reflect()` costs ~$0.05 and 1-3 seconds per call.** Don't wire the
  "Show learned patterns" button to auto-fire on every interaction.

---

## 6. Decision Reliability Index (DRI)

DRI is the confidence number attached to every recommendation. It answers a
different question from `confidence` (which is capped by whether real evidence
was cited): *how much do we actually trust this, given what memory returned?*

Implemented in `dri.py`, called from `app.py` via `calculate_dri(stage, query)`.

### Formula

```
DRI = 100 × (0.6 × P + 0.4 × O)
```

- **P — precedent** — the highest Hindsight *reranker* score returned for the
  current query, clamped to `0..1`. This measures retrieval confidence.
- **O — outcome** — outcome-bearing Dhan Mart decision memories ÷ Dhan Mart
  decision memories in the recall result. This measures whether the memories
  we found are actual experiences with results attached, rather than
  unsupported opinions.

The raw components are returned alongside the score (`precedent`, `outcome`,
`decision_memories`, `outcome_memories`) for debugging and validation, while the
UI displays only the final score.

### Detection rules

A memory counts as a **decision memory** only if it matches one of the
`_DECISION_PATTERNS` regexes — e.g. *"Dhan Mart decided / chose / piloted /
responded…"*. It then counts as an **outcome memory** if it also contains any
`_OUTCOME_MARKERS` — *"resulted in"*, *"revenue"*, *"retention"*, *"margin"*,
*"successful"*, *"failed"*, and similar.

This is deliberately regex-based rather than LLM-based, so the score stays
deterministic and fast — an LLM call in this path would add latency and
non-determinism to a number the UI presents as a measurement.

### Banks

DRI is stage-scoped. `_bank(stage)` returns `{HINDSIGHT_BANK_ID}-{stage}`, so
the index is computed against exactly the same memory the agent recalled from.

### Where it shows up in the UI

- One DRI card beneath the recommendation card, on every analysis.
- **Before Learning** and **After Learning** cards, each with their own DRI, once
  a Live decision has been saved — so the jump in index after a decision is
  visible side by side.

Because it only reads memory, it is safe on every stage. Note it only reads
memory — it never writes. Learning still only ever happens on `live`.

---

## 7. Future enhancements

- **Multiple tracked competitors at once** — this is where Hindsight's graph
  retrieval arm would start doing real work (cross-competitor pattern
  detection: "every rival who tried X failed the same way").
- **Real public-signal ingestion** — job boards, press releases, review
  sites feeding `retain()` automatically instead of a hand-written seed
  script.
- **Mission / directives / disposition on the bank** — give it an explicit
  skeptical-strategist persona and hard rules ("never recommend a pricing
  practice that could be seen as predatory"). Only affects `reflect()`, not
  `recall()` — worth exploring since it's unused right now.
- **Surface observations directly**, not just recall results — Hindsight
  consolidates repeated facts into evidence-backed beliefs with a proof
  count; right now the UI shows raw recalled facts and a `reflect()` prose
  summary, but never the consolidated belief layer in between.
- **Use `reflect()`'s `.based_on` field** (confirmed to exist, unused so
  far) to show which memories back the "learned patterns" summary, the same
  way evidence is shown for individual plans.
- **Let the user push back** on a recommendation in a follow-up turn, and
  retain that exchange as an experience fact — closer to a real negotiation
  than a one-shot recommendation.
- **A consistency eval harness** — run the same event N times, measure how
  often the same valid citations get chosen, given the stochastic-output
  limitation above.

---

## 8. How this differs from others

**From other competitive-intelligence tools:** most watch the competitor and
stop there — pricing pages, job postings, press releases. That's monitoring,
not memory. This agent's differentiator is remembering **our own decisions
and their outcomes**, which is the one thing that can't be scraped from a
public source. The advice compounds specifically because the company's own
trial-and-error is retained.

**From a plain RAG chatbot** (the most likely thing other hackathon teams
ship):

| | Typical RAG demo | This build |
|---|---|---|
| Retrieval | One similarity search per query | Two merged, targeted queries — event-similar facts *and* our-own-outcomes facts, specifically because a single search buries the outcomes |
| Evidence | "Informed by memory" badge, true whenever anything was retrieved | Every citation validated against what was actually recalled; confidence is programmatically capped when evidence is thin |
| Improvement over time | Asserted, rarely shown | Directly demonstrable — same event, three memory stages, three different verified outputs, in this document |
| Honesty about uncertainty | Usually absent | Explicit `has_direct_precedent` flag and confidence tier, separated from general LLM reasoning in the output structure |

The judging rubric weights "memory clearly improves the agent" at 25%. The
cold vs. full comparison in section 4 is the artifact that proves that claim
with real, reproducible output rather than a claim in a slide.

---

## 9. Running the React frontend

### Layout

```
Hackathon/
  agent.py           <- memory logic (single source of truth)
  dri.py             <- Decision Reliability Index
  server.py          <- FastAPI wrapper + SSE learning cycle
  app.py             <- Streamlit UI (alternative frontend)
  frontend/
    src/api.ts       <- typed client + SSE parser
    src/App.tsx      <- main shell, stage picker, decision panel
    src/components/  <- PlanCard, DriGauge, LearningCycle, LearningResult
    src/styles.css   <- design system
```

`server.py` does **not** reimplement any memory logic. It imports `agent` and
`dri` and exposes them over HTTP, so Streamlit and React always agree.

### Start

Two terminals:

```bash
# terminal 1 — backend
.\.venv\Scripts\python.exe -m uvicorn server:app --port 8000

# terminal 2 — frontend
cd frontend
npm install     # first time only
npm run dev     ->  http://localhost:5173
```

Vite proxies `/api/*` to `127.0.0.1:8000`, so there is no CORS setup and no
hardcoded host in the frontend.

### Setting up the venv

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify the install before seeding or running — these tests are fully offline, so
a pass proves the Python environment works without needing valid API keys:

```bash
.\.venv\Scripts\python.exe -m pytest -q     # expected: 18 passed
```

If `.venv` was copied from another machine and `.\.venv\Scripts\python.exe`
reports *"did not find executable at C:\Python314\python.exe"*, the venv still
points at the base interpreter it was built against. Delete `.venv` and
recreate it with the two commands above — that error is not fixable in place.

`.env` must be filled in before `seed_hindsight.py` or the first analysis. Both
`seed_hindsight.py` and `server.py` fail with an explicit message naming the
missing key, so a failure here means `.env` is absent or incomplete.

### API surface

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness + whether API keys are configured |
| `GET /api/events` | Competitor events for the picker |
| `GET /api/learning-steps` | Authoritative learning-cycle step labels (from `agent.LEARNING_STEPS`) |
| `POST /api/analyze` | Recall → plan → DRI |
| `POST /api/patterns` | `reflect()` report |
| `POST /api/learn` | Full learning cycle, streamed over SSE |

### Important: don't remove the single-thread executor

`agent.py` caches one global Hindsight client whose aiohttp connection pool
binds to the first event loop that touches it. FastAPI runs sync endpoints in
a thread pool, so a second request would reuse a pool attached to a different
loop and aiohttp raises:

```
RuntimeError: Timeout context manager should be used inside a task
```

`server.py` pins every agent call to one dedicated thread
(`_AGENT_EXECUTOR`) so the process keeps a single event loop. Removing it
brings back intermittent 500s.

### Judging-rubric mapping

| Criterion | Weight | Where this build answers it |
|---|---|---|
| Innovation | 30% | DRI (a measured reliability score, not a confidence vibe check) + a real streamed learning cycle |
| Hindsight memory | 25% | Three-stage memory cutoffs, before/after comparison, saved-decision recall validation |
| Technical implementation | 20% | Typed API contract, SSE, pinned event loop, single source of truth for memory logic |
| User experience | 15% | Radial DRI gauge, streaming progress, evidence provenance on every citation |
| Real-world impact | 10% | Pricing/acquisition decisions with margin consequences, grounded in company history |

### Possible next improvements

- **Competitor timeline view** — the problem statement stresses that
  "competitive intelligence is only useful if it is cumulative." A date-ordered
  panel of Sitara's moves would make six months of history visible at a glance.
- **Trend line for DRI across saves** — plot each saved decision's index so the
  improvement is a curve, not two points.
- **Simulated time travel** — re-run an event against an earlier stage
  ("what would we have advised in March?") to dramatise the learning curve.
- **Eval harness** — run each event N times and measure citation stability;
  addresses the stochastic-output limitation noted in section 5.
