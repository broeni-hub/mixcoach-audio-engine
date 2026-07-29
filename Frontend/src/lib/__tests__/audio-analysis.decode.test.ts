// Regression test for the decode buffer allocation bug.
//
// Background: an earlier version of audio-analysis.ts allocated the
// OfflineAudioContext with `DECODE_SAMPLE_RATE * 60` samples even though
// MAX_ANALYZE_SECONDS was 120. That silently truncated any track longer
// than 60s before mixToMono had a chance to cap it. This test pins the
// allocation length to at least MAX_ANALYZE_SECONDS so the bug can't
// come back.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { analyzeAudioFile } from "../audio-analysis";

vi.mock("web-audio-beat-detector", () => ({
  analyze: vi.fn().mockResolvedValue(124),
}));

const DECODE_SAMPLE_RATE = 22050;
const MAX_ANALYZE_SECONDS = 120;

class FakeAudioBuffer {
  numberOfChannels = 1;
  sampleRate = DECODE_SAMPLE_RATE;
  length: number;
  private chan: Float32Array;
  constructor(length: number) {
    this.length = length;
    this.chan = new Float32Array(length);
    // Fill with a deterministic low-amplitude sine so RMS/FFT don't divide by zero.
    for (let i = 0; i < length; i++) {
      this.chan[i] = Math.sin((2 * Math.PI * 440 * i) / DECODE_SAMPLE_RATE) * 0.2;
    }
  }
  getChannelData() {
    return this.chan;
  }
  copyToChannel(src: Float32Array) {
    this.chan.set(src);
  }
}

const offlineCtorCalls: Array<{ channels: number; length: number; sampleRate: number }> = [];

class FakeOfflineAudioContext {
  channels: number;
  length: number;
  sampleRate: number;
  constructor(channels: number, length: number, sampleRate: number) {
    this.channels = channels;
    this.length = length;
    this.sampleRate = sampleRate;
    offlineCtorCalls.push({ channels, length, sampleRate });
  }
  async decodeAudioData(_buf: ArrayBuffer) {
    // Return a buffer the size of the allocation so mixToMono sees the full length.
    return new FakeAudioBuffer(this.length) as unknown as AudioBuffer;
  }
  createBuffer(_ch: number, length: number, _sr: number) {
    return new FakeAudioBuffer(length) as unknown as AudioBuffer;
  }
}

beforeEach(() => {
  offlineCtorCalls.length = 0;
  (globalThis as unknown as { window: typeof globalThis }).window = globalThis;
  (globalThis as unknown as { OfflineAudioContext: unknown }).OfflineAudioContext =
    FakeOfflineAudioContext;
  (globalThis as unknown as { window: { OfflineAudioContext: unknown } }).window =
    Object.assign(globalThis, { OfflineAudioContext: FakeOfflineAudioContext });
});

describe("analyzeAudioFile decode allocation", () => {
  it("allocates enough samples to cover MAX_ANALYZE_SECONDS (regression: 60s bug)", async () => {
    const file = new File([new ArrayBuffer(1024)], "test.mp3", { type: "audio/mpeg" });

    await analyzeAudioFile(file);

    expect(offlineCtorCalls.length).toBeGreaterThan(0);
    const decodeCall = offlineCtorCalls[0];
    const minRequired = DECODE_SAMPLE_RATE * MAX_ANALYZE_SECONDS;

    expect(decodeCall.sampleRate).toBe(DECODE_SAMPLE_RATE);
    expect(decodeCall.length).toBeGreaterThanOrEqual(minRequired);
    // Guard against accidentally regressing to a much smaller window (e.g. 60s).
    expect(decodeCall.length).toBeGreaterThan(DECODE_SAMPLE_RATE * 60);
  });
});
