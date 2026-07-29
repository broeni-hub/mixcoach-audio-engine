import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAppState } from "@/lib/store";
import {
  Dumbbell, Check, Flame, Target, Play, Clock, Zap, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { useMemo } from "react";
import { buildCoachInsight, EXERCISE_LIBRARY, type CoachExercise } from "@/lib/coach";
import { computeSkillStats } from "@/lib/progression";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/training")({
  head: () => ({ meta: [{ title: "Training — MixCoach" }] }),
  component: Training,
});

function todaysMission(state: ReturnType<typeof useAppState>[0]) {
  const skills = computeSkillStats(state);
  const weak = [...skills].sort((a, b) => a.avgScore - b.avgScore)[0] ?? null;
  const insight = buildCoachInsight(state);
  return {
    exercise: insight.recommendedTraining.exercise,
    reason: weak?.sampleCount
      ? `${weak.def.title} is your weakest skill at ${weak.avgScore}/100. This exercise targets it directly.`
      : "This exercise builds the foundation every other skill depends on.",
  };
}

function moreChallenges(todayId: string, count = 3): CoachExercise[] {
  return EXERCISE_LIBRARY
    .filter((e) => e.id !== todayId)
    .slice(0, count);
}

export default function Training() {
  const [state, update] = useAppState();
  const { exercise: mission, reason } = useMemo(() => todaysMission(state), [state]);
  const extras = useMemo(() => moreChallenges(mission.id), [mission.id]);

  const complete = (id: string, xp: number) => {
    if (state.completedChallenges.includes(id)) return;
    update((s) => ({
      ...s,
      completedChallenges: [...s.completedChallenges, id],
      profile: { ...s.profile, xp: s.profile.xp + xp },
    }));
    toast.success(`+${xp} XP earned`);
  };

  const missionDone = state.completedChallenges.includes(mission.id);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Training</h1>
          <p className="text-muted-foreground mt-1">One mission. Three options. No noise.</p>
        </div>
        <Badge variant="secondary" className="text-sm">
          <Flame className="h-3 w-3 mr-1 text-primary" />
          {state.profile.streak}-day streak
        </Badge>
      </div>

      {/* SECTION 1 — TODAY'S MISSION */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="h-8 w-8 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
            <Target className="h-4 w-4 text-primary" />
          </span>
          <p className="eyebrow">Today's mission</p>
        </div>

        <Card className="glass relative overflow-hidden border-primary/40">
          <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[image:var(--gradient-primary)] opacity-15 blur-3xl" />
          <CardContent className="relative p-7 md:p-9 space-y-5">
            <div className="space-y-2">
              <h2 className="font-display text-2xl md:text-3xl font-bold leading-tight">
                {mission.name}
              </h2>
              <p className="text-sm text-foreground/80 leading-relaxed max-w-2xl">
                <span className="text-muted-foreground">Recommended because: </span>
                {reason}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge className="gap-1.5 py-1.5 px-3 bg-primary/15 text-primary border-primary/30">
                <Zap className="h-3.5 w-3.5" /> +{mission.xp} XP
              </Badge>
              <Badge variant="outline" className="gap-1.5 py-1.5 px-3">
                <Clock className="h-3.5 w-3.5" /> {mission.durationMin} min
              </Badge>
              <Badge variant="outline" className="py-1.5 px-3">
                {mission.difficulty}
              </Badge>
              <Badge variant="outline" className="py-1.5 px-3">
                {mission.targetSkillTitle}
              </Badge>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                size="lg"
                className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90 h-12 px-6 text-base"
                disabled={missionDone}
                onClick={() => complete(mission.id, mission.xp)}
              >
                {missionDone ? (
                  <><Check className="h-4 w-4" /> Completed</>
                ) : (
                  <><Play className="h-4 w-4" /> Start Exercise</>
                )}
              </Button>
              <Button asChild size="lg" variant="outline" className="h-12 px-6 text-base">
                <Link to="/app/upload">
                  Upload for this <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* SECTION 2 — MORE CHALLENGES (max 3) */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="h-8 w-8 rounded-lg bg-secondary border border-border flex items-center justify-center">
            <Dumbbell className="h-4 w-4 text-accent" />
          </span>
          <div>
            <p className="eyebrow">More challenges</p>
            <p className="text-xs text-muted-foreground">Pick one if you want variety.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {extras.map((exercise) => {
            const done = state.completedChallenges.includes(exercise.id);
            return (
              <Card key={exercise.id} className="glass flex flex-col">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-base leading-tight">{exercise.name}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col gap-4 pt-0">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                      {exercise.targetSkillTitle}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                      {exercise.difficulty}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] uppercase tracking-wide gap-1">
                      <Clock className="h-3 w-3" /> {exercise.durationMin}m
                    </Badge>
                    <Badge variant="outline" className="text-[10px] uppercase tracking-wide gap-1">
                      <Zap className="h-3 w-3" /> +{exercise.xp} XP
                    </Badge>
                  </div>

                  <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                    {exercise.instructions[0]}
                  </p>

                  <Button
                    className={`w-full ${done ? "" : "bg-[image:var(--gradient-primary)] border-0 hover:opacity-90"}`}
                    variant={done ? "outline" : "default"}
                    disabled={done}
                    onClick={() => complete(exercise.id, exercise.xp)}
                  >
                    {done ? (
                      <><Check className="h-4 w-4" /> Completed</>
                    ) : (
                      <><Play className="h-4 w-4" /> Start Exercise</>
                    )}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <NextActionBar
        title="Record yourself trying today's drill."
        subtitle="Upload the take and I'll tell you exactly what to fix."
        cta="Record this Drill"
        to="/app/upload"
      />
    </div>
  );
}
