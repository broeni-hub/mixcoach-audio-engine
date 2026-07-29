import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useAppState, levelFromXp } from "@/lib/store";
import {
  Upload, Flame, Sparkles, ArrowRight, Target, Dumbbell,
  Headphones, TrendingUp, Trophy, Calendar, Zap, Music2, Clock,
} from "lucide-react";
import type { AnalysisResult, AnalysisScores } from "@/lib/analysis";
import { CelebrationModal } from "@/components/CelebrationModal";
import { CoachLines, CoachActions } from "@/components/CoachInsight";
import { NextActionBar } from "@/components/NextActionBar";
import { fetchCoachProfile, type CoachExercise } from "@/lib/coach-profile";
import { useLang } from "@/lib/i18n";

export const Route = createFileRoute("/app/dashboard")({
  head: () => ({ meta: [{ title: "Today's Training — MixCoach" }] }),
  component: Dashboard,
});

const SKILLS: { key: keyof AnalysisScores; label: string; icon: typeof Headphones }[] = [
  { key: "beatmatching", label: "Your Timing",      icon: Music2 },
  { key: "eq",           label: "Clean Mixing",     icon: Headphones },
  { key: "timing",       label: "Transition Flow",  icon: Calendar },
  { key: "flow",         label: "Crowd Momentum",   icon: Zap },
  { key: "musicality",   label: "Track Pairing",    icon: Sparkles },
  { key: "creativity",   label: "Your Signature",   icon: Trophy },
];

function Dashboard() {
  const [state] = useAppState();
  const lvl = levelFromXp(state.profile.xp);
  const analyses = state.analyses;
  const last = analyses[0];

  const skillAverages = useMemo(() => computeSkills(analyses), [analyses]);
  const recent = useMemo(() => computeSkills(analyses.slice(0, 3)), [analyses]);
  const older = useMemo(() => computeSkills(analyses.slice(3, 8)), [analyses]);

  const weakness = useMemo(() => {
    if (!skillAverages.length) return null;
    return [...skillAverages].sort((a, b) => a.value - b.value)[0];
  }, [skillAverages]);

  const mostImproved = useMemo(() => {
    if (!recent.length || !older.length) return null;
    const deltas = SKILLS.map((s) => {
      const r = recent.find((x) => x.key === s.key)?.value ?? 0;
      const o = older.find((x) => x.key === s.key)?.value ?? 0;
      return { ...s, delta: r - o };
    }).sort((a, b) => b.delta - a.delta);
    return deltas[0]?.delta > 1 ? deltas[0] : null;
  }, [recent, older]);

  const lang = useLang();
  const [coachEx, setCoachEx] = useState<CoachExercise | null>(null);
  useEffect(() => {
    fetchCoachProfile(lang).then((prof) => {
      setCoachEx(prof?.exercises?.[0] ?? null);
    });
  }, [lang]);

  const mission = pickTodaysDrill(last, weakness?.label);
  const missionReason = buildMissionReason({ mostImproved, weakness, mission });
  const coachInsight = buildCoachInsight({ last, mostImproved, weakness });

  const [celebration, setCelebration] = useState<null | {
    kind: "level-up" | "achievement"; title: string; subtitle?: string; description?: string;
  }>(null);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const lvlKey = "mixcoach.lastSeenLevel";
    const achKey = "mixcoach.lastSeenAchievements";
    // Level-Up-Overlay ("Welcome to ...") bewusst entfernt - Nutzerwunsch:
    // kein Popup beim Start. Der Levelstand bleibt gespeichert.
    localStorage.setItem(lvlKey, lvl.name);

    const seenAch = JSON.parse(localStorage.getItem(achKey) ?? "[]") as string[];
    const fresh = state.achievements.filter((a) => !seenAch.includes(a));
    if (fresh.length && !celebration) {
      setCelebration({
        kind: "achievement",
        title: fresh[0],
        subtitle: fresh.length > 1 ? `+${fresh.length - 1} more unlocked` : undefined,
        description: "Keep training to unlock the next tier.",
      });
    }
    localStorage.setItem(achKey, JSON.stringify(state.achievements));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lvl.name, state.profile.xp, state.achievements.join(",")]);

  return (
    <div className="space-y-8 animate-fade-in">
      <CelebrationModal
        open={!!celebration}
        onOpenChange={(v) => !v && setCelebration(null)}
        kind={celebration?.kind ?? "level-up"}
        title={celebration?.title ?? ""}
        subtitle={celebration?.subtitle}
        description={celebration?.description}
      />

      {/* Greeting */}
      <div>
        <p className="eyebrow text-xs text-accent">{greeting()}, {state.profile.name}</p>
        <h1 className="font-display text-2xl font-bold mt-1 text-muted-foreground">
          Here's what you should do <span className="text-foreground">today</span>.
        </h1>
      </div>

      {/* SECTION 1 — TODAY'S MISSION (Hero) */}
      <Card className="glass relative overflow-hidden border-primary/40">
        <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-[image:var(--gradient-primary)] opacity-20 blur-3xl" />
        <CardContent className="relative p-8 md:p-10 space-y-6">
          <div className="flex items-center gap-2">
            <span className="h-9 w-9 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
              <Target className="h-4 w-4 text-primary" />
            </span>
            <p className="eyebrow text-xs text-primary">Today's mission</p>
          </div>

          <div className="space-y-3">
            <h2 className="font-display text-3xl md:text-4xl font-bold leading-tight">
              {coachEx?.title ?? mission.title}
            </h2>
            <p className="text-base text-foreground/80 max-w-2xl">
              <span className="text-muted-foreground">Why this matters: </span>
              {coachEx?.description ?? mission.why}
            </p>
          </div>

          {!coachEx && (
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="gap-1.5 py-1.5 px-3">
                <Clock className="h-3.5 w-3.5" /> ~{mission.minutes} min
              </Badge>
              <Badge variant="outline" className="gap-1.5 py-1.5 px-3">
                Focus: {mission.focus}
              </Badge>
            </div>
          )}

          <div className="pt-2">
            <Button asChild size="lg" className="bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90 h-12 px-6 text-base">
              {coachEx ? (
                <Link
                  to="/app/analyses/$id"
                  params={{ id: coachEx.analysisId }}
                  search={{ listen: coachEx.startSec ?? coachEx.midSec ?? undefined }}
                >
                  <Headphones className="h-4 w-4" /> {lang === "de" ? "Stelle anhören & üben" : "Listen & practice"}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <Link to="/app/upload">
                  <Upload className="h-4 w-4" /> Start training
                  <ArrowRight className="h-4 w-4" />
                </Link>
              )}
            </Button>
          </div>

          <div className="flex items-start gap-2.5 pt-3 border-t border-border/60">
            <Sparkles className="h-4 w-4 text-accent mt-0.5 shrink-0" />
            <p className="text-sm text-foreground/85 italic leading-relaxed">
              {missionReason}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 2 — COACH INSIGHT (3-line mentor card) */}
      <Card className="glass border-accent/30">
        <CardContent className="p-6 space-y-5">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-accent">
            <Headphones className="h-3.5 w-3.5" /> Coach
          </div>
          <CoachLines
            improved={coachInsight.improved}
            issue={coachInsight.issue}
            next={coachInsight.next}
          />
          <CoachActions analysisId={last?.id} />
        </CardContent>
      </Card>

      {/* SECTION 3 — PROGRESS SNAPSHOT */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="glass">
          <CardContent className="p-5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Level</p>
            <p className="font-display text-2xl font-bold mt-1">{lvl.name}</p>
            <p className="text-xs text-muted-foreground mt-1 font-mono">Tier {lvl.index + 1}</p>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">XP progress</p>
            <p className="font-display text-2xl font-bold mt-1 font-mono">
              {state.profile.xp}<span className="text-base text-muted-foreground"> / {lvl.next}</span>
            </p>
            <Progress value={lvl.progress} className="mt-2 h-1.5" />
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current streak</p>
            <div className="flex items-baseline gap-2 mt-1">
              <p className="font-display text-2xl font-bold">{state.profile.streak}</p>
              <Flame className="h-5 w-5 text-primary" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">days in a row</p>
          </CardContent>
        </Card>
      </div>

      {/* SECTION 4 — LATEST ANALYSIS (compact) */}
      <Card className="glass">
        <CardContent className="p-5">
          {last ? (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3 min-w-0">
                <Music2 className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Latest analysis</p>
                  <p className="text-sm font-medium truncate">{last.fileName}</p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {last.bpm ?? "—"} BPM • {last.key ?? "—"} • {last.scores.overall ?? "—"}/100
                  </p>
                </div>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to="/app/analyses/$id" params={{ id: last.id }}>
                  Open report <ArrowRight className="h-3 w-3" />
                </Link>
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No analyses yet — your first upload starts the coaching loop.</p>
          )}
        </CardContent>
      </Card>

      {/* Everything else — moved further down, collapsed footer area */}
      <div className="pt-4 border-t border-border/40">
        <div className="flex items-center justify-between mb-3">
          <p className="eyebrow text-xs text-muted-foreground">More</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <FooterLink to="/app/training" icon={Dumbbell} title="Training plan" desc="All drills & weekly schedule" />
          <FooterLink to="/app/progress" icon={TrendingUp} title="Skill tree" desc="Full progression breakdown" />
          <FooterLink to="/app/analyses" icon={Music2} title="All analyses" desc="History & comparisons" />
          <FooterLink to="/app/coach" icon={Sparkles} title="Coach" desc="Weekly plan & insights" />
        </div>
      </div>

      <NextActionBar
        title="Today's mission is ready when you are."
        subtitle="One focused drill keeps your streak alive and moves you forward."
        cta="Start Today's Training"
        to="/app/training"
      />
    </div>
  );
}

function FooterLink({ to, icon: Icon, title, desc }: { to: string; icon: typeof Headphones; title: string; desc: string }) {
  return (
    <Link to={to} className="group rounded-xl border border-border bg-card/30 p-4 hover:border-primary/40 hover:bg-card/60 transition-colors">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
        <span className="text-sm font-medium">{title}</span>
      </div>
      <p className="text-xs text-muted-foreground mt-1">{desc}</p>
    </Link>
  );
}

function computeSkills(list: AnalysisResult[]) {
  if (!list.length) return [] as { key: keyof AnalysisScores; label: string; value: number }[];
  return SKILLS.map((s) => {
    // Nur echte Messwerte mitteln - null (nicht gemessen) verzerrt sonst den Schnitt.
    const vals = list.map((a) => a.scores[s.key]).filter((v): v is number => v != null);
    const avg = vals.length ? Math.round(vals.reduce((acc, v) => acc + v, 0) / vals.length) : 0;
    return { key: s.key, label: s.label, value: avg };
  });
}

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Late night session";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function buildMissionReason({
  mostImproved, weakness, mission,
}: {
  mostImproved: { label: string; delta: number } | null;
  weakness: { label: string; value: number } | null;
  mission: ReturnType<typeof pickTodaysDrill>;
}) {
  if (mostImproved && weakness) {
    return `Your ${mostImproved.label} improved significantly. Today's mission focuses on ${weakness.label} because this is currently your biggest limitation.`;
  }
  if (weakness) {
    return `${weakness.label} is your weakest skill right now — this drill targets it directly so the next jump comes fast.`;
  }
  return `${mission.focus} is the fastest skill to build early. Knock this out and your next analysis will show it.`;
}

function buildCoachInsight({
  last, mostImproved, weakness,
}: {
  last?: AnalysisResult;
  mostImproved: { label: string; delta: number } | null;
  weakness: { label: string; value: number } | null;
}): { improved: string; issue: string; next: string } {
  if (!last) {
    return {
      improved: "You showed up — that's the entire first rep.",
      issue: "No data yet, so nothing to fix.",
      next: "Upload one transition. I'll map the fastest win.",
    };
  }
  const improved = mostImproved
    ? `${mostImproved.label} is up ${mostImproved.delta} points.`
    : `Consistent at ${last.scores.overall ?? "—"}/100 — you're not slipping.`;
  const issue = weakness
    ? `${weakness.label} is your ceiling at ${weakness.value}/100.`
    : `Nothing critical — push a harder mix to find the next limit.`;
  const next = weakness
    ? `Two focused sessions on ${weakness.label} this week.`
    : `Lock in your strengths with one challenge mix.`;
  return { improved, issue, next };
}

function pickTodaysDrill(last: AnalysisResult | undefined, focus: string | undefined) {
  const focusKey = (focus ?? "").toLowerCase();
  if (focusKey.includes("eq") || focusKey.includes("clean")) return { title: "Perfect Bass Swap", why: "A clean bass swap is the difference between a transition that feels professional and one that muddies the floor.", description: "Pull the old bass out at the exact moment the new bass comes in — no overlap, no mud.", xp: 30, minutes: 10, focus: "Clean Mixing" };
  if (focusKey.includes("beat") || focusKey.includes("timing")) return { title: "Pitch Micro-Trim", why: "Tiny timing nudges are what keep long blends locked together instead of drifting apart.", description: "Hold both tracks in sync for 32 bars using only the smallest pitch nudges — no jog wheel.", xp: 30, minutes: 12, focus: "Your Timing" };
  if (focusKey.includes("phrase") || focusKey.includes("transition")) return { title: "16-Bar Phrase Lock", why: "Drops that land right in the pocket are the single biggest signal of a trained DJ to a trained ear.", description: "Only bring the new track in on bar 1 of a fresh phrase — every time.", xp: 40, minutes: 15, focus: "Transition Flow" };
  if (focusKey.includes("flow") || focusKey.includes("energy") || focusKey.includes("momentum")) return { title: "Momentum Hold", why: "Keeping the room moving through a long blend is what keeps the floor full instead of emptying it.", description: "Use a high-pass sweep so the energy in the room never dips through the middle of the blend.", xp: 35, minutes: 12, focus: "Crowd Momentum" };
  if (focusKey.includes("musical") || focusKey.includes("pairing") || focusKey.includes("creativ") || focusKey.includes("signature")) return { title: "Harmonic Hop", why: "Picking tracks that sing together turns a competent set into a memorable one — the crowd feels it even if they can't name it.", description: "Mix three tracks staying within one step on the Camelot wheel.", xp: 45, minutes: 18, focus: "Track Pairing" };
  if (last?.feedback?.exercise) return { title: "Coach's pick", why: "This is tailored to what I heard in your last upload — the highest-leverage move for you right now.", description: last.feedback.exercise, xp: 35, minutes: 12, focus: "Coach choice" };
  return { title: "16-Bar Phrase Challenge", why: "Phrase awareness is the foundation every other mixing skill sits on — start here and everything else gets easier.", description: "Mix two tracks so their 16-bar phrases line up perfectly.", xp: 40, minutes: 15, focus: "Transition Flow" };
}
