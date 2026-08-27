// Coach-Profil: Trends, Muster und Uebungen ueber alle Sets - vom Backend
// aggregiert (inkl. Feedback-Filter: Fehlalarme zaehlen nicht).

import { engineFetch } from "@/lib/api/engineFetch";
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

/** Ein Punkt der Pegel-Sauberkeit: eine AUFNAHME, nicht ein Report. */
export interface LoudnessPoint {
  fileName: string;
  analysisId: string;
  createdAt: string;
  /** Median des Pegelsprungs dieser Aufnahme in dB. Niedriger ist besser. */
  medianJumpDb: number;
  shareAboveThresholdPct: number;
  transitions: number;
  /** Wie viele Analysen dieser Aufnahme zusammengefasst wurden. */
  analyses: number;
  /** Eigene Aufnahme oder fremdes Set zum Studieren (Heuristik, siehe
   *  profile._selbst_aufgenommen). Nur eigene zaehlen in den Trend. */
  ownRecording: boolean;
}

export interface LoudnessTrend {
  /** Aktueller Median in dB, Mittel der letzten drei Aufnahmen. */
  current: number | null;
  /** Veraenderung gegen die drei davor. NEGATIV IST FORTSCHRITT. */
  delta: number | null;
  /** Immer true - steht hier, damit die Anzeige es nicht raten muss. */
  lowerIsBetter: boolean;
  /** Auf wie vielen eigenen Aufnahmen der Trend ruht. */
  recordings: number;
  /** Wie viele fremde Sets nicht mitgezaehlt wurden. */
  excludedForeign?: number;
  currentSharePct: number | null;
  deltaSharePct: number | null;
  thresholdDb?: number;
}

export interface CoachProfile {
  setsAnalyzed: number;
  transitionsMeasured: number;
  timeline: Array<Record<string, unknown>>;
  trends: Record<string, CoachTrend>;
  /** Pegelsprung ueber die Zeit - Spearman -0,339 gegen das menschliche
   *  Urteil. Bis zum 20.08.2026 stand hier "die einzige Groesse mit
   *  belegtem Zusammenhang"; seitdem ist der Beat-Jitter die zweite
   *  (-0,336, siehe app/audio/beat_jitter.py). Eine Zeitreihe hat bisher
   *  nur der Pegelsprung. Siehe profile.pegel_zeitreihe. */
  loudnessSeries?: LoudnessPoint[];
  loudnessTrend?: LoudnessTrend;
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
    const res = await engineFetch(`${base}/coach/profile?lang=${lang}`);
    if (!res.ok) return null;
    return (await res.json()) as CoachProfile;
  } catch {
    return null;
  }
}
