import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Radar, RadarChart, PolarAngleAxis, PolarGrid, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import {
  ArrowLeft, ArrowLeftRight, CheckCircle2, AlertTriangle,
  Sparkles, Trophy, Minus,
} from "lucide-react";
import { useAppState } from "@/lib/store";
import { classifyTransition, TRANSITION_META } from "@/lib/api/transitionTypes";
import type { SetTransition } from "@/lib/set-analysis";

export const Route = createFileRoute("/app/analyses/$id/compare")({
  head: () => ({ meta: [{ title: "Compare transitions — MixCoach" }] }),
  validateSearch: (s: Record<string, unknown>) => ({
    a: typeof s.a === "string" ? s.a : undefined,
    b: typeof s.b === "string" ? s.b : undefined,
  }),
  component: CompareTransitions,
  notFoundComponent: () => (
    <div className="max-w-md mx-auto text-center py-16">
      <p className="text-muted-foreground">Analysis not found.</p>
      <Button asChild className="mt-4"><Link to="/app/analyses">Back to analyses</Link></Button>
    </div>
  ),
});

function CompareTransitions() {
  const { id } = Route.useParams();
  const search = Route.useSearch();
  const [state] = useAppState();
  const a = state.analyses.find((x) => x.id === id);
  if (!a) throw notFound();

  const transitions = a.setTransitions ?? [];
  const firstIdx = transitions[0]?.index?.toString() ?? "";
  const secondIdx = transitions[1]?.index?.toString() ?? firstIdx;
  const [aIdx, setAIdx] = useState<string>(search.a ?? firstIdx);
  const [bIdx, setBIdx] = useState<string>(search.b ?? secondIdx);

  const tA = transitions.find((t) => t.index.toString() === aIdx);
  const tB = transitions.find((t) => t.index.toString() === bIdx);

  if (transitions.length < 2) {
    return (
      <div className="space-y-6 animate-fade-in">
        <BackBar id={id} />
        <Card className="glass">
          <CardContent className="py-16 text-center space-y-3">
            <ArrowLeftRight className="h-10 w-10 text-muted-foreground mx-auto" />
            <p className="text-lg font-semibold">Need at least two transitions</p>
            <p className="text-sm text-muted-foreground">
              This analysis only has {transitions.length} detected transition
              {transitions.length === 1 ? "" : "s"}. Upload a full set to compare.
            </p>
            <Button asChild className="mt-2">
              <Link to="/app/upload">Upload a set</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <BackBar id={id} />

      <Card className="glass">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ArrowLeftRight className="h-5 w-5 text-accent" /> Compare transitions
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Pick any two transitions from this set to see side-by-side metrics, what worked,
            what didn't, and which drills to run next.
          </p>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <TransitionPicker label="Transition A" value={aIdx} onChange={setAIdx} options={transitions} />
          <TransitionPicker label="Transition B" value={bIdx} onChange={setBIdx} options={transitions} />
        </CardContent>
      </Card>

      {tA && tB && <ComparisonBody tA={tA} tB={tB} analysisId={id} />}
    </div>
  );
}

function BackBar({ id }: { id: string }) {
  return (
    <Button asChild variant="ghost" size="sm">
      <Link to="/app/analyses/$id" params={{ id }}>
        <ArrowLeft className="h-4 w-4" /> Back to analysis
      </Link>
    </Button>
  );
}

function TransitionPicker({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: SetTransition[];
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">{label}</div>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger><SelectValue /></SelectTrigger>
        <SelectContent>
          {options.map((t) => (
            <SelectItem key={t.index} value={t.index.toString()}>
              T{t.index} • {fmt(t.mid_sec)} • {t.label} • score {t.quality_score}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function ComparisonBody({ tA, tB, analysisId }: { tA: SetTransition; tB: SetTransition; analysisId: string }) {
  const sideA = useMemo(() => deriveSide(tA), [tA]);
  const sideB = useMemo(() => deriveSide(tB), [tB]);

  // Achsen "Beatmatch" und "Phrase" entfallen (31.07.2026) - deriveSide
  // liefert sie nicht mehr, siehe Kommentar dort.
  const radarData = [
    { skill: "EQ", A: sideA.metrics.eq, B: sideB.metrics.eq },
    { skill: "Energy", A: sideA.metrics.energy, B: sideB.metrics.energy },
    { skill: "Smoothness", A: sideA.metrics.smoothness, B: sideB.metrics.smoothness },
  ];

  const barData = radarData.map((d) => ({ skill: d.skill, A: d.A, B: d.B }));

  const winner = sideA.overall === sideB.overall ? "tie" : sideA.overall > sideB.overall ? "A" : "B";
  const exercises = recommendDrills(sideA, sideB);

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <ScoreCard side="A" t={tA} data={sideA} winner={winner} />
        <ScoreCard side="B" t={tB} data={sideB} winner={winner} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="glass">
          <CardHeader><CardTitle>Skill radar</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="oklch(0.3 0.02 270)" />
                <PolarAngleAxis dataKey="skill" tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 12 }} />
                <Radar name="A" dataKey="A" stroke="oklch(0.65 0.24 295)" fill="oklch(0.65 0.24 295)" fillOpacity={0.3} />
                <Radar name="B" dataKey="B" stroke="oklch(0.72 0.18 220)" fill="oklch(0.72 0.18 220)" fillOpacity={0.3} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader><CardTitle>Score breakdown</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                <XAxis dataKey="skill" tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "oklch(0.18 0.02 270)", border: "1px solid oklch(0.3 0.02 270)", borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="A" fill="oklch(0.65 0.24 295)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="B" fill="oklch(0.72 0.18 220)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <StrengthsCard side="A" data={sideA} />
        <StrengthsCard side="B" data={sideB} />
      </div>

      <Card className="glass">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" /> Recommended drills
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Targeted at the biggest gap between these two transitions.
          </p>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {exercises.map((ex) => (
            <div key={ex.title} className="rounded-lg border border-border bg-card/40 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="font-display font-semibold">{ex.title}</div>
                <Badge variant="outline" className="font-mono">+{ex.xp} XP</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{ex.description}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex justify-center gap-3">
        <Button asChild variant="outline">
          <Link to="/app/analyses/$id/transitions/$tIdx" params={{ id: analysisId, tIdx: tA.index.toString() }}>
            Open T{tA.index} detail
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/app/analyses/$id/transitions/$tIdx" params={{ id: analysisId, tIdx: tB.index.toString() }}>
            Open T{tB.index} detail
          </Link>
        </Button>
      </div>
    </>
  );
}

function ScoreCard({
  side, t, data, winner,
}: {
  side: "A" | "B"; t: SetTransition; data: Side; winner: "A" | "B" | "tie";
}) {
  const meta = TRANSITION_META[data.type];
  const Icon = meta.icon;
  const isWinner = winner === side;
  const isTie = winner === "tie";
  const accent = side === "A" ? "text-primary" : "text-accent";

  return (
    <Card className={`glass relative overflow-hidden ${isWinner ? "ring-1 ring-primary/50" : ""}`}>
      <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
      <CardHeader>
        <div className="flex items-center gap-3">
          <span className={`h-10 w-10 rounded-xl ${meta.bg} ${meta.color} flex items-center justify-center border ${meta.border}`}>
            <Icon className="h-5 w-5" />
          </span>
          <div>
            <p className={`eyebrow text-xs ${accent}`}>Transition {side}</p>
            <CardTitle className="text-xl mt-1">T{t.index} • {fmt(t.mid_sec)}</CardTitle>
          </div>
          <div className="ml-auto text-right">
            <div className="font-display text-4xl font-bold gradient-text">{data.overall}</div>
            <p className="text-[10px] text-muted-foreground">Overall</p>
            {isWinner && !isTie && (
              <Badge className="mt-1 gap-1"><Trophy className="h-3 w-3" /> Better</Badge>
            )}
            {isTie && <Badge variant="outline" className="mt-1 gap-1"><Minus className="h-3 w-3" /> Tied</Badge>}
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Type" value={meta.label} />
        <Row label="Duration" value={`${Math.round(t.end_sec - t.start_sec)}s`} />
        <Row label="BPM" value={`${t.bpm_before || "?"}→${t.bpm_after || "?"}`} />
        <Row label="Energy dip" value={`${t.energy_dip_pct}%`} />
        <Row label="Bass clash risk" value={`${t.bass_overlap_score}/100`} />
      </CardContent>
    </Card>
  );
}

function StrengthsCard({ side, data }: { side: "A" | "B"; data: Side }) {
  return (
    <Card className="glass">
      <CardHeader>
        <CardTitle className="text-base">Transition {side} — what stood out</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <div className="flex items-center gap-2 text-primary mb-1.5">
            <CheckCircle2 className="h-4 w-4" /> Strengths
          </div>
          <ul className="space-y-1">
            {data.strengths.length === 0
              ? <li className="text-muted-foreground">No standout strengths.</li>
              : data.strengths.map((s) => (
                <li key={s} className="text-muted-foreground pl-5 relative before:absolute before:left-1 before:top-2 before:h-1 before:w-1 before:rounded-full before:bg-primary">{s}</li>
              ))}
          </ul>
        </div>
        <div>
          <div className="flex items-center gap-2 text-destructive mb-1.5">
            <AlertTriangle className="h-4 w-4" /> Weaknesses
          </div>
          <ul className="space-y-1">
            {data.weaknesses.length === 0
              ? <li className="text-muted-foreground">No major weaknesses.</li>
              : data.weaknesses.map((w) => (
                <li key={w} className="text-muted-foreground pl-5 relative before:absolute before:left-1 before:top-2 before:h-1 before:w-1 before:rounded-full before:bg-destructive">{w}</li>
              ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-card/30 px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-sm">{value}</div>
    </div>
  );
}

// ---------- derivation ----------

interface Side {
  type: ReturnType<typeof classifyTransition>;
  // beatmatch und phrase sind am 31.07.2026 entfallen, siehe deriveSide.
  metrics: { eq: number; energy: number; smoothness: number };
  overall: number;
  strengths: string[];
  weaknesses: string[];
}

function deriveSide(t: SetTransition): Side {
  const type = classifyTransition({
    duration_sec: Math.max(0, t.end_sec - t.start_sec),
    energy_dip_pct: t.energy_dip_pct,
    bpm_drift: t.bpm_drift,
    phrase_alignment_score: t.phrase_alignment_score,
    label: t.label,
  });
  // beatmatch und phrase sind hier am 31.07.2026 entfallen: beide waren aus
  // bpm_drift bzw. phrase_alignment_score abgeleitet, die nicht messen, was
  // ihr Name sagt (siehe NOT_YET_MEASURED in app/api/analysis_mapper.py).
  // beatmatch lag durch die 89 % Nullwerte praktisch immer bei 100 und hat
  // den overall-Mittelwert damit systematisch nach oben gezogen.
  const eq = clamp(100 - t.bass_overlap_score);
  const energy = clamp(100 - t.energy_dip_pct);
  const smoothness = clamp(t.quality_score);
  const metrics = { eq, energy, smoothness };
  const overall = Math.round((eq + energy + smoothness) / 3);

  const strengths: string[] = [];
  const weaknesses: string[] = [];
  if (eq >= 80) strengths.push("Clean low-end swap, no bass clash.");
  else if (eq < 60) weaknesses.push(`Bass overlap risk ${t.bass_overlap_score}/100 — cut the outgoing bass earlier.`);
  if (energy >= 80) strengths.push("Energy held through the blend.");
  else if (energy < 60) weaknesses.push(`Energy dropped ${t.energy_dip_pct}% mid-blend.`);
  if (smoothness >= 80) strengths.push("Reads as smooth on the dancefloor.");
  else if (t.label === "rough") weaknesses.push("Overall feel was rough — listeners notice.");

  return { type, metrics, overall, strengths, weaknesses };
}

// "Pitch-fader micro-trim" und "16-Bar Phrase Lock" sind hier entfallen
// (31.07.2026). Sie wurden aus beatmatch/phrase zugewiesen, also aus
// bpm_drift und phrase_alignment_score - siehe NOT_YET_MEASURED in
// app/api/analysis_mapper.py. Einen DJ eine Uebungseinheit in ein Problem
// investieren zu lassen, das die Engine nicht belegen kann, ist der
// schwerste Fall der Ehrlichkeitsverletzung, nicht der leichteste.
function recommendDrills(a: Side, b: Side): { title: string; description: string; xp: number }[] {
  const skills: Array<keyof Side["metrics"]> = ["eq", "energy", "smoothness"];
  const gaps = skills
    .map((s) => ({ skill: s, weakest: Math.min(a.metrics[s], b.metrics[s]) }))
    .sort((x, y) => x.weakest - y.weakest);
  const top = gaps.slice(0, 2).map((g) => DRILLS[g.skill]);
  return top;
}

const DRILLS: Record<keyof Side["metrics"], { title: string; description: string; xp: number }> = {
  eq: { title: "Perfect EQ Swap", description: "Cut outgoing bass at the exact moment you bring in the new bass — same fader move, mirrored.", xp: 30 },
  energy: { title: "Energy Hold Drill", description: "Use a high-pass sweep to keep perceived energy flat through a long blend.", xp: 35 },
  smoothness: { title: "Long-Blend Builder", description: "Stretch a single transition to 64 bars, layering EQ, filter, and FX gradually.", xp: 45 },
};

function fmt(s: number): string {
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(Math.floor(s % 60)).padStart(2, "0");
  return `${mm}:${ss}`;
}

function clamp(n: number) { return Math.max(0, Math.min(100, Math.round(n))); }
