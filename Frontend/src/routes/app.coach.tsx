import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/store";
import { buildCoachInsight, weeklyPlan, EXERCISE_LIBRARY, type CoachExercise } from "@/lib/coach";
import { CoachInsight, ExerciseCard } from "@/components/CoachInsight";
import { CoachProfilePanel } from "@/components/CoachProfilePanel";
import {
  Calendar, Headphones, Disc, Music2, Sparkles, ChevronRight, CheckCircle2,
} from "lucide-react";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/coach")({
  head: () => ({ meta: [{ title: "Coach — MixCoach" }] }),
  component: CoachPage,
});

function CoachPage() {
  const [state] = useAppState();
  const bundle = buildCoachInsight(state);
  const plan = weeklyPlan(state);
  const todayIdx = ((new Date().getDay() + 6) % 7); // Mon=0
  const [activeDay, setActiveDay] = useState(todayIdx);
  const [startedIds, setStartedIds] = useState<Set<string>>(new Set());

  const activeExercise: CoachExercise = plan[activeDay].exercise;

  const start = (ex: CoachExercise) => {
    setStartedIds((s) => new Set(s).add(ex.id));
  };

  return (
    <div className="animate-fade-in space-y-8">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-primary flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> Your Personal Coach
          </div>
          <h1 className="font-display text-4xl font-bold mt-1">{bundle.greeting}.</h1>
          <p className="text-muted-foreground mt-1">Honest reads. Specific drills. Built around your gear and your genre.</p>
        </div>
        <ContextChips bundle={bundle} />
      </header>

      {/* Echte Engine-Diagnosen zuerst: Trends, Muster und Uebungen aus den
          EIGENEN Sets (GET /coach/profile). Rendert nichts, wenn das Backend
          nicht erreichbar ist oder noch keine Sets analysiert sind - dann
          bleiben nur die lokalen Heuristiken darunter (Ehrlichkeits-Regel:
          keine Engine-Diagnosen behaupten, die es nicht gibt). */}
      <CoachProfilePanel />

      {/* Weekly insight */}
      <CoachInsight bundle={bundle} />

      {/* Weekly training plan */}
      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <h2 className="font-display text-2xl font-bold flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" /> This week's plan
            </h2>
            <p className="text-sm text-muted-foreground">Tap a day to load the drill.</p>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-2 mb-5">
          {plan.map((d, idx) => {
            const isActive = idx === activeDay;
            const isToday = idx === todayIdx;
            const done = startedIds.has(d.exercise.id);
            return (
              <button
                key={d.day}
                onClick={() => setActiveDay(idx)}
                className={`relative rounded-xl border p-3 text-left transition-all ${
                  isActive
                    ? "border-primary bg-primary/10 glow-purple"
                    : "border-border/60 hover:border-primary/40 bg-secondary/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs uppercase tracking-widest ${isActive ? "text-primary" : "text-muted-foreground"}`}>
                    {d.day}
                  </span>
                  {isToday && <Badge className="bg-accent/20 text-accent border-accent/40 text-[10px] px-1.5 py-0">Today</Badge>}
                </div>
                <div className="mt-2 text-sm font-semibold leading-tight line-clamp-2">{d.exercise.name}</div>
                <div className="mt-1.5 text-[10px] text-muted-foreground">+{d.exercise.xp} XP · {d.exercise.durationMin}m</div>
                {done && (
                  <CheckCircle2 className="absolute top-2 right-2 h-3.5 w-3.5 text-emerald-400" />
                )}
              </button>
            );
          })}
        </div>

        {/* Active day rationale */}
        <Card className="glass border-primary/20 mb-4">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">{plan[activeDay].fullDay} — why this drill: </span>
              <span className="text-foreground">{plan[activeDay].rationale}</span>
            </div>
          </CardContent>
        </Card>

        <ExerciseCard
          exercise={activeExercise}
          eyebrow={`${plan[activeDay].fullDay} · ${activeExercise.targetSkillTitle}`}
          onStart={() => start(activeExercise)}
        />
      </section>

      {/* Exercise library */}
      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <h2 className="font-display text-2xl font-bold">Full exercise library</h2>
            <p className="text-sm text-muted-foreground">All {EXERCISE_LIBRARY.length} drills the coach can prescribe.</p>
          </div>
          <Button asChild variant="ghost" size="sm" className="gap-1">
            <Link to="/app/training">Open training <ChevronRight className="h-4 w-4" /></Link>
          </Button>
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {EXERCISE_LIBRARY.map((ex) => (
            <Card key={ex.id} className="glass hover:border-primary/40 transition-colors">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold leading-tight">{ex.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{ex.targetSkillTitle}</div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">{ex.difficulty}</Badge>
                </div>
                <div className="flex gap-2 text-[11px] text-muted-foreground">
                  <span>+{ex.xp} XP</span><span>·</span><span>{ex.durationMin}m</span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => { setActiveDay(plan.findIndex((p) => p.exercise.id === ex.id) >= 0 ? plan.findIndex((p) => p.exercise.id === ex.id) : activeDay); start(ex); }}>
                    Start
                  </Button>
                  <Button asChild size="sm" variant="ghost">
                    <Link to="/app/upload">Upload</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <NextActionBar
        title="Your plan is set — let's run the first drill."
        subtitle="One session today keeps your coach calibrated to your real progress."
        cta="Start This Plan"
        to="/app/training"
      />
    </div>
  );
}

function ContextChips({ bundle }: { bundle: ReturnType<typeof buildCoachInsight> }) {
  const { context } = bundle;
  return (
    <div className="flex flex-wrap gap-1.5 max-w-md justify-end">
      <Badge variant="outline" className="gap-1"><Disc className="h-3 w-3" />{context.experience}</Badge>
      {context.genres.slice(0, 2).map((g) => (
        <Badge key={g} variant="outline" className="gap-1"><Music2 className="h-3 w-3" />{g}</Badge>
      ))}
      {context.equipment.slice(0, 1).map((e) => (
        <Badge key={e} variant="outline" className="gap-1"><Headphones className="h-3 w-3" />{e}</Badge>
      ))}
      <Badge variant="outline">{context.analysisCount} analyses</Badge>
      {context.streak > 0 && <Badge className="bg-accent/20 text-accent border-accent/40">{context.streak}d streak</Badge>}
    </div>
  );
}
