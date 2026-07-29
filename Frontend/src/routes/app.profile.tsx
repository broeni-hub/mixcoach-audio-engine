import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppState, levelFromXp } from "@/lib/store";
import { Flame, Trophy, Fingerprint, Medal, CalendarRange, Users, User, Settings as SettingsIcon } from "lucide-react";
import { Achievements } from "@/routes/app.achievements";
import { CareerPage } from "@/routes/app.career";
import { DnaPage } from "@/routes/app.dna";
import { MonthlyPage } from "@/routes/app.monthly";
import { CommunityPage } from "@/routes/app.community";

const TABS = [
  { id: "overview",     label: "Overview",       icon: User },
  { id: "career",       label: "Career",         icon: Medal },
  { id: "achievements", label: "Achievements",   icon: Trophy },
  { id: "dna",          label: "DJ DNA",         icon: Fingerprint },
  { id: "monthly",      label: "Monthly Report", icon: CalendarRange },
  { id: "community",    label: "Community",      icon: Users },
] as const;

type TabId = typeof TABS[number]["id"];

export const Route = createFileRoute("/app/profile")({
  head: () => ({ meta: [{ title: "Profile — MixCoach" }] }),
  validateSearch: z.object({
    tab: z.enum(["overview", "career", "achievements", "dna", "monthly", "community"]).optional(),
  }),
  component: ProfilePage,
});

function ProfilePage() {
  const { tab = "overview" } = Route.useSearch();
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <p className="eyebrow text-xs text-accent">Profile</p>
          <h1 className="font-display text-2xl font-bold mt-1">Your DJ identity</h1>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to="/app/settings"><SettingsIcon className="h-4 w-4" /> Settings</Link>
        </Button>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-border -mx-1 px-1">
        {TABS.map((t) => {
          const active = t.id === tab;
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => navigate({ to: "/app/profile", search: { tab: t.id }, replace: true })}
              className={`relative flex items-center gap-2 px-4 py-2.5 text-sm whitespace-nowrap transition-colors ${
                active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {t.label}
              {active && <span className="absolute inset-x-2 -bottom-px h-[2px] bg-[image:var(--gradient-primary)] rounded-full" />}
            </button>
          );
        })}
      </div>

      <div>
        {tab === "overview"     && <Overview />}
        {tab === "career"       && <CareerPage />}
        {tab === "achievements" && <Achievements />}
        {tab === "dna"          && <DnaPage />}
        {tab === "monthly"      && <MonthlyPage />}
        {tab === "community"    && <CommunityPage />}
      </div>
    </div>
  );
}

function Overview() {
  const [state] = useAppState();
  const lvl = levelFromXp(state.profile.xp);
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="glass">
        <CardContent className="p-6 space-y-4">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">DJ name</p>
            <p className="font-display text-2xl font-bold mt-1">{state.profile.name}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{state.profile.experience}</Badge>
            <Badge variant="outline" className="capitalize">{state.profile.plan} plan</Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {state.profile.genres.map((g) => <Badge key={g} className="bg-primary/15 text-primary border-primary/30">{g}</Badge>)}
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Equipment</p>
            <p className="text-sm mt-1">{state.profile.equipment.join(", ") || "—"}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardContent className="p-6 space-y-5">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current level</p>
            <p className="font-display text-2xl font-bold mt-1">{lvl.name}</p>
            <Progress value={lvl.progress} className="mt-3 h-1.5" />
            <p className="text-xs text-muted-foreground mt-2 font-mono">{state.profile.xp} / {lvl.next} XP</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border bg-card/40 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Streak</p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="font-display text-xl font-bold">{state.profile.streak}</p>
                <Flame className="h-4 w-4 text-primary" />
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card/40 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Analyses</p>
              <p className="font-display text-xl font-bold mt-1">{state.analyses.length}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
