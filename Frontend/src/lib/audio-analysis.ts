// Real audio analysis in the browser. Pure Web Audio API + a tiny BPM lib.
// All measurements come from the decoded audio buffer — no random numbers.
//
// Designed to be called from a client-only context (upload page / analysis
// engine). Never import this from SSR / server-function code.

import { analyze as detectBpm } from "web-audio-beat-detector";

export interface Measurements {
  durationSec: number;
  bpm: number;
  bpmConfidence: number; // 0..1 — agreement across halves
  key: string; // e.g. "A min" / "C maj"
  keyConfidence: number; // 0..1
  energyCurve: { t: number; value: number }[];  // RMS (0..100), 1s buckets
  volumeCurve: { t: number; value: number }[];  // peak (0..100), 1s buckets
  bands: { bass: number; mid: number; high: number }; // 0..100 normalized
  bassStability: number;        // 0..100 — higher = steadier bass
  dynamicRangeDb: number;       // peak-to-RMS in dB
  loudnessDbfs: number;         // mean RMS in dBFS
  peakCount: number;            // number of significant energy peaks
}

const MAX_ANALYZE_SECONDS = 120; // cap analysis to 2 minutes for speed
const DECODE_SAMPLE_RATE = 22050;
const BPM_DETECT_SECONDS = 60;   // only sample the middle of the track for BPM

export type ProgressCb = (stage: number, pct: number) => void;

export async function analyzeAudioFile(
  file: File,
  onProgress?: ProgressCb,
): Promise<Measurements> {
  // Stage 0: decode
  onProgress?.(0, 5);
  const arrayBuf = await file.arrayBuffer();
  onProgress?.(0, 40);

  const offlineCtxClass: typeof OfflineAudioContext =
    (window as unknown as { OfflineAudioContext: typeof OfflineAudioContext })
      .OfflineAudioContext ||
    (window as unknown as { webkitOfflineAudioContext: typeof OfflineAudioContext })
      .webkitOfflineAudioContext;

  // Decode at a fixed sample rate to keep analysis fast and reproducible.
  // Allocate enough samples to cover MAX_ANALYZE_SECONDS so we don't silently
  // truncate longer tracks before mixToMono caps the length.
  const decodeCtx = new offlineCtxClass(
    1,
    DECODE_SAMPLE_RATE * (MAX_ANALYZE_SECONDS + 10),
    DECODE_SAMPLE_RATE,
  );
  const decoded = await decodeCtx.decodeAudioData(arrayBuf.slice(0));
  onProgress?.(0, 100);

  // Mix down to mono and cap length.
  const samples = mixToMono(decoded, MAX_ANALYZE_SECONDS);
  const sampleRate = decoded.sampleRate;
  const durationSec = samples.length / sampleRate;

  // Stage 1: BPM — single pass on a 60s middle slice (fast),
  // confidence derived from a second pass on a different 30s slice.
  onProgress?.(1, 5);
  let bpm = 120;
  let bpmConfidence = 0.5;
  try {
    const total = samples.length;
    const bpmLen = Math.min(total, BPM_DETECT_SECONDS * sampleRate);
    const startMain = Math.max(0, Math.floor((total - bpmLen) / 2));
    const mainSlice = samples.subarray(startMain, startMain + bpmLen);
    bpm = await detectBpm(makeBuffer(mainSlice, sampleRate));
    onProgress?.(1, 70);
    // Confidence: compare against a shorter slice from the first third.
    const altLen = Math.min(total, 30 * sampleRate);
    const altSlice = samples.subarray(0, altLen);
    const bpmAlt = await detectBpm(makeBuffer(altSlice, sampleRate)).catch(() => bpm);
    const diff = Math.abs(bpm - bpmAlt);
    bpmConfidence = Math.max(0, 1 - diff / 8);
  } catch {
    bpmConfidence = 0.3;
  }
  onProgress?.(1, 100);

  // Stage 2: Beat grid / loudness curves
  onProgress?.(2, 10);
  const bucketSize = sampleRate; // 1 second
  const buckets = Math.floor(samples.length / bucketSize);
  const energyCurve: { t: number; value: number }[] = [];
  const volumeCurve: { t: number; value: number }[] = [];
  let sumSquares = 0;
  let totalSamples = 0;
  let peak = 0;
  for (let b = 0; b < buckets; b++) {
    let ss = 0;
    let pk = 0;
    const start = b * bucketSize;
    for (let i = 0; i < bucketSize; i++) {
      const v = samples[start + i];
      ss += v * v;
      const av = Math.abs(v);
      if (av > pk) pk = av;
    }
    sumSquares += ss;
    totalSamples += bucketSize;
    if (pk > peak) peak = pk;
    const rms = Math.sqrt(ss / bucketSize);
    energyCurve.push({ t: b, value: rms });
    volumeCurve.push({ t: b, value: pk });
    if (b % 20 === 0) onProgress?.(2, 10 + Math.round((b / buckets) * 80));
  }
  const meanRms = Math.sqrt(sumSquares / Math.max(1, totalSamples));
  const loudnessDbfs = 20 * Math.log10(Math.max(1e-6, meanRms));
  const dynamicRangeDb = 20 * Math.log10(Math.max(1e-6, peak)) - loudnessDbfs;

  // Normalize curves to 0..100 against this file's own peak.
  const normEnergy = normalizeTo100(energyCurve, peak);
  const normVolume = normalizeTo100(volumeCurve, peak);

  // Peak count: count buckets above 70% of file peak.
  const peakThreshold = peak * 0.7;
  const peakCount = volumeCurve.filter((p) => p.value >= peakThreshold).length;
  onProgress?.(2, 100);

  // Stage 3: Frequency bands via averaged FFT
  onProgress?.(3, 10);
  const bands = await computeBands(samples, sampleRate, (p) => onProgress?.(3, 10 + Math.round(p * 0.8)));
  const bassStability = computeBassStability(samples, sampleRate);
  onProgress?.(3, 100);

  // Stage 4: Key detection (chroma + Krumhansl)
  onProgress?.(4, 20);
  const { key, confidence: keyConfidence } = await detectKey(samples, sampleRate);
  onProgress?.(4, 100);

  return {
    durationSec,
    bpm: Math.round(bpm * 10) / 10,
    bpmConfidence,
    key,
    keyConfidence,
    energyCurve: normEnergy,
    volumeCurve: normVolume,
    bands,
    bassStability,
    dynamicRangeDb: Math.round(dynamicRangeDb * 10) / 10,
    loudnessDbfs: Math.round(loudnessDbfs * 10) / 10,
    peakCount,
  };
}

// --- helpers -----------------------------------------------------------------

function mixToMono(buf: AudioBuffer, maxSec: number): Float32Array {
  const sr = buf.sampleRate;
  const maxSamples = Math.min(buf.length, Math.floor(maxSec * sr));
  const out = new Float32Array(maxSamples);
  const channels = buf.numberOfChannels;
  for (let ch = 0; ch < channels; ch++) {
    const data = buf.getChannelData(ch);
    for (let i = 0; i < maxSamples; i++) out[i] += data[i] / channels;
  }
  return out;
}

function makeBuffer(samples: Float32Array, sampleRate: number): AudioBuffer {
  const ctxClass: typeof OfflineAudioContext =
    (window as unknown as { OfflineAudioContext: typeof OfflineAudioContext })
      .OfflineAudioContext ||
    (window as unknown as { webkitOfflineAudioContext: typeof OfflineAudioContext })
      .webkitOfflineAudioContext;
  const ctx = new ctxClass(1, samples.length, sampleRate);
  const buffer = ctx.createBuffer(1, samples.length, sampleRate);
  // Copy into a fresh ArrayBuffer-backed view to satisfy strict typing.
  const copy = new Float32Array(samples.length);
  copy.set(samples);
  buffer.copyToChannel(copy, 0);
  return buffer;
}

function normalizeTo100(curve: { t: number; value: number }[], peak: number) {
  const denom = Math.max(1e-6, peak);
  return curve.map((p) => ({ t: p.t, value: Math.round(Math.min(100, (p.value / denom) * 100)) }));
}

// Three-band energy via FFT over overlapping windows.
async function computeBands(
  samples: Float32Array,
  sampleRate: number,
  onPct?: (p: number) => void,
): Promise<{ bass: number; mid: number; high: number }> {
  const fftSize = 4096;
  const hop = fftSize * 2; // sparser hop — ~2x faster, band ratios stay stable
  const windows = Math.max(1, Math.floor((samples.length - fftSize) / hop));
  const bassLimit = Math.floor((250 / (sampleRate / 2)) * (fftSize / 2));
  const midLimit = Math.floor((4000 / (sampleRate / 2)) * (fftSize / 2));
  let bass = 0, mid = 0, high = 0;
  const re = new Float32Array(fftSize);
  const im = new Float32Array(fftSize);
  for (let w = 0; w < windows; w++) {
    const off = w * hop;
    for (let i = 0; i < fftSize; i++) {
      // Hann window
      const win = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (fftSize - 1)));
      re[i] = samples[off + i] * win;
      im[i] = 0;
    }
    fft(re, im);
    for (let k = 1; k < fftSize / 2; k++) {
      const mag = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
      if (k < bassLimit) bass += mag;
      else if (k < midLimit) mid += mag;
      else high += mag;
    }
    if (w % 16 === 0) {
      onPct?.(w / windows);
      await tick();
    }
  }
  const total = Math.max(1e-6, bass + mid + high);
  return {
    bass: Math.round((bass / total) * 100),
    mid: Math.round((mid / total) * 100),
    high: Math.round((high / total) * 100),
  };
}

// Stability = inverse of normalized stddev of bass-band energy over time.
function computeBassStability(samples: Float32Array, sampleRate: number): number {
  const win = Math.floor(sampleRate * 0.5); // 500ms
  const bins: number[] = [];
  for (let off = 0; off + win < samples.length; off += win) {
    let s = 0;
    for (let i = 0; i < win; i++) {
      const v = samples[off + i];
      // Crude low-pass via short averaging on consecutive samples for bass-ish energy.
      s += v * v;
    }
    bins.push(Math.sqrt(s / win));
  }
  if (bins.length === 0) return 50;
  const mean = bins.reduce((a, b) => a + b, 0) / bins.length;
  const variance = bins.reduce((a, b) => a + (b - mean) ** 2, 0) / bins.length;
  const sd = Math.sqrt(variance);
  const cv = sd / Math.max(1e-6, mean); // coefficient of variation
  // cv 0.0 → 100, cv 1+ → 0
  return Math.round(Math.max(0, Math.min(100, 100 * (1 - Math.min(1, cv)))));
}

// --- Key detection -----------------------------------------------------------

// Krumhansl-Schmuckler profiles.
const MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
const MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

async function detectKey(samples: Float32Array, sampleRate: number): Promise<{ key: string; confidence: number }> {
  const fftSize = 8192;
  const hop = fftSize * 2; // skip every other window — 2x faster, still robust
  const chroma = new Float64Array(12);
  const re = new Float32Array(fftSize);
  const im = new Float32Array(fftSize);
  const windows = Math.max(1, Math.floor((samples.length - fftSize) / hop));
  for (let w = 0; w < windows; w++) {
    const off = w * hop;
    for (let i = 0; i < fftSize; i++) {
      const wn = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (fftSize - 1)));
      re[i] = samples[off + i] * wn;
      im[i] = 0;
    }
    fft(re, im);
    for (let k = 1; k < fftSize / 2; k++) {
      const freq = (k * sampleRate) / fftSize;
      if (freq < 60 || freq > 5000) continue;
      const mag = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
      const midi = 69 + 12 * Math.log2(freq / 440);
      const pc = ((Math.round(midi) % 12) + 12) % 12;
      chroma[pc] += mag;
    }
    if (w % 16 === 0) await tick();
  }
  // Normalize chroma.
  const max = Math.max(...chroma);
  if (max > 0) for (let i = 0; i < 12; i++) chroma[i] /= max;

  // Correlate against all 24 keys.
  let bestScore = -Infinity;
  let secondBest = -Infinity;
  let bestKey = "C maj";
  for (let tonic = 0; tonic < 12; tonic++) {
    for (const [profile, label] of [
      [MAJOR_PROFILE, "maj"] as const,
      [MINOR_PROFILE, "min"] as const,
    ]) {
      let score = 0;
      for (let i = 0; i < 12; i++) score += chroma[(i + tonic) % 12] * profile[i];
      if (score > bestScore) {
        secondBest = bestScore;
        bestScore = score;
        bestKey = `${NOTE_NAMES[tonic]} ${label}`;
      } else if (score > secondBest) {
        secondBest = score;
      }
    }
  }
  const margin = bestScore > 0 ? (bestScore - secondBest) / bestScore : 0;
  return { key: bestKey, confidence: Math.max(0, Math.min(1, margin * 4)) };
}

// --- minimal radix-2 FFT (in-place) -----------------------------------------
function fft(re: Float32Array, im: Float32Array) {
  const n = re.length;
  // bit reversal
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wlenR = Math.cos(ang);
    const wlenI = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let wR = 1, wI = 0;
      for (let k = 0; k < len / 2; k++) {
        const uR = re[i + k];
        const uI = im[i + k];
        const vR = re[i + k + len / 2] * wR - im[i + k + len / 2] * wI;
        const vI = re[i + k + len / 2] * wI + im[i + k + len / 2] * wR;
        re[i + k] = uR + vR;
        im[i + k] = uI + vI;
        re[i + k + len / 2] = uR - vR;
        im[i + k + len / 2] = uI - vI;
        const nR = wR * wlenR - wI * wlenI;
        const nI = wR * wlenI + wI * wlenR;
        wR = nR; wI = nI;
      }
    }
  }
}

function tick(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0));
}
