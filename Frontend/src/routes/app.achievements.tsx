import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { useAppState, ACHIEVEMENTS, computeAchievements } from "@/lib/store";
import { Trophy, Lock } from "lucide-react";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/achievements")({
  head: () => ({ meta: [{ title: "Achievements — MixCoach" }] }),
  component: Achievements,
});

export function Achievements() {
  const [state] = useAppState();
  const unlocked = computeAchievements(state);

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold">Achievements</h1>
        <p className="text-muted-foreground mt-1">{unlocked.length} / {ACHIEVEMENTS.length} unlocked</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ACHIEVEMENTS.map((a) => {
          const got = unlocked.includes(a.id);
          return (
            <Card key={a.id} className={`glass ${got ? "glow-purple border-primary/40" : "opacity-60"}`}>
              <CardContent className="p-5 flex items-start gap-4">
                <div className={`h-12 w-12 rounded-xl flex items-center justify-center shrink-0 ${got ? "bg-[image:var(--gradient-primary)]" : "bg-secondary"}`}>
                  {got ? <Trophy className="h-5 w-5 text-white" /> : <Lock className="h-5 w-5 text-muted-foreground" />}
                </div>
                <div>
                  <h3 className="font-semibold">{a.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{a.desc}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <NextActionBar
        title="One more session puts a new badge in reach."
        subtitle="Most badges unlock through consistent practice — not perfect mixes."
        cta="Earn Next Badge"
        to="/app/training"
      />
    </div>
  );
}
