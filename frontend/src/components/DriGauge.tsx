import type { Dri } from "../api";

interface DriGaugeProps {
  dri: Dri;
  label?: string;
  compact?: boolean;
}

function toneFor(score: number | null): string {
  if (score === null) return "var(--sub)";
  if (score >= 75) return "var(--green)";
  if (score >= 50) return "var(--amber)";
  return "var(--red)";
}

function noteFor(score: number | null): string {
  if (score === null) return "Reliability index unavailable";
  if (score >= 75) return "Strong historical support";
  if (score >= 50) return "Moderate historical support";
  return "Limited historical support";
}

/**
 * Decision Reliability Index shown as a radial gauge.
 *
 * DRI = 100 x (0.6 * precedent + 0.4 * outcome). Both components are drawn on
 * the same arc so the score is decomposable at a glance rather than being an
 * opaque number.
 */
export function DriGauge({ dri, label, compact = false }: DriGaugeProps) {
  const score = dri?.score ?? null;
  const clamped = score === null ? 0 : Math.max(0, Math.min(100, score));
  const pct = compact ? 0.24 : 0.32;
  const radius = 52;
  const circumference = 2 * Math.PI * radius;

  const precedent = Math.max(0, Math.min(1, dri?.precedent ?? 0));
  const outcome = Math.max(0, Math.min(1, dri?.outcome ?? 0));

  const size = compact ? 118 : 168;
  const centre = size / 2;

  return (
    <div className={`dri-gauge ${compact ? "dri-gauge--compact" : ""}`}>
      {label && <div className="dri-gauge__label">{label}</div>}

      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`Decision Reliability Index: ${
          score === null ? "unavailable" : `${score} out of 100`
        }`}
      >
        <circle
          cx={centre}
          cy={centre}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={compact ? 9 : 11}
        />

        {/* Total score */}
        <circle
          cx={centre}
          cy={centre}
          r={radius}
          fill="none"
          stroke={toneFor(score)}
          strokeWidth={compact ? 9 : 11}
          strokeLinecap="round"
          strokeDasharray={`${circumference * (clamped / 100)} ${circumference}`}
          transform={`rotate(-90 ${centre} ${centre})`}
          style={{ transition: "stroke-dasharray .6s ease" }}
        />

        {/* Precedent component (0.6 weight) */}
        <circle
          cx={centre}
          cy={centre}
          r={radius - 8}
          fill="none"
          stroke="var(--indigo)"
          strokeOpacity={0.85}
          strokeWidth={compact ? 4 : 5}
          strokeLinecap="round"
          strokeDasharray={`${circumference * precedent * pct} ${circumference}`}
          transform={`rotate(-90 ${centre} ${centre})`}
        />

        {/* Outcome component (0.4 weight) */}
        <circle
          cx={centre}
          cy={centre}
          r={radius - 17}
          fill="none"
          stroke="var(--cyan)"
          strokeOpacity={0.85}
          strokeWidth={compact ? 4 : 5}
          strokeLinecap="round"
          strokeDasharray={`${circumference * outcome * pct} ${circumference}`}
          transform={`rotate(-90 ${centre} ${centre})`}
        />
      </svg>

      <div className="dri-gauge__readout">
        <div className="dri-gauge__score" style={{ color: toneFor(score) }}>
          {score === null ? "—" : score}
        </div>
        {!compact && <div className="dri-gauge__unit">/ 100</div>}
      </div>

      <div className="dri-gauge__note">{noteFor(score)}</div>

      {!compact && (
        <div className="dri-gauge__legend">
          <span className="dot dot--indigo" />
          <span>Precedent {precedent.toFixed(2)}</span>
          <span className="dot dot--cyan" />
          <span>Outcome {outcome.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}
