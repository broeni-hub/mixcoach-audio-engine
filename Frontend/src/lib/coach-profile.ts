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
  /** Einheit der Zahlen: "dB" beim Pegelsprung, "ms" beim Beat-Jitter. */
  unit?: string;
  /** Welche Groesse hier gemessen wird. */
  metric?: string;
  /** Rangkorrelation der GANZEN Reihe gegen die Reihenfolge.
   *
   *  Der Grund, warum es dieses Feld gibt: `delta` vergleicht nur die
   *  letzten drei Aufnahmen mit den drei davor, und das taeuscht in beide
   *  Richtungen. Im Bestand vom 27.08.2026 meldet der Beat-Jitter
   *  delta = -3,8 ms bei einer Korrelation von -0,004 (also gar keine
   *  Entwicklung), und der Pegelsprung delta = 0,0 bei -0,73 (also sehr
   *  wohl eine). Wer nur delta anzeigt, zeigt einmal Fortschritt, wo keiner
   *  ist, und einmal keinen, wo welcher ist. */
  rankCorrelation?: number | null;
  /** Bewegt sich die Groesse ueber die Aufnahmen ueberhaupt in eine
   *  Richtung? Ist das false, darf KEIN Pfeil erscheinen - "keine
   *  Veraenderung" und "keine Entwicklung erkennbar" sind zweierlei. */
  developmentVisible?: boolean;
}

export interface CoachProfile {
  /** Eigene AUFNAHMEN, nicht Reports - und ohne fremde Sets. Bis zum
   *  27.08.2026 stand hier die Zahl der Reports: "56 Sets" bei 24
   *  Aufnahmen, davon 6 fremde. REC001 allein lag elfmal vor. */
  setsAnalyzed: number;
  transitionsMeasured: number;
  /** Wie viele fremde Sets nicht mitgezaehlt wurden - eine stille Auswahl
   *  ist eine, ueber die niemand nachfragen kann. */
  excludedForeignRecordings?: number;
  timeline: Array<Record<string, unknown>>;
  trends: Record<string, CoachTrend>;
  /** Pegelsprung ueber die Zeit - Spearman -0,339 gegen das menschliche
   *  Urteil. Bis zum 20.08.2026 stand hier "die einzige Groesse mit
   *  belegtem Zusammenhang"; seitdem ist der Beat-Jitter die zweite
   *  (-0,336, siehe app/audio/beat_jitter.py). Eine Zeitreihe hat bisher
   *  nur der Pegelsprung. Siehe profile.pegel_zeitreihe. */
  loudnessSeries?: LoudnessPoint[];
  loudnessTrend?: LoudnessTrend;
  /** Zweite Achse seit dem 27.08.2026: Beat-Jitter in ms. Ueber Sebastians
   *  14 eigene Aufnahmen FLACH (r = -0,004) - die Achse gibt es, eine
   *  Entwicklung zeigt sie nicht. Steht trotzdem da: eine ehrliche Null
   *  ist ein Ergebnis. */
  jitterSeries?: LoudnessPoint[];
  jitterTrend?: LoudnessTrend;
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

/** Darf neben einer Achse ein Fortschritts-Pfeil stehen?
 *
 *  Die Regel steht hier und nicht in der Komponente, weil sie eine Aussage
 *  über die Messung ist und keine über das Layout: ein Pfeil behauptet eine
 *  Richtung, und die gibt es nur, wenn sich die GANZE Reihe in eine bewegt.
 *
 *  `delta` allein reicht nicht. Es vergleicht die letzten drei Aufnahmen mit
 *  den drei davor und täuscht in beide Richtungen — im Bestand vom
 *  27.08.2026 meldet der Beat-Jitter delta = −3,8 ms bei einer
 *  Rangkorrelation von −0,004 (kein Fortschritt), der Pegelsprung delta = 0,0
 *  bei −0,73 (sehr wohl einer).
 */
export function zeigtPfeil(trend?: LoudnessTrend | null): boolean {
  if (!trend) return false;
  return trend.developmentVisible === true
    && trend.delta != null
    && trend.delta !== 0;
}
