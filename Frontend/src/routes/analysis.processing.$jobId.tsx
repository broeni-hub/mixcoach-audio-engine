// Premium standalone processing screen. Polls the analysis job, animates a
// 9-step pipeline, surfaces ETA + educational tips, and offers retry /
// demo-fallback / re-upload when the backend fails.

import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CircleDashed,
  Loader2,
  RefreshCw,
  Upload,
  X,
  Headphones,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { useAnalysisJob, useCancelJob, useRetryJob } from "@/lib/api/hooks";
import type { PipelineStage, AnalysisJob } from "@/lib/api/types";
import { buildAnalysisResult } from "@/lib/analysis";
import { addAnalysis } from "@/lib/store";
import { getAnalysisProvider } from "@/lib/api/provider";

export const Route = createFileRoute("/analysis/processing/$jobId")({
  ssr: false,
  head: () => ({ meta: [{ title: "Analyzing — MixCoach" }] }),
  component: ProcessingPage,
});

const ACTIVE_KEY = "mixcoach.activeJobId.v1";

// 9-step UI pipeline. We map every backend stage onto one of these display
// rows so the visual contract stays stable regardless of provider.
type DisplayStep = {
  id: string;
  label: string;
  stages: PipelineStage[];
};

const STEPS: DisplayStep[] = [
  { id: "upload",       label: "Upload completed",      stages: ["uploaded"] },
  { id: "preprocess",   label: "Audio preprocessing",   stages: ["preprocessing"] },
  { id: "bpm",          label: "BPM detection",         stages: ["bpm_detection", "audio_feature_extraction", "feature_extraction"] },
  { id: "key",          label: "Key detection",         stages: ["key_detection"] },
  { id: "beatgrid",     label: "Beat grid analysis",    stages: ["beatgrid_detection"] },
  { id: "phrase",       label: "Phrase detection",      stages: ["phrase_detection"] },
  { id: "transition",   label: "Transition detection",  stages: ["transition_detection", "transition_analysis"] },
  { id: "coaching",     label: "Coach generation",      stages: ["ai_coaching_generation", "coaching_generation"] },
  { id: "report",       label: "Report generation",     stages: ["report", "stored"] },
];

const ALL_STAGES_ORDER: PipelineStage[] = STEPS.flatMap((s) => s.stages);

function activeStepIndex(stage: PipelineStage): number {
  for (let i = 0; i < STEPS.length; i++) {
    if (STEPS[i].stages.includes(stage)) return i;
  }
  // unknown stage → derive by position in PIPELINE_STAGES order
  const pos = ALL_STAGES_ORDER.indexOf(stage);
  return pos >= 0 ? STEPS.findIndex((s) => s.stages.includes(ALL_STAGES_ORDER[pos])) : 0;
}

const TIPS = [
  "Pro tip — Cut the bass of the outgoing track before bringing in the new bass. Two basslines never play at the same time.",
  "Phrase your transitions in 16- or 32-bar blocks. Most house and techno tracks are built around 8-bar units.",
  "Harmonic mixing: stay within ±1 step on the Camelot wheel for the smoothest key changes.",
  "Energy curves matter more than tempo. A 124 → 126 BPM jump feels fine if the energy keeps building.",
  "Leave headroom. Master your transitions around -6 dB so the drop has somewhere to go.",
  "Use a high-pass filter on the outgoing track during the last 4 bars to make space for the incoming kick.",
];

function ProcessingPage() {
  const { jobId } = Route.useParams();
  const navigate = useNavigate();
  const { data: job, isLoading } = useAnalysisJob(jobId);
  const cancelJob = useCancelJob();
  const retryJob = useRetryJob();
  const navigatedRef = useRef(false);

  // rotate tips every 6s
  const [tipIdx, setTipIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTipIdx((i) => (i + 1) % TIPS.length), 6000);
    return () => clearInterval(t);
  }, []);

  // auto-navigate when complete - vorher das Ergebnis vom Backend in den
  // Store holen, sonst zeigt die Report-Seite "Analysis not found".
  useEffect(() => {
    if (!job || navigatedRef.current) return;
    if (job.status === "completed" && job.analysisId) {
      navigatedRef.current = true;
      const analysisId = job.analysisId;
      void (async () => {
        try {
          const result = await getAnalysisProvider().getAnalysis(analysisId);
          if (result) addAnalysis(result);
        } catch {
          // Report-Seite zeigt dann "not found" - besser als Crash.
        }
        if (typeof window !== "undefined") localStorage.removeItem(ACTIVE_KEY);
        toast.success(job.fromCache ? "Cached analysis restored" : "Analysis ready");
        navigate({ to: "/app/analyses/$id", params: { id: analysisId } });
      })();
    }
  }, [job, navigate]);

  const analysisType = useMemo<"single" | "set">(() => {
    // Heuristic from filename — a real "set" is usually >20 minutes; we
    // approximate with filesize (>40 MB ≈ likely a full set).
    if (!job) return "single";
    if (job.fileSize > 40 * 1024 * 1024) return "set";
    return "single";
  }, [job]);

  async function handleCancel() {
    await cancelJob(jobId);
    if (typeof window !== "undefined") localStorage.removeItem(ACTIVE_KEY);
    navigate({ to: "/app/upload" });
  }

  async function handleRetry() {
    try {
      const nextId = await retryJob(jobId);
      if (typeof window !== "undefined") localStorage.setItem(ACTIVE_KEY, nextId);
      navigate({ to: "/analysis/processing/$jobId", params: { jobId: nextId } });
    } catch (e) {
      toast.error((e as Error).message ?? "Could not retry job");
    }
  }

  function handleDemo() {
    const file = { name: job?.fileName ?? "demo-mix.wav", size: job?.fileSize ?? 0 };
    const result = buildAnalysisResult(file);
    addAnalysis(result);
    if (typeof window !== "undefined") localStorage.removeItem(ACTIVE_KEY);
    toast.message("Demo report generated", { description: "Numbers are illustrative — re-run analysis on your file for real coaching." });
    navigate({ to: "/app/analyses/$id", params: { id: result.id } });
  }

  // ---- empty / missing -----------------------------------------------------
  if (!job && !isLoading) {
    return (
      <Shell>
        <Card className="border-border/60 bg-card/60 backdrop-blur">
          <CardContent className="p-10 text-center">
            <CircleDashed className="h-8 w-8 mx-auto text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">This job is no longer available.</p>
            <Button asChild className="mt-6">
              <Link to="/app/upload">Upload a track</Link>
            </Button>
          </CardContent>
        </Card>
      </Shell>
    );
  }

  // ---- failed --------------------------------------------------------------
  if (job?.status === "failed") {
    return (
      <Shell>
        <Card className="border-destructive/40 bg-card/70 backdrop-blur">
          <CardContent className="p-8 md:p-10">
            <div className="flex items-start gap-4">
              <div className="h-11 w-11 rounded-xl bg-destructive/15 border border-destructive/30 flex items-center justify-center shrink-0">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] uppercase tracking-[0.18em] text-destructive/80">Analysis failed</p>
                <h1 className="font-display text-xl font-semibold truncate mt-1">{job.fileName}</h1>
                <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
                  Analysis failed. You can retry or generate a demo report.
                </p>
                {job.errorMessage && (
                  <p className="mt-2 text-xs text-muted-foreground/80 font-mono break-words">
                    {job.errorMessage}
                    {job.attempts ? `  ·  Attempt ${job.attempts + 1}` : ""}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-8 grid sm:grid-cols-3 gap-2">
              <Button onClick={handleRetry} className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                <RefreshCw className="h-4 w-4" /> Retry analysis
              </Button>
              <Button onClick={handleDemo} variant="outline" className="border-border/60">
                <Sparkles className="h-4 w-4" /> Use demo report
              </Button>
              <Button asChild variant="ghost">
                <Link to="/app/upload"><Upload className="h-4 w-4" /> Upload another file</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </Shell>
    );
  }

  // ---- running -------------------------------------------------------------
  const currentIdx = job ? activeStepIndex(job.stage) : 0;
  const currentLabel = job ? STEPS[currentIdx]?.label ?? "Preparing…" : "Preparing…";

  return (
    <Shell>
      <Card className="border-border/60 bg-card/70 backdrop-blur overflow-hidden">
        <div className="h-px w-full bg-[image:var(--gradient-primary)] opacity-60" />
        <CardContent className="p-8 md:p-10">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-[11px] uppercase tracking-[0.18em] text-primary/80">
                {analysisType === "set" ? "Full set analysis" : "Single transition analysis"}
              </p>
              <h1 className="font-display text-xl md:text-2xl font-semibold truncate mt-1">
                {job?.fileName ?? "Preparing your file…"}
              </h1>
              <p className="mt-1 text-xs text-muted-foreground">
                {currentLabel}
                {job?.fallback && <span className="ml-2 text-amber-400/80">· demo fallback</span>}
              </p>
            </div>
            <Button size="icon" variant="ghost" onClick={handleCancel} aria-label="Cancel analysis" className="shrink-0">
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Overall progress */}
          <div className="mt-7">
            <div className="flex items-end justify-between">
              <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Overall progress</span>
              <span className="font-display text-3xl font-bold tabular-nums">{job?.progress ?? 0}%</span>
            </div>
            <Progress value={job?.progress ?? 0} className="mt-3 h-1.5" />
            <div className="mt-2 flex justify-between text-[11px] text-muted-foreground">
              <span>{etaLabel(job)}</span>
              <span>{job?.status === "queued" ? "Queued" : job?.status === "running" ? "Processing" : ""}</span>
            </div>
          </div>

          {/* Pipeline */}
          <ol className="mt-8 space-y-1">
            {STEPS.map((step, i) => {
              const status: "completed" | "active" | "pending" | "failed" =
                !job ? "pending"
                : job.status === "completed" ? "completed"
                : i < currentIdx ? "completed"
                : i === currentIdx ? "active"
                : "pending";
              return <StepRow key={step.id} label={step.label} status={status} pct={status === "active" ? Math.round(job?.stageProgress ?? 0) : status === "completed" ? 100 : 0} />;
            })}
          </ol>

          {/* Tip */}
          <div className="mt-8 rounded-lg border border-border/60 bg-secondary/40 px-4 py-3 flex items-start gap-3">
            <Headphones className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground leading-relaxed">{TIPS[tipIdx]}</p>
          </div>

          <p className="mt-6 text-xs text-muted-foreground text-center">
            You can leave this page — we&apos;ll keep analyzing in the background.{" "}
            <Link to="/app/dashboard" className="underline-offset-4 hover:underline inline-flex items-center gap-1">
              Back to dashboard <ArrowRight className="h-3 w-3" />
            </Link>
          </p>
        </CardContent>
      </Card>
    </Shell>
  );
}

// -- subcomponents -----------------------------------------------------------

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background relative">
      {/* Premium ambient glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-[420px] w-[820px] rounded-full bg-primary/15 blur-[140px]" />
        <div className="absolute top-40 right-10 h-[280px] w-[280px] rounded-full bg-accent/15 blur-[120px]" />
      </div>
      <div className="relative mx-auto max-w-2xl px-4 py-10 md:py-16">
        <div className="flex items-center justify-between mb-6">
          <Link to="/app/dashboard" className="text-xs uppercase tracking-[0.2em] text-muted-foreground hover:text-foreground">
            MixCoach
          </Link>
          <Link to="/app/upload" className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <Upload className="h-3 w-3" /> New upload
          </Link>
        </div>
        {children}
      </div>
    </div>
  );
}

function StepRow({ label, status, pct }: { label: string; status: "completed" | "active" | "pending" | "failed"; pct: number }) {
  return (
    <li className="group">
      <div className="flex items-center gap-3 py-2">
        <span
          className={[
            "h-6 w-6 rounded-full border flex items-center justify-center shrink-0 transition-colors",
            status === "completed" && "bg-accent/15 border-accent text-accent",
            status === "active" && "border-primary text-primary bg-primary/10",
            status === "pending" && "border-border/60 text-muted-foreground/60",
            status === "failed" && "border-destructive text-destructive bg-destructive/10",
          ].filter(Boolean).join(" ")}
        >
          {status === "completed" && <Check className="h-3.5 w-3.5" />}
          {status === "active" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {status === "pending" && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
          {status === "failed" && <X className="h-3.5 w-3.5" />}
        </span>
        <span
          className={[
            "flex-1 text-sm transition-colors",
            status === "completed" && "text-foreground/80",
            status === "active" && "text-foreground font-medium",
            status === "pending" && "text-muted-foreground/70",
            status === "failed" && "text-destructive",
          ].filter(Boolean).join(" ")}
        >
          {label}
        </span>
        {status === "active" && (
          <span className="text-xs font-mono tabular-nums text-primary w-10 text-right">{pct}%</span>
        )}
        {status === "completed" && (
          <span className="text-[10px] uppercase tracking-wider text-accent/80">Done</span>
        )}
      </div>
      {status === "active" && (
        <div className="ml-9 h-[3px] rounded-full bg-secondary/70 overflow-hidden">
          <div
            className="h-full bg-[image:var(--gradient-primary)] transition-[width] duration-200"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </li>
  );
}

function etaLabel(job: AnalysisJob | null | undefined): string {
  if (!job) return "Estimating…";
  if (job.status === "queued") return "Waiting in queue";
  const s = job.estimatedRemainingSeconds;
  if (typeof s !== "number" || !isFinite(s) || s <= 0) return "Estimating remaining time…";
  if (s < 60) return `~${Math.max(1, Math.round(s))}s remaining`;
  const m = Math.floor(s / 60);
  const r = Math.round(s % 60);
  return r ? `~${m}m ${r}s remaining` : `~${m}m remaining`;
}
