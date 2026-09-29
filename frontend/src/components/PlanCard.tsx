import type { Plan } from "../api";

interface PlanCardProps {
  plan: Plan;
}

/**
 * The core deliverable: the recommendation, plus explicit provenance.
 *
 * The memory bar makes the "memory was actually used" claim visible - every
 * recalled memory is a chip, and chips that were cited as evidence are lit.
 * This is the artifact that backs the 25% memory criterion.
 */
export function PlanCard({ plan }: PlanCardProps) {
  const recalled = plan.memories?.length ?? 0;
  const cited = plan.evidence?.length ?? 0;

  return (
    <section className="plan-card">
      <div className="plan-card__badges">
        {plan.has_direct_precedent ? (
          <span className="badge badge--good">Direct precedent found</span>
        ) : (
          <span className="badge badge--warn">No direct precedent</span>
        )}

        <span
          className={`badge badge--${
            plan.confidence === "high"
              ? "good"
              : plan.confidence === "medium"
                ? "info"
                : "neutral"
          }`}
        >
          Confidence: {plan.confidence}
        </span>
      </div>

      {recalled > 0 ? (
        <div className="memory-bar">
          <div className="memory-bar__chips">
            {Array.from({ length: Math.max(recalled, cited) }).map((_, i) => (
              <span
                key={i}
                className={`memory-chip ${i < cited ? "memory-chip--cited" : ""}`}
              />
            ))}
          </div>
          <div className="memory-bar__caption">
            {recalled} memories recalled &middot; {cited} used as evidence
          </div>
        </div>
      ) : (
        <p className="memory-bar__caption">
          No memories were recalled for this request.
        </p>
      )}

      <p className="plan-card__text">
        {plan.recommendation || "No recommendation was returned."}
      </p>
    </section>
  );
}

interface EvidenceListProps {
  evidence: Plan["evidence"];
  title?: string;
}

export function EvidenceList({ evidence, title = "Company memory" }: EvidenceListProps) {
  const items = evidence ?? [];

  return (
    <div className="evidence">
      <h4 className="section-title">{title}</h4>

      {items.length === 0 ? (
        <div className="evidence__empty">
          No directly relevant company memory was selected.
        </div>
      ) : (
        <ul className="evidence__list">
          {items.map((item, index) => (
            <li key={item.id || index} className="evidence__item">
              <div className="evidence__tag">Cited evidence &middot; {item.id}</div>
              <p className="evidence__text">{item.text}</p>
              {item.why && (
                <p className="evidence__why">Why it matters: {item.why}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
