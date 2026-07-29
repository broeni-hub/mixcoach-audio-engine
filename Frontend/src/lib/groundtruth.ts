// Ground-Truth-Feedback: DJs bestaetigen oder korrigieren erkannte
// Uebergaenge direkt im Report. Jede Rueckmeldung landet im Backend
// (ground_truth/) und verbessert die Erkennungs-Engine.

import { getEngineBaseUrl } from "./api/remoteProvider";

export type Verdict = "correct" | "not_a_transition" | "timing_off";

export interface FeedbackState {
  verdicts: Record<string, { midSec: number; verdict: Verdict }>;
  missed: number[];
}

function base(): string | null {
  return getEngineBaseUrl();
}

export async function fetchFeedback(analysisId: string): Promise<FeedbackState | null> {
  const url = base();
  if (!url) return null;
  try {
    const res = await fetch(`${url}/analysis/${encodeURIComponent(analysisId)}/feedback`);
    if (!res.ok) return null;
    return (await res.json()) as FeedbackState;
  } catch {
    return null;
  }
}

export async function sendVerdict(
  analysisId: string,
  index: number,
  midSec: number,
  verdict: Verdict,
  correctedSec?: number,
): Promise<boolean> {
  const url = base();
  if (!url) return false;
  try {
    const res = await fetch(`${url}/analysis/${encodeURIComponent(analysisId)}/feedback/verdict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index, midSec, verdict, correctedSec: correctedSec ?? null }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function sendMissed(analysisId: string, sec: number): Promise<boolean> {
  const url = base();
  if (!url) return false;
  try {
    const res = await fetch(`${url}/analysis/${encodeURIComponent(analysisId)}/feedback/missed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sec }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// Vision-Datenschleife: die eigenen Korrekturen als exakte Segmentgrenzen
// nutzen, um Track-Erkennung nachzuschaerfen. Gibt den aktualisierten
// Report zurueck (oder null, wenn Backend/Feedback fehlt).
export async function requestRematch(analysisId: string): Promise<{ added: number } | null> {
  const url = base();
  if (!url) return null;
  try {
    const res = await fetch(`${url}/analysis/${encodeURIComponent(analysisId)}/rematch`, {
      method: "POST",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return { added: data?.rematch?.added ?? 0 };
  } catch {
    return null;
  }
}
