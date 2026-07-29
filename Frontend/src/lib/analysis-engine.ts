// Persistent analysis job engine. Runs the REAL audio analysis pipeline
// (see audio-analysis.ts) and surfaces per-stage progress to the UI.
//
// Job metadata is persisted to localStorage so the active-job pill survives
// route changes. The decoded File itself is NOT persistable, so if the page
// is reloaded mid-analysis the job is marked "interrupted" and the user is
// asked to re-upload — we never fake progress on a missing file.

import { ANALYSIS_STAGES, buildAnalysisResult } from "./analysis";
import { addAnalysis } from "./store";
import { persistAnalysis } from "./sync";
import { hashFilesCombined, getCachedResultId, setCachedResultId } from "./file-hash";
import { evaluateRules, loadKb, metricsFromMeasurements, persistFindings } from "./coaching";
import { saveAudio } from "./audio-store";


const JOBS_KEY = "mixcoach.jobs.v1";
const JOBS_EVENT = "mixcoach:jobs";

export type JobStatus = "running" | "done" | "error";

export interface AnalysisJob {
  id: string;
  fileName: string;
  fileSize: number;
  stageIndex: number;     // 0..ANALYSIS_STAGES.length
  stageProgress: number;  // 0..100 within current stage
  overall: number;        // 0..100 across all stages
  status: JobStatus;
  startedAt: number;
  updatedAt: number;
  resultId?: string;
  error?: string;
  fromCache?: boolean;
}

type JobsMap = Record<string, AnalysisJob>;

function readJobs(): JobsMap {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(JOBS_KEY) || "{}"); } catch { return {}; }
}

function writeJobs(jobs: JobsMap) {
  if (typeof window === "undefined") return;
  localStorage.setItem(JOBS_KEY, JSON.stringify(jobs));
  window.dispatchEvent(new CustomEvent(JOBS_EVENT));
}

function patch(id: string, partial: Partial<AnalysisJob>) {
  const jobs = readJobs();
  const cur = jobs[id];
  if (!cur) return;
  jobs[id] = { ...cur, ...partial, updatedAt: Date.now() };
  writeJobs(jobs);
}

function computeOverall(stageIndex: number, stageProgress: number): number {
  const total = ANALYSIS_STAGES.length;
  const done = Math.min(stageIndex, total);
  const pct = ((done + Math.min(stageProgress, 100) / 100) / total) * 100;
  return Math.min(100, Math.round(pct));
}

// Tracks in-flight Files for the lifetime of this tab. Cleared on reload.
const liveFiles = new Map<string, File>();

export async function startJob(
  file: File,
  opts?: { fileB?: File; cuePointSec?: number; overlapSec?: number },
): Promise<string> {
  const id = crypto.randomUUID();
  const now = Date.now();
  const job: AnalysisJob = {
    id,
    fileName: opts?.fileB ? `${file.name}  →  ${opts.fileB.name}` : file.name,
    fileSize: file.size + (opts?.fileB?.size ?? 0),
    stageIndex: 0,
    stageProgress: 0,
    overall: 0,
    status: "running",
    startedAt: now,
    updatedAt: now,
  };
  writeJobs({ ...readJobs(), [id]: job });
  liveFiles.set(id, file);
  // Compute hash up-front; if a cached result exists, short-circuit the pipeline.
  void (async () => {
    try {
      const { hash, resultId } = await findCachedResult(file, opts);
      if (resultId) {
        patch(id, {
          stageIndex: ANALYSIS_STAGES.length,
          stageProgress: 100,
          overall: 100,
          status: "done",
          resultId,
          fromCache: true,
        });
        liveFiles.delete(id);
        return;
      }
      await runPipeline(id, file, opts, hash);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Audio analysis failed";
      patch(id, { status: "error", error: message });
      liveFiles.delete(id);
    }
  })();
  return id;
}

function localAnalysisExists(id: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = localStorage.getItem("mixcoach.state.v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    return Array.isArray(state?.analyses) && state.analyses.some((a: { id: string }) => a.id === id);
  } catch {
    return false;
  }
}

// Ein gecachter Browser-Fallback-Report (engine:"local") darf NIE als
// Cache-Treffer wiederverwendet werden - sonst liefert ein erneuter Upload
// derselben Datei den schwachen Fallback zurueck, obwohl die Engine jetzt
// laeuft (Falle bei MixCoach2, 2026-07-17). Solche Eintraege gelten als
// "nicht vorhanden", die Analyse laeuft dann frisch ueber die Engine.
function usableCachedAnalysis(id: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = localStorage.getItem("mixcoach.state.v1");
    if (!raw) return false;
    const state = JSON.parse(raw);
    const a = (state?.analyses || []).find((x: { id: string }) => x.id === id);
    return !!a && a.engine !== "local";
  } catch {
    return false;
  }
}

/** Insert a remote analysis into local store without awarding XP again.
 *  Exportiert fuer den "Auf dem Analyse-Server gefunden"-Import auf der
 *  Analysen-Seite (Engine-Reports, die im Browser-Store fehlen, z.B. nach
 *  einem stillen Fallback waehrend des Laufs). */
export function mergeRemoteAnalysisIntoStore(remote: import("./analysis").AnalysisResult) {
  if (typeof window === "undefined") return;
  try {
    const raw = localStorage.getItem("mixcoach.state.v1") || "{}";
    const state = JSON.parse(raw);
    const list = Array.isArray(state.analyses) ? state.analyses : [];
    if (list.some((a: { id: string }) => a.id === remote.id)) return;
    state.analyses = [remote, ...list];
    localStorage.setItem("mixcoach.state.v1", JSON.stringify(state));
    window.dispatchEvent(new Event("mixcoach:update"));
  } catch (err) {
    console.warn("[engine] failed to merge remote analysis", err);
  }
}

/** Look up the cached analysis for these files. Checks the local hash cache
 *  first (instant), then the Cloud cache (cross-device). On a remote hit the
 *  analysis row is hydrated into the local store so the report page renders
 *  immediately. */
export async function findCachedResult(
  file: File,
  opts?: { fileB?: File; cuePointSec?: number; overlapSec?: number },
): Promise<{ hash: string; resultId?: string }> {
  const hash = await hashFilesCombined(file, opts?.fileB, {
    cue: opts?.cuePointSec ?? 0,
    overlap: opts?.overlapSec ?? 0,
  });

  // 1) Local cache — fastest path. Fallback-Reports werden bewusst
  //    uebersprungen (usableCachedAnalysis), damit ein Re-Upload bei
  //    laufender Engine frisch analysiert statt den Fallback zu servieren.
  const cachedId = getCachedResultId(hash);
  if (cachedId && usableCachedAnalysis(cachedId)) return { hash, resultId: cachedId };

  // 2) Cloud cache — works across devices/browsers as long as the user is signed in.
  try {
    const { lookupHashFn } = await import("./hash-cache.functions");
    const res = await lookupHashFn({ data: { hash } });
    if (res.hit) {
      const remote = res.analysis as unknown as import("./analysis").AnalysisResult;
      if (!localAnalysisExists(remote.id)) mergeRemoteAnalysisIntoStore(remote);
      setCachedResultId(hash, remote.id);
      return { hash, resultId: remote.id };
    }
  } catch (err) {
    // Offline / signed-out / network — fall through to a real run.
    console.warn("[engine] remote hash lookup failed", err);
  }

  return { hash };
}

async function runPipeline(
  id: string,
  file: File,
  opts?: { fileB?: File; cuePointSec?: number; overlapSec?: number },
  cacheHash?: string,
) {
  try {
    const { analyzeAudioFile } = await import("./audio-analysis");
    let measurements: Awaited<ReturnType<typeof analyzeAudioFile>>;
    let extras: Parameters<typeof buildAnalysisResult>[3];

    if (opts?.fileB) {
      // 2-track: use the transition analyzer (which calls analyzeAudioFile twice).
      const { analyzeTransition } = await import("./transition-analysis");
      const result = await analyzeTransition(file, opts.fileB, opts.cuePointSec ?? 0, opts.overlapSec, (stage, pct) => {
        const mappedStage = Math.min(stage + 1, ANALYSIS_STAGES.length - 1);
        patch(id, { stageIndex: mappedStage, stageProgress: pct, overall: computeOverall(mappedStage, pct) });
      });
      measurements = result.trackA;
      extras = {
        trackB: { ...result.trackB, fileName: opts.fileB.name },
        transition: result.transition,
      };
    } else {
      measurements = await analyzeAudioFile(file, (stage, pct) => {
        const mappedStage = Math.min(stage + 1, ANALYSIS_STAGES.length - 1);
        patch(id, { stageIndex: mappedStage, stageProgress: pct, overall: computeOverall(mappedStage, pct) });
      });

      // Single-file uploads can be full DJ sets. Scan the whole recording
      // for transition points so the report covers every transition, not
      // just the first 120s window analyzeAudioFile sees.
      try {
        const { analyzeSetTransitions } = await import("./set-analysis");
        const setResult = await analyzeSetTransitions(file, (pct) => {
          const mapped = Math.round(pct * 0.6); // map set progress to stage 5 0..60%
          patch(id, { stageIndex: 5, stageProgress: mapped, overall: computeOverall(5, mapped) });
        });
        extras = {
          setTransitions: setResult.transitions,
          totalDurationSec: setResult.totalDurationSec,
          fullVolumeCurve: setResult.volumeCurve,
        };
      } catch (err) {
        console.warn("[engine] set transition analysis failed", err);
      }
    }

    // Coaching rules — local fast layer (still useful even if LLM is offline).
    patch(id, { stageIndex: 5, stageProgress: 70, overall: computeOverall(5, 70) });
    let findings: Awaited<ReturnType<typeof evaluateRules>> | undefined;
    try {
      const kb = await loadKb();
      findings = evaluateRules(kb, metricsFromMeasurements(measurements));
    } catch (err) {
      console.warn("[engine] coaching KB unavailable, using heuristic fallback", err);
    }

    // Build report.
    patch(id, { stageIndex: 6, stageProgress: 40, overall: computeOverall(6, 40) });
    const result = buildAnalysisResult({ name: file.name, size: file.size }, measurements, findings, extras);
    // Browser-Pfad = Fallback ohne Analyse-Engine: im Report deutlich
    // kennzeichnen (siehe AnalysisResult.engine).
    result.engine = "local";
    addAnalysis(result);
    // Browser-Fallback-Ergebnisse NICHT unter dem Datei-Hash cachen: sonst
    // liefert ein erneuter Upload derselben Datei den schwachen Fallback aus
    // dem Cache zurueck, statt ihn (bei jetzt laufender Engine) richtig neu
    // zu analysieren (genau die Falle bei MixCoach2, 2026-07-17). Nur echte
    // Engine-Reports duerfen gecacht werden.
    void persistAnalysis(result, false);
    void saveAudio(result.id, file);
    if (opts?.fileB) void saveAudio(`${result.id}:B`, opts.fileB);
    if (findings && findings.length > 0) void persistFindings(result.id, findings);

    // LLM coach — generate after persistAnalysis so the row exists in DB
    // (RLS check passes). Best-effort: failure is non-fatal.
    patch(id, { stageIndex: 6, stageProgress: 70, overall: computeOverall(6, 70) });
    try {
      const { generateCoachFeedbackFn } = await import("./coach-feedback.functions");
      // give the upsert a tick to land before the LLM call
      await new Promise((r) => setTimeout(r, 250));
      await generateCoachFeedbackFn({
        data: {
          analysis_id: result.id,
          filename: result.fileName,
          track_b_filename: result.trackB?.fileName ?? null,
          level: "intermediate",
          measurements: {
            bpm: measurements.bpm,
            bpm_confidence: measurements.bpmConfidence,
            key: measurements.key,
            key_confidence: measurements.keyConfidence,
            bass_pct: measurements.bands.bass,
            mid_pct: measurements.bands.mid,
            high_pct: measurements.bands.high,
            bass_stability: measurements.bassStability,
            dynamic_range_db: measurements.dynamicRangeDb,
            loudness_dbfs: measurements.loudnessDbfs,
            peak_count: measurements.peakCount,
            duration_sec: measurements.durationSec,
          },
          findings: (findings ?? []).map((f) => ({
            rule_slug: f.rule.slug,
            title: f.rule.title,
            diagnosis: f.rule.diagnosis,
            fix: f.rule.fix,
            severity: f.rule.severity,
            metric: f.metric,
            value: f.value,
          })),
          transition: extras?.transition,
        },
      });
    } catch (err) {
      console.warn("[engine] LLM coach generation failed", err);
    }

    patch(id, {
      stageIndex: ANALYSIS_STAGES.length,
      stageProgress: 100,
      overall: 100,
      status: "done",
      resultId: result.id,
    });
    liveFiles.delete(id);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Audio analysis failed";
    patch(id, { status: "error", error: message });
    liveFiles.delete(id);
  }
}

export function getJob(id: string): AnalysisJob | undefined {
  return readJobs()[id];
}

export function listJobs(): AnalysisJob[] {
  return Object.values(readJobs()).sort((a, b) => b.startedAt - a.startedAt);
}

export function activeJobs(): AnalysisJob[] {
  return listJobs().filter((j) => j.status === "running");
}

export function removeJob(id: string) {
  liveFiles.delete(id);
  const jobs = readJobs();
  delete jobs[id];
  writeJobs(jobs);
}

export function cancelJob(id: string) {
  const jobs = readJobs();
  const job = jobs[id];
  if (!job) return;
  liveFiles.delete(id);
  writeJobs({ ...jobs, [id]: { ...job, status: "error", error: "Cancelled", updatedAt: Date.now() } });
}

export function isLive(id: string): boolean {
  return liveFiles.has(id);
}

export function subscribe(cb: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = () => cb();
  window.addEventListener(JOBS_EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(JOBS_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

// On module load: any "running" job not backed by a live File came from
// a previous page load. Mark it interrupted — the user must re-upload.
let bootstrapped = false;
export function bootstrapEngine() {
  if (bootstrapped || typeof window === "undefined") return;
  bootstrapped = true;
  for (const job of activeJobs()) {
    if (!liveFiles.has(job.id)) {
      patch(job.id, { status: "error", error: "Interrupted — re-upload to resume" });
    }
  }
}

export function clearCompletedJobs() {
  const jobs = readJobs();
  const next: JobsMap = {};
  for (const [id, job] of Object.entries(jobs)) {
    if (job.status === "running") next[id] = job;
  }
  writeJobs(next);
}

export function clearAllJobs() {
  liveFiles.clear();
  writeJobs({});
}
