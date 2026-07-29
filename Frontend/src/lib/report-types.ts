// Shared report types. The Python backend, the in-browser fallback, and the
// mock fixtures all hydrate into these shapes so every report page renders
// against one contract. All fields except `id` are optional — the UI must
// degrade gracefully when the backend omits something.

export interface AudioMetric {
  /** Display label, e.g. "BPM Drift" */
  label: string;
  /** Raw numeric value if available */
  value: number | null;
  /** Pre-formatted display string (e.g. "124 BPM", "+2.3 dB") */
  display?: string;
  /** Optional 0..100 confidence reported by the analyzer */
  confidence?: number | null;
  /** Optional severity hint to colour the chip */
  severity?: "info" | "good" | "warning" | "critical";
}

export interface TimelineEvent {
  /** Display time, mm:ss */
  time: string;
  /** Optional raw seconds offset */
  timeSec?: number;
  label: string;
  type: "good" | "warning" | "info";
}

export interface SkillScore {
  /** Stable key, e.g. "beatmatching" */
  key: string;
  /** Display label */
  label: string;
  /** 0..100, or null when not measured */
  value: number | null;
  /** Optional one-line rationale */
  rationale?: string;
}

export interface CoachFeedback {
  /** Headline summary, 1–2 sentences */
  summary?: string;
  /** Things the user did well */
  worked: string[];
  /** Things to improve */
  improve: string[];
  /** 0..100 model confidence */
  confidence?: number | null;
}

export interface ExerciseRecommendation {
  id?: string;
  title: string;
  description: string;
  /** XP reward when completed */
  xp?: number;
  /** 1..5 difficulty */
  difficulty?: number;
  /** Optional CTA target */
  href?: string;
}

export interface CurvePoint {
  t: number;
  value: number;
}

export interface FrequencyBalance {
  bass: number;
  mid: number;
  high: number;
}

/** Single point on a horizontal energy/volume curve. */
export interface DetectedTransition {
  index: number;
  /** Seconds offsets within the recording */
  startSec: number;
  endSec: number;
  midSec: number;
  bpmBefore: number | null;
  bpmAfter: number | null;
  bpmDrift: number | null;
  /** 0..100 overall transition quality */
  qualityScore: number | null;
  /** Optional skill breakdown, same keys as SkillScore */
  scores?: Partial<Record<string, number>>;
  /** Human label */
  label: "smooth" | "neutral" | "rough" | string;
  /** Optional headline note ("Bass clash at 02:14") */
  note?: string;
}

/** Base shape shared by every report. Every field is optional so partial
 *  backend responses still render. */
export interface AnalysisResult {
  id: string;
  fileName?: string;
  createdAt?: string;
  /** "single" = one transition; "set" = long recording with many transitions */
  mode?: "single" | "set";
  bpm?: number | null;
  key?: string | null;
  durationSec?: number | null;
  overallScore?: number | null;
  skills?: SkillScore[];
  energyCurve?: CurvePoint[];
  volumeCurve?: CurvePoint[];
  frequency?: FrequencyBalance | null;
  timeline?: TimelineEvent[];
  strengths?: string[];
  weaknesses?: string[];
  coach?: CoachFeedback | null;
  exercises?: ExerciseRecommendation[];
  /** Provider name — "local", "remote", "mock". Used for diagnostics. */
  source?: "local" | "remote" | "mock" | "cache";
}

export interface SingleTransitionAnalysisResult extends AnalysisResult {
  mode?: "single";
  /** The cue / overlap region. */
  transition?: {
    cuePointSec: number | null;
    overlapSec: number | null;
    bpmDrift: number | null;
    harmonicLabel?: string;
    camelotA?: string;
    camelotB?: string;
    bassClashScore?: number | null;
    phraseAlignmentScore?: number | null;
  };
  trackB?: { fileName: string; bpm?: number | null; key?: string | null };
}

export interface FullSetAnalysisResult extends AnalysisResult {
  mode?: "set";
  /** Total set duration in seconds */
  setDurationSec?: number | null;
  /** Average BPM across the set */
  averageBpm?: number | null;
  /** All transitions detected in chronological order */
  transitions?: DetectedTransition[];
  /** Indices into `transitions` */
  bestTransitionIndex?: number | null;
  weakestTransitionIndex?: number | null;
  /** Free-form list of recurring issues found across the set */
  commonMistakes?: string[];
  /** Coach commentary on the overall set flow / arc */
  setFlowFeedback?: string;
}

/** Type-guard helpers. */
export function isFullSet(r: AnalysisResult): r is FullSetAnalysisResult {
  return r.mode === "set" || Array.isArray((r as FullSetAnalysisResult).transitions);
}
