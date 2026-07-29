// Coach-Profil: Trends, Muster und Uebungen ueber alle Sets - vom Backend
// aggregiert (inkl. Feedback-Filter: Fehlalarme zaehlen nicht).

import { getEngineBaseUrl } from "./api/remoteProvider";

export interface CoachTrend {
  current: number | null;
  delta: number | null;
}

export interface CoachPattern {
  id: string;
  title: string;
  evidence: string;
}

export interface CoachExercise {
  title: string;
  description: string;
  analysisId: string;
  midSec: number | null;
  startSec: number | null;
}

export interface CoachHighlight {
  analysisId: string;
  fileName: string;
  index: number;
  midSec: number | null;
  startSec: number | null;
  name: string;
  quality: number;
  feedback: string | null;
}

export interface CoachProfile {
  setsAnalyzed: number;
  transitionsMeasured: number;
  timeline: Array<Record<string, unknown>>;
  trends: Record<string, CoachTrend>;
  patterns: CoachPattern[];
  best: CoachHighlight | null;
  worst: CoachHighlight | null;
  exercises: CoachExercise[];
  enoughData: boolean;
}

export async function fetchCoachProfile(lang: "de" | "en" = "de"): Promise<CoachProfile | null> {
  const base = getEngineBaseUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/coach/profile?lang=${lang}`);
    if (!res.ok) return null;
    return (await res.json()) as CoachProfile;
  } catch {
    return null;
  }
}
