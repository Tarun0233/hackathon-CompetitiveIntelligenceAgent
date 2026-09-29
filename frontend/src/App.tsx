import { useCallback, useEffect, useState } from "react";
import {
  api,
  runLearningCycle,
  STAGES,
  type AnalyzeResponse,
  type CompetitorEvent,
  type HealthResponse,
  type LearningResult as Result,
  type Stage,
  type StepState,
} from "./api";
import { DriGauge } from "./components/DriGauge";
import { EvidenceList, PlanCard } from "./components/PlanCard";
import { LearningCycle } from "./components/LearningCycle";
import { LearningResult } from "./components/LearningResult";

/* Step labels are owned by agent.py and served from /api/learning-steps, so the
   console always matches what the backend actually does. */

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [events, setEvents] = useState<CompetitorEvent[]>([]);
  const [stage, setStage] = useState<Stage>("full");
  const [eventIndex, setEventIndex] = useState(0);
  const [question, setQuestion] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [patterns, setPatterns] = useState<string | null>(null);

  const [analysing, setAnalysing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [decision, setDecision] = useState("Adopted");
  const [outcomeNote, setOutcomeNote] = useState("");

  const [cycleSteps, setCycleSteps] = useState<string[]>([]);
  const [cycleStates, setCycleStates] = useState<StepState[]>([]);
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  const event = events[eventIndex];

  /* ---------------------------------------------------------- bootstrap */
  useEffect(() => {
    Promise.all([api.health(), api.events(), api.learningSteps()])
      .then(([h, e, s]) => {
        setHealth(h);
        setEvents(e);
        setCycleSteps(s.steps);
        setCycleStates(s.steps.map(() => "pending"));
        if (e.length > 0) setQuestion(e[0].description);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  /* --------------------------------- reveal the learning result on arrival
     Runs after React has committed the result to the DOM, so the element is
     guaranteed to exist and have its final height. Without this the user is
     left staring at the finished console, with the payoff below the fold. */
  useEffect(() => {
    if (!result) return;

    const frame = requestAnimationFrame(() => {
      document
        .getElementById("learning-result")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    return () => cancelAnimationFrame(frame);
  }, [result]);

  /* --------------------------------------------- stage change resets view */
  const changeStage = (next: Stage) => {
    setStage(next);
    setAnalysis(null);
    setResult(null);
    setPatterns(null);
    setCycleStates(cycleSteps.map(() => "pending"));
    setActiveStep(null);
  };

  const selectEvent = (index: number) => {
    setEventIndex(index);
    if (events[index]) setQuestion(events[index].description);
    setAnalysis(null);
    setResult(null);
  };

  /* ----------------------------------------------------------- analysis */
  const runAnalysis = useCallback(async () => {
    const trimmed = question.trim();

    if (!trimmed) {
      setError("Enter a competitor event or question first.");
      return;
    }

    setAnalysing(true);
    setError(null);

    try {
      const data = await api.analyze(stage, trimmed);
      setAnalysis(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAnalysing(false);
    }
  }, [question, stage]);

  /* ------------------------------------------------------ learned patterns */
  const loadPatterns = useCallback(async () => {
    try {
      const data = await api.patterns(stage);
      setPatterns(data.patterns);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [stage]);

  /* ------------------------------------------------------ learning cycle */
  const saveDecision = useCallback(async () => {
    if (!analysis || !event) return;

    setRunning(true);
    setResult(null);
    setError(null);
    setCycleStates(cycleSteps.map(() => "pending"));
    setActiveStep(0);

    // Scroll the console into view immediately so it is the focus.
    setTimeout(() => {
      document
        .getElementById("learning-cycle")
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 60);

    await runLearningCycle(
      {
        ...analysis,
        event_title: event.title,
        event_date: event.date,
        decision,
        outcome_note: outcomeNote,
      },
      {
        onSteps: setCycleSteps,
        onStep: (step, state) => {
          setCycleStates((prev) => {
            const next = [...prev];
            next[step] = state;
            return next;
          });
          setActiveStep(state === "active" ? step : null);
        },
        onResult: (data) => setResult(data),
        onError: setError,
      }
    );

    setRunning(false);
    setActiveStep(null);
  }, [analysis, event, decision, outcomeNote, cycleSteps]);

  const isLive = stage === "live";
  const currentStageMeta = STAGES.find((s) => s.id === stage);

  return (
    <div className="app">
      <header className="app__header">
        <h1>Competitive Intelligence Agent</h1>
        <p className="app__subtitle">
          A decision-support agent that recalls competitive experience, proposes
          a response, and learns from outcomes.
        </p>
        {health && (
          <div className="app__status">
            <span className={health.hindsight_configured ? "ok" : "bad"}>
              Hindsight {health.hindsight_configured ? "connected" : "not configured"}
            </span>
            <span className={health.groq_configured ? "ok" : "bad"}>
              Groq {health.groq_configured ? "connected" : "not configured"}
            </span>
            <span className="muted">bank: {health.bank}</span>
          </div>
        )}
      </header>

      <div className="layout">
        {/* ---------------------------------------------------- sidebar */}
        <aside className="sidebar">
          <h3 className="section-title">Memory stage</h3>

          <div className="stages">
            {STAGES.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`stage ${stage === s.id ? "stage--active" : ""} ${
                  s.id === "live" ? "stage--live" : ""
                }`}
                onClick={() => changeStage(s.id)}
                title={s.blurb}
              >
                <span className="stage__label">{s.label}</span>
                <span className="stage__blurb">{s.blurb}</span>
              </button>
            ))}
          </div>

          <div className="sidebar__mode">
            {isLive ? (
              <span className="badge badge--good">Learning enabled</span>
            ) : (
              <span className="badge badge--neutral">Read-only</span>
            )}
          </div>

          <h3 className="section-title">Competitor event</h3>

          <select
            className="select"
            value={eventIndex}
            onChange={(e) => selectEvent(Number(e.target.value))}
          >
            {events.map((e, i) => (
              <option key={i} value={i}>
                {e.title}
              </option>
            ))}
          </select>

          {event && (
            <div className="event-card">
              <div className="event-card__label">Event date</div>
              <div className="event-card__value">{event.date}</div>
              <div className="event-card__label">Competitor move</div>
              <div className="event-card__value">{event.description}</div>
            </div>
          )}

          {!isLive && (
            <>
              <button
                type="button"
                className="btn btn--primary"
                onClick={runAnalysis}
                disabled={analysing}
              >
                {analysing ? "Analysing…" : "Get counter-plan"}
              </button>

              <button type="button" className="btn" onClick={loadPatterns}>
                Show learned patterns
              </button>
            </>
          )}

          {patterns && (
            <div className="patterns">
              <h3 className="section-title">Learned patterns</h3>
              <pre className="patterns__body">{patterns}</pre>
            </div>
          )}
        </aside>

        {/* ------------------------------------------------------ main */}
        <main className="main">
          <div className="composer">
            <textarea
              className="composer__input"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                // Behave like a chat input: Enter sends, Shift+Enter newlines.
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  runAnalysis();
                }
              }}
              placeholder="Describe a competitor move, or ask a strategy question…"
              aria-label="Ask me anything"
            />

            <button
              type="button"
              className="composer__send"
              onClick={runAnalysis}
              disabled={analysing || !question.trim()}
              aria-label="Send question"
              title="Send question"
            >
              {analysing ? (
                <span className="composer__spinner" />
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="19" x2="12" y2="5" />
                  <polyline points="5 12 12 5 19 12" />
                </svg>
              )}
            </button>
          </div>

          <div className="composer__meta">
            <span className="composer__hint">
              Press <kbd>Enter</kbd> to send &middot; <kbd>Shift</kbd>+
              <kbd>Enter</kbd> for a new line
            </span>
            {question.trim() && <span className="composer__count">{question.trim().length} chars</span>}
          </div>

          {/* In Live the chat input IS the way to ask, so no extra send button.
              Read-only stages keep an explicit button next to the input. */}
          {!isLive && (
            <button
              type="button"
              className="btn btn--primary btn--wide"
              onClick={runAnalysis}
              disabled={analysing}
            >
              {analysing ? "Analysing…" : "Generate counter-plan"}
            </button>
          )}

          {error && <div className="notice notice--bad">{error}</div>}

          {isLive && (
            <div className="live-status" aria-live="polite">
              {analysing ? (
                <>
                  <span className="composer__spinner" /> Thinking&hellip; recalling
                  memory and reasoning with Groq
                </>
              ) : (
                <>Live is writable &mdash; the decision you save here trains the agent.</>
              )}
            </div>
          )}

          {!analysis && !analysing && (
            <div className="empty">
              <h3>{isLive ? "Live Intelligence" : "Counter-plan"}</h3>
              <p>
                {isLive
                  ? "Ask a question to begin."
                  : "Select a competitor event and generate a counter-plan."}
              </p>
              {currentStageMeta && (
                <p className="muted">{currentStageMeta.blurb}</p>
              )}
            </div>
          )}

          {analysis && (
            <>
              <div className="question">
                <strong>Your question</strong>
                <p>{analysis.question}</p>
              </div>

              <div className="grid">
                <div className="grid__main">
                  <PlanCard plan={analysis.plan} />

                  {analysis.plan.general_reasoning && (
                    <>
                      <h4 className="section-title">Agent reasoning</h4>
                      <p className="muted">
                        General strategy reasoning, kept separate from memory
                        evidence above.
                      </p>
                      <div className="panel">
                        {analysis.plan.general_reasoning}
                      </div>
                    </>
                  )}

                  {analysis.plan.avoid && (
                    <div className="avoid">
                      <span className="tag tag--bad">Avoid</span>
                      <p>{analysis.plan.avoid}</p>
                    </div>
                  )}

                  {isLive && (
                    <div className="decision">
                      <h4 className="section-title">Decision</h4>

                      <div className="decision__options">
                        {["Adopted", "Rejected"].map((option) => (
                          <button
                            key={option}
                            type="button"
                            className={`chip ${
                              decision === option ? "chip--active" : ""
                            }`}
                            onClick={() => setDecision(option)}
                          >
                            {option}
                          </button>
                        ))}
                      </div>

                      <textarea
                        className="outcome__input"
                        rows={2}
                        value={outcomeNote}
                        onChange={(e) => setOutcomeNote(e.target.value)}
                        placeholder="Optional. Describe what happened after the decision."
                      />

                      <button
                        type="button"
                        className="btn btn--primary btn--wide"
                        onClick={saveDecision}
                        disabled={running}
                      >
                        {running ? "Learning…" : "Save decision"}
                      </button>
                    </div>
                  )}
                </div>

                <div className="grid__side">
                  <DriGauge dri={analysis.dri} label="Decision Reliability Index" />

                  {!analysis.plan.has_direct_precedent && (
                    <p className="muted small">
                      The recommendation uses available company memory and
                      general reasoning, not a directly matching prior event.
                    </p>
                  )}

                  <EvidenceList evidence={analysis.plan.evidence} />
                </div>
              </div>
            </>
          )}

          {(running || cycleStates.some((s) => s !== "pending")) && (
            <LearningCycle
              steps={cycleSteps}
              states={cycleStates}
              activeStep={activeStep}
              running={running}
            />
          )}

          {result && <LearningResult result={result} />}
        </main>
      </div>
    </div>
  );
}
