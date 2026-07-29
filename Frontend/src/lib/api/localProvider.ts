// LocalProvider — wraps the existing browser-side analysis engine in the
// AnalysisAPI contract. Translates internal stage indices into the public
// PipelineStage enum and tracks ETA via a moving average.

import {
  startJob as engineStart,
  cancelJob as engineCancel,
  removeJob,
  getJob as engineGetJob,
  listJobs as engineListJobs,
  subscribe as engineSubscribe,
} from "../analysis-engine";
import { ANALYSIS_STAGES } from "../analysis";
import { useAppState } from "../store";
import type {
  AnalysisAPI,
  AnalysisJob,
  CreateAnalysisInput,
  CreateAnalysisResponse,
  PipelineStage,
} from "./types";
import type { AnalysisResult } from "../analysis";

// Engine stage index → public pipeline stage. The engine has 7 internal
// stages; we map them onto the richer external pipeline.
const STAGE_MAP: PipelineStage[] = [
  "preprocessing",        // 0 Uploading
  "feature_extraction",   // 1 BPM
  "feature_extraction",   // 2 Beat grid
  "feature_extraction",   // 3 Energy
  "feature_extraction",   // 4 EQ
  "transition_detection", // 5 Coaching (also where set detection runs)
  "report",               // 6 Report
];

function toPublic(j: ReturnType<typeof engineGetJob>, fileSize: number): AnalysisJob | null {
  if (!j) return null;
  const status: AnalysisJob["status"] =
    j.status === "done" ? "completed" : j.status === "error" ? "failed" : "running";
  const stage: PipelineStage =
    status === "completed"
      ? "completed"
      : status === "failed"
        ? "failed"
        : (STAGE_MAP[Math.min(j.stageIndex, STAGE_MAP.length - 1)] ?? "queued");
  const elapsed = (Date.now() - j.startedAt) / 1000;
  const remaining =
    j.overall > 5 && j.overall < 100
      ? Math.max(1, Math.round((elapsed * (100 - j.overall)) / j.overall))
      : undefined;
  return {
    jobId: j.id,
    analysisId: j.resultId,
    status,
    stage,
    progress: j.overall,
    stageProgress: j.stageProgress,
    startedAt: j.startedAt,
    finishedAt: status === "completed" || status === "failed" ? j.updatedAt : undefined,
    errorMessage: j.error,
    estimatedRemainingSeconds: remaining,
    fromCache: j.fromCache,
    fileName: j.fileName,
    fileSize: fileSize || j.fileSize,
  };
}

export const localProvider: AnalysisAPI = {
  name: "local",
  async createAnalysis(input: CreateAnalysisInput): Promise<CreateAnalysisResponse> {
    const jobId = await engineStart(
      input.file,
      input.fileB
        ? { fileB: input.fileB, cuePointSec: input.cuePointSec, overlapSec: input.overlapSec }
        : undefined,
    );
    return { jobId };
  },
  async getJob(jobId) {
    return toPublic(engineGetJob(jobId), 0);
  },
  async listJobs() {
    return engineListJobs().map((j) => toPublic(j, 0)!).filter(Boolean);
  },
  async cancelJob(jobId) {
    engineCancel(jobId);
    removeJob(jobId);
  },
  async getAnalysis(id): Promise<AnalysisResult | null> {
    // The local provider reads from the persisted app state (localStorage).
    // Components that have hook-level access should use useAnalysis() — this
    // method is here so a future remote provider can fetch from REST.
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem("mixcoach.state.v1");
      if (!raw) return null;
      const state = JSON.parse(raw);
      return (state?.analyses ?? []).find((a: AnalysisResult) => a.id === id) ?? null;
    } catch {
      return null;
    }
  },
  subscribe(cb) {
    return engineSubscribe(cb);
  },
};

// Re-export stage labels for dev visibility.
export const ENGINE_STAGES = ANALYSIS_STAGES;

// Hook helper for components that want the cached AnalysisResult via the
// existing app state (avoids round-tripping through localStorage parsing).
export { useAppState };
