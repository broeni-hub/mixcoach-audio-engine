import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sparkles, Play, BarChart3, Clock, Zap, Upload,
} from "lucide-react";
import type { CoachExercise, CoachInsightBundle } from "@/lib/coach";

/**
 * The Coach Card.
 * Three lines. No paragraphs. Two CTAs. Always.
 *   ✅ What improved
 *   ⚠ Biggest issue
 *   🎯 Next focus
 */
export function CoachInsight({
  bundle,
  latestAnalysisId,
  // kept for backwards-compat with older callers
  compact: _compact = false,
}: {
  bundle: CoachInsightBundle;
  latestAnalysisId?: string;
  compact?: boolean;
}) {
  const improved = bundle.recentImprovement?.title ?? "Showing up. That's the work.";
  const issue =
    bundle.patternDetected?.title ??
    bundle.currentFocus.title ??
    bundle.mainWeakness?.title ??
    "Nothing flagged — push a harder mix to find the next limit.";
  const next = bundle.recommendedTraining.title;

  return (
    <Card className="glass border-primary/30 glow-purple">
      <CardContent className="p-6 space-y-5">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-primary">
          <Sparkles className="h-3.5 w-3.5" /> Coach
        </div>

        <CoachLines improved={improved} issue={issue} next={next} />

        <CoachActions
          exerciseId={bundle.recommendedTraining.exercise.id}
          analysisId={latestAnalysisId}
        />
      </CardContent>
    </Card>
  );
}

/**
 * Compact 3-line coach block for embedding in other cards (dashboard hero, etc.).
 * Same structure, no card shell, no actions.
 */
export function CoachLines({
  improved, issue, next,
}: { improved: string; issue: string; next: string }) {
  return (
    <ul className="space-y-2.5 text-[15px] leading-snug">
      <li className="flex items-start gap-3">
        <span aria-hidden className="text-emerald-400 shrink-0 mt-px">✅</span>
        <div>
          <span className="text-[10px] uppercase tracking-widest text-emerald-400/80 mr-2">What improved</span>
          <span className="text-foreground/95">{trimSentence(improved)}</span>
        </div>
      </li>
      <li className="flex items-start gap-3">
        <span aria-hidden className="text-amber-400 shrink-0 mt-px">⚠</span>
        <div>
          <span className="text-[10px] uppercase tracking-widest text-amber-400/80 mr-2">Biggest issue</span>
          <span className="text-foreground/95">{trimSentence(issue)}</span>
        </div>
      </li>
      <li className="flex items-start gap-3">
        <span aria-hidden className="text-primary shrink-0 mt-px">🎯</span>
        <div>
          <span className="text-[10px] uppercase tracking-widest text-primary/80 mr-2">Next focus</span>
          <span className="text-foreground/95">{trimSentence(next)}</span>
        </div>
      </li>
    </ul>
  );
}

/** Shared CTA pair for every coach card. */
export function CoachActions({
  exerciseId: _exerciseId, analysisId,
}: { exerciseId?: string; analysisId?: string }) {
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      <Button asChild className="bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90">
        <Link to="/app/training">
          <Play className="h-4 w-4" /> Start Exercise
        </Link>
      </Button>
      {analysisId ? (
        <Button asChild variant="outline">
          <Link to="/app/analyses/$id" params={{ id: analysisId }}>
            <BarChart3 className="h-4 w-4" /> View Analysis
          </Link>
        </Button>
      ) : (
        <Button asChild variant="outline">
          <Link to="/app/analyses">
            <BarChart3 className="h-4 w-4" /> View Analysis
          </Link>
        </Button>
      )}
    </div>
  );
}

/** Force a single tight sentence — no rambling paragraphs. */
function trimSentence(s: string): string {
  const clean = (s ?? "").trim().replace(/\s+/g, " ");
  if (!clean) return "—";
  // First sentence only.
  const m = clean.match(/^.*?[.!?](\s|$)/);
  let one = (m ? m[0] : clean).trim();
  // Hard cap so a single sentence can't run on.
  if (one.length > 140) one = one.slice(0, 137).trimEnd() + "…";
  if (!/[.!?]$/.test(one)) one += ".";
  return one;
}


export function ExerciseCard({
  exercise, eyebrow, onStart,
}: { exercise: CoachExercise; eyebrow?: string; onStart?: () => void }) {
  return (
    <Card className="glass hover:border-primary/40 transition-colors">
      <CardContent className="p-5 space-y-4">
        {eyebrow && <div className="text-xs uppercase tracking-widest text-primary">{eyebrow}</div>}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="font-display text-xl font-bold leading-tight">{exercise.name}</h3>
            <div className="text-xs text-muted-foreground mt-1">Targets {exercise.targetSkillTitle}</div>
          </div>
          <div className="flex gap-1.5 flex-wrap">
            <Badge variant="outline" className="gap-1"><Zap className="h-3 w-3" />+{exercise.xp} XP</Badge>
            <Badge variant="outline" className="gap-1"><Clock className="h-3 w-3" />{exercise.durationMin}m</Badge>
            <Badge variant="outline">{exercise.difficulty}</Badge>
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1.5">Instructions</div>
          <ol className="text-sm space-y-1 list-decimal list-inside text-muted-foreground">
            {exercise.instructions.map((i, idx) => <li key={idx}><span className="text-foreground/90">{i}</span></li>)}
          </ol>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 text-sm">
          <div className="rounded-md bg-secondary/30 p-3">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">What to upload</div>
            <div className="text-foreground/90">{exercise.uploadAsk}</div>
          </div>
          <div className="rounded-md bg-secondary/30 p-3">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">Success criteria</div>
            <ul className="space-y-0.5">
              {exercise.successCriteria.map((c, i) => (
                <li key={i} className="text-foreground/90">· {c}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          <Button onClick={onStart} className="gap-2">
            <Play className="h-4 w-4" /> Start Exercise
          </Button>
          <Button asChild variant="outline" className="gap-2">
            <Link to="/app/upload"><Upload className="h-4 w-4" /> Upload for this Exercise</Link>
          </Button>
          <Button asChild variant="ghost" className="gap-2">
            <Link to="/app/career"><BarChart3 className="h-4 w-4" /> View Skill Progress</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
