import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ArrowRight, TrendingUp, TrendingDown, Award, Target, Sparkles } from "lucide-react";
import { useAppState } from "@/lib/store";
import { computeMonthlyReport } from "@/lib/retention";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/monthly")({
  head: () => ({ meta: [{ title: "Monthly report — MixCoach" }] }),
  component: MonthlyPage,
});

export function MonthlyPage() {
  const [state] = useAppState();
  const [offset, setOffset] = useState(0);
  const r = computeMonthlyReport(state, offset);

  return (
    <div className="container mx-auto max-w-5xl space-y-6 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Monthly report</div>
          <h1 className="font-display text-3xl font-bold tracking-tight">{r.monthLabel}</h1>
          <p className="text-muted-foreground">{r.uploads} session{r.uploads === 1 ? "" : "s"} this month.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setOffset(offset + 1)}>
            <ArrowLeft className="h-4 w-4" /> Previous
          </Button>
          <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(offset - 1)}>
            Next <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card className="border-primary/30 bg-[image:var(--gradient-primary)]/10">
        <CardContent className="grid gap-6 p-6 sm:grid-cols-3">
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Avg overall</div>
            <div className="font-display text-4xl font-bold">{r.avgOverallNow || "—"}</div>
            {r.avgOverallPrev > 0 && (
              <div className={`mt-1 text-xs ${r.improvementDelta >= 0 ? "text-emerald-400" : "text-orange-400"}`}>
                {r.improvementDelta >= 0 ? "+" : ""}{r.improvementDelta} vs last month
              </div>
            )}
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Uploads</div>
            <div className="font-display text-4xl font-bold">{r.uploads}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Best score</div>
            <div className="font-display text-4xl font-bold">{r.bestTransition?.scores.overall ?? "—"}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" /> Coach summary</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-base leading-relaxed">{r.summary}</p>
          <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
            <div className="flex items-start gap-2">
              <Target className="mt-0.5 h-4 w-4 text-primary" />
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Next month focus</div>
                <div className="text-sm">{r.nextFocus}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Skill improvements</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {r.skillDeltas.map((s) => (
            <div key={s.key} className="flex items-center gap-3 rounded-lg border border-border p-3">
              <div className="flex-1">
                <div className="text-sm font-medium">{s.label}</div>
                <div className="text-xs text-muted-foreground">{s.prev || "—"} → {s.now || "—"}</div>
              </div>
              <Badge
                variant="outline"
                className={s.delta > 0 ? "border-emerald-500/40 text-emerald-400" : s.delta < 0 ? "border-orange-500/40 text-orange-400" : ""}
              >
                {s.delta > 0 ? <TrendingUp className="mr-1 h-3 w-3" /> : s.delta < 0 ? <TrendingDown className="mr-1 h-3 w-3" /> : null}
                {s.delta > 0 ? "+" : ""}{s.delta}
              </Badge>
            </div>
          ))}
          {r.skillDeltas.every((s) => s.now === 0) && (
            <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
              No sessions logged this month yet.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Award className="h-5 w-5 text-amber-400" /> Best transition</CardTitle></CardHeader>
          <CardContent>
            {r.bestTransition ? (
              <div className="space-y-2">
                <div className="font-medium">{r.bestTransition.fileName}</div>
                <div className="text-sm text-muted-foreground">Overall {r.bestTransition.scores.overall} · {r.bestTransition.bpm} BPM · {r.bestTransition.key}</div>
                <Button asChild variant="outline" size="sm">
                  <Link to="/app/analyses/$id" params={{ id: r.bestTransition.id }}>Open report <ArrowRight className="ml-1 h-3 w-3" /></Link>
                </Button>
              </div>
            ) : <div className="text-sm text-muted-foreground">No transitions yet.</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Weakest recurring issue</CardTitle></CardHeader>
          <CardContent>
            {r.weakest ? (
              <div className="space-y-2">
                <div className="font-medium">{r.weakest.label}</div>
                <div className="text-sm text-muted-foreground">Avg this month: {r.weakest.value}</div>
                <Button asChild variant="outline" size="sm">
                  <Link to="/app/training">Open drill <ArrowRight className="ml-1 h-3 w-3" /></Link>
                </Button>
              </div>
            ) : <div className="text-sm text-muted-foreground">Not enough data yet.</div>}
          </CardContent>
        </Card>
      </div>

      <NextActionBar
        title="Set the tone for next month — start strong."
        subtitle="Pick up where you left off with a fresh focus session."
        cta="Start Next Month's Goal"
        to="/app/training"
      />
    </div>
  );
}
