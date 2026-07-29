// Set-level transition detection. Designed for long DJ mixes (10–45 min)
// where a single recording contains many transitions. We decode the whole
// file at 22.05 kHz mono, scan for energy dips that look like transition
// windows, then measure BPM before/after, dip depth, bass smoothness, and
// phrase alignment around each candidate to assign a quality score.
//
// Client-only — uses Web Audio. Never import from SSR.
import { analyze as detectBpm } from "web-audio-beat-detector";

export interface SetTransition {
  index: number;
  start_sec: number;
  end_sec: number;
  mid_sec: number;
  bpm_before: number;
  bpm_after: number;
  bpm_drift: number;
  energy_dip_pct: number;        // 0..100 — how far below baseline the dip went
  bass_overlap_score: number;    // 0..100 — lower is smoother
  phrase_alignment_score: number;// 0..100 — higher is better
  quality_score: number;         // 0..100 overall
  label: "smooth" | "neutral" | "rough";
  loudness_jump_db?: number | null; // Pegelsprung des Uebergangs in dB (K-gewichtet)
  feedback?: string | null;        // echter Backend-Satz (deutsch)
  feedback_en?: string | null;     // echter Backend-Satz (englisch)
  // Aus Library-Fingerprinting (optional): echte Tracknamen + Erkennungsart.
  track_out?: string | null;
  track_in?: string | null;
  detection?: string | null;
  // Trackwechsel per Fingerprint sicher, aber zwischen den erkannten
  // Abschnitten liegt eine Luecke -> genaue Uebergangsposition ist geschaetzt.
  position_estimated?: boolean | null;
  gap_seconds?: number | null;               // Groesse der Luecke in Sekunden
  possible_unrecognized_track?: boolean | null; // sehr grosse Luecke: evtl. Zwischentrack
}

export interface SetAnalysisResult {
  transitions: SetTransition[];
  totalDurationSec: number;
  volumeCurve: { t: number; value: number }[]; // 1s peaks across full file
}

const MAX_SET_SECONDS = 60 * 45; // hard cap: 45 min

export async function analyzeSetTransitions(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<SetAnalysisResult> {
  onProgress?.(2);
  const arrayBuf = await file.arrayBuffer();
  const ctxClass: typeof OfflineAudioContext =
    (window as unknown as { OfflineAudioContext: typeof OfflineAudioContext }).OfflineAudioContext ||
    (window as unknown as { webkitOfflineAudioContext: typeof OfflineAudioContext }).webkitOfflineAudioContext;
  const decodeCtx = new ctxClass(1, 22050 * 60, 22050);
  const decoded = await decodeCtx.decodeAudioData(arrayBuf.slice(0));
  onProgress?.(20);

  const sr = decoded.sampleRate;
  const sampleCount = Math.min(decoded.length, Math.floor(MAX_SET_SECONDS * sr));
  const samples = new Float32Array(sampleCount);
  const channels = decoded.numberOfChannels;
  for (let ch = 0; ch < channels; ch++) {
    const data = decoded.getChannelData(ch);
    for (let i = 0; i < sampleCount; i++) samples[i] += data[i] / channels;
  }
  const durationSec = sampleCount / sr;

  // 1-second peak + RMS buckets
  const bucket = Math.floor(sr);
  const buckets = Math.floor(sampleCount / bucket);
  const volume = new Float64Array(buckets);
  for (let b = 0; b < buckets; b++) {
    let pk = 0;
    const start = b * bucket;
    for (let i = 0; i < bucket; i++) {
      const v = Math.abs(samples[start + i]);
      if (v > pk) pk = v;
    }
    volume[b] = pk;
  }
  const peakMax = Math.max(1e-6, ...Array.from(volume));
  const volumeCurve = Array.from(volume).map((v, t) => ({ t, value: Math.round((v / peakMax) * 100) }));
  onProgress?.(40);

  // Smooth (4s) and long baseline (30s) rolling means
  const smooth = rollingMean(volume, 4);
  const baseline = rollingMean(volume, 30);

  // Candidate transitions: smoothed energy < 0.78× baseline and a local minimum within ±10s.
  const candidates: number[] = [];
  for (let i = 15; i < smooth.length - 15; i++) {
    if (smooth[i] >= baseline[i] * 0.78) continue;
    let isMin = true;
    for (let j = -10; j <= 10; j++) {
      if (smooth[i + j] < smooth[i] - 1e-4) { isMin = false; break; }
    }
    if (isMin) candidates.push(i);
  }
  // Dedupe: keep dips ≥ 25 s apart
  const dips: number[] = [];
  for (const c of candidates) {
    if (dips.length === 0 || c - dips[dips.length - 1] >= 25) dips.push(c);
  }
  onProgress?.(55);

  // For each dip, compute BPM before/after + scores. BPM detection on 25 s slices.
  const transitions: SetTransition[] = [];
  for (let i = 0; i < dips.length; i++) {
    const midSec = dips[i];
    const preStart = Math.max(0, midSec - 35) * sr;
    const preEnd = Math.max(preStart + sr * 8, (midSec - 10) * sr);
    const postStart = Math.max(0, Math.min(sampleCount - sr * 8, (midSec + 10) * sr));
    const postEnd = Math.min(sampleCount, (midSec + 35) * sr);
    const preSlice = samples.subarray(preStart, preEnd);
    const postSlice = samples.subarray(postStart, postEnd);

    let bpmPre = 0, bpmPost = 0;
    try { bpmPre = await detectBpm(makeBuffer(preSlice, sr)); } catch { /* keep 0 */ }
    try { bpmPost = await detectBpm(makeBuffer(postSlice, sr)); } catch { /* keep 0 */ }
    const drift = bpmPre && bpmPost ? Math.abs(bpmPre - bpmPost) : 0;

    const baseAt = baseline[midSec] || 1e-6;
    const dipPct = Math.round(Math.max(0, Math.min(100, (1 - smooth[midSec] / baseAt) * 100)));

    // Roughness proxy: coefficient of variation of volume in a ±6s window.
    const w = 6;
    const around: number[] = [];
    for (let j = Math.max(0, midSec - w); j <= Math.min(volume.length - 1, midSec + w); j++) {
      around.push(volume[j]);
    }
    const mean = around.reduce((a, b) => a + b, 0) / around.length;
    const variance = around.reduce((a, b) => a + (b - mean) ** 2, 0) / around.length;
    const cv = Math.sqrt(variance) / Math.max(1e-6, mean);
    const bassOverlap = Math.round(Math.max(0, Math.min(100, cv * 200)));

    const phraseAlign = computePhraseAlignment(bpmPre || 120, midSec);

    const driftScore = Math.max(0, 100 - drift * 12);
    const dipScore = 100 - Math.abs(dipPct - 40) * 1.5; // sweet spot ≈ 40%
    const overlapScore = 100 - bassOverlap;
    const quality = Math.round(
      Math.max(0, Math.min(100,
        driftScore * 0.35 + dipScore * 0.2 + overlapScore * 0.25 + phraseAlign * 0.2)),
    );
    const label: SetTransition["label"] = quality >= 75 ? "smooth" : quality < 55 ? "rough" : "neutral";

    transitions.push({
      index: i + 1,
      start_sec: Math.max(0, midSec - 8),
      end_sec: Math.min(durationSec, midSec + 8),
      mid_sec: midSec,
      bpm_before: Math.round(bpmPre * 10) / 10,
      bpm_after: Math.round(bpmPost * 10) / 10,
      bpm_drift: Math.round(drift * 100) / 100,
      energy_dip_pct: dipPct,
      bass_overlap_score: bassOverlap,
      phrase_alignment_score: phraseAlign,
      quality_score: quality,
      label,
    });
    onProgress?.(55 + Math.round(((i + 1) / Math.max(1, dips.length)) * 40));
  }
  onProgress?.(100);

  return { transitions, totalDurationSec: durationSec, volumeCurve };
}

function rollingMean(arr: Float64Array, win: number): Float64Array {
  const out = new Float64Array(arr.length);
  for (let i = 0; i < arr.length; i++) {
    const a = Math.max(0, i - win);
    const b = Math.min(arr.length, i + win + 1);
    let s = 0;
    for (let j = a; j < b; j++) s += arr[j];
    out[i] = s / (b - a);
  }
  return out;
}

function computePhraseAlignment(bpm: number, cueSec: number): number {
  if (!bpm || bpm < 40) return 0;
  const beatSec = 60 / bpm;
  const phraseSec = 16 * 4 * beatSec;
  if (phraseSec === 0) return 0;
  const offset = ((cueSec % phraseSec) + phraseSec) % phraseSec;
  const dist = Math.min(offset, phraseSec - offset);
  return Math.round(Math.max(0, Math.min(100, 100 * (1 - dist / (phraseSec / 2)))));
}

function makeBuffer(samples: Float32Array, sampleRate: number): AudioBuffer {
  const ctxClass: typeof OfflineAudioContext =
    (window as unknown as { OfflineAudioContext: typeof OfflineAudioContext }).OfflineAudioContext ||
    (window as unknown as { webkitOfflineAudioContext: typeof OfflineAudioContext }).webkitOfflineAudioContext;
  const ctx = new ctxClass(1, samples.length, sampleRate);
  const buffer = ctx.createBuffer(1, samples.length, sampleRate);
  const copy = new Float32Array(samples.length);
  copy.set(samples);
  buffer.copyToChannel(copy, 0);
  return buffer;
}
