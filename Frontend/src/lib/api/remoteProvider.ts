// RemoteProvider — talks to a real Python audio-analysis backend over HTTP.
//
// Expected endpoints:
//   POST /analysis/jobs                       multipart: file, fileB?, metadata
//   GET  /analysis/jobs/:jobId                returns { jobId, status, stage, progress, ... }
//   GET  /analysis/:analysisId                returns AnalysisResult
//   POST /analysis/jobs/:jobId/retry          returns { jobId }
//
// Configure with VITE_AUDIO_ANALYSIS_API_URL. When the env var is missing
// or the backend is unreachable, callers fall back to the local provider
// via `provider.ts`.

import type {
  AnalysisAPI,
  AnalysisJob,
  CreateAnalysisInput,
  CreateAnalysisResponse,
  JobStatus,
  PipelineStage,
} from "./types";
import type { AnalysisResult } from "../analysis";

const DEFAULT_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 2;
const RETRY_DELAYS = [400, 1200]; // ms backoff

interface RemoteJobDTO {
  jobId: string;
  analysisId?: string | null;
  status?: string;
  stage?: string;
  progress?: number;
  stageProgress?: number;
  startedAt?: number | string;
  finishedAt?: number | string;
  errorMessage?: string | null;
  estimatedRemainingSeconds?: number;
  fromCache?: boolean;
  fileName?: string;
  fileSize?: number;
  attempts?: number;
}

const BACKEND_STAGE_TO_PUBLIC: Record<string, PipelineStage> = {
  uploaded: "uploaded",
  queued: "queued",
  preprocessing: "preprocessing",
  audio_feature_extraction: "audio_feature_extraction",
  feature_extraction: "feature_extraction",
  bpm_detection: "bpm_detection",
  key_detection: "key_detection",
  beatgrid_detection: "beatgrid_detection",
  phrase_detection: "phrase_detection",
  transition_detection: "transition_detection",
  transition_analysis: "transition_analysis",
  ai_coaching_generation: "ai_coaching_generation",
  coaching_generation: "coaching_generation",
  report: "report",
  completed: "completed",
  stored: "stored",
  failed: "failed",
};

const BACKEND_STATUS_TO_PUBLIC: Record<string, JobStatus> = {
  uploaded: "running",
  queued: "queued",
  preprocessing: "running",
  audio_feature_extraction: "running",
  feature_extraction: "running",
  bpm_detection: "running",
  key_detection: "running",
  beatgrid_detection: "running",
  phrase_detection: "running",
  transition_detection: "running",
  transition_analysis: "running",
  ai_coaching_generation: "running",
  coaching_generation: "running",
  report: "running",
  running: "running",
  in_progress: "running",
  completed: "completed",
  done: "completed",
  failed: "failed",
  error: "failed",
};

function normalizeStage(s: string | undefined): PipelineStage {
  if (!s) return "queued";
  return BACKEND_STAGE_TO_PUBLIC[s] ?? "preprocessing";
}

function normalizeStatus(dto: RemoteJobDTO): JobStatus {
  const explicit = dto.status ? BACKEND_STATUS_TO_PUBLIC[dto.status] : undefined;
  if (explicit) return explicit;
  // Fall back to stage-derived status.
  return BACKEND_STATUS_TO_PUBLIC[dto.stage ?? ""] ?? "running";
}

function toEpoch(v: number | string | undefined, fallback: number): number {
  if (v == null) return fallback;
  if (typeof v === "number") return v;
  const t = Date.parse(v);
  return Number.isFinite(t) ? t : fallback;
}

function dtoToJob(dto: RemoteJobDTO): AnalysisJob {
  const now = Date.now();
  const status = normalizeStatus(dto);
  return {
    jobId: dto.jobId,
    analysisId: dto.analysisId ?? undefined,
    status,
    stage:
      status === "completed" ? "completed" :
      status === "failed" ? "failed" :
      normalizeStage(dto.stage),
    progress: Math.min(100, Math.max(0, Math.round(dto.progress ?? 0))),
    stageProgress: Math.min(100, Math.max(0, Math.round(dto.stageProgress ?? 0))),
    startedAt: toEpoch(dto.startedAt, now),
    finishedAt: dto.finishedAt ? toEpoch(dto.finishedAt, now) : undefined,
    errorMessage: dto.errorMessage ?? undefined,
    estimatedRemainingSeconds: dto.estimatedRemainingSeconds,
    fromCache: dto.fromCache,
    fileName: dto.fileName ?? "uploaded.audio",
    fileSize: dto.fileSize ?? 0,
    attempts: dto.attempts ?? 0,
  };
}

export function getEngineBaseUrl(): string | null {
  return getBaseUrl();
}

function getBaseUrl(): string | null {
  // 1. Developer-Settings-Override (gleicher Key wie der Audio-Engine-Client,
  //    d.h. EINE URL in den Settings aktiviert beide Wege).
  if (typeof window !== "undefined") {
    try {
      const override = window.localStorage.getItem("mixcoach.audioEngineUrl");
      if (override && override.trim()) return override.trim().replace(/\/+$/, "");
    } catch { /* ignore */ }
  }
  // 2. Env-Variable (Build-Zeit).
  const raw = (import.meta as any).env?.VITE_AUDIO_ANALYSIS_API_URL
    ?? (import.meta as any).env?.VITE_AUDIO_ENGINE_URL;
  if (raw && typeof raw === "string") return raw.replace(/\/+$/, "");

  // 3. Lokale Entwicklung: Frontend auf localhost -> Backend auf Port 8000.
  //    Dadurch ist beim lokalen Testen KEINE Konfiguration noetig.
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8000";
    }
  }

  return null;
}

async function fetchWithRetry(input: string, init: RequestInit, attempts = MAX_RETRIES): Promise<Response> {
  let lastErr: unknown;
  for (let i = 0; i <= attempts; i++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
    try {
      const res = await fetch(input, { ...init, signal: controller.signal });
      clearTimeout(timer);
      // Retry on 5xx; surface 4xx immediately.
      if (res.status >= 500 && i < attempts) {
        await new Promise((r) => setTimeout(r, RETRY_DELAYS[i] ?? 1500));
        continue;
      }
      return res;
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      if (i < attempts) {
        await new Promise((r) => setTimeout(r, RETRY_DELAYS[i] ?? 1500));
        continue;
      }
    }
  }
  throw lastErr ?? new Error("Network error");
}

class RemoteAnalysisProvider implements AnalysisAPI {
  name = "remote";
  private baseUrl: string;
  private listeners = new Set<() => void>();
  private knownJobs = new Map<string, AnalysisJob>();

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private notify() {
    for (const cb of this.listeners) cb();
  }

  async createAnalysis(input: CreateAnalysisInput): Promise<CreateAnalysisResponse> {
    const form = new FormData();
    form.append("file", input.file, input.file.name);
    if (input.fileB) form.append("fileB", input.fileB, input.fileB.name);
    const metadata: Record<string, unknown> = {
      fileName: input.file.name,
      fileSize: input.file.size,
      cuePointSec: input.cuePointSec,
      overlapSec: input.overlapSec,
      genre: input.genre,
      goal: input.goal,
    };
    form.append("metadata", JSON.stringify(metadata));

    const res = await fetchWithRetry(`${this.baseUrl}/analysis/jobs`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Backend rejected job (${res.status})`);
    const data = (await res.json()) as { jobId: string };
    if (!data?.jobId) throw new Error("Backend returned invalid job response");

    // Seed an "uploaded" job so the UI has something to render before the
    // first poll lands.
    this.knownJobs.set(data.jobId, {
      jobId: data.jobId,
      status: "running",
      stage: "uploaded",
      progress: 1,
      stageProgress: 100,
      startedAt: Date.now(),
      fileName: input.file.name,
      fileSize: input.file.size,
      attempts: 0,
    });
    this.notify();
    return { jobId: data.jobId };
  }

  async getJob(jobId: string): Promise<AnalysisJob | null> {
    try {
      const res = await fetchWithRetry(`${this.baseUrl}/analysis/jobs/${encodeURIComponent(jobId)}`, {
        method: "GET",
      });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error(`Job fetch failed (${res.status})`);
      const dto = (await res.json()) as RemoteJobDTO;
      const job = dtoToJob({ ...dto, jobId });
      this.knownJobs.set(jobId, job);
      this.notify();
      return job;
    } catch (err) {
      // Surface the last-known job (with errorMessage) instead of throwing
      // so the UI can still show "connection lost" without crashing.
      const prev = this.knownJobs.get(jobId);
      if (prev) {
        return { ...prev, errorMessage: (err as Error).message };
      }
      throw err;
    }
  }

  async listJobs(): Promise<AnalysisJob[]> {
    return [...this.knownJobs.values()].sort((a, b) => b.startedAt - a.startedAt);
  }

  async cancelJob(jobId: string): Promise<void> {
    try {
      await fetchWithRetry(`${this.baseUrl}/analysis/jobs/${encodeURIComponent(jobId)}`, {
        method: "DELETE",
      }, 0);
    } catch {
      // best-effort cancel
    }
    this.knownJobs.delete(jobId);
    this.notify();
  }

  async retryJob(jobId: string): Promise<CreateAnalysisResponse> {
    const res = await fetchWithRetry(`${this.baseUrl}/analysis/jobs/${encodeURIComponent(jobId)}/retry`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Retry failed (${res.status})`);
    const data = (await res.json()) as { jobId: string };
    const newId = data?.jobId ?? jobId;
    const prev = this.knownJobs.get(jobId);
    this.knownJobs.set(newId, {
      jobId: newId,
      status: "running",
      stage: "queued",
      progress: 0,
      stageProgress: 0,
      startedAt: Date.now(),
      fileName: prev?.fileName ?? "uploaded.audio",
      fileSize: prev?.fileSize ?? 0,
      attempts: (prev?.attempts ?? 0) + 1,
    });
    this.notify();
    return { jobId: newId };
  }

  async getAnalysis(id: string): Promise<AnalysisResult | null> {
    const res = await fetchWithRetry(`${this.baseUrl}/analysis/${encodeURIComponent(id)}`, {
      method: "GET",
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Result fetch failed (${res.status})`);
    return (await res.json()) as AnalysisResult;
  }

  async deleteAnalysis(id: string): Promise<void> {
    try {
      await fetchWithRetry(`${this.baseUrl}/analysis/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }, 0);
    } catch {
      // best-effort — local/Supabase state is already updated by the caller
    }
  }

  subscribe(cb: () => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }
}

export function createRemoteProvider(baseUrl?: string): RemoteAnalysisProvider | null {
  const url = baseUrl ?? getBaseUrl();
  if (!url) return null;
  return new RemoteAnalysisProvider(url);
}

export async function pingBackend(baseUrl?: string, timeoutMs = 3000): Promise<boolean> {
  const url = baseUrl ?? getBaseUrl();
  if (!url) return false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${url}/health`, { method: "GET", signal: controller.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}
