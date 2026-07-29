import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/store";
import {
  Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip,
  BarChart, Bar, CartesianGrid,
} from "recharts";
import { TrendingUp, TrendingDown, ArrowRight, Music, Target, Zap } from "lucide-react";
import { NextActionBar } from "@/components/NextActionBar";
import { CoachProfilePanel } from "@/components/CoachProfilePanel";
import { CalibrationProgress } from "@/components/CalibrationProgress";

export const Route = createFileRoute("/app/progress")({
  head: () => ({ meta: [{ title: "Progress — MixCoach" }] }),
  component: ProgressPage,
});

const SKILL_LABELS: Record<string, string> = {
  beatmatching: "Your timing",
  eq: "Clean mixing",
  timing: "Transition flow",
  creativity: "Your signature",
  flow: "Crowd momentum",
  musicality: "Track pairing",
};

function ProgressPage() {
  const [state] = useAppState();
  const analyses = state.analyses.slice().sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());

  const hasEnough = analyses.length >= 2;
  const split = Math.max(1, Math.floor(analyses.length / 2));
  const firstHalf = analyses.slice(0, split);
  const secondHalf = analyses.slice(split);

  const measured = (xs: (number | null)[]) => xs.filter((v): v is number => v != null);
  const previousAvg = hasEnough ? avg(measured(firstHalf.map((a) => a.scores.overall))) : 0;
  const currentAvg = hasEnough ? avg(measured(secondHalf.map((a) => a.scores.overall))) : avg(measured(analyses.map((a) => a.scores.overall)));
  const avgDelta = currentAvg - previousAvg;

  const skills = ["beatmatching", "eq", "timing", "creativity", "flow", "musicality"] as const;
  const skillChanges = skills.map((key) => {
    const prev = hasEnough ? avg(measured(firstHalf.map((a) => a.scores[key]))) : 0;
    const cur = hasEnough ? avg(measured(secondHalf.map((a) => a.scores[key]))) : avg(measured(analyses.map((a) => a.scores[key])));
    return { key, label: SKILL_LABELS[key], prev, cur, delta: cur - prev };
  });

  const biggestImprovement = skillChanges.reduce((best, s) => (s.delta > best.delta ? s : best), skillChanges[0]);
  const holdingBack = skillChanges.reduce((worst, s) => (s.cur < worst.cur ? s : worst), skillChanges[0]);

  // weekly trend for chart
  const weeks: { week: string; count: number; avg: number }[] = [];
  for (let i = 7; i >= 0; i--) {
    const start = Date.now() - (i + 1) * 7 * 86400_000;
    const end = Date.now() - i * 7 * 86400_000;
    const items = analyses.filter((a) => {
      const t = new Date(a.createdAt).getTime();
      return t >= start && t < end;
    });
    weeks.push({
      week: `W-${i}`,
      count: items.length,
      avg: items.length ? Math.round(items.reduce((s, a) => s + (a.scores.overall ?? 0), 0) / items.length) : 0,
    });
  }

  const skillDist = skillChanges.map((s) => ({ name: s.label, value: s.cur }));

  return (
    <div className="space-y-8 animate-fade-in">
      <CalibrationProgress />
      <CoachProfilePanel />
      <div className="space-y-1">
        <h1 className="font-display text-4xl font-bold tracking-tight">You are improving.</h1>
        <p className="text-muted-foreground text-lg">Your mixes are getting better. Here is the proof.</p>
      </div>

      {!hasEnough ? (
        <Card className="glass p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Music className="h-6 w-6 text-primary" />
          </div>
          <h2 className="font-display text-xl font-semibold">Upload a few more transitions</h2>
          <p className="text-muted-foreground mt-2 max-w-md mx-auto">
            We need at least two analyses to show your progress. Keep uploading and your numbers will appear here.
          </p>
          <Button className="mt-6" asChild>
            <a href="/app/upload">Upload transition</a>
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="glass relative overflow-hidden">
              <CardContent className="p-6">
                <div className="text-muted-foreground text-sm font-medium uppercase tracking-wide">Average score</div>
                <div className="mt-3 flex items-baseline gap-3">
                  <span className="font-display text-4xl font-bold text-muted-foreground">{previousAvg}</span>
                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  <span className="font-display text-5xl font-bold">{currentAvg}</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1 text-sm font-medium text-accent">
                  <TrendingUp className="h-4 w-4" />
                  +{avgDelta} points
                </div>
                <p className="text-muted-foreground mt-3 text-sm">Your mixes are sounding more confident than they used to.</p>
              </CardContent>
            </Card>

            <Card className="glass relative overflow-hidden">
              <CardContent className="p-6">
                <div className="text-muted-foreground text-sm font-medium uppercase tracking-wide">Biggest improvement</div>
                <div className="mt-3 font-display text-3xl font-bold">{biggestImprovement.label}</div>
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-sm font-medium text-emerald-400">
                  <TrendingUp className="h-4 w-4" />
                  +{biggestImprovement.delta}%
                </div>
                <p className="text-muted-foreground mt-3 text-sm">This is where your practice is paying off the most.</p>
              </CardContent>
            </Card>

            <Card className="glass relative overflow-hidden">
              <CardContent className="p-6">
                <div className="text-muted-foreground text-sm font-medium uppercase tracking-wide">Still holding you back</div>
                <div className="mt-3 font-display text-3xl font-bold">{holdingBack.label}</div>
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-sm font-medium text-amber-400">
                  <Target className="h-4 w-4" />
                  Score {holdingBack.cur}%
                </div>
                <p className="text-muted-foreground mt-3 text-sm">Put your attention here next and the rest of your sets lift with it.</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="glass">
              <div className="p-5 border-b border-border">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-primary" />
                  <h3 className="font-display text-lg font-semibold">How your mixing is trending</h3>
                </div>
                <p className="text-muted-foreground text-sm mt-1">How your sets have sounded across the last 8 weeks.</p>
              </div>
              <CardContent className="h-72 pt-5">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weeks}>
                    <defs>
                      <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="oklch(0.50 0.08 255)" stopOpacity={0.6} />
                        <stop offset="100%" stopColor="oklch(0.50 0.08 255)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                    <XAxis dataKey="week" tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <YAxis tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.014 270)", border: "1px solid oklch(0.28 0.018 270)", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="avg" stroke="oklch(0.50 0.08 255)" fill="url(#ga)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="glass">
              <div className="p-5 border-b border-border">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <h3 className="font-display text-lg font-semibold">Where you stand right now</h3>
                </div>
                <p className="text-muted-foreground text-sm mt-1">A snapshot of the six things that make a DJ feel complete.</p>
              </div>
              <CardContent className="h-72 pt-5">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={skillDist} layout="vertical">
                    <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} domain={[0, 100]} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 11 }} width={100} />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.014 270)", border: "1px solid oklch(0.28 0.018 270)", borderRadius: 8 }} />
                    <Bar dataKey="value" fill="oklch(0.78 0.10 85)" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <NextActionBar
        title="Keep the momentum — one more session this week."
        subtitle="The next drill targets your weakest area first."
        cta="Continue Improving"
        to="/app/training"
      />
    </div>
  );
}

function avg(arr: number[]) {
  if (!arr.length) return 0;
  return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
}
