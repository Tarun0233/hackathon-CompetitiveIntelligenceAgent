/**
 * Typed client for the FastAPI backend (server.py).
 *
 * All requests go to a relative /api path, which Vite proxies to
 * http://127.0.0.1:8000 in development. This keeps CORS out of the picture and
 * means the same build works behind a reverse proxy in production.
 */

export type Stage = "cold" | "early" | "full" | "live";

export const STAGES: { id: Stage; label: string; blurb: string }[] = [
  {
    id: "cold",
    label: "Cold",
    blurb: "No history at all. Shows the generic, memory-free baseline.",
  },
  {
    id: "early",
    label: "Early",
    blurb: "Only the first slice of history, including known failures.",
  },
  {
    id: "full",
    label: "Full",
    blurb: "Everything retained, including successes and outcomes.",
  },
  {
    id: "live",
    label: "Live",
    blurb: "Writable. Saves decisions and re-learns from them.",
  },
];

export interface CompetitorEvent {
  title: string;
  date: string;
  description: string;
}

export interface EvidenceItem {
  id: string;
  text: string;
  why: string;
}

export interface Plan {
  has_direct_precedent: boolean;
  confidence: string;
  recommendation: string;
  general_reasoning: string;
  avoid: string;
  memories: string[];
  evidence: EvidenceItem[];
}

export interface Dri {
  score: number | null;
  precedent: number;
  outcome: number;
  decision_memories?: number;
  outcome_memories?: number;
  error?: string;
}

export interface AnalyzeResponse {
  stage: Stage;
  question: string;
  plan: Plan;
  dri: Dri;
}

export interface LearningResult {
  saved: { saved_text: string; document_id: string; bank_id: string };
  before: Plan;
  after: Plan;
  updated_memories: string[];
  saved_memory_recalled: boolean;
  memory_evidence_used: boolean;
  recommendation_changed: boolean;
  learning_complete: boolean;
  dri_before: Dri;
  dri_after: Dri;
}

export interface HealthResponse {
  status: string;
  hindsight_configured: boolean;
  groq_configured: boolean;
  bank: string;
  stages: Stage[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new Error(
      "Could not reach the API. Is the backend running on port 8000?"
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;

    try {
      const body = await response.json();
      detail = body?.detail ?? detail;
    } catch {
      /* non-JSON error body; keep the generic message */
    }

    throw new Error(String(detail));
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  events: () => request<CompetitorEvent[]>("/events"),

  /** Authoritative step labels — the UI must not hardcode these. */
  learningSteps: () => request<{ steps: string[] }>("/learning-steps"),

  analyze: (stage: Stage, question: string) =>
    request<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify({ stage, question }),
    }),

  patterns: (stage: Stage) =>
    request<{ patterns: string }>("/patterns", {
      method: "POST",
      body: JSON.stringify({ stage }),
    }),
};

/* ============================================================
   LEARNING CYCLE — Server-Sent Events
   ============================================================ */

export type StepState = "pending" | "active" | "completed";

export interface LearnCallbacks {
  onSteps?: (steps: string[]) => void;
  onStep?: (step: number, state: StepState) => void;
  onSaved?: (saved: LearningResult["saved"]) => void;
  onResult?: (result: LearningResult) => void;
  onError?: (message: string) => void;
}

/**
 * Run the learning cycle, delivering each step over SSE as it really finishes.
 *
 * fetch() is used instead of EventSource because this is a POST with a JSON
 * body, which EventSource cannot issue. The response body is read as a stream
 * and parsed frame by frame.
 */
export async function runLearningCycle(
  payload: AnalyzeResponse & {
    event_title: string;
    event_date: string;
    decision: string;
    outcome_note: string;
  },
  callbacks: LearnCallbacks,
  signal?: AbortSignal
): Promise<void> {
  let response: Response;

  try {
    response = await fetch("/api/learn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stage: "live",
        question: payload.question,
        has_direct_precedent: payload.plan.has_direct_precedent,
        confidence: payload.plan.confidence,
        recommendation: payload.plan.recommendation,
        general_reasoning: payload.plan.general_reasoning,
        avoid: payload.plan.avoid,
        memories: payload.plan.memories,
        evidence: payload.plan.evidence,
        event_title: payload.event_title,
        event_date: payload.event_date,
        decision: payload.decision,
        outcome_note: payload.outcome_note,
      }),
      signal,
    });
  } catch {
    callbacks.onError?.("Could not reach the API. Is the backend running?");
    return;
  }

  if (!response.ok || !response.body) {
    callbacks.onError?.(`Learning cycle failed (${response.status})`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const eventLine = frame
        .split("\n")
        .find((line) => line.startsWith("event: "));
      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data: "));

      if (!eventLine || !dataLine) continue;

      const event = eventLine.slice(7).trim();
      const data = JSON.parse(dataLine.slice(6));

      if (event === "steps") callbacks.onSteps?.(data.steps);
      if (event === "status") callbacks.onStep?.(data.step, data.state);
      if (event === "saved") callbacks.onSaved?.(data);
      if (event === "result") callbacks.onResult?.(data);
      if (event === "error") callbacks.onError?.(data.message);
      if (event === "done") return;
    }
  }
}
