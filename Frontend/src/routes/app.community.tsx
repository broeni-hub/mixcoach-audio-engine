import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lock, Users, Trophy, Sparkles } from "lucide-react";
import { COMMUNITY_CHALLENGES } from "@/lib/retention";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/community")({
  head: () => ({ meta: [{ title: "Community — MixCoach" }] }),
  component: CommunityPage,
});

export function CommunityPage() {
  return (
    <div className="container mx-auto max-w-5xl space-y-6 py-6">
      <div className="space-y-1">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">Coming soon</div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Community challenges</h1>
        <p className="text-muted-foreground">Weekly drills, leaderboards, and signature badges.</p>
      </div>

      <Card className="border-primary/30 bg-[image:var(--gradient-primary)]/10">
        <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Users className="h-8 w-8 text-primary" />
            <div>
              <div className="font-display text-xl font-semibold">Train with other DJs</div>
              <div className="text-sm text-muted-foreground">Compete in weekly themed challenges and earn signature badges judged by the community.</div>
            </div>
          </div>
          <Badge variant="outline" className="border-primary/40 text-primary">Premium</Badge>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {COMMUNITY_CHALLENGES.map((c) => (
          <Card key={c.id} className="relative overflow-hidden">
            <div className="absolute inset-0 bg-background/40 backdrop-blur-[2px]" />
            <CardHeader className="relative">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-amber-400" /> {c.title}
                </CardTitle>
                {c.premium ? (
                  <Badge variant="outline" className="border-primary/40 text-primary"><Lock className="mr-1 h-3 w-3" /> Premium</Badge>
                ) : (
                  <Badge variant="outline"><Lock className="mr-1 h-3 w-3" /> Soon</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="relative space-y-3">
              <p className="text-sm text-muted-foreground">{c.description}</p>
              <div className="flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1 text-muted-foreground"><Sparkles className="h-3 w-3" /> Badge: <span className="text-foreground">{c.badge}</span></span>
                <span className="text-muted-foreground">{c.eta}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <NextActionBar
        title="Practice now so you're ready when the challenge drops."
        subtitle="Sharpen the skill behind this month's brief with one focused drill."
        cta="Train for the Next Challenge"
        to="/app/training"
      />
    </div>
  );
}
