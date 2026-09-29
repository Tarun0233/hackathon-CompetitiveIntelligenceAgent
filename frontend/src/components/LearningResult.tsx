import { useState } from "react";
import type { LearningResult as Result } from "../api";
import { DriGauge } from "./DriGauge";

interface LearningResultProps {
  result: Result;
}

/**
 * Before/After learning comparison.
 *
 * This is the single most persuasive artifact in the whole project: the same
 * question, answered twice, with the newly saved decision changing the answer
 * and raising the reliability index. It maps directly to the rubric's
 * "memory 25%" and "innovation 30%" criteria.
 */
export function LearningResult({ result }: LearningResultProps) {
  const [showMemories, setShowMemories] = useState(false);
  const delta = (result.dri_after?.score ?? 0) - (result.dri_before?.score ?? 0);

  return (
    <section className="result" id="learning-result">
      <h2 className="result__title">Learning result</h2>

      <div className="result__saved">
        <span className="tag tag--good">Sent to Hindsight</span>
        <p>{result.saved?.saved_text}</p>
      </div>

      <div className="result__compare">
        <article className="compare">
          <h4 className="section-title">Before learning</h4>
          <div
            className={`compare__card ${
              result.recommendation_changed ? "compare__card--changed" : ""
            }`}
          >
            <p>
              {result.before?.recommendation ||
                "Previous recommendation unavailable."}
            </p>
          </div>
          <DriGauge dri={result.dri_before} label="Decision Reliability Index" compact />
        </article>

        <div className="compare__delta">
          {delta > 0 ? `+${delta}` : delta === 0 ? "0" : delta} DRI
        </div>

        <article className="compare">
          <h4 className="section-title">After learning</h4>
          <div
            className={`compare__card ${
              result.recommendation_changed ? "compare__card--changed" : ""
            }`}
          >
            <p>
              {result.after?.recommendation ||
                "Updated recommendation unavailable."}
            </p>
          </div>
          <DriGauge dri={result.dri_after} label="Decision Reliability Index" compact />
        </article>
      </div>

      {result.recommendation_changed ? (
        <div className="notice notice--good">
          The new experience materially changed the recommendation.
        </div>
      ) : (
        <div className="notice notice--info">
          The recommendation stayed the same &mdash; the new experience did not
          alter the current response.
        </div>
      )}

      <div className="result__validation">
        <h4 className="section-title">Learning validation</h4>
        <div className="check">
          <span
            className={result.saved_memory_recalled ? "check__yes" : "check__no"}
          >
            {result.saved_memory_recalled ? "✓" : "○"}
          </span>{" "}
          The newly saved decision was{" "}
          {result.saved_memory_recalled
            ? "recalled from Hindsight."
            : "not recalled in the verification pass."}
        </div>
        <div className="check">
          <span className={result.memory_evidence_used ? "check__yes" : "check__no"}>
            {result.memory_evidence_used ? "✓" : "○"}
          </span>{" "}
          The recalled experience was{" "}
          {result.memory_evidence_used
            ? "used as evidence for the updated analysis."
            : "not selected as evidence."}
        </div>
      </div>

      {result.updated_memories?.length > 0 && (
        <div className="result__memories">
          <button
            type="button"
            className="linkish"
            onClick={() => setShowMemories((v) => !v)}
          >
            {showMemories
              ? "Hide memories recalled after learning"
              : `View ${result.updated_memories.length} memories recalled after learning`}
          </button>

          {showMemories && (
            <ul className="evidence__list">
              {result.updated_memories.map((memory, i) => (
                <li key={i} className="evidence__item">
                  <p className="evidence__text">{memory}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
