// Normalize the legacy in-app `AnalysisResult` (src/lib/analysis.ts) into the
// shared `ReportView` shape used by every report page. Anything that's
// missing comes through as `null` / empty array so the UI can render
// placeholders instead of crashing.

import type { AnalysisResult as LegacyAnalysisResult } from "./analysis";
import type {
  AnalysisResult as ReportView,
  DetectedTransition,
  FullSetAnalysisResult,
  SingleTransitionAnalysisResult,
  SkillScore,
} from "./report-types";

const SKILL_LABELS: Record<string, string> = {
  beatmatching: "Your Timing",
  eq: "Clean Mixing",
  flow: "Crowd Momentum",
  timing: "Transition Flow",
  musicality: "Track Pairing",
  creativity: "Your Signature",
};

function num(n: unknown): number | null {
  return typeof n === "number" && isFinite(n) ? n : null;
}

/** Wie num(), aber fuer optionale Felder: fehlt heisst fehlt, nicht null. */
function numOpt(n: unknown): number | undefined {
  return typeof n === "number" && isFinite(n) ? n : undefined;
}

export function toReportView(a: LegacyAnalysisResult): ReportView {
  const skills: SkillScore[] = (["beatmatching", "eq", "flow", "timing", "musicality", "creativity"] as const).map((k) => ({
    key: k,
    label: SKILL_LABELS[k],
    value: num(a.scores?.[k]),
  }));

  const isSet = Array.isArray(a.setTransitions) && a.setTransitions.length > 0;

  const base: ReportView = {
    id: a.id,
    fileName: a.fileName,
    createdAt: a.createdAt,
    mode: isSet ? "set" : "single",
    bpm: num(a.bpm),
    key: a.key || null,
    durationSec: num(a.totalDurationSec) ?? num(a.transitionLength),
    overallScore: num(a.scores?.overall),
    skills,
    energyCurve: a.energyCurve ?? [],
    volumeCurve: a.volumeCurve ?? [],
    energyArc: a.energyArc ?? null,
    frequency: a.frequency
      ? { bass: a.frequency.bass, mid: a.frequency.mid, high: a.frequency.high }
      : null,
    timeline: (a.timeline ?? []).map((t) => ({ time: t.time, label: t.label, type: t.type })),
    strengths: a.strengths ?? [],
    weaknesses: a.weaknesses ?? [],
    coach: a.feedback
      ? {
          worked: a.feedback.worked ?? [],
          improve: a.feedback.improve ?? [],
          summary: a.feedback.exercise || undefined,
          confidence: num(a.feedback.confidence),
        }
      : null,
    // Bis zum 15.08.2026 standen hier nur title/description/xp - der Beleg
    // (metric, value, target) und die Sprungmarke (atSec, transitionIndex)
    // fielen still weg. Die Zahl stand zwar im Text, aber die Seite konnte
    // nichts damit anfangen: kein Anspringen, keine Anzeige des Belegs.
    exercises: (a.exercises ?? []).map((e) => ({
      title: e.title,
      description: e.description,
      xp: e.xp,
      atSec: numOpt(e.atSec),
      transitionIndex: numOpt(e.transitionIndex),
      metric: e.metric,
      value: numOpt(e.value),
      target: numOpt(e.target),
    })),
    // Getrennte Liste, nicht dieselbe: "das ist so" ist keine Aufgabe.
    observations: (a.observations ?? []).map((o) => ({
      text: o.text,
      atSec: numOpt(o.atSec),
      transitionIndex: numOpt(o.transitionIndex),
      metric: o.metric,
      value: numOpt(o.value),
    })),
  };

  if (isSet) {
    return toFullSetView(base, a);
  }
  return toSingleView(base, a);
}

function toSingleView(base: ReportView, a: LegacyAnalysisResult): SingleTransitionAnalysisResult {
  const t = a.transition;
  return {
    ...base,
    mode: "single",
    transition: t
      ? {
          cuePointSec: num(t.cue_point_sec),
          overlapSec: num(t.overlap_sec),
          bpmDrift: num(t.bpm_drift),
          harmonicLabel: t.harmonic_label,
          camelotA: t.camelot_a,
          camelotB: t.camelot_b,
          bassClashScore: num(t.bass_clash_score),
          phraseAlignmentScore: num(t.phrase_alignment_score),
        }
      : undefined,
    trackB: a.trackB
      ? { fileName: a.trackB.fileName, bpm: num(a.trackB.bpm), key: a.trackB.key }
      : undefined,
  };
}

function toFullSetView(base: ReportView, a: LegacyAnalysisResult): FullSetAnalysisResult {
  const transitions: DetectedTransition[] = (a.setTransitions ?? []).map((t) => ({
    index: t.index,
    startSec: t.start_sec,
    endSec: t.end_sec,
    midSec: t.mid_sec,
    bpmBefore: num(t.bpm_before),
    bpmAfter: num(t.bpm_after),
    bpmDrift: num(t.bpm_drift),
    qualityScore: num(t.quality_score),
    label: t.label,
    // beatmatching und timing werden hier NICHT mehr abgeleitet (31.07.2026).
    // Diese Stelle rechnete am Mapper vorbei: sie bildete die Noten aus
    // bpm_drift und phrase_alignment_score selbst nach, sodass ein null aus
    // dem Backend sie nicht erreicht haette. Begruendung und Zahlen:
    // NOT_YET_MEASURED in app/api/analysis_mapper.py.
    scores: {
      beatmatching: undefined,
      eq: num(t.bass_overlap_score) === null ? undefined : 100 - (t.bass_overlap_score ?? 0),
      timing: undefined,
    },
    note: undefined,
  }));

  // best / weakest
  let bestIdx: number | null = null;
  let weakIdx: number | null = null;
  let bestScore = -Infinity;
  let weakScore = Infinity;
  transitions.forEach((t, i) => {
    const s = t.qualityScore;
    if (s === null) return;
    if (s > bestScore) { bestScore = s; bestIdx = i; }
    if (s < weakScore) { weakScore = s; weakIdx = i; }
  });

  // average BPM across detected transitions
  const bpms = transitions
    .flatMap((t) => [t.bpmBefore, t.bpmAfter])
    .filter((x): x is number => typeof x === "number");
  const avgBpm = bpms.length ? Math.round(bpms.reduce((s, n) => s + n, 0) / bpms.length) : (base.bpm ?? null);

  // common mistakes — derive from weak transitions
  const mistakes = new Set<string>();
  for (const t of transitions) {
    if (t.label === "rough") {
      // "drifted out of sync" aus bpmDrift entfaellt (31.07.2026) - der Wert
      // ist in 89 % der Uebergaenge exakt 0, und die Ausreisser sind Spruenge
      // des Tempo-Schaetzers zwischen seinen 14 Kandidatenwerten.
      if ((t.scores?.eq ?? 100) < 60) mistakes.add(`The low end got crowded around ${formatTime(t.midSec)}`);
      // "landed off the phrase" ebenfalls entfallen: scores.timing wird oben
      // nicht mehr befuellt, die Bedingung waere ohnehin nie wahr geworden.
    }
  }

  return {
    ...base,
    mode: "set",
    setDurationSec: base.durationSec,
    averageBpm: avgBpm,
    transitions,
    bestTransitionIndex: bestIdx,
    weakestTransitionIndex: weakIdx,
    commonMistakes: Array.from(mistakes).slice(0, 5),
    setFlowFeedback: a.feedback?.exercise || undefined,
  };
}

export function formatTime(sec: number | null | undefined): string {
  if (typeof sec !== "number" || !isFinite(sec)) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function formatDuration(sec: number | null | undefined): string {
  if (typeof sec !== "number" || !isFinite(sec) || sec <= 0) return "—";
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s ? `${m}m ${s}s` : `${m}m`;
}
