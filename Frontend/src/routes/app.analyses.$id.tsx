import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { useAppState } from "@/lib/store";
import {
  Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Radar, RadarChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, BarChart, Bar, CartesianGrid,
} from "recharts";
import {
  CheckCircle2, AlertTriangle, Sparkles, ArrowLeft, Clock, Activity, ArrowLeftRight, Wand2,
  Trophy, TrendingDown, ListChecks, Target, Timer, Zap, ChevronRight,
} from "lucide-react";
import { Waveform } from "@/components/Waveform";
import { CoachFeedbackCard } from "@/components/CoachFeedbackCard";
import { SetTransitionsExplorer } from "@/components/SetTransitionsExplorer";
import { AnalysisFeedbackForm } from "@/components/AnalysisFeedbackForm";
import { EmptyBlock, Placeholder, ValueOr } from "@/components/report/Placeholder";
import { toReportView, formatTime, formatDuration } from "@/lib/report-view";
import { getEngineBaseUrl } from "@/lib/api/remoteProvider";
import { fetchFeedback, sendMissed, requestRematch } from "@/lib/groundtruth";
import { toast } from "sonner";
import { MetricsExplainer } from "@/components/MetricsExplainer";
import { TrackLane } from "@/components/TrackLane";
import { useEffect, useState } from "react";
import { useLang } from "@/lib/i18n";
import type { EnergyArc, FullSetAnalysisResult, SingleTransitionAnalysisResult, ExerciseRecommendation } from "@/lib/report-types";
import { isFullSet } from "@/lib/report-types";
import { NextActionBar } from "@/components/NextActionBar";

export const Route = createFileRoute("/app/analyses/$id")({
  head: () => ({ meta: [{ title: "Analysis Report — MixCoach" }] }),
  validateSearch: (search: Record<string, unknown>) => ({
    listen:
      search.listen != null && !Number.isNaN(Number(search.listen))
        ? Number(search.listen)
        : undefined,
  }),
  component: AnalysisDetail,
});


const REPORT_TEXTS = {
  de: {
    s1: "Coach-Fazit", s1sub: "Was der Coach gesehen hat — in drei Zeilen.",
    s2: "Deine Übung", s2sub: "Mach das als Nächstes — abgeleitet aus dem größten Problem oben.",
    s3: "Set & Übergänge", s3sub: "Anhören, nachvollziehen, Feedback geben.",
    s4: "Messwerte & Charts", s4sub: "Die Zahlen hinter dem Urteil — optional.",
    well: "Das lief gut", issue: "Größtes Problem", focus: "Heutiger Fokus",
    fullCoach: "Vollständiges Coach-Feedback anzeigen",
  },
  en: {
    s1: "Coach summary", s1sub: "What the coach saw — in three lines.",
    s2: "Recommended exercise", s2sub: "Do this next — derived from the biggest issue above.",
    s3: "Set & transitions", s3sub: "Listen, verify, give feedback.",
    s4: "Metrics & charts", s4sub: "The numbers behind the call — optional.",
    well: "What you did well", issue: "Biggest issue", focus: "Today's focus",
    fullCoach: "Show full coach feedback",
  },
} as const;

function AnalysisDetail() {
  const { id } = Route.useParams();
  const [state] = useAppState();
  const legacy = state.analyses.find((x) => x.id === id);

  // WICHTIG: Alle Hooks MUESSEN vor dem "not found"-Fruehausstieg stehen
  // (Rules of Hooks). Sonst crasht die Seite, wenn der Store erst nach dem
  // ersten Render laedt ("Rendered more hooks than during previous render").
  const lang = useLang();
  const H = REPORT_TEXTS[lang];
  const [missedMarks, setMissedMarks] = useState<number[]>([]);
  const legacyId = legacy?.id;

  // Der Korrekturweg: einmal beim Oeffnen bei der Engine nachfragen.
  //
  // Ohne das bleibt jede Verbesserung auf der Platte liegen. Diese Seite
  // rendert aus dem localStorage (state.analyses oben), und bis zum
  // 13.08.2026 gab es KEINEN Pfad, der einen Report je neu geholt haette -
  // ein einmal angesehener Report war eingefroren, korrigierbar nur durch
  // Cache-Loeschen. Uebernommen wird nur, was eine hoehere scoringVersion
  // traegt (mergeRemoteAnalysisIntoStore); ist die Engine nicht erreichbar,
  // bleibt schlicht der gespeicherte Stand stehen.
  //
  // Kosten: ein GET je geoeffnetem Report, derselbe Aufruf, den der Knopf
  // "Mit meinen Korrekturen neu erkennen" schon macht.
  useEffect(() => {
    if (!id) return;
    let abgebrochen = false;
    void (async () => {
      try {
        const { getAnalysisProvider } = await import("@/lib/api/provider");
        const { mergeRemoteAnalysisIntoStore } = await import("@/lib/analysis-engine");
        const frisch = await getAnalysisProvider().getAnalysis(id);
        if (!abgebrochen && frisch) mergeRemoteAnalysisIntoStore(frisch);
      } catch {
        /* Engine aus oder offline - der gespeicherte Stand gilt weiter. */
      }
    })();
    return () => { abgebrochen = true; };
  }, [id]);

  // Coach-Uebung: ?listen=<sec> springt nach dem Laden direkt an die Stelle.
  const { listen } = Route.useSearch();
  useEffect(() => {
    if (!legacyId || listen == null) return;
    const timer = setTimeout(() => {
      window.dispatchEvent(
        new CustomEvent("mixcoach:listen", { detail: { sec: Math.max(0, listen - 10) } }),
      );
    }, 1200);
    return () => clearTimeout(timer);
  }, [legacyId, listen]);
  useEffect(() => {
    if (!legacyId) return;
    let cancelled = false;
    void fetchFeedback(legacyId).then((f) => {
      if (!cancelled && f) setMissedMarks(f.missed ?? []);
    });
    return () => { cancelled = true; };
  }, [legacyId]);

  if (!legacy) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <p className="text-muted-foreground">Analysis not found.</p>
        <Button asChild className="mt-4"><Link to="/app/analyses">Back to list</Link></Button>
      </div>
    );
  }

  const view = toReportView(legacy);

  // Original-Audio vom Backend streamen (Nachhoeren der bewerteten Stellen).
  const engineBase = getEngineBaseUrl();
  const remoteAudioUrl = legacy.audioPath && engineBase ? `${engineBase}${legacy.audioPath}` : null;

  const markMissed = async (sec: number) => {
    const ok = await sendMissed(legacy.id, sec);
    if (ok) {
      setMissedMarks((m) => (m.some((x) => Math.abs(x - sec) < 15) ? m : [...m, sec].sort((a, b) => a - b)));
      const mm = Math.floor(sec / 60);
      const ss = Math.floor(sec % 60).toString().padStart(2, "0");
      toast.success(`Gemerkt: Übergang bei ${mm}:${ss} fehlte — jetzt als Flagge in der Waveform sichtbar.`);
    } else {
      toast.error("Konnte nicht gespeichert werden (Backend erreichbar?).");
    }
  };

  const missedMarkers = missedMarks.map((sec) => ({
    time: formatTime(sec),
    label: "Von dir markiert: Übergang wurde nicht erkannt",
    type: "warning" as const,
  }));
  const setView = isFullSet(view) ? (view as FullSetAnalysisResult) : null;
  const singleView = !setView ? (view as SingleTransitionAnalysisResult) : null;

  const setMarkers = (setView?.transitions ?? []).map((t) => ({
    // Blend-START anzeigen - DJs denken in "ab wann kommt der neue Track".
    // (98 Nutzer-Korrekturen: Mitte lag im Median 26s "zu spaet", Start -4s.)
    time: formatTime(t.startSec ?? t.midSec),
    label: `T${t.index} • ${t.bpmBefore ?? "?"}→${t.bpmAfter ?? "?"} BPM • ${t.label}`,
    type: (t.label === "smooth" ? "good" : t.label === "rough" ? "warning" : "info") as "good" | "warning" | "info",
  }));
  const waveformMarkers = [
    ...(setMarkers.length ? [...(view.timeline ?? []), ...setMarkers] : (view.timeline ?? [])),
    ...missedMarkers,
  ];

  const radarData = (view.skills ?? [])
    .filter((s) => s.value !== null)
    .map((s) => ({ skill: s.label, value: s.value as number }));

  const freqData = view.frequency
    ? [
        { band: "Bass", value: view.frequency.bass },
        { band: "Mid", value: view.frequency.mid },
        { band: "High", value: view.frequency.high },
      ]
    : [];

  // ---- Coach summary (3 cards) ----
  const wins = view.coach?.worked ?? view.strengths ?? [];
  const issues = view.coach?.improve ?? view.weaknesses ?? [];
  const topWin = trimLine(wins[0]);
  const topIssue = trimLine(issues[0]);
  const exercises = view.exercises ?? [];
  const focusExercise: ExerciseRecommendation | null = exercises[0] ?? null;
  const todaysFocus = trimLine(focusExercise?.title ?? issues[0] ?? "Run another transition to surface a focus.") ?? "Run another transition to surface a focus.";

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm"><Link to="/app/analyses"><ArrowLeft className="h-4 w-4" /> All analyses</Link></Button>
        <Badge variant="outline">{view.createdAt ? new Date(view.createdAt).toLocaleString() : "—"}</Badge>
      </div>

      {/* Title */}
      <div>
        <p className="eyebrow text-xs text-muted-foreground">
          {setView ? "Full Set" : "Single Transition"} · Overall {view.overallScore ?? "—"}/100
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-bold mt-1 truncate">
          {view.fileName ?? "Untitled analysis"}
        </h1>
      </div>

      {/* Fallback-Banner: dieser Report entstand OHNE die Analyse-Engine
          (Browser-Heuristik). Muss unuebersehbar sein - die Heuristik
          uebersieht auf sauber gemixten Sets fast alle Uebergaenge
          (MixCoach2.WAV: Fallback ~0, Engine 10, 2026-07-17). */}
      {legacy.engine === "local" && (
        <Card className="border-red-500/50 bg-red-500/10">
          <CardContent className="p-4">
            <p className="text-sm font-semibold flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-red-400" />
              <span>
                Eingeschränkte Browser-Auswertung — die Analyse-Engine war bei diesem
                Upload nicht erreichbar. Übergangs-Erkennung und Messwerte sind hier nur
                grobe Schätzungen; es können viele Übergänge fehlen. Engine starten und
                das Set erneut hochladen für den vollständigen Report.
              </span>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Ehrlichkeits-Banner: Warnungen der Analyse-Engine (honest-v2).
          Wird nur angezeigt, wenn das Backend Unsicherheiten gemeldet hat. */}
      {(legacy.analysisWarnings?.length ?? 0) > 0 && (
        <Card className="border-orange-500/40 bg-orange-500/5">
          <CardContent className="p-4 space-y-2">
            <p className="eyebrow text-[10px] uppercase tracking-wider text-orange-400">Analysis notes</p>
            {legacy.analysisWarnings!.map((w, i) => (
              <p key={i} className="text-sm flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-orange-400" />
                <span>{w}</span>
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 1. COACH SUMMARY — 3 cards */}
      <section className="space-y-3">
        <SectionHeader index={1} title={H.s1} subtitle={H.s1sub} />
        <div className="grid gap-3 md:grid-cols-3">
          <SummaryCard
            tone="green"
            icon={<CheckCircle2 className="h-4 w-4" />}
            eyebrow={H.well}
            line={topWin ?? "Keep mixing — wins will surface once we see a clean move."}
          />
          <SummaryCard
            tone="orange"
            icon={<AlertTriangle className="h-4 w-4" />}
            eyebrow={H.issue}
            line={topIssue ?? "No critical issues detected on this run."}
          />
          <SummaryCard
            tone="purple"
            icon={<Target className="h-4 w-4" />}
            eyebrow={H.focus}
            line={todaysFocus}
          />
        </div>

        <details className="group">
          <summary className="cursor-pointer select-none text-sm text-muted-foreground hover:text-foreground list-none flex items-center gap-1">
            <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" /> {H.fullCoach}
          </summary>
          <div className="mt-3 space-y-4">
            <Card className="glass border-primary/30">
              <CardContent className="pt-5">
                {view.coach && (view.coach.worked.length || view.coach.improve.length) ? (
                  <CoachFeedbackCard analysis={legacy} />
                ) : (
                  <EmptyBlock title="Coach feedback not generated yet" hint="Retry analysis or run again with a longer recording." />
                )}
              </CardContent>
            </Card>
            <div className="grid gap-4 md:grid-cols-2">
              <Card className="glass">
                <CardHeader><CardTitle className="flex items-center gap-2 text-base"><CheckCircle2 className="h-4 w-4 text-accent" /> Strengths</CardTitle></CardHeader>
                <CardContent>
                  <ValueOr value={view.strengths} label="No strengths detected yet">
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {(view.strengths ?? []).map((s, i) => <li key={i}>• {s}</li>)}
                    </ul>
                  </ValueOr>
                </CardContent>
              </Card>
              <Card className="glass">
                <CardHeader><CardTitle className="flex items-center gap-2 text-base"><AlertTriangle className="h-4 w-4 text-primary" /> Weaknesses</CardTitle></CardHeader>
                <CardContent>
                  <ValueOr value={view.weaknesses} label="No weaknesses detected">
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {(view.weaknesses ?? []).map((s, i) => <li key={i}>• {s}</li>)}
                    </ul>
                  </ValueOr>
                </CardContent>
              </Card>
            </div>
          </div>
        </details>
      </section>

      {/* 2. RECOMMENDED EXERCISE */}
      <section className="space-y-3">
        <SectionHeader index={2} title={H.s2} subtitle={H.s2sub} />
        <RecommendedExerciseCard exercise={focusExercise} />
      </section>

      {/* 3. TRANSITION TIMELINE */}
      <section className="space-y-3">
        <SectionHeader index={3} title={H.s3} subtitle={H.s3sub} />
        {setView && setView.transitions && setView.transitions.length > 0 ? (
          <>
          {(view.volumeCurve ?? []).length > 0 && (
            <Card className="glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4 text-accent" /> Waveform
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Waveform analysisId={view.id} peaks={view.volumeCurve ?? []} markers={waveformMarkers} height={140} remoteAudioUrl={remoteAudioUrl} onMarkMissed={markMissed} />
                <EnergyArcNote arc={view.energyArc} />
              </CardContent>
            </Card>
          )}
          {legacy.library && legacy.library.matches?.length > 0 && (
            <>
              <TrackLane
                matches={legacy.library.matches}
                totalDurationSec={view.durationSec ?? legacy.totalDurationSec ?? 0}
                tracksInLibrary={legacy.library.tracks_in_library}
              />
              {legacy.engine !== "local" && <RematchButton analysisId={legacy.id} />}
            </>
          )}
          <Card className="glass border-accent/30 relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="eyebrow text-xs text-accent">{setView.transitions.length} transitions detected</p>
                  <CardTitle className="text-xl mt-1">Every transition in your set</CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    {Math.round((setView.setDurationSec ?? 0) / 60)} min · color = score (green 85+, yellow 70+, orange 55+, red &lt;55).
                  </p>
                </div>
                {setView.transitions.length >= 2 && (
                  <Button asChild size="sm" variant="outline" className="shrink-0">
                    <Link to="/app/analyses/$id/compare" params={{ id: view.id }}>
                      <ArrowLeftRight className="h-4 w-4" /> Compare
                    </Link>
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <SetTransitionsExplorer
                analysisId={view.id}
                totalDurationSec={setView.setDurationSec ?? 0}
                transitions={legacy.setTransitions ?? []}
              />
            </CardContent>
          </Card>
          </>
        ) : (
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-accent" /> Waveform & markers
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(view.volumeCurve ?? []).length > 0 ? (
                <Waveform analysisId={view.id} peaks={view.volumeCurve ?? []} markers={waveformMarkers} height={140} remoteAudioUrl={remoteAudioUrl} onMarkMissed={markMissed} />
              ) : (
                <EmptyBlock title="Waveform not available" hint="Original audio file is no longer cached locally." />
              )}
            </CardContent>
          </Card>
        )}
      </section>

      {/* 4. CHARTS */}
      <section className="space-y-3">
        <SectionHeader index={4} title={H.s4} subtitle={H.s4sub} />

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="glass">
            <CardHeader><CardTitle className="text-base">Skill radar</CardTitle></CardHeader>
            <CardContent className="h-64">
              {radarData.length >= 3 ? (
                <ResponsiveContainer width="100%" height="100%" minWidth={200} minHeight={200}>
                  <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                    <PolarGrid stroke="oklch(0.3 0.02 270)" />
                    <PolarAngleAxis dataKey="skill" tick={{ fill: "oklch(0.7 0.02 270)", fontSize: 11 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar dataKey="value" stroke="oklch(0.65 0.24 295)" fill="oklch(0.65 0.24 295)" fillOpacity={0.35} isAnimationActive={false} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : radarData.length > 0 ? (
                /* Weniger als 3 Messwerte: Chips statt leerem Chart. */
                <div className="flex flex-wrap gap-2 items-start pt-4">
                  {radarData.map((s) => (
                    <span key={s.skill} className="rounded-lg border border-border bg-card/40 px-3 py-2 text-sm">
                      {s.skill}: <strong>{s.value}</strong>
                    </span>
                  ))}
                </div>
              ) : (
                <EmptyBlock title="Skill scores not available" hint="The backend hasn't returned a skill breakdown." />
              )}
            </CardContent>
          </Card>

          <MetricsExplainer />

          <Card className="glass">
            <CardHeader><CardTitle className="text-base">Energy curve</CardTitle></CardHeader>
            <CardContent className="h-64">
              {(view.energyCurve ?? []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={view.energyCurve}>
                    <defs>
                      <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="oklch(0.65 0.24 295)" stopOpacity={0.7} />
                        <stop offset="100%" stopColor="oklch(0.65 0.24 295)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                    <XAxis dataKey="t" tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <YAxis tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.014 270)", border: "1px solid oklch(0.28 0.018 270)", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="value" stroke="oklch(0.65 0.24 295)" fill="url(#g1)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <EmptyBlock title="No energy curve" />}
            </CardContent>
          </Card>

          <Card className="glass">
            <CardHeader>
              <CardTitle className="text-base">
                {/* Engine-Reports liefern hier die echte K-gewichtete
                    Lautheit (BS.1770); der Browser-Fallback nur den
                    Pegel-Verlauf - ehrlich benennen, was gezeigt wird. */}
                {legacy.engine === "local" ? "Volume curve" : "Loudness (K-gewichtet)"}
              </CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              {(view.volumeCurve ?? []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={view.volumeCurve}>
                    <defs>
                      <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="oklch(0.78 0.18 230)" stopOpacity={0.7} />
                        <stop offset="100%" stopColor="oklch(0.78 0.18 230)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                    <XAxis dataKey="t" tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <YAxis tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.014 270)", border: "1px solid oklch(0.28 0.018 270)", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="value" stroke="oklch(0.78 0.18 230)" fill="url(#g2)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <EmptyBlock title="No volume curve" />}
            </CardContent>
          </Card>

          <Card className="glass">
            <CardHeader><CardTitle className="text-base">Frequency balance</CardTitle></CardHeader>
            <CardContent className="h-64">
              {view.frequency ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={freqData}>
                    <CartesianGrid stroke="oklch(0.25 0.02 270)" strokeDasharray="3 3" />
                    <XAxis dataKey="band" tick={{ fill: "oklch(0.7 0.02 270)" }} />
                    <YAxis tick={{ fill: "oklch(0.6 0.02 270)", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "oklch(0.18 0.014 270)", border: "1px solid oklch(0.28 0.018 270)", borderRadius: 8 }} />
                    <Bar dataKey="value" fill="oklch(0.65 0.24 295)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyBlock title="Frequency balance not measured" />}
            </CardContent>
          </Card>
        </div>
        <Card className="glass">
          <CardHeader><CardTitle className="text-base">Track basics</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <Stat label="BPM" value={view.bpm != null ? String(view.bpm) : "—"} />
              <Stat label="Key" value={view.key ?? "—"} />
              <Stat label="Duration" value={formatDuration(view.durationSec)} />
              <Stat label="Overall" value={view.overallScore != null ? `${view.overallScore}/100` : "—"} />
            </div>
          </CardContent>
        </Card>

        {singleView?.transition && (
          <Card className="glass">
            <CardHeader>
              <CardTitle className="text-base">Transition metrics</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Track A → Track B
                {singleView.transition.cuePointSec != null && ` • cue at ${singleView.transition.cuePointSec}s`}
                {singleView.transition.overlapSec != null && ` • ${singleView.transition.overlapSec}s overlap`}
              </p>
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              {/* "Timing drift" und "Phrase landing" zeigen seit 31.07.2026
                  bewusst nichts mehr an - siehe NOT_YET_MEASURED in
                  app/api/analysis_mapper.py. Die Kacheln bleiben stehen, damit
                  sichtbar ist, DASS die Groesse existiert und nicht gemessen
                  wird; das ist der Unterschied zwischen Weg B und Loeschen. */}
              <Stat label="Timing drift" value="nicht gemessen" />
              <Stat label="Key pairing" value={singleView.transition.camelotA && singleView.transition.camelotB ? `${singleView.transition.camelotA} → ${singleView.transition.camelotB}` : "—"} />
              <Stat label="Low-end clash" value={singleView.transition.bassClashScore != null ? `${singleView.transition.bassClashScore}/100` : "—"} />
              <Stat label="Phrase landing" value="nicht gemessen" />

            </CardContent>
          </Card>
        )}

        {setView && <FullSetSummary view={setView} />}

        <Card className="glass">
          <CardHeader><CardTitle className="text-base">Event timeline</CardTitle></CardHeader>
          <CardContent>
            {(view.timeline ?? []).length > 0 ? (
              <ol className="space-y-3">
                {(view.timeline ?? []).map((t, i) => {
                  const color =
                    t.type === "good" ? "text-accent border-accent/40 bg-accent/10" :
                    t.type === "warning" ? "text-primary border-primary/40 bg-primary/10" :
                    "text-muted-foreground border-border bg-card";
                  return (
                    <li key={i} className="flex items-center gap-3">
                      <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-mono ${color}`}>
                        <Clock className="h-3 w-3" /> {t.time}
                      </span>
                      <span className="text-sm">{t.label}</span>
                    </li>
                  );
                })}
              </ol>
            ) : <EmptyBlock title="No timeline events" />}
          </CardContent>
        </Card>

        {exercises.length > 1 && (
          <Card className="glass">
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-4 w-4 text-accent" /> More recommended exercises</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                {exercises.slice(1).map((ex, i) => (
                  <div key={i} className="rounded-lg border border-border bg-card/50 p-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold">{ex.title}</h4>
                      {ex.xp != null && <Badge variant="secondary">+{ex.xp} XP</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground mt-2">{ex.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <AnalysisFeedbackForm analysisId={view.id} />
      </section>

      <NextActionBar
        title="Turn this feedback into reps."
        subtitle="Your coach already lined up the drill that fixes the biggest issue."
        cta="Practice this Exercise"
        to="/app/training"
      />
    </div>
  );
}

// ---------- Helpers ----------

function trimLine(s?: string | null): string | null {
  if (!s) return null;
  const first = s.split(/(?<=[.!?])\s+/)[0]?.trim() ?? s.trim();
  return first.length > 160 ? first.slice(0, 157) + "…" : first;
}

function estimateMinutes(ex: ExerciseRecommendation | null): number {
  if (!ex) return 10;
  const d = ex.difficulty ?? 2;
  return Math.max(5, 4 + d * 3);
}

function SectionHeader({ index, title, subtitle }: { index: number; title: string; subtitle?: string }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="font-mono text-xs text-muted-foreground tabular-nums">{String(index).padStart(2, "0")}</span>
      <div>
        <h2 className="font-display text-xl font-semibold">{title}</h2>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function SummaryCard({
  tone, icon, eyebrow, line,
}: {
  tone: "green" | "orange" | "purple";
  icon: React.ReactNode;
  eyebrow: string;
  line: string;
}) {
  const toneClass =
    tone === "green"
      ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-300"
      : tone === "orange"
        ? "border-amber-500/40 bg-amber-500/5 text-amber-300"
        : "border-primary/40 bg-primary/5 text-primary";
  return (
    <Card className={`glass relative overflow-hidden border ${toneClass}`}>
      <CardContent className="p-5 space-y-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider">
          {icon}
          <span>{eyebrow}</span>
        </div>
        <p className="text-foreground text-base leading-snug font-medium">
          {line}
        </p>
      </CardContent>
    </Card>
  );
}

function RecommendedExerciseCard({ exercise }: { exercise: ExerciseRecommendation | null }) {
  if (!exercise) {
    return (
      <Card className="glass">
        <CardContent className="p-6">
          <EmptyBlock title="No exercise recommended yet" hint="The coach surfaces a targeted drill once a clear weakness shows up." />
        </CardContent>
      </Card>
    );
  }
  const minutes = estimateMinutes(exercise);
  const xp = exercise.xp ?? 50;
  return (
    <Card className="glass border-primary/40 relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
      <CardContent className="p-6 md:p-8 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Recommended exercise</span>
            </div>
            <h3 className="font-display text-2xl md:text-3xl font-bold leading-tight">
              {exercise.title}
            </h3>
            <p className="text-sm text-muted-foreground max-w-2xl">{exercise.description}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="gap-1.5">
            <Timer className="h-3.5 w-3.5" /> {minutes} min
          </Badge>
          <Badge variant="outline" className="gap-1.5">
            <Zap className="h-3.5 w-3.5 text-accent" /> +{xp} XP
          </Badge>
          {exercise.difficulty != null && (
            <Badge variant="outline">Difficulty {exercise.difficulty}/5</Badge>
          )}
        </div>

        <div className="pt-2">
          <Button asChild size="lg" className="gap-2">
            <Link to="/app/training">
              Start exercise <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function FullSetSummary({ view }: { view: FullSetAnalysisResult }) {
  const transitions = view.transitions ?? [];
  const best = view.bestTransitionIndex != null ? transitions[view.bestTransitionIndex] : null;
  const weak = view.weakestTransitionIndex != null ? transitions[view.weakestTransitionIndex] : null;
  return (
    <Card className="glass">
      <CardHeader>
        <CardTitle className="text-base">Set summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Stat label="Set duration" value={formatDuration(view.setDurationSec)} />
          <Stat label="Avg BPM" value={view.averageBpm != null ? String(view.averageBpm) : "—"} />
          <Stat label="Transitions" value={String(transitions.length)} />
          <Stat label="Overall" value={view.overallScore != null ? `${view.overallScore}/100` : "—"} />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-accent/40 bg-accent/5 p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-accent">
              <Trophy className="h-3.5 w-3.5" /> Best transition
            </div>
            {best ? (
              <div className="mt-2">
                <p className="font-display text-lg font-semibold">
                  T{best.index} · {formatTime(best.midSec)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {best.bpmBefore ?? "?"}→{best.bpmAfter ?? "?"} BPM · score {best.qualityScore ?? "—"}/100
                </p>
              </div>
            ) : <Placeholder label="Not enough data" />}
          </div>
          <div className="rounded-lg border border-primary/40 bg-primary/5 p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-primary">
              <TrendingDown className="h-3.5 w-3.5" /> Weakest transition
            </div>
            {weak ? (
              <div className="mt-2">
                <p className="font-display text-lg font-semibold">
                  T{weak.index} · {formatTime(weak.midSec)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {weak.bpmBefore ?? "?"}→{weak.bpmAfter ?? "?"} BPM · score {weak.qualityScore ?? "—"}/100
                </p>
              </div>
            ) : <Placeholder label="Not enough data" />}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <ListChecks className="h-3.5 w-3.5" /> Common mistakes
          </div>
          {(view.commonMistakes ?? []).length > 0 ? (
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
              {(view.commonMistakes ?? []).map((m, i) => <li key={i}>• {m}</li>)}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground/70">No recurring issues detected across the set.</p>
          )}
        </div>

        {view.setFlowFeedback && (
          <div className="rounded-lg border border-border bg-card/40 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Set flow</p>
            <p className="text-sm">{view.setFlowFeedback}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/40 p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-display text-sm font-bold mt-1">{value}</div>
    </div>
  );
}

// Energiebogen ueber das ganze Set - BESCHREIBEND, ohne Note.
//
// Absicht: das hier ist der Gegenentwurf zu den Werten, die am 31.07.2026
// aus der Anzeige genommen wurden. Kein "/100", kein gut/schlecht, keine
// Handlungsanweisung. Der Verlauf ist nachgemessen deterministisch und
// unterscheidet die Aufnahmen; wo ein Hoehepunkt zu LIEGEN hat, ist dagegen
// nicht gemessen - also wird es auch nicht behauptet.
//
// Wird nichts gerendert, wenn kein Bogen vorliegt: eine Aufnahme ohne Kurve
// hat keinen gemessenen Verlauf, und das ist kein Grund fuer einen Platzhalter.
function EnergyArcNote({ arc }: { arc?: EnergyArc | null }) {
  if (!arc) return null;

  const mmss = (s: number) => {
    const m = Math.floor(s / 60);
    return `${m}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  };
  const teile: string[] = [];
  if (Math.abs(arc.anstieg_gesamt) >= 5) {
    teile.push(
      `letztes Drittel ${Math.abs(arc.anstieg_gesamt).toFixed(0)} Punkte ` +
        `${arc.anstieg_gesamt > 0 ? "höher" : "niedriger"} als das erste`,
    );
  } else {
    teile.push("erstes und letztes Drittel auf gleicher Höhe");
  }
  if (arc.laengster_aufbau_sec && arc.laengster_aufbau_anteil >= 0.15) {
    teile.push(
      `längster durchgehender Aufbau ${(arc.laengster_aufbau_sec / 60).toFixed(0)} min`,
    );
  }
  if (arc.peak_sec != null) teile.push(`höchste Energie bei ${mmss(arc.peak_sec)}`);

  return (
    <div className="mt-3 rounded-lg border border-border bg-card/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        Energieverlauf
      </div>
      <div className="text-sm mt-1">{arc.form}</div>
      <div className="text-xs text-muted-foreground mt-1">{teile.join(" · ")}</div>
    </div>
  );
}

// Vision-Datenschleife im Report: die eigenen Korrekturen als exakte
// Segmentgrenzen nutzen, um Tracks nachzuerkennen, die der automatische
// Lauf verfehlte. Nach Erfolg wird der Store aus dem Backend neu geladen.
function RematchButton({ analysisId }: { analysisId: string }) {
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      const res = await requestRematch(analysisId);
      if (res == null) {
        toast.error("Nicht möglich — läuft die Analyse-Engine und gibt es Korrekturen?");
        return;
      }
      if (res.added > 0) {
        toast.success(`${res.added} zusätzliche${res.added === 1 ? "r Track" : " Tracks"} anhand deiner Korrekturen erkannt.`);
      } else {
        toast.success("Neu abgeglichen — keine zusätzlichen Tracks über der Sicherheitsschwelle.");
      }
      // Aktualisierten Report aus dem Backend in den lokalen Store holen.
      try {
        const { getAnalysisProvider } = await import("@/lib/api/provider");
        const { mergeRemoteAnalysisIntoStore } = await import("@/lib/analysis-engine");
        const full = await getAnalysisProvider().getAnalysis(analysisId);
        if (full) {
          mergeRemoteAnalysisIntoStore({ ...full });
          window.dispatchEvent(new Event("mixcoach:update"));
        }
      } catch { /* Anzeige aktualisiert sich beim naechsten Laden */ }
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <Button variant="outline" size="sm" onClick={run} disabled={busy} className="gap-2">
        <Wand2 className="h-3.5 w-3.5" />
        {busy ? "Erkenne neu…" : "Mit meinen Korrekturen neu erkennen"}
      </Button>
      <p className="text-xs text-muted-foreground">
        Nutzt deine „Startet woanders"/„fehlt hier"-Korrekturen als exakte Grenzen — holt Tracks nach, die der automatische Lauf verpasst hat.
      </p>
    </div>
  );
}
