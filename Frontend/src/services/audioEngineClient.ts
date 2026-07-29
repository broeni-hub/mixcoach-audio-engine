// MixCoach — Audio Engine HTTP client.
//
// Talks to the separate Python audio-analysis backend. No audio analysis
// happens in the browser — this client uploads the file as multipart/form-data,
// streams metadata, and returns a normalized AnalysisResult.
//
// Configuration order:
//   1. localStorage override (set via Developer Settings UI)
//   2. VITE_AUDIO_ENGINE_URL env var
//
// When neither is set, or the backend is unreachable, callers should fall
// back to demo analysis. This module never throws on missing config — it
// reports `isConfigured() === false` and lets the caller decide.

import type { AnalysisResult } from "@/lib/analysis";

const URL_OVERRIDE_KEY = "mixcoach.audioEngineUrl";
const STATUS_KEY = "mixcoach.audioEngineStatus";

export type ConnectionStatus = "unknown" | "ok" | "error";

export interface ConnectionState {
  status: ConnectionStatus;
  checkedAt: number | null;
  error: string | null;
  url: string | null;
}

export interface AnalyzeMetadata {
  title?: string;
  genre?: string;
  userExperienceLevel?: "Beginner" | "Intermediate" | "Advanced";
  analysisGoal?: string;
  cuePointSec?: number;
  overlapSec?: number;
}

export interface AnalyzeTransitionInput {
  trackA: File;
  trackB?: File;
  metadata?: AnalyzeMetadata;
  signal?: AbortSignal;
  onProgress?: (loaded: number, total: number) => void;
}

export interface AnalyzeSetInput {
  file: File;
  metadata?: AnalyzeMetadata;
  signal?: AbortSignal;
  onProgress?: (loaded: number, total: number) => void;
}

export class AudioEngineError extends Error {
  constructor(message: string, public readonly cause?: unknown, public readonly status?: number) {
    super(message);
    this.name = "AudioEngineError";
  }
}

function readEnvUrl(): string | null {
  const v = (import.meta as { env?: Record<string, string | undefined> }).env?.VITE_AUDIO_ENGINE_URL;

  return v && typeof v === "string" ? v : null;
}

function readOverride(): string | null {
  if (typeof window === "undefined") return null;
  try { return window.localStorage.getItem(URL_OVERRIDE_KEY); } catch { return null; }
}

function readStoredStatus(): ConnectionState {
  if (typeof window === "undefined") {
    return { status: "unknown", checkedAt: null, error: null, url: null };
  }
  try {
    const raw = window.localStorage.getItem(STATUS_KEY);
    if (!raw) return { status: "unknown", checkedAt: null, error: null, url: null };
    return JSON.parse(raw) as ConnectionState;
  } catch {
    return { status: "unknown", checkedAt: null, error: null, url: null };
  }
}

function writeStoredStatus(s: ConnectionState) {
  if (typeof window === "undefined") return;
  try { window.localStorage.setItem(STATUS_KEY, JSON.stringify(s)); } catch { /* ignore */ }
  window.dispatchEvent(new Event("mixcoach:engine-status"));
}

function trimSlash(u: string) { return u.replace(/\/+$/, ""); }

class AudioEngineClient {
  /** Resolve the active backend URL: override → env → localhost-Default. */
  getUrl(): string | null {
    const override = readOverride();
    if (override && override.trim()) return trimSlash(override.trim());
    const env = readEnvUrl();
    if (env) return trimSlash(env);

    // Lokale Entwicklung: automatisch das lokale Backend verwenden.
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      if (host === "localhost" || host === "127.0.0.1") {
        return "http://127.0.0.1:8000";
      }
    }

    return null;
  }

  setUrl(url: string | null) {
    if (typeof window === "undefined") return;
    if (!url) window.localStorage.removeItem(URL_OVERRIDE_KEY);
    else window.localStorage.setItem(URL_OVERRIDE_KEY, url);
    window.dispatchEvent(new Event("mixcoach:engine-status"));
  }

  isConfigured(): boolean {
    return !!this.getUrl();
  }

  getLastStatus(): ConnectionState {
    return readStoredStatus();
  }

  /** GET /health — returns true on 2xx. Stores result for Developer Settings UI. */
  async testConnection(timeoutMs = 5000): Promise<ConnectionState> {
    const url = this.getUrl();
    if (!url) {
      const s: ConnectionState = {
        status: "error",
        checkedAt: Date.now(),
        error: "No backend URL configured.",
        url: null,
      };
      writeStoredStatus(s);
      return s;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${url}/health`, { method: "GET", signal: controller.signal });
      if (!res.ok) throw new AudioEngineError(`Backend returned ${res.status}`, undefined, res.status);
      const s: ConnectionState = { status: "ok", checkedAt: Date.now(), error: null, url };
      writeStoredStatus(s);
      return s;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const s: ConnectionState = { status: "error", checkedAt: Date.now(), error: message, url };
      writeStoredStatus(s);
      return s;
    } finally {
      clearTimeout(timer);
    }
  }

  async analyzeTransition(input: AnalyzeTransitionInput): Promise<AnalysisResult> {
    return this.uploadAndAnalyze("/analyze/transition", this.buildTransitionForm(input), input.signal, input.onProgress);
  }

  async analyzeSet(input: AnalyzeSetInput): Promise<AnalysisResult> {
    return this.uploadAndAnalyze("/analyze/set", this.buildSetForm(input), input.signal, input.onProgress);
  }

  // ───────────────────────── internals ─────────────────────────

  private buildTransitionForm(input: AnalyzeTransitionInput): FormData {
    const form = new FormData();
    form.append("file", input.trackA, input.trackA.name);
    if (input.trackB) form.append("fileB", input.trackB, input.trackB.name);
    form.append("metadata", JSON.stringify(this.normalizeMetadata(input.metadata, input.trackA.name)));
    return form;
  }

  private buildSetForm(input: AnalyzeSetInput): FormData {
    const form = new FormData();
    form.append("file", input.file, input.file.name);
    form.append("metadata", JSON.stringify(this.normalizeMetadata(input.metadata, input.file.name)));
    return form;
  }

  private normalizeMetadata(m: AnalyzeMetadata | undefined, fallbackTitle: string) {
    return {
      title: m?.title ?? fallbackTitle,
      genre: m?.genre ?? null,
      userExperienceLevel: m?.userExperienceLevel ?? null,
      analysisGoal: m?.analysisGoal ?? null,
      cuePointSec: m?.cuePointSec ?? null,
      overlapSec: m?.overlapSec ?? null,
    };
  }

  private async uploadAndAnalyze(
    path: string,
    form: FormData,
    externalSignal: AbortSignal | undefined,
    onProgress: ((loaded: number, total: number) => void) | undefined,
  ): Promise<AnalysisResult> {
    const url = this.getUrl();
    if (!url) throw new AudioEngineError("Audio engine is not configured.");

    try {
      const json = onProgress
        ? await this.xhrUpload(`${url}${path}`, form, externalSignal, onProgress)
        : await this.fetchUpload(`${url}${path}`, form, externalSignal);
      const normalized = this.normalizeResult(json);
      writeStoredStatus({ status: "ok", checkedAt: Date.now(), error: null, url });
      return normalized;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      writeStoredStatus({ status: "error", checkedAt: Date.now(), error: message, url });
      if (err instanceof AudioEngineError) throw err;
      throw new AudioEngineError(message, err);
    }
  }

  private async fetchUpload(url: string, form: FormData, signal?: AbortSignal): Promise<unknown> {
    const res = await fetch(url, { method: "POST", body: form, signal });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new AudioEngineError(`Backend rejected upload (${res.status}) ${text}`.trim(), undefined, res.status);
    }
    return res.json();
  }

  private xhrUpload(
    url: string,
    form: FormData,
    signal: AbortSignal | undefined,
    onProgress: (loaded: number, total: number) => void,
  ): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", url, true);
      xhr.responseType = "json";
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded, e.total);
      };
      xhr.onerror = () => reject(new AudioEngineError("Network error during upload"));
      xhr.ontimeout = () => reject(new AudioEngineError("Upload timed out"));
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.response);
        } else {
          reject(new AudioEngineError(`Backend rejected upload (${xhr.status})`, undefined, xhr.status));
        }
      };
      if (signal) {
        if (signal.aborted) { xhr.abort(); reject(new AudioEngineError("Aborted")); return; }
        signal.addEventListener("abort", () => xhr.abort());
      }
      xhr.send(form);
    });
  }

  /** Map a backend payload into the canonical AnalysisResult shape used by the UI. */
  private normalizeResult(raw: unknown): AnalysisResult {
    if (!raw || typeof raw !== "object") {
      throw new AudioEngineError("Backend returned an empty response.");
    }
    const data = raw as Record<string, unknown>;
    const r = (data.result ?? data) as Partial<AnalysisResult> & Record<string, unknown>;

    if (!r.id || !r.fileName || !r.scores) {
      throw new AudioEngineError("Backend response is missing required fields (id, fileName, scores).");
    }
    return {
      ...(r as AnalysisResult),
      source: "engine",
      createdAt: (r.createdAt as string) ?? new Date().toISOString(),
    };
  }
}

export const audioEngineClient = new AudioEngineClient();

/** React-friendly subscription for the Developer Settings panel. */
export function subscribeEngineStatus(cb: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("mixcoach:engine-status", cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener("mixcoach:engine-status", cb);
    window.removeEventListener("storage", cb);
  };
}
