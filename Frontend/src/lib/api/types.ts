// MixCoach Analysis API — provider-agnostic contracts.
//
// Every UI component talks to this interface, never to a concrete
// implementation. Today the `localProvider` runs the analysis in the
// browser. Tomorrow a Python backend can implement the same interface and
// the UI does not change.

import type { AnalysisResult } from "../analysis";

export type PipelineStage =
  | "uploaded"
  | "queued"
  | "preprocessing"
  | "audio_feature_extraction"
  | "feature_extraction"
  | "bpm_detection"
  | "key_detection"
  | "beatgrid_detection"
  | "phrase_detection"
  | "transition_detection"
  | "transition_analysis"
  | "ai_coaching_generation"
  | "coaching_generation"
  | "report"
  | "completed"
  | "stored"
  | "failed";

export const PIPELINE_STAGES: PipelineStage[] = [
  "uploaded",
  "queued",
  "preprocessing",
  "audio_feature_extraction",
  "feature_extraction",
  "bpm_detection",
  "key_detection",
  "beatgrid_detection",
  "phrase_detection",
  "transition_detection",
  "transition_analysis",
  "ai_coaching_generation",
  "coaching_generation",
  "report",
  "completed",
];

export const STAGE_LABEL: Record<PipelineStage, string> = {
  uploaded: "Upload complete",
  queued: "Queued for analysis",
  preprocessing: "Audio preprocessing",
  audio_feature_extraction: "Audio feature extraction",
  feature_extraction: "BPM, key & frequency",
  bpm_detection: "BPM detection",
  key_detection: "Key detection",
  beatgrid_detection: "Beat grid detection",
  phrase_detection: "Phrase detection",
  transition_detection: "Transition detection",
  transition_analysis: "Transition analysis",
  ai_coaching_generation: "Coach generation",
  coaching_generation: "Coach generation",
  report: "Report generation",
  completed: "Completed",
  stored: "Stored",
  failed: "Failed",
};

export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface AnalysisJob {
  jobId: string;
  analysisId?: string;
  status: JobStatus;
  stage: PipelineStage;
  progress: number; // 0..100 overall
  stageProgress: number; // 0..100 within current stage
  startedAt: number;
  finishedAt?: number;
  errorMessage?: string;
  estimatedRemainingSeconds?: number;
  fromCache?: boolean;
  fileName: string;
  fileSize: number;
  /** Set when this job is running against the in-browser fallback engine. */
  fallback?: boolean;
  /** How many times this job has been retried. */
  attempts?: number;
}

export interface CreateAnalysisInput {
  file: File;
  fileB?: File;
  cuePointSec?: number;
  overlapSec?: number;
  genre?: string;
  goal?: string;
}

export interface CreateAnalysisResponse {
  jobId: string;
}

export interface AnalysisAPI {
  /** Submit a new analysis. Returns a jobId that the UI polls. */
  createAnalysis(input: CreateAnalysisInput): Promise<CreateAnalysisResponse>;
  /** Current job state. */
  getJob(jobId: string): Promise<AnalysisJob | null>;
  /** All jobs known to the provider (most recent first). */
  listJobs(): Promise<AnalysisJob[]>;
  /** Cancel + remove a running job. */
  cancelJob(jobId: string): Promise<void>;
  /** Retry a failed job. Returns the same or a new jobId depending on the backend. */
  retryJob?(jobId: string): Promise<CreateAnalysisResponse>;
  /** Full analysis report. */
  getAnalysis(id: string): Promise<AnalysisResult | null>;
  /** Archive the stored result on the backend (best-effort; not all providers support this). */
  deleteAnalysis?(id: string): Promise<void>;
  /** Subscribe to job updates. Returns unsubscribe. */
  subscribe(cb: () => void): () => void;
  /** Provider name — used in dev tools / settings. */
  name: string;
}

