// Analysis report builder. Consumes real audio measurements (see
// src/lib/audio-analysis.ts) and turns them into the report shape consumed
// by the UI. When DB-backed coaching findings are provided, they override
// the local heuristic strengths/weaknesses/feedback/exercises.
import type { Measurements } from "./audio-analysis";
import type { Finding } from "./coaching";
import type { TransitionMetrics } from "./transition-analysis";
import type { SetTransition } from "./set-analysis";


export type Genre =
  | "House" | "Tech House" | "Melodic House" | "Afro House"
  | "Progressive House" | "Techno" | "Drum & Bass";

export interface TimelineEvent {
  time: string; // mm:ss
  label: string;
  type: "good" | "warning" | "info";
}

// Backend-Vertrag "honest-v2": Ein Score ist null, wenn er (noch) nicht
// wirklich gemessen wird. Die UI zeigt dann einen Platzhalter statt einer Zahl.
export interface AnalysisScores {
  beatmatching: number | null;
  eq: number | null;
  timing: number | null;
  creativity: number | null;
  flow: number | null;
  musicality: number | null;
  overall: number | null;
}

export interface CurvePoint { t: number; value: number }

export interface AIFeedback {
  worked: string[];
  improve: string[];
  exercise: string;
  confidence: number; // 0-100
}

export interface AnalysisResult {
  id: string;
  fileName: string;
  createdAt: string;
  /** Herkunft des Reports: "local" = eingeschraenkte Browser-Auswertung
   *  (Fallback ohne Analyse-Engine, grobe Schaetzwerte). Fehlt bei
   *  Engine-Reports (Backend-Payload kennt das Feld nicht). Wird im
   *  Report als deutliche Warnung angezeigt - Ehrlichkeits-Regel: nie so
   *  tun, als waere eine Heuristik eine Messung (real passiert bei
   *  MixCoach2.WAV: Fallback zeigte fast keine Uebergaenge, waehrend die
   *  Engine 10 fand, 2026-07-17). */
  engine?: "local";
  bpm: number | null;
  key: string | null;
  transitionLength: number | null; // seconds
  energyCurve: CurvePoint[];
  volumeCurve: CurvePoint[];
  frequency: { bass: number; mid: number; high: number } | null;
  /** Vom Backend gemeldete Analyse-Warnungen (honest-v2). */
  analysisWarnings?: string[];
  /** Liste der Metriken, die das Backend noch nicht misst. */
  notMeasured?: string[];
  /** Herkunft: echtes Backend ("engine") oder Browser-Demo ("browser"). */
  source?: "engine" | "browser";
  /** Backend-Pfad zum Original-Audio (Nachhoeren im Report). */
  audioPath?: string | null;
  scores: AnalysisScores;
  timeline: TimelineEvent[];
  strengths: string[];
  weaknesses: string[];
  feedback: AIFeedback;
  exercises: { title: string; description: string; xp: number }[];
  // Optional 2-track transition data
  trackB?: { fileName: string; bpm: number; key: string };
  transition?: TransitionMetrics;
  // Optional set-mode: many transitions detected inside one long recording
  setTransitions?: SetTransition[];
  /** Library-Fingerprinting: welche Tracks wann im Set liefen. */
  library?: {
    tracks_in_library: number;
    matches: Array<{ title: string | null; artist: string | null; start: number; end: number; score: number }>;
  } | null;
  totalDurationSec?: number;
  // Persisted rule-engine findings (for 👍/👎 wiring on the report).
  findings?: { rule_id: string; rule_slug: string; title: string; diagnosis: string; fix: string; severity: "info" | "warning" | "critical"; metric: string | null; value: number | null }[];
}

function rand(min: number, max: number) { return Math.random() * (max - min) + min; }

function curve(n: number, base: number, variance: number): CurvePoint[] {
  const pts: CurvePoint[] = [];
  let v = base;
  for (let i = 0; i < n; i++) {
    v = Math.max(0, Math.min(100, v + rand(-variance, variance)));
    pts.push({ t: i, value: Math.round(v) });
  }
  return pts;
}

const EXERCISES = [
  { title: "16-Bar Phrase Challenge", description: "Mix two tracks aligning their 16-bar phrases perfectly.", xp: 40 },
  { title: "Perfect EQ Swap", description: "Practice cutting bass on outgoing track exactly as you bring in the new bass.", xp: 30 },
  { title: "Harmonic Mix Drill", description: "Mix three tracks staying within the Camelot wheel ±1.", xp: 50 },
  { title: "Filter Transition", description: "Use only a high-pass filter to transition between two tracks.", xp: 25 },
];

function pickN<T>(arr: T[], n: number): T[] {
  return [...arr].sort(() => Math.random() - 0.5).slice(0, n);
}

const STAGES = [
  "Uploading...",
  "Analyzing BPM...",
  "Analyzing Beat Grid...",
  "Analyzing Energy...",
  "Analyzing EQ...",
  "Generating Coaching...",
  "Preparing Report...",
] as const;

export const ANALYSIS_STAGES = STAGES;

export function buildAnalysisResult(
  file: { name: string; size: number },
  m?: Measurements,
  findings?: Finding[],
  extras?: {
    trackB?: Measurements & { fileName: string };
    transition?: TransitionMetrics;
    setTransitions?: SetTransition[];
    totalDurationSec?: number;
    fullVolumeCurve?: CurvePoint[];
  },
): AnalysisResult {
  // If we have real measurements, derive scores from them. Otherwise fall
  // back to a neutral, clearly non-random baseline.
  const measured = !!m;

  // --- Scores derived from measurements ---
  const beatmatching = measured
    ? Math.round(60 + 35 * (m as Measurements).bpmConfidence) // 60..95 by BPM agreement
    : 75;
  const bands = m?.bands ?? { bass: 33, mid: 34, high: 33 };
  const bandBalance = 100 - Math.min(100, Math.abs(bands.bass - 33) + Math.abs(bands.mid - 34) + Math.abs(bands.high - 33));
  const eq = measured ? Math.round(50 + bandBalance * 0.45) : 70;
  const timing = measured ? Math.round(55 + ((m as Measurements).bassStability) * 0.4) : 75;
  const musicality = measured ? Math.round(55 + ((m as Measurements).keyConfidence) * 40) : 70;
  const dr = m?.dynamicRangeDb ?? 8;
  const flow = Math.round(Math.max(40, Math.min(95, 50 + dr * 3))); // 6-12 dB DR ideal
  const peakCount = m?.peakCount ?? 0;
  const creativity = measured ? Math.round(Math.max(45, Math.min(92, 55 + peakCount * 2))) : 65;
  const overall = Math.round((beatmatching + eq + timing + creativity + flow + musicality) / 6);

  // --- Strengths / weaknesses ---
  // Prefer DB-driven findings when available, fall back to heuristic text.
  let strengths: string[] = [];
  let weaknesses: string[] = [];
  let coachExercise: string | null = null;
  let recommendedExercises: { title: string; description: string; xp: number }[] = [];

  if (findings && findings.length > 0) {
    for (const f of findings) {
      const line = `${f.rule.title}: ${f.rule.diagnosis}`;
      if (f.rule.severity === "info") strengths.push(line);
      else weaknesses.push(line);
    }
    const top = findings.find((f) => f.rule.severity !== "info") ?? findings[0];
    coachExercise = top?.exercise
      ? `${top.exercise.title} — ${top.exercise.description}`
      : top?.rule.fix ?? null;
    const seenEx = new Set<string>();
    for (const f of findings) {
      if (!f.exercise || seenEx.has(f.exercise.id)) continue;
      seenEx.add(f.exercise.id);
      recommendedExercises.push({
        title: f.exercise.title,
        description: f.exercise.description,
        xp: 20 + (f.exercise.difficulty ?? 1) * 10,
      });
      if (recommendedExercises.length >= 3) break;
    }
  }

  if (measured && strengths.length === 0 && weaknesses.length === 0) {
    const mm = m as Measurements;
    if (mm.bpmConfidence > 0.75) strengths.push(`Tempo stays locked at ${mm.bpm} BPM across the whole track (${Math.round(mm.bpmConfidence * 100)}% agreement between halves).`);
    else weaknesses.push(`Tempo drifts noticeably — only ${Math.round(mm.bpmConfidence * 100)}% agreement between the first and second half. Re-check sync before each phrase.`);

    if (bandBalance > 80) strengths.push(`Frequency balance is healthy (Bass ${bands.bass}% / Mid ${bands.mid}% / High ${bands.high}%).`);
    else weaknesses.push(`EQ balance is skewed — Bass ${bands.bass}%, Mid ${bands.mid}%, High ${bands.high}%. Aim for roughly even thirds during the transition.`);

    if (mm.bassStability > 75) strengths.push(`Bass energy is consistent (${mm.bassStability}/100 stability), no audible bass clashes.`);
    else weaknesses.push(`Bass energy fluctuates a lot (${mm.bassStability}/100). Stagger low-EQ cuts so two basslines never play full-volume together.`);

    if (mm.keyConfidence > 0.4) strengths.push(`Key reads cleanly as ${mm.key} (${Math.round(mm.keyConfidence * 100)}% confidence) — pick harmonically compatible neighbours.`);
    else weaknesses.push(`Key detection is ambiguous (${mm.key}, only ${Math.round(mm.keyConfidence * 100)}% confidence). The mix may modulate or sit between keys — double-check before harmonic mixing.`);

    if (dr < 4) weaknesses.push(`Dynamic range is compressed (${dr} dB). Leave more headroom so drops can hit harder.`);
    else if (dr > 12) strengths.push(`Good dynamic range (${dr} dB) — drops have room to breathe.`);
  }
  // Pad with at least one item each so the UI never looks empty.
  while (strengths.length < 1) strengths.push("Mix is technically clean and listenable end-to-end.");
  while (weaknesses.length < 1) weaknesses.push("No major issues detected — try a more ambitious transition next time.");

  // --- Coach text — concrete numbers, no template fluff ---
  const worked = strengths.slice(0, 2);
  const improve = weaknesses.slice(0, 2);
  const exercise = coachExercise
    ?? (measured
      ? (m as Measurements).bassStability < 70
        ? "Practice 4-beat bass swaps: at every 16-bar boundary cut Deck A bass exactly as you bring Deck B bass up. Record 5 attempts and re-upload."
        : (m as Measurements).bpmConfidence < 0.7
          ? `Set both decks to ${(m as Measurements).bpm.toFixed(0)} BPM with sync off and beatmatch by ear for 90 seconds without drifting.`
          : "Try a creative transition using only a high-pass filter and one effect — no EQ swap allowed."
      : EXERCISES[0].description);

  // Confidence reflects how much we trust the report.
  const confidence = measured
    ? Math.round(60 + (((m as Measurements).bpmConfidence + (m as Measurements).keyConfidence) / 2) * 35)
    : 60;

  // --- Timeline from real loudness curve ---
  const timeline: TimelineEvent[] = measured
    ? buildTimeline(m as Measurements)
    : [{ time: "00:00", label: "No timeline available", type: "info" }];

  // --- Curves: use measured ones if present, downsample to ~40 points ---
  // For long DJ sets we receive a full-length volume curve via extras so
  // the waveform spans the whole mix, not just the 120s sample window.
  const energyCurve = measured ? downsample((m as Measurements).energyCurve, 40) : curve(40, 50, 6);
  const volumeCurve = extras?.fullVolumeCurve
    ? downsample(extras.fullVolumeCurve, 240)
    : measured
      ? downsample((m as Measurements).volumeCurve, 40)
      : curve(40, 70, 4);

  if (recommendedExercises.length === 0) recommendedExercises = pickN(EXERCISES, 2);

  // Pack rule-engine findings into a UI-friendly array so the report can
  // render 👍/👎 against each rule trigger.
  const findingDtos = (findings ?? []).map((f) => ({
    rule_id: f.rule.id,
    rule_slug: f.rule.slug,
    title: f.rule.title,
    diagnosis: f.rule.diagnosis,
    fix: f.rule.fix,
    severity: f.rule.severity,
    metric: f.metric,
    value: f.value,
  }));

  return {
    source: "browser",
    id: crypto.randomUUID(),
    fileName: file.name,
    createdAt: new Date().toISOString(),
    bpm: m ? Math.round(m.bpm) : 120,
    key: m?.key ?? "C maj",
    transitionLength: extras?.totalDurationSec
      ? Math.round(extras.totalDurationSec)
      : m
        ? Math.round(m.durationSec)
        : 60,
    energyCurve,
    volumeCurve,
    frequency: bands,
    scores: { beatmatching, eq, timing, creativity, flow, musicality, overall },
    timeline,
    strengths,
    weaknesses,
    feedback: { worked, improve, exercise, confidence },
    exercises: recommendedExercises,
    trackB: extras?.trackB ? { fileName: extras.trackB.fileName, bpm: Math.round(extras.trackB.bpm), key: extras.trackB.key } : undefined,
    transition: extras?.transition,
    setTransitions: extras?.setTransitions,
    totalDurationSec: extras?.totalDurationSec,
    findings: findingDtos,
  };
}


function downsample(points: { t: number; value: number }[], n: number): CurvePoint[] {
  if (points.length <= n) return points.map((p, i) => ({ t: i, value: p.value }));
  const out: CurvePoint[] = [];
  const step = points.length / n;
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * step);
    const end = Math.floor((i + 1) * step);
    let s = 0, c = 0;
    for (let j = start; j < end; j++) { s += points[j].value; c++; }
    out.push({ t: i, value: Math.round(s / Math.max(1, c)) });
  }
  return out;
}

function buildTimeline(m: Measurements): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  const curve = m.energyCurve;
  if (curve.length === 0) return events;
  const mean = curve.reduce((a, b) => a + b.value, 0) / curve.length;
  const max = Math.max(...curve.map((p) => p.value));
  const peakThreshold = Math.max(mean + 15, max * 0.8);
  const dipThreshold = Math.max(0, mean - 20);
  let lastEvent = -10;
  for (let i = 1; i < curve.length - 1; i++) {
    if (i - lastEvent < 8) continue;
    const v = curve[i].value;
    const prev = curve[i - 1].value;
    const next = curve[i + 1].value;
    if (v >= peakThreshold && v >= prev && v >= next) {
      events.push({ time: secsToMmss(curve[i].t), label: `Energy peak (${v}/100)`, type: "good" });
      lastEvent = i;
    } else if (v <= dipThreshold && v <= prev && v <= next) {
      events.push({ time: secsToMmss(curve[i].t), label: `Energy dip (${v}/100)`, type: "warning" });
      lastEvent = i;
    }
  }
  events.unshift({ time: "00:00", label: `Track starts • ${m.bpm.toFixed(0)} BPM • ${m.key}`, type: "info" });
  return events.slice(0, 8);
}

function secsToMmss(s: number): string {
  const mm = Math.floor(s / 60).toString().padStart(2, "0");
  const ss = Math.floor(s % 60).toString().padStart(2, "0");
  return `${mm}:${ss}`;
}

