import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Flame, Snowflake, Trophy, Calendar, ArrowRight } from "lucide-react";
import { useAppState } from "@/lib/store";
import { computeStreak } from "@/lib/retention";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/streak")({
  head: () => ({ meta: [{ title: "Streak — MixCoach" }] }),
  component: StreakPage,
});

function StreakPage() {
  const [state] = useAppState();
  const s = computeStreak(state);
  const progress = Math.min(100, Math.round((s.current / s.nextReward.at) * 100));

  return (
    <div className="container mx-auto max-w-5xl space-y-6 py-6">
      <div className="space-y-1">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">Retention</div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Your training streak</h1>
        <p className="text-muted-foreground">Train at least once a day to keep momentum.</p>
      </div>

      <Card className="border-primary/30 bg-[image:var(--gradient-primary)]/10">
        <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-2xl bg-background/40 p-4">
              <Flame className="h-10 w-10 text-orange-400" />
            </div>
            <div>
              <div className="font-display text-4xl font-bold">{s.current} days</div>
              <div className="text-sm text-muted-foreground">
                Longest: {s.longest} · {s.trainedToday ? "Today done ✓" : "Train today to extend"}
              </div>
            </div>
          </div>
          <Button asChild className="bg-[image:var(--gradient-primary)] border-0 glow-purple">
            <Link to="/app/upload">Train now <ArrowRight className="ml-1 h-4 w-4" /></Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Trained this week</CardTitle></CardHeader>
          <CardContent><div className="font-display text-3xl font-bold">{s.trainedThisWeek}<span className="text-base text-muted-foreground"> / 7</span></div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Missed this week</CardTitle></CardHeader>
          <CardContent><div className="font-display text-3xl font-bold">{s.missedThisWeek}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Streak freezes</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Snowflake className="h-6 w-6 text-blue-400" />
              <div className="font-display text-3xl font-bold">{s.freezesAvailable}</div>
              <Badge variant="outline" className="ml-auto">Premium soon</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5" /> This week</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-7 gap-2">
            {s.weekDays.map((d, i) => (
              <div key={i} className={`flex flex-col items-center gap-2 rounded-lg border p-3 text-center ${d.isToday ? "border-primary" : "border-border"}`}>
                <div className="text-xs text-muted-foreground">{d.label}</div>
                <div className={`flex h-9 w-9 items-center justify-center rounded-full ${d.trained ? "bg-[image:var(--gradient-primary)] text-white glow-purple" : "bg-muted text-muted-foreground"}`}>
                  {d.trained ? <Flame className="h-4 w-4" /> : "·"}
                </div>
                <div className="text-[10px] text-muted-foreground">{d.date.getDate()}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Trophy className="h-5 w-5 text-amber-400" /> Next reward</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Reach {s.nextReward.at} days for <span className="font-medium text-foreground">{s.nextReward.label}</span></span>
            <span className="text-muted-foreground">+{s.nextReward.xp} XP</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-[image:var(--gradient-primary)]" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-muted-foreground">{s.current} / {s.nextReward.at} days</div>
        </CardContent>
      </Card>

      <NextActionBar
        title="Don't break the chain — train today."
        subtitle="A single drill keeps your streak alive and your momentum building."
        cta="Train Today"
        to="/app/training"
      />
    </div>
  );
}
