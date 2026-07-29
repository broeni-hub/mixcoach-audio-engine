// Live pipeline UI — animated checklist of every pipeline stage. Reads from
// the public AnalysisJob shape so it works with any provider.

import { Check, Loader2, Circle, X } from "lucide-react";
import { PIPELINE_STAGES, STAGE_LABEL, type AnalysisJob, type PipelineStage } from "@/lib/api/types";
import { Progress } from "@/components/ui/progress";

interface Props {
  job: AnalysisJob;
}

// Visual stages displayed to the user. We collapse "queued" and show the
// active set.
const DISPLAY_STAGES: PipelineStage[] = [
  "uploaded",
  "preprocessing",
  "feature_extraction",
  "transition_detection",
  "transition_analysis",
  "coaching_generation",
  "report",
  "completed",
];

function stageIndex(stage: PipelineStage): number {
  return PIPELINE_STAGES.indexOf(stage);
}

export function AnalysisPipeline({ job }: Props) {
  const currentIdx = stageIndex(job.stage);
  const failed = job.status === "failed";

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Overall progress</span>
        <span className="font-display font-bold">{job.progress}%</span>
      </div>
      <Progress value={job.progress} className="mt-2 h-2" />
      {typeof job.estimatedRemainingSeconds === "number" && job.status === "running" && (
        <p className="mt-1 text-[11px] text-muted-foreground text-right">
          ~{formatEta(job.estimatedRemainingSeconds)} remaining
        </p>
      )}

      <ol className="mt-6 space-y-2.5">
        {DISPLAY_STAGES.map((s) => {
          const idx = stageIndex(s);
          const done = !failed && (idx < currentIdx || job.status === "completed");
          const active = !failed && idx === currentIdx && job.status === "running";
          const pct = done ? 100 : active ? Math.round(job.stageProgress) : 0;
          return (
            <li key={s} className={`transition-opacity ${done || active ? "opacity-100" : "opacity-45"}`}>
              <div className="flex items-center gap-3 text-sm">
                <span
                  className={`h-5 w-5 rounded-full flex items-center justify-center border ${
                    done
                      ? "bg-accent border-accent text-accent-foreground"
                      : active
                        ? "border-primary text-primary"
                        : "border-border text-muted-foreground"
                  }`}
                >
                  {done ? (
                    <Check className="h-3 w-3" />
                  ) : active ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Circle className="h-2 w-2" />
                  )}
                </span>
                <span className="flex-1 font-medium">{STAGE_LABEL[s]}</span>
                {active && (
                  <span className="text-xs text-muted-foreground font-mono w-10 text-right">{pct}%</span>
                )}
              </div>
              {active && (
                <div className="mt-1.5 ml-8 h-1 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-[image:var(--gradient-primary)] transition-[width] duration-150"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              )}
            </li>
          );
        })}
        {failed && (
          <li className="flex items-center gap-3 text-sm text-destructive">
            <span className="h-5 w-5 rounded-full border border-destructive flex items-center justify-center">
              <X className="h-3 w-3" />
            </span>
            <span>{job.errorMessage ?? "Analysis failed"}</span>
          </li>
        )}
      </ol>
    </div>
  );
}

function formatEta(s: number): string {
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r ? `${m}m ${r}s` : `${m}m`;
}
