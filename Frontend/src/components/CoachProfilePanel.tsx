// Der echte Coach: zeigt Muster und Uebungen aus den EIGENEN Sets.
// Datenquelle ist GET /coach/profile (Backend-Aggregation ueber alle
// gespeicherten Analysen, bereinigt um vom DJ markierte Fehlalarme).

import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Brain, Play, TrendingDown, TrendingUp, Trophy, AlertTriangle } from "lucide-react";
import { fetchCoachProfile, type CoachProfile } from "@/lib/coach-profile";
import { useLang } from "@/lib/i18n";

const PANEL_TEXTS = {
  de: {
    labels: { overall: "Gesamt", timing: "Phrase-Timing", beatmatching: "Beatmatching",
              musicality: "Harmonie", flow: "Energiefluss" } as Record<string, string>,
    title: "Dein Coach-Profil",
    badge: (sets: number, tr: number) => `${sets} Sets · ${tr} Übergänge gemessen`,
    fewData: "Noch wenig Datenbasis — ab 3 analysierten Sets werden Trends und Muster belastbar.",
    best: (name: string, q: number, file: string) => `Dein bester Übergang: ${name} (Score ${q}) in „${file}"`,
    exercises: "Deine Übungen (aus deinen eigenen Sets)",
    listen: "anhören",
  },
  en: {
    labels: { overall: "Overall", timing: "Phrase timing", beatmatching: "Beatmatching",
              musicality: "Harmony", flow: "Energy flow" } as Record<string, string>,
    title: "Your coach profile",
    badge: (sets: number, tr: number) => `${sets} sets · ${tr} transitions measured`,
    fewData: "Limited data so far — trends and patterns become reliable from 3 analyzed sets.",
    best: (name: string, q: number, file: string) => `Your best transition: ${name} (score ${q}) in "${file}"`,
    exercises: "Your exercises (from your own sets)",
    listen: "listen",
  },
} as const;

function fmtSec(sec: number | null): string {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function CoachProfilePanel() {
  const lang = useLang();
  const T = PANEL_TEXTS[lang];
  const [profile, setProfile] = useState<CoachProfile | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetchCoachProfile(lang).then((p) => {
      setProfile(p);
      setLoaded(true);
    });
  }, [lang]);

  if (!loaded) return null;
  if (!profile || profile.setsAnalyzed === 0) return null;

  const pegel = profile.loudnessTrend;

  return (
    <Card className="border-primary/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-5 w-5 text-primary" />
          {T.title}
          <Badge variant="secondary">
            {T.badge(profile.setsAnalyzed, profile.transitionsMeasured)}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Trends */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(profile.trends).map(([skill, t]) => {
            if (t.current == null) return null;
            const up = (t.delta ?? 0) > 0;
            return (
              <div key={skill} className="rounded-lg border border-border bg-card/50 px-3 py-2">
                <p className="text-[11px] text-muted-foreground">{T.labels[skill] ?? skill}</p>
                <p className="flex items-center gap-1.5 text-sm font-semibold">
                  {t.current}
                  {t.delta != null && t.delta !== 0 && (
                    <span className={`flex items-center gap-0.5 text-xs ${up ? "text-green-500" : "text-red-400"}`}>
                      {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {up ? "+" : ""}{t.delta}
                    </span>
                  )}
                </p>
              </div>
            );
          })}
        </div>

        {/* Pegel-Sauberkeit.
            Eigene Karte statt eines Chips oben, aus einem Grund: dort faerbt
            delta > 0 gruen ("mehr ist besser"). Hier ist NIEDRIGER BESSER -
            dieselbe Logik wuerde Fortschritt als Rueckschritt anzeigen.
            Der Name sagt, was gemessen wird: der Pegelsprung, in dB. Nicht
            "Qualitaet" - ein Composite, der zu 98 % aus einer Dimension
            besteht, war schon einmal der Fehler. */}
        {pegel && pegel.current != null && (
          <div className="rounded-lg border border-primary/30 bg-card/50 p-3">
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-semibold">Pegel-Sauberkeit</p>
              <p className="text-[11px] text-muted-foreground">niedriger ist besser</p>
            </div>
            <p className="mt-1 flex items-center gap-2 text-sm font-semibold">
              {pegel.current.toFixed(2).replace(".", ",")} dB
              {pegel.delta != null && pegel.delta !== 0 && (
                <span className={`flex items-center gap-0.5 text-xs ${
                  pegel.delta < 0 ? "text-green-500" : "text-red-400"}`}>
                  {pegel.delta < 0 ? <TrendingDown className="h-3 w-3" />
                                   : <TrendingUp className="h-3 w-3" />}
                  {pegel.delta > 0 ? "+" : ""}{pegel.delta.toFixed(2).replace(".", ",")} dB
                </span>
              )}
            </p>
            {pegel.currentSharePct != null && (
              <p className="mt-1 text-xs text-muted-foreground">
                {pegel.currentSharePct.toFixed(0)} % der Übergänge über{" "}
                {(pegel.thresholdDb ?? 3).toFixed(0)} dB
                {pegel.deltaSharePct != null && pegel.deltaSharePct !== 0 && (
                  <> ({pegel.deltaSharePct > 0 ? "+" : ""}
                  {pegel.deltaSharePct.toFixed(0)} pp)</>
                )}
              </p>
            )}
            {/* Die Unsicherheit gehoert daneben, nicht in eine Fussnote. */}
            <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
              Median des Pegelsprungs, über {pegel.recordings}{" "}
              {pegel.recordings === 1 ? "eigene Aufnahme" : "eigene Aufnahmen"}
              {pegel.excludedForeign ? ` (${pegel.excludedForeign} fremde Sets zählen nicht mit)` : ""}.
              {" "}Ein deutlicher Hinweis, keine Gewissheit — ein Bewerter, wenige Wochen.
            </p>
          </div>
        )}

        {!profile.enoughData && (
          <p className="text-xs text-muted-foreground">
            {T.fewData}
          </p>
        )}

        {/* Muster */}
        {profile.patterns.length > 0 && (
          <div className="space-y-2">
            {profile.patterns.map((p) => (
              <div key={p.id} className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" /> {p.title}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{p.evidence}</p>
              </div>
            ))}
          </div>
        )}

        {/* Bester Uebergang */}
        {profile.best && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Trophy className="h-4 w-4 text-yellow-500 shrink-0" />
            {T.best(profile.best.name, profile.best.quality, profile.best.fileName)}
          </p>
        )}

        {/* Uebungen aus eigenem Material */}
        {profile.exercises.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold">{T.exercises}</p>
            {profile.exercises.map((ex, i) => (
              <div key={i} className="flex items-start justify-between gap-3 rounded-lg border border-border bg-card/50 p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{ex.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{ex.description}</p>
                </div>
                <Button asChild size="sm" variant="outline" className="shrink-0">
                  <Link
                    to="/app/analyses/$id"
                    params={{ id: ex.analysisId }}
                    search={{ listen: ex.startSec ?? ex.midSec ?? undefined }}
                  >
                    <Play className="h-3.5 w-3.5" /> {fmtSec(ex.startSec ?? ex.midSec)} {T.listen}
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
