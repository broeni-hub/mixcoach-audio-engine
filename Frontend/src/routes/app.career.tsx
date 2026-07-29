import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/store";
import {
  SKILLS, computeSkillStats, CAREER_PATH, computeCareer,
  ACHIEVEMENT_DEFS, computeUnlockedAchievements,
} from "@/lib/progression";
import {
  Trophy, Lock, TrendingUp, TrendingDown, Minus, Sparkles,
  Headphones, Sliders, Activity, Music, Disc3, Zap,
  Check, Flame, Star,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/career")({
  head: () => ({ meta: [{ title: "Career — MixCoach" }] }),
  component: CareerPage,
});

const SKILL_ICONS = {
  beatmatching: Headphones,
  eq: Sliders,
  energy: Activity,
  phrase: Disc3,
  musicality: Music,
  creativity: Zap,
} as const;

const TIER_STYLES = {
  bronze: { ring: "ring-amber-700/40", bg: "from-amber-900/40 to-amber-700/20", icon: "text-amber-400" },
  silver: { ring: "ring-slate-400/40", bg: "from-slate-500/30 to-slate-300/10", icon: "text-slate-200" },
  gold:   { ring: "ring-yellow-400/50", bg: "from-yellow-600/40 to-yellow-300/20", icon: "text-yellow-300" },
} as const;

const LAST_SEEN_KEY = "mixcoach.career.lastSeenStage";

export function CareerPage() {
  const [state] = useAppState();
  const skills = computeSkillStats(state);
  const career = computeCareer(state.profile.xp);
  const unlocked = computeUnlockedAchievements(state);
  const [newlyUnlocked, setNewlyUnlocked] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const lastSeen = Number(localStorage.getItem(LAST_SEEN_KEY) ?? "0");
    if (career.current.index > lastSeen) {
      setNewlyUnlocked(career.current.index);
      localStorage.setItem(LAST_SEEN_KEY, String(career.current.index));
    }
  }, [career.current.index]);

  return (
    <div className="animate-fade-in space-y-10">
      {/* Hero — current stage */}
      <section className="relative overflow-hidden rounded-2xl border border-primary/20 bg-primary/5 p-8">
        <div className="absolute inset-0 bg-[image:var(--gradient-hero)] pointer-events-none" />
        <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-primary/80">
              <Sparkles className="h-3.5 w-3.5" />
              Stage {career.current.index + 1} of {CAREER_PATH.length}
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold">{career.current.title}</h1>
            <p className="text-lg text-foreground/90 max-w-2xl leading-relaxed">{career.current.story}</p>
            {newlyUnlocked === career.current.index && (
              <div className="inline-flex items-center gap-1.5 rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-accent animate-pulse">
                <Star className="h-4 w-4" />
                Newly unlocked
              </div>
            )}
          </div>
          <div className="text-left md:text-right">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Total XP</div>
            <div className="font-display text-4xl font-bold">{state.profile.xp.toLocaleString()}</div>
            {state.profile.streak > 0 && (
              <div className="mt-2 flex items-center gap-1.5 text-sm text-accent md:justify-end">
                <Flame className="h-4 w-4" /> {state.profile.streak}-day streak
              </div>
            )}
          </div>
        </div>

        {career.next ? (
          <div className="relative mt-8">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-muted-foreground">Next: <span className="text-foreground font-medium">{career.next.title}</span></span>
              <span className="text-muted-foreground">{career.xpToNext.toLocaleString()} XP to unlock</span>
            </div>
            <Progress value={career.progress} className="h-2.5" />
            <div className="text-xs text-muted-foreground mt-1.5">{career.xpIntoStage} / {career.xpForStage} XP this stage</div>
          </div>
        ) : (
          <div className="relative mt-8 text-sm text-accent">You reached the final stage. Now keep the legend alive.</div>
        )}
      </section>

      {/* Skill tree */}
      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <h2 className="font-display text-2xl font-bold">Skill tree</h2>
            <p className="text-sm text-muted-foreground">Six core skills. Every analysis levels them up.</p>
          </div>
          <Button asChild variant="ghost" size="sm"><Link to="/app/upload">Run an analysis</Link></Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {skills.map((s) => {
            const Icon = SKILL_ICONS[s.def.key];
            const Trend = s.recentDelta > 1 ? TrendingUp : s.recentDelta < -1 ? TrendingDown : Minus;
            const trendColor = s.recentDelta > 1 ? "text-emerald-400" : s.recentDelta < -1 ? "text-rose-400" : "text-muted-foreground";
            return (
              <Card key={s.def.key} className="glass border-border/60 hover:border-primary/40 transition-colors">
                <CardContent className="p-5 space-y-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-primary/10 ring-1 ring-primary/30 flex items-center justify-center">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold leading-tight">{s.def.title}</h3>
                        <p className="text-xs text-muted-foreground">Lv {s.level} · {s.xp} XP</p>
                      </div>
                    </div>
                    <Badge variant="outline" className={`gap-1 ${trendColor}`}>
                      <Trend className="h-3 w-3" />
                      {s.recentDelta > 0 ? `+${s.recentDelta}` : s.recentDelta}
                    </Badge>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                      <span>Progress</span>
                      <span>{s.xpToNext} XP to Lv {s.level + 1}</span>
                    </div>
                    <Progress value={s.progress} className="h-1.5" />
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-secondary/30 p-2.5">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Avg score</div>
                      <div className="font-display text-xl font-bold">{s.avgScore || "—"}</div>
                    </div>
                    <div className="rounded-lg bg-secondary/30 p-2.5">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Samples</div>
                      <div className="font-display text-xl font-bold">{s.sampleCount}</div>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground border-t border-border/60 pt-3">
                    <div><span className="text-foreground/80 font-medium">Weak spot:</span> {s.weakness}</div>
                    <div className="mt-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <div className="font-medium text-foreground">Next drill · +{s.exercise.xp} XP</div>
                      <div>{s.exercise.title} — {s.exercise.description}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Career story timeline */}
      <section>
        <div className="mb-5">
          <h2 className="font-display text-2xl font-bold">Career path</h2>
          <p className="text-sm text-muted-foreground">From bedroom to legend. Every stage earns its story.</p>
        </div>
        <div className="space-y-4">
          {CAREER_PATH.map((stage) => {
            const reached = state.profile.xp >= stage.xpRequired;
            const isCurrent = stage.index === career.current.index;
            const isFuture = !reached;
            const isNewlyUnlocked = newlyUnlocked === stage.index;

            if (isCurrent) {
              return (
                <Card key={stage.index} className="glass border-primary/40 ring-1 ring-primary/30 bg-primary/5">
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <div className="h-12 w-12 shrink-0 rounded-full bg-[image:var(--gradient-primary)] flex items-center justify-center ring-2 ring-primary/50">
                        <Check className="h-6 w-6 text-primary-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <h3 className="font-display text-2xl font-bold">{stage.title}</h3>
                          <Badge className="bg-primary/20 text-primary border-primary/40">You are here</Badge>
                          {isNewlyUnlocked && (
                            <Badge className="bg-accent/15 text-accent border-accent/30 gap-1">
                              <Star className="h-3 w-3" /> Newly unlocked
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-accent font-medium">{stage.tagline}</p>
                        <p className="mt-3 text-foreground/90 leading-relaxed">{stage.story}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            }

            return (
              <Card
                key={stage.index}
                className={`glass border-border/60 transition-opacity ${isFuture ? "opacity-45" : ""}`}
              >
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    <div className={`h-10 w-10 shrink-0 rounded-full flex items-center justify-center ring-2 ${
                      reached
                        ? "bg-primary/20 ring-primary/40"
                        : "bg-secondary ring-border"
                    }`}>
                      {reached
                        ? <Check className="h-5 w-5 text-primary-foreground" />
                        : <Lock className="h-4 w-4 text-muted-foreground" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className={`font-display text-lg font-bold ${reached ? "" : "text-muted-foreground"}`}>
                          {stage.title}
                        </h3>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {stage.xpRequired.toLocaleString()} XP
                        </span>
                      </div>
                      <p className="text-sm text-accent/80 font-medium">{stage.tagline}</p>
                      <p className={`mt-2 text-sm leading-relaxed ${reached ? "text-foreground/80" : "text-muted-foreground"}`}>
                        {stage.story}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Achievements */}
      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <h2 className="font-display text-2xl font-bold">Achievements</h2>
            <p className="text-sm text-muted-foreground">{unlocked.size} of {ACHIEVEMENT_DEFS.length} unlocked.</p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {ACHIEVEMENT_DEFS.map((a) => {
            const got = unlocked.has(a.id);
            const t = TIER_STYLES[a.tier];
            return (
              <Card key={a.id} className={`glass ${got ? `ring-1 ${t.ring}` : "opacity-55"}`}>
                <CardContent className="p-4">
                  <div
                    className={`mx-auto h-14 w-14 rounded-full flex items-center justify-center bg-gradient-to-br ${
                      got ? t.bg : "from-secondary to-secondary/60"
                    }`}
                  >
                    {got
                      ? <Trophy className={`h-6 w-6 ${t.icon}`} />
                      : <Lock className="h-5 w-5 text-muted-foreground" />}
                  </div>
                  <div className="mt-3 text-center">
                    <div className="font-semibold text-sm">{a.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{a.desc}</div>
                    <div className={`mt-2 text-[10px] uppercase tracking-widest ${got ? t.icon : "text-muted-foreground"}`}>
                      {a.tier}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <NextActionBar
        title="One step closer to your next stage."
        subtitle="Train the skills holding you back to level up the timeline."
        cta="Unlock Next Stage"
        to="/app/training"
      />
    </div>
  );
}
