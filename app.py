import html
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import agent
import dri
from synthetic_data import DEMO_EVENTS


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="Competitive Intelligence Agent",
    layout="wide",
)

# ------------------------------------------------------------
# THEME
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --bg:#0B1020; --bg2:#11182B; --card:#172033; --card2:#1D2940;
        --cyan:#22D3EE; --indigo:#6366F1; --green:#34D399;
        --amber:#FBBF24; --red:#F87171; --text:#F8FAFC; --sub:#94A3B8;
        --border:#26344D;
    }

    /* base app + Streamlit's own chrome (top toolbar, footer) */
    html, body, .stApp { background: var(--bg) !important; }
    header[data-testid="stHeader"] { background: var(--bg) !important; }
    header[data-testid="stHeader"] * { color: var(--text) !important; }
    .block-container { padding-top: 2rem; padding-bottom: 6rem; }

    h1, h2, h3, h4 { color: var(--text) !important; }
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] li { color: var(--text); }
    .stApp [data-testid="stCaptionContainer"] { color: var(--sub) !important; }
    section[data-testid="stSidebar"] { background: var(--bg2); border-right: 1px solid var(--border); }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--card); border: 1px solid var(--border) !important;
        border-radius: 10px;
    }

    /* ---- every text/select input: background is NOT inherited by children,
       so the wrapper div and the actual <textarea>/<input> element both need
       an explicit background, not just the wrapper. ---- */
    textarea, input, select {
        color: var(--text) !important; background: var(--card) !important;
    }
    div[data-baseweb="textarea"], div[data-baseweb="input"], div[data-baseweb="select"],
    div[data-baseweb="base-input"] {
        background: var(--card) !important; border-color: var(--border) !important;
    }
    div[data-baseweb="select"] * { color: var(--text) !important; background: transparent !important; }
    div[data-baseweb="select"] > div { background: var(--card) !important; }
    ::placeholder { color: var(--sub) !important; opacity: 1; }

    /* selectbox: cover every nested layer Streamlit renders, including the
       portal-rendered popup list, which lives outside the normal dark wrapper */
    div[data-testid="stSelectbox"], div[data-testid="stSelectbox"] * {
        background-color: var(--card) !important; color: var(--text) !important;
    }
    div[data-testid="stSelectbox"] svg { fill: var(--sub) !important; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        border-color: var(--border) !important;
    }
    ul[role="listbox"] { background: var(--card) !important; border: 1px solid var(--border) !important; }
    ul[role="listbox"] li { color: var(--text) !important; background: transparent !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background: var(--card2) !important; }

    /* catch-all for the fixed bottom chat bar: force every nested element dark,
       not just the outer wrapper, since background never cascades to children */
    [data-testid*="Bottom"], [data-testid*="Bottom"] * { background-color: var(--bg2) !important; }
    div[data-testid="stChatInput"], div[data-testid="stChatInput"] * {
        background-color: var(--card) !important; color: var(--text) !important;
    }
    div[data-testid="stChatInput"] button svg { color: var(--cyan) !important; }

    /* ---- chat input ("Ask me anything") floats fixed to the bottom by default ---- */
    div[data-testid="stChatInput"],
    div[data-testid="stBottom"] {
        background: var(--bg2) !important; border-top: 1px solid var(--border) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: var(--card) !important; color: var(--text) !important;
    }
    div[data-testid="stChatInput"] button svg { color: var(--cyan) !important; }

    .ci-plan-card {
        background: linear-gradient(135deg, var(--card2), var(--card));
        border: 1px solid var(--indigo); border-radius: 12px;
        padding: 22px 24px; margin-bottom: 6px;
        box-shadow: 0 0 0 1px rgba(99,102,241,.15);
    }
    .ci-plan-text { color: var(--text); font-size: 16px; line-height: 1.55; margin-top: 12px; }

    .ci-badge { display:inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 12px; font-weight: 600; margin-right: 8px; letter-spacing:.02em; }
    .ci-badge-direct  { background: rgba(52,211,153,.15); color: var(--green); border:1px solid var(--green); }
    .ci-badge-none    { background: rgba(248,113,113,.15); color: var(--red); border:1px solid var(--red); }
    .ci-badge-conf    { background: rgba(34,211,238,.12); color: var(--cyan); border:1px solid var(--cyan); }
    .ci-badge-neutral { background: rgba(148,163,184,.12); color: var(--sub); border:1px solid var(--border); }

    .ci-mem-bar { display:flex; gap:4px; margin: 14px 0 4px 0; }
    .ci-mem-chip { flex:1; height:7px; border-radius:4px; background: var(--border); }
    .ci-mem-chip.cited { background: var(--cyan); }
    .ci-mem-caption { color: var(--sub); font-size: 13px; margin-bottom: 4px; }

    .ci-mem-tag { font-size: 11px; letter-spacing:.06em; text-transform: uppercase;
        color: var(--cyan); font-weight: 700; margin-bottom: 6px; }

    .ci-question { border-left: 3px solid var(--cyan); padding-left: 14px; color: var(--sub);
        font-size: 15px; margin-bottom: 18px; }

    .ci-diff-changed   { border-left: 3px solid var(--amber); }
    .ci-diff-unchanged { border-left: 3px solid var(--border); }

    .ci-check-yes { color: var(--green); }
    .ci-check-no  { color: var(--sub); }

    /* ---- technical / console-styled learning cycle panel ---- */
    .ci-trace {
        border: 1px solid var(--cyan); border-radius: 12px; padding: 22px 28px;
        background: radial-gradient(120% 100% at 0% 0%, rgba(34,211,238,.08), var(--bg2) 60%);
        margin: 18px 0 26px 0;
        box-shadow: 0 0 24px rgba(34,211,238,.08);
        font-family: "SFMono-Regular", Consolas, "Courier New", monospace;
    }
    .ci-trace-head { display:flex; justify-content:space-between; align-items:center; margin-bottom: 18px; }
    .ci-trace-title { color: var(--cyan); font-size: 13px; letter-spacing:.12em; font-weight: 700; }
    .ci-trace-pct { color: var(--sub); font-size: 12px; }
    .ci-trace-track { height: 4px; background: var(--border); border-radius: 2px; margin-bottom: 22px; overflow:hidden; }
    .ci-trace-fill { height: 100%; background: linear-gradient(90deg, var(--indigo), var(--cyan)); transition: width .5s ease; }

    .ci-trace-step { position:relative; display:flex; align-items:center; gap: 14px; padding: 8px 10px; margin: 0 -10px; border-radius: 8px; transition: background .3s ease; }
    .ci-trace-step:not(:last-child)::before {
        content: ""; position:absolute; left: 23px; top: 34px; width: 2px; height: 24px;
        background: var(--border); z-index: 0;
    }
    .ci-trace-step.completed:not(:last-child)::before { background: var(--green); }
    .ci-trace-step.active { background: rgba(34,211,238,.07); }

    .ci-trace-idx {
        width: 26px; height: 26px; flex: 0 0 26px; border-radius: 50%;
        font-size: 11px; color: var(--sub); border: 1px solid var(--border);
        display:flex; align-items:center; justify-content:center; position:relative; z-index:1;
        background: var(--bg2);
    }
    .ci-trace-step.completed .ci-trace-idx { color: #0B1020; background: var(--green); border-color: var(--green); font-weight: 700; }
    .ci-trace-step.active .ci-trace-idx { border-color: var(--cyan); }

    .ci-spin-ring {
        width: 12px; height: 12px; border-radius: 50%;
        border: 2px solid rgba(34,211,238,.25); border-top-color: var(--cyan);
        animation: ci-spin 0.7s linear infinite;
    }
    @keyframes ci-spin { to { transform: rotate(360deg); } }

    .ci-trace-label { font-size: 13.5px; color: var(--sub); }
    .ci-trace-step.completed .ci-trace-label { color: var(--text); }
    .ci-trace-step.active .ci-trace-label { color: var(--cyan); font-weight: 600; }
    .ci-trace-step.active .ci-trace-label::after { content: "▍"; animation: ci-blink 1s steps(1) infinite; margin-left: 4px; }
    @keyframes ci-blink { 50% { opacity: 0; } }

    .ci-dri-card { margin: 16px 0 20px; padding: 18px 20px; border: 1px solid var(--border); border-radius: 14px; background: linear-gradient(135deg, rgba(99,102,241,.12), rgba(34,211,238,.06)); text-align: center; }
    .ci-dri-label { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--sub); font-weight: 700; }
    .ci-dri-score { margin-top: 4px; font-size: 32px; line-height: 1.1; font-weight: 750; color: var(--text); }
    .ci-dri-note { margin-top: 5px; font-size: 12px; color: var(--sub); }
    .ci-dri-compare { min-height: 120px; margin-top: 12px; display:flex; flex-direction:column; justify-content:center; border:1px solid var(--border); border-radius:14px; background:var(--card); padding:18px 20px; }
    .ci-dri-compare-label { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:var(--sub); font-weight:700; }
    .ci-dri-compare-score { margin-top:8px; font-size:30px; font-weight:750; color:var(--text); }
    .ci-dri-compare-note { margin-top:4px; font-size:12px; color:var(--sub); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "plan": None,
    "stage": "full",
    "selected_event": None,
    "question": None,
    "learning_result": None,
    "patterns": None,
    "saved_decision": None,
    "current_dri": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def event_field(event, field, default=""):
    if isinstance(event, dict):
        return event.get(field, default)
    return getattr(event, field, default)


def plan_field(plan, field, default=None):
    if plan is None:
        return default
    return getattr(plan, field, default)


def calculate_dri(stage, question):
    try:
        return dri.calculate_dri(stage=stage, query=question)
    except Exception as exc:
        return {"score": None, "precedent": 0.0, "outcome": 0.0, "error": str(exc)}


def render_dri_card(dri_data, label="Decision Reliability Index"):
    score = dri_data.get("score") if isinstance(dri_data, dict) else None
    if score is None:
        value = "—"
        note = "Reliability index unavailable for this recall."
    else:
        value = f"{int(score)} / 100"
        if score >= 75:
            note = "Strong historical support"
        elif score >= 50:
            note = "Moderate historical support"
        else:
            note = "Limited historical support"
    st.markdown(
        f'''<div class="ci-dri-card">
            <div class="ci-dri-label">{html.escape(label)}</div>
            <div class="ci-dri-score">{html.escape(value)}</div>
            <div class="ci-dri-note">{html.escape(note)}</div>
        </div>''',
        unsafe_allow_html=True,
    )


def get_event_names():
    return [event_field(e, "title", "") for e in DEMO_EVENTS if event_field(e, "title", "")]


def get_event_details(event_name):
    for event in DEMO_EVENTS:
        if event_field(event, "title", "") == event_name:
            event_date = event_field(event, "date", datetime.now().date().isoformat())
            description = event_field(event, "description", "")
            return str(event_date), str(description)
    raise ValueError(f"Competitor event '{event_name}' was not found.")


def run_analysis(stage, question, event_name):
    plan = agent.analyze(stage, question)
    st.session_state.plan = plan
    st.session_state.stage = stage
    st.session_state.selected_event = event_name
    st.session_state.question = question
    st.session_state.learning_result = None
    st.session_state.saved_decision = None
    st.session_state.current_dri = calculate_dri(stage, question)


def evidence_items(evidence):
    """Yield (memory_text, why, memory_id) triples, skipping malformed entries."""
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        yield text, str(item.get("why", "")).strip(), str(item.get("id", "")).strip()


# ============================================================
# PLAN CARD (built as ONE html string -> ONE st.markdown call,
# so the wrapping <div> actually contains its children. Splitting
# this across multiple st.markdown calls was the earlier bug:
# each call is its own isolated block in Streamlit, so an opening
# tag in one call and content in the next never nest.)
# ============================================================

def verdict_badges_html(plan) -> str:
    has_precedent = plan_field(plan, "has_direct_precedent", False)
    confidence = plan_field(plan, "confidence", None)
    out = (
        '<span class="ci-badge ci-badge-direct">✅ Direct precedent</span>'
        if has_precedent
        else '<span class="ci-badge ci-badge-none">⚠️ No direct precedent</span>'
    )
    if confidence:
        out += f'<span class="ci-badge ci-badge-conf">Confidence: {html.escape(str(confidence)).upper()}</span>'
    return out


def memory_bar_html(plan) -> str:
    evidence = plan_field(plan, "evidence", []) or []
    cited_count = sum(1 for _t, _w, _id in evidence_items(evidence))
    total = plan_field(plan, "memories", None)
    total_count = len(total) if isinstance(total, (list, tuple)) else cited_count

    if total_count == 0:
        return '<div class="ci-mem-caption">No memories were recalled for this request.</div>'

    chips = "".join(
        f'<div class="ci-mem-chip{" cited" if i < cited_count else ""}"></div>'
        for i in range(max(total_count, cited_count))
    )
    return (
        f'<div class="ci-mem-bar">{chips}</div>'
        f'<div class="ci-mem-caption">{total_count} memories recalled &middot; '
        f'{cited_count} used as evidence</div>'
    )


def render_plan_card(plan, recommendation: str) -> None:
    body = html.escape(recommendation) if recommendation else "No recommendation was returned."
    full_html = (
        '<div class="ci-plan-card">'
        + verdict_badges_html(plan)
        + memory_bar_html(plan)
        + f'<div class="ci-plan-text">{body}</div>'
        + "</div>"
    )
    st.markdown(full_html, unsafe_allow_html=True)


# ============================================================
# MEMORY EVIDENCE
# ============================================================

def render_memory_evidence(evidence, heading="Company memory"):
    st.markdown(f"#### {heading}")
    items = list(evidence_items(evidence))
    if not items:
        with st.container(border=True):
            st.write("No directly relevant company memory was selected.")
        return
    for text, why, mem_id in items:
        with st.container(border=True):
            label = f"📌 cited evidence &middot; {html.escape(mem_id)}" if mem_id else "📌 cited evidence"
            st.markdown(f'<div class="ci-mem-tag">{label}</div>', unsafe_allow_html=True)
            st.write(text)
            if why:
                st.caption(f"Why it matters: {why}")


# ============================================================
# LEARNING CYCLE — technical console panel (also built as one block)
# ============================================================

# Step labels live in agent.py so this UI, the FastAPI backend, and the React
# console can never drift apart.
LEARNING_STEPS = list(agent.LEARNING_STEPS)


_CHECK_SVG = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#0B1020" '
    'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"></polyline></svg>'
)


def render_learning_stepper(placeholder, completed_steps=None, active_step=None):
    completed_steps = set(completed_steps or [])
    pct = int(100 * len(completed_steps) / len(LEARNING_STEPS))

    steps_html = []
    for index, label in enumerate(LEARNING_STEPS):
        safe_label = html.escape(label)
        idx_number = f"{index + 1:02d}"
        if index in completed_steps:
            idx_inner, row_class = _CHECK_SVG, "completed"
        elif index == active_step:
            idx_inner, row_class = '<div class="ci-spin-ring"></div>', "active"
        else:
            idx_inner, row_class = idx_number, ""
        steps_html.append(
            f'<div class="ci-trace-step {row_class}">'
            f'<div class="ci-trace-idx">{idx_inner}</div>'
            f'<div class="ci-trace-label">{safe_label}</div></div>'
        )

    full_html = (
        '<div class="ci-trace">'
        '<div class="ci-trace-head">'
        '<span class="ci-trace-title">&#9881; LIVE LEARNING CYCLE</span>'
        f'<span class="ci-trace-pct">{pct}%</span></div>'
        f'<div class="ci-trace-track"><div class="ci-trace-fill" style="width:{pct}%;"></div></div>'
        + "".join(steps_html)
        + "</div>"
    )
    with placeholder:
        st.html(full_html)


def scroll_to_learning_cycle():
    """Jump the page to the trace panel the instant Save is clicked, so judges
    land on it instead of hunting for it after it has already finished."""
    components.html(
        """<script>
        setTimeout(function() {
            var el = window.parent.document.getElementById('ci-learning-anchor');
            if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
        }, 80);
        </script>""",
        height=0,
    )


# ============================================================
# HEADER
# ============================================================

st.title("Competitive Intelligence Agent")
st.caption(
    "A decision-support agent that recalls competitive experience, "
    "proposes a response, and learns from outcomes."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## Analysis")

    stage_options = ["cold", "early", "full", "live"]
    stage_labels = {"cold": "Cold", "early": "Early", "full": "Full", "live": "Live"}

    current_stage = st.session_state.stage if st.session_state.stage in stage_options else "full"
    selected_stage = st.radio(
        "Memory stage", options=stage_options, index=stage_options.index(current_stage),
        format_func=lambda v: stage_labels[v],
    )
    st.markdown(
        '<span class="ci-badge ci-badge-neutral">🔒 read-only</span>'
        if selected_stage != "live"
        else '<span class="ci-badge ci-badge-direct">🟢 learning enabled</span>',
        unsafe_allow_html=True,
    )

    if selected_stage != st.session_state.stage:
        st.session_state.stage = selected_stage
        st.session_state.plan = None
        st.session_state.question = None
        st.session_state.learning_result = None
        st.session_state.patterns = None
        st.session_state.saved_decision = None
        st.session_state.current_dri = None

    st.markdown("### Competitor event")
    event_names = get_event_names()
    if not event_names:
        st.error("No competitor events were found.")
        st.stop()

    current_event = st.session_state.selected_event
    event_index = event_names.index(current_event) if current_event in event_names else 0
    selected_event_name = st.selectbox("Competitor event", options=event_names, index=event_index)
    event_date, event_description = get_event_details(selected_event_name)
    st.session_state.selected_event = selected_event_name

    with st.container(border=True):
        st.caption("Event date")
        st.write(event_date)
        st.caption("Competitor move")
        st.write(event_description)

    if selected_stage != "live":
        if st.button("Get counter-plan", use_container_width=True, type="primary"):
            try:
                run_analysis(stage=selected_stage, question=event_description, event_name=selected_event_name)
            except Exception as exc:
                st.error(f"Unable to generate counter-plan: {exc}")

        if st.button("Show learned patterns", use_container_width=True):
            try:
                st.session_state.patterns = agent.reflect_patterns(selected_stage)
            except Exception as exc:
                st.error(f"Unable to retrieve learned patterns: {exc}")

        if st.session_state.patterns:
            st.markdown("### Learned patterns")
            patterns = st.session_state.patterns
            pattern_list = patterns if isinstance(patterns, list) else [patterns]
            for pattern in pattern_list:
                with st.container(border=True):
                    st.write(str(pattern))
    else:
        # shortened per request — the dropdown above still drives the demo event;
        # this just clarifies Live is the only writable stage.
        st.caption("🟢 Live learns from the decisions you save here.")


# ============================================================
# CURRENT PLAN
# ============================================================

plan = st.session_state.plan

if plan is None:
    if st.session_state.stage == "live":
        st.markdown("### Live Intelligence")
        with st.container(border=True):
            st.write("Ask a question to begin.")
    else:
        st.markdown("### Counter-plan")
        with st.container(border=True):
            st.write("Select a competitor event and generate a counter-plan.")

else:
    if st.session_state.question:
        st.markdown(
            f'<div class="ci-question">💬 <strong>Your question</strong><br>'
            f'{html.escape(st.session_state.question)}</div>',
            unsafe_allow_html=True,
        )

    recommendation = plan_field(plan, "recommendation", "")
    general_reasoning = plan_field(plan, "general_reasoning", "")
    avoid = plan_field(plan, "avoid", "")
    evidence = plan_field(plan, "evidence", [])
    has_direct_precedent = plan_field(plan, "has_direct_precedent", False)

    render_plan_card(plan, recommendation)

    current_dri = st.session_state.current_dri or calculate_dri(selected_stage, st.session_state.question or event_description)
    st.session_state.current_dri = current_dri
    render_dri_card(current_dri)

    if not has_direct_precedent:
        st.caption(
            "⚠️ The recommendation uses available company memory and general reasoning, "
            "not a directly matching prior event."
        )

    main_column, memory_column = st.columns([1.7, 1], gap="large")

    with main_column:
        st.markdown("#### Agent reasoning")
        st.caption("General strategy reasoning, kept separate from memory evidence above.")
        with st.container(border=True):
            st.write(general_reasoning if general_reasoning else "No additional reasoning was returned.")

        if avoid:
            st.markdown(
                f'<div class="ci-plan-card" style="border-color:#F87171;">'
                f'<div class="ci-mem-tag" style="color:#F87171;">⚠️ avoid</div>'
                f'<div class="ci-plan-text">{html.escape(avoid)}</div></div>',
                unsafe_allow_html=True,
            )

    with memory_column:
        render_memory_evidence(evidence, "Company memory")

        if selected_stage == "live":
            st.markdown("#### Decision")
            decision = st.radio("Decision", options=["Adopted", "Rejected"], horizontal=True, key="live_decision")
            outcome_note = st.text_area(
                "Outcome or feedback",
                placeholder="Optional. Describe what happened after the decision.",
                height=100, key="live_outcome",
            )

            if st.button("Save decision", use_container_width=True, type="primary"):
                # Reserved right here, in the same spot as the button — matches
                # where this used to render before it was moved full-width.
                st.markdown('<div id="ci-learning-anchor"></div>', unsafe_allow_html=True)
                stepper_placeholder = st.empty()
                try:
                    selected_event = st.session_state.selected_event or selected_event_name
                    selected_event_date, _ = get_event_details(selected_event)

                    # Jump the page to the panel immediately, before any work starts,
                    # so the judge is already looking at it when step 1 lights up.
                    scroll_to_learning_cycle()

                    request_text = st.session_state.question or event_description
                    before_dri = calculate_dri(selected_stage, request_text)

                    render_learning_stepper(stepper_placeholder, completed_steps=[], active_step=0)
                    saved = agent.record_decision(
                        stage=selected_stage, event_title=selected_event,
                        event_date=str(selected_event_date), plan=plan,
                        decision=decision, outcome_note=outcome_note,
                    )
                    render_learning_stepper(stepper_placeholder, completed_steps=[0], active_step=1)

                    # The verification/re-evaluation work is one real backend call.
                    # No artificial delays are used between steps.
                    render_learning_stepper(stepper_placeholder, completed_steps=[0, 1], active_step=2)
                    learning_result = agent.learn_from_decision(
                        request_text=request_text, event_title=selected_event,
                        event_date=str(selected_event_date), plan=plan,
                        decision=decision, outcome_note=outcome_note,
                    )

                    done = learning_result.get("learning_complete", False)
                    render_learning_stepper(
                        stepper_placeholder,
                        completed_steps=[0, 1, 2, 3, 4, 5],
                        active_step=6,
                    )

                    after_dri = calculate_dri("live", request_text)
                    learning_result["dri_before"] = before_dri
                    learning_result["dri_after"] = after_dri
                    learning_result["learning_complete"] = bool(done)

                    render_learning_stepper(
                        stepper_placeholder,
                        completed_steps=[0, 1, 2, 3, 4, 5, 6] if done else [0, 1, 2, 3, 4, 5],
                        active_step=None if done else 6,
                    )

                    st.session_state.learning_result = learning_result
                    st.session_state.saved_decision = saved
                except Exception as exc:
                    stepper_placeholder.empty()
                    st.error(f"Unable to complete learning cycle: {exc}")


# ============================================================
# LEARNING RESULT — full width, sits right below the trace panel
# once the page reruns with a saved result.
# ============================================================

learning_result = st.session_state.learning_result

if learning_result:
    st.markdown("---")
    st.markdown("## Learning result")

    st.markdown("#### Added to Live memory")
    saved = learning_result.get("saved", {})
    saved_text = saved.get("saved_text", "") or (st.session_state.saved_decision or {}).get("saved_text", "")
    with st.container(border=True):
        st.markdown('<div class="ci-mem-tag">🟢 sent to hindsight</div>', unsafe_allow_html=True)
        st.write(saved_text if saved_text else "The decision was saved, but the saved memory text was not returned.")

    before = learning_result.get("before")
    after = learning_result.get("after")
    recommendation_changed = learning_result.get("recommendation_changed", False)

    diff_class = "ci-diff-changed" if recommendation_changed else "ci-diff-unchanged"
    before_column, after_column = st.columns(2, gap="large")

    dri_before = learning_result.get("dri_before", {})
    dri_after = learning_result.get("dri_after", {})

    with before_column:
        st.markdown("#### Before learning")
        before_text = plan_field(before, "recommendation", "")
        st.markdown(
            f'<div class="ci-plan-card {diff_class}"><div class="ci-plan-text">'
            f'{html.escape(before_text) if before_text else "Previous recommendation unavailable."}</div></div>',
            unsafe_allow_html=True,
        )
        score = dri_before.get("score") if isinstance(dri_before, dict) else None
        note = ("Strong historical support" if score is not None and score >= 75 else
                "Moderate historical support" if score is not None and score >= 50 else
                "Limited historical support" if score is not None else "Reliability index unavailable")
        st.markdown(
            f'<div class="ci-dri-compare"><div class="ci-dri-compare-label">Decision Reliability Index</div>'
            f'<div class="ci-dri-compare-score">{html.escape(str(int(score)) + " / 100" if score is not None else "—")}</div>'
            f'<div class="ci-dri-compare-note">{html.escape(note)}</div></div>',
            unsafe_allow_html=True,
        )

    with after_column:
        st.markdown("#### After learning")
        after_text = plan_field(after, "recommendation", "")
        st.markdown(
            f'<div class="ci-plan-card {diff_class}"><div class="ci-plan-text">'
            f'{html.escape(after_text) if after_text else "Updated recommendation unavailable."}</div></div>',
            unsafe_allow_html=True,
        )
        score = dri_after.get("score") if isinstance(dri_after, dict) else None
        note = ("Strong historical support" if score is not None and score >= 75 else
                "Moderate historical support" if score is not None and score >= 50 else
                "Limited historical support" if score is not None else "Reliability index unavailable")
        st.markdown(
            f'<div class="ci-dri-compare"><div class="ci-dri-compare-label">Decision Reliability Index</div>'
            f'<div class="ci-dri-compare-score">{html.escape(str(int(score)) + " / 100" if score is not None else "—")}</div>'
            f'<div class="ci-dri-compare-note">{html.escape(note)}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")
    if recommendation_changed:
        st.success("The new experience materially changed the recommendation.")
    else:
        st.info("The recommendation stayed the same — the new experience did not alter the current response.")

    st.markdown("#### Updated memory")
    updated_evidence = plan_field(after, "evidence", []) or learning_result.get("updated_memories", [])
    items = list(evidence_items(updated_evidence)) if updated_evidence and isinstance(updated_evidence[0], dict) \
        else [(str(m).strip(), "", "") for m in (updated_evidence or []) if str(m).strip()]

    if items:
        with st.expander("View relevant memories recalled after learning"):
            for text, why, mem_id in items:
                with st.container(border=True):
                    if mem_id:
                        st.caption(mem_id)
                    st.write(text)
                    if why:
                        st.caption(f"Why it matters: {why}")
    else:
        with st.container(border=True):
            st.write("No relevant updated memory was selected.")

    st.markdown("#### Learning validation")
    saved_memory_recalled = learning_result.get("saved_memory_recalled", False)
    memory_evidence_used = learning_result.get("memory_evidence_used", False)
    with st.container(border=True):
        mark1 = '<span class="ci-check-yes">✓</span>' if saved_memory_recalled else '<span class="ci-check-no">○</span>'
        mark2 = '<span class="ci-check-yes">✓</span>' if memory_evidence_used else '<span class="ci-check-no">○</span>'
        st.markdown(
            f'{mark1} The newly saved decision was '
            f'{"recalled from Hindsight." if saved_memory_recalled else "not recalled in the verification pass."}',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'{mark2} The recalled experience was '
            f'{"used as evidence for the updated analysis." if memory_evidence_used else "not selected as evidence."}',
            unsafe_allow_html=True,
        )


# ============================================================
# ASK ME ANYTHING
# ============================================================

user_question = st.chat_input("Ask me anything...")

if user_question and user_question.strip():
    try:
        run_analysis(stage=st.session_state.stage, question=user_question.strip(), event_name=selected_event_name)
        st.rerun()
    except Exception as exc:
        st.error(f"Unable to process your question: {exc}")