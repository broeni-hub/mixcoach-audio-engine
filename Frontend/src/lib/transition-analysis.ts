// Two-track transition analysis. Re-uses the single-track analyzer for both
// decks and then derives metrics that only make sense across the cue point:
// BPM drift, harmonic (Camelot) distance, bass/energy overlap, and phrase
// alignment relative to Track A's bar grid.
import type { Measurements, ProgressCb } from "./audio-analysis";
import { analyzeAudioFile } from "./audio-analysis";

export interface TransitionMetrics {
  cue_point_sec: number;       // where Track B drops over Track A (sec from A's start)
  overlap_sec: number;         // how long the overlap window we evaluated is
  bpm_a: number;
  bpm_b: number;
  bpm_drift: number;           // |bpm_a - bpm_b|
  key_a: string;
  key_b: string;
  camelot_a: string;
  camelot_b: string;
  camelot_distance: number;    // 0=identical, 1=±1 step (compatible), 6=opposite
  harmonic_label: "perfect" | "compatible" | "energy_boost" | "clash";
  bass_clash_score: number;    // 0..100, lower = less bass overlap (better)
  phrase_alignment_score: number; // 0..100, higher = closer to a 16-bar grid mark
  phrase_offset_sec: number;
}

export interface TwoTrackResult {
  trackA: Measurements;
  trackB: Measurements;
  transition: TransitionMetrics;
}

const DEFAULT_OVERLAP_SEC = 16;

// Krumhansl key → Camelot wheel mapping ("1A".."12B")
const CAMELOT_MAP: Record<string, string> = {
  "C maj": "8B", "G maj": "9B", "D maj": "10B", "A maj": "11B",
  "E maj": "12B", "B maj": "1B", "F# maj": "2B", "C# maj": "3B",
  "G# maj": "4B", "D# maj": "5B", "A# maj": "6B", "F maj": "7B",
  "A min": "8A", "E min": "9A", "B min": "10A", "F# min": "11A",
  "C# min": "12A", "G# min": "1A", "D# min": "2A", "A# min": "3A",
  "F min": "4A", "C min": "5A", "G min": "6A", "D min": "7A",
};

function keyToCamelot(key: string): string {
  return CAMELOT_MAP[key] ?? "?";
}

function camelotDistance(a: string, b: string): number {
  if (a === "?" || b === "?") return 6;
  const numA = parseInt(a, 10);
  const letterA = a.slice(-1);
  const numB = parseInt(b, 10);
  const letterB = b.slice(-1);
  if (Number.isNaN(numA) || Number.isNaN(numB)) return 6;
  let stepDist = Math.abs(numA - numB);
  stepDist = Math.min(stepDist, 12 - stepDist);
  const letterPenalty = letterA === letterB ? 0 : 1;
  return stepDist + letterPenalty;
}

function harmonicLabel(distance: number): TransitionMetrics["harmonic_label"] {
  if (distance === 0) return "perfect";
  if (distance === 1) return "compatible";
  if (distance === 2) return "energy_boost";
  return "clash";
}

// Sample volumeCurve buckets (1s each) within [startSec, startSec+overlap].
function windowValues(curve: { t: number; value: number }[], startSec: number, overlap: number): number[] {
  const out: number[] = [];
  const end = startSec + overlap;
  for (const p of curve) {
    if (p.t >= startSec && p.t < end) out.push(p.value);
  }
  return out;
}

function computeBassClash(a: Measurements, b: Measurements, cueA: number, overlap: number): number {
  // We don't have time-resolved bass curves; use volumeCurve (peak loudness)
  // weighted by each track's bass-band share as a defensible proxy.
  const va = windowValues(a.volumeCurve, cueA, overlap);
  const vb = windowValues(b.volumeCurve, 0, overlap);
  const len = Math.min(va.length, vb.length);
  if (len === 0) return 0;
  const bassWeightA = a.bands.bass / 100;
  const bassWeightB = b.bands.bass / 100;
  let acc = 0;
  for (let i = 0; i < len; i++) {
    acc += Math.min(va[i] * bassWeightA, vb[i] * bassWeightB);
  }
  // Normalise: max possible overlap is 100 (both at full bass). Scale to 0..100.
  return Math.round(Math.min(100, (acc / len) * 1.6));
}

function computePhraseAlignment(bpm: number, cueSec: number): { score: number; offsetSec: number } {
  // 16-bar phrase length in 4/4: 16 bars * 4 beats / (bpm/60) seconds
  if (!bpm || bpm < 40) return { score: 0, offsetSec: 0 };
  const beatSec = 60 / bpm;
  const phraseSec = 16 * 4 * beatSec;
  if (phraseSec === 0) return { score: 0, offsetSec: 0 };
  const offset = ((cueSec % phraseSec) + phraseSec) % phraseSec;
  const dist = Math.min(offset, phraseSec - offset); // distance to nearest phrase mark
  const score = Math.round(Math.max(0, Math.min(100, 100 * (1 - dist / (phraseSec / 2)))));
  return { score, offsetSec: Math.round(dist * 100) / 100 };
}

/**
 * Analyze Track A, Track B, and the overlap at `cuePointSec` of Track A.
 * Progress callback fires across both tracks (0..50% A, 50..100% B).
 */
export async function analyzeTransition(
  fileA: File,
  fileB: File,
  cuePointSec: number,
  overlapSec: number | undefined,
  onProgress?: ProgressCb,
): Promise<TwoTrackResult> {
  // Decode + analyse both tracks in parallel — roughly halves wall time on
  // multi-core CPUs because decodeAudioData runs off the main thread.
  let progA = 0;
  let progB = 0;
  const emit = () => {
    const ui = (progA + progB) / 2; // 0..100
    const stage = Math.min(3, Math.floor(ui / 25));
    const pct = Math.min(100, Math.round((ui % 25) * 4));
    onProgress?.(stage, pct);
  };
  const [trackA, trackB] = await Promise.all([
    analyzeAudioFile(fileA, (stage, pct) => { progA = ((stage + pct / 100) / 5) * 100; emit(); }),
    analyzeAudioFile(fileB, (stage, pct) => { progB = ((stage + pct / 100) / 5) * 100; emit(); }),
  ]);

  const overlap = Math.max(4, Math.min(overlapSec ?? DEFAULT_OVERLAP_SEC, 60));
  const clampedCue = Math.max(0, Math.min(cuePointSec, Math.max(0, trackA.durationSec - overlap)));
  const phrase = computePhraseAlignment(trackA.bpm, clampedCue);
  const camA = keyToCamelot(trackA.key);
  const camB = keyToCamelot(trackB.key);
  const camDist = camelotDistance(camA, camB);

  const transition: TransitionMetrics = {
    cue_point_sec: Math.round(clampedCue * 10) / 10,
    overlap_sec: overlap,
    bpm_a: trackA.bpm,
    bpm_b: trackB.bpm,
    bpm_drift: Math.round(Math.abs(trackA.bpm - trackB.bpm) * 100) / 100,
    key_a: trackA.key,
    key_b: trackB.key,
    camelot_a: camA,
    camelot_b: camB,
    camelot_distance: camDist,
    harmonic_label: harmonicLabel(camDist),
    bass_clash_score: computeBassClash(trackA, trackB, clampedCue, overlap),
    phrase_alignment_score: phrase.score,
    phrase_offset_sec: phrase.offsetSec,
  };

  return { trackA, trackB, transition };
}
