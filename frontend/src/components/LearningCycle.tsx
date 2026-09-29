import { useEffect, useRef } from "react";
import type { StepState } from "../api";

interface LearningCycleProps {
  steps: string[];
  states: StepState[];
  activeStep: number | null;
  running: boolean;
}

/**
 * Live console for the 7-step learning cycle.
 *
 * Crucially, each step lights up only when the real backend call it represents
 * has actually returned - these are driven by SSE frames from the API, not by
 * a timer. The old Streamlit version painted all seven at once on rerun.
 */
export function LearningCycle({
  steps,
  states,
  activeStep,
  running,
}: LearningCycleProps) {
  const anchorRef = useRef<HTMLDivElement>(null);

  // Keep the active step in view as the cycle progresses.
  useEffect(() => {
    if (activeStep === null || !anchorRef.current) return;
    anchorRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeStep]);

  const completed = states.filter((s) => s === "completed").length;
  const pct = steps.length ? Math.round((100 * completed) / steps.length) : 0;

  return (
    <div className="cycle" ref={anchorRef} id="learning-cycle">
      <div className="cycle__head">
        <span className="cycle__title">
          {running ? "LIVE LEARNING CYCLE" : "LEARNING CYCLE"}
        </span>
        <span className="cycle__pct">{pct}%</span>
      </div>

      <div className="cycle__track">
        <div className="cycle__fill" style={{ width: `${pct}%` }} />
      </div>

      <ol className="cycle__steps">
        {steps.map((label, index) => {
          const state = states[index] ?? "pending";

          return (
            <li
              key={label}
              className={`cycle__step cycle__step--${state}`}
            >
              <span className="cycle__marker">
                {state === "completed" ? (
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#0B1020"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : state === "active" ? (
                  <span className="cycle__spinner" />
                ) : (
                  String(index + 1).padStart(2, "0")
                )}
              </span>
              <span className="cycle__label">{label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
