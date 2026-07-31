import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Clock, Sparkles } from "lucide-react";
import {
  Radar, RadarChart, PolarAngleAxis, PolarGrid, ResponsiveContainer,
} from "recharts";
import { useAppState } from "@/lib/store";
import { classifyTransition, TRANSITION_META } from "@/lib/api/transitionTypes";
import { Waveform } from "@/components/Waveform";

export const Route = createFileRoute("/app/analyses/$id/transitions/$tIdx")({
  head: () => ({ meta: [{ title: "Transition detail — MixCoach" }] }),
  component: TransitionDetail,
  notFoundComponent: () => (
    <div className="max-w-md mx-auto text-center py-16">
      <p className="text-muted-foreground">Transition not found.</p>
      <Button asChild className="mt-4"><Link to="/app/analyses">Back to analyses</Link></Button>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="max-w-md mx-auto text-center py-16">
      <p className="text-destructive">{error.message}</p>
    </div>
  ),
});

function TransitionDetail() {
  const { id, tIdx } = Route.useParams();
  const [state] = useAppState();
  const a = state.analyses.find((x) => x.id === id);
  if (!a) throw notFound();
  const idx = Number(tIdx);
  const t = a.setTransitions?.find((x) => x.index === idx);
  if (!t) throw notFound();

  const type = classifyTransition({
    duration_sec: Math.max(0, t.end_sec - t.start_sec),
    energy_dip_pct: t.energy_dip_pct,
    bpm_drift: t.bpm_drift,
    phrase_alignment_score: t.phrase_alignment_score,
    label: t.label,
  });
  const meta = TRANSITION_META[type];
  const Icon = meta.icon;

  // Achsen "Beatmatch" und "Phrase" entfallen (31.07.2026): beide wurden aus
  // bpm_drift bzw. phrase_alignment_score gebildet, und die messen nicht, was
  // ihr Name sagt - Begruendung und Zahlen in NOT_YET_MEASURED,
  // app/api/analysis_mapper.py. Beatmatch war praktisch konstant 100, weil
  // bpm_drift in 89 % der Uebergaenge exakt 0 ist.
  const metrics = [
    { skill: "EQ", value: clamp(100 - t.bass_overlap_score) },
    { skill: "Energy", value: clamp(100 - t.energy_dip_pct) },
    { skill: "Musicality", value: a.scores.musicality },
    { skill: "Creativity", value: a.scores.creativity },
  ].filter((m): m is { skill: string; value: number } => m.value != null);
  // Konfidenz aus den beiden Groessen, die hier tatsaechlich etwas tragen.
  const confidence = Math.round(
    50 + (clamp(100 - t.bass_overlap_score) + clamp(100 - t.energy_dip_pct)) / 4,
  );

  const mid = fmt(t.mid_sec);
  const dur = Math.round(t.end_sec - t.start_sec);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/app/analyses/$id" params={{ id }}>
            <ArrowLeft className="h-4 w-4" /> Back to analysis
          </Link>
        </Button>
        <Badge variant="outline" className="font-mono">T{t.index}</Badge>
      </div>

      <Card className={`glass relative overflow-hidden ${meta.border}`}>
        <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className={`h-10 w-10 rounded-xl ${meta.bg} ${meta.color} flex items-center justify-center border ${meta.border}`}>
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <p className={`eyebrow text-xs ${meta.color}`}>{meta.label}</p>
              <CardTitle className="text-2xl mt-1">Transition {t.index} • {mid}</CardTitle>
            </div>
            <div className="ml-auto text-right">
              <div className="font-display text-5xl font-bold gradient-text">{t.quality_score}</div>
              <p className="text-xs text-muted-foreground">Quality score</p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-2">{meta.description}</p>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Duration" value={`${dur}s`} />
          <Stat label="BPM" value={`${t.bpm_before || "?"} → ${t.bpm_after || "?"}`} />
          <Stat label="Confidence" value={`${confidence}%`} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="glass lg:col-span-2">
          <CardHeader><CardTitle>Metrics</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={metrics}>
                <PolarGrid stroke="oklch(0.3 0.02 270)" />
                <PolarAngleAxis dataKey="skill" tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 12 }} />
                <Radar dataKey="value" stroke="oklch(0.65 0.24 295)" fill="oklch(0.65 0.24 295)" fillOpacity={0.35} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader><CardTitle className="text-base">Audio metrics</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Energy dip" value={`${t.energy_dip_pct}%`} />
            {/* "Phrase alignment X/100" entfernt - siehe Kommentar oben. */}
            <Row label="Phrase alignment" value="nicht gemessen" />
            <Row label="Bass clash risk" value={`${t.bass_overlap_score}/100`} />
            <Row label="Vocal clash risk" value="—" />
            <Row label="Label" value={t.label} />
          </CardContent>
        </Card>
      </div>

      <Card className="glass">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Clock className="h-4 w-4 text-accent" /> Timeline</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">{fmt(t.start_sec)} → {fmt(t.end_sec)} ({dur}s)</p>
        </CardHeader>
        <CardContent>
          <Waveform
            analysisId={a.id}
            peaks={a.volumeCurve}
            markers={[
              { time: fmt(t.start_sec), label: "Transition start", type: "info" },
              { time: fmt(t.mid_sec), label: `${meta.label} mid`, type: t.label === "smooth" ? "good" : t.label === "rough" ? "warning" : "info" },
              { time: fmt(t.end_sec), label: "Transition end", type: "info" },
            ]}
            height={120}
          />
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader><CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent" /> Suggested drill</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm">
            {t.label === "rough"
              ? `This ${meta.label.toLowerCase()} lost ${t.energy_dip_pct}% energy. Re-attempt with a longer overlap and stagger the bass cut by 4 bars.`
              : t.label === "smooth"
                ? `Solid ${meta.label.toLowerCase()}. Try the same pattern with a more drastic key change to push creativity.`
                : `Neutral ${meta.label.toLowerCase()}. Bass handover sits at ${t.bass_overlap_score}/100 — tighten the low end for a cleaner read.`}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/40 p-3">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-display text-lg font-bold mt-1">{value}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border/40 pb-1.5 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}

function fmt(s: number): string {
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(Math.floor(s % 60)).padStart(2, "0");
  return `${mm}:${ss}`;
}

function clamp(n: number) { return Math.max(0, Math.min(100, Math.round(n))); }
