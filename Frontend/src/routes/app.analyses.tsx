import { useEffect, useState } from "react";
import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/store";
import { CloudDownload, Music2, Upload } from "lucide-react";
import { NextActionBar } from "@/components/NextActionBar";
import { fetchServerAnalyses, type ServerAnalysisEntry } from "@/lib/server-analyses";
import { getAnalysisProvider } from "@/lib/api/provider";
import { mergeRemoteAnalysisIntoStore } from "@/lib/analysis-engine";
import { toast } from "sonner";

export const Route = createFileRoute("/app/analyses")({
  head: () => ({ meta: [{ title: "My Analyses — MixCoach" }] }),
  component: AnalysesLayout,
});

function AnalysesLayout() {
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  if (pathname !== "/app/analyses") return <Outlet />;
  return <AnalysesList />;
}

function AnalysesList() {
  const [state] = useAppState();
  const archived = new Set(state.archivedIds);
  const visible = state.analyses.filter((a) => !archived.has(a.id));

  // Engine-Reports, die es serverseitig gibt, aber nicht in diesem Browser:
  // passiert, wenn die App waehrend eines Laufs still auf den Browser-
  // Fallback gewechselt hat, waehrend die Engine fertig analysierte
  // (MixCoach2.WAV, 2026-07-17). Ohne diesen Import waere der gute Report
  // aus der App heraus fuer immer unsichtbar.
  const [serverOnly, setServerOnly] = useState<ServerAnalysisEntry[]>([]);
  const [importing, setImporting] = useState<string | null>(null);
  const localIds = new Set(state.analyses.map((a) => a.id));
  useEffect(() => {
    fetchServerAnalyses().then((list) => {
      if (!list) return;
      setServerOnly(list.filter((e) => e.id && !localIds.has(e.id)));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.analyses.length]);

  const importOne = async (entry: ServerAnalysisEntry) => {
    setImporting(entry.id);
    try {
      const full = await getAnalysisProvider().getAnalysis(entry.id);
      if (!full) throw new Error("Report nicht ladbar");
      mergeRemoteAnalysisIntoStore(full);
      setServerOnly((s) => s.filter((e) => e.id !== entry.id));
      toast.success(`„${entry.fileName ?? entry.id}" importiert.`);
    } catch {
      toast.error("Import fehlgeschlagen — läuft die Analyse-Engine?");
    } finally {
      setImporting(null);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl font-bold">My Analyses</h1>
          <p className="text-muted-foreground mt-1">
            All your past transitions and reports.
            {archived.size > 0 && (
              <span className="ml-2 text-xs">({archived.size} archived — manage in Settings)</span>
            )}
          </p>
        </div>
        <Button asChild className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
          <Link to="/app/upload"><Upload className="h-4 w-4" /> New analysis</Link>
        </Button>
      </div>
      {serverOnly.length > 0 && (
        <Card className="glass border-primary/40 mb-4">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 font-semibold">
              <CloudDownload className="h-4 w-4 text-primary" />
              Auf dem Analyse-Server gefunden
              <Badge variant="secondary">{serverOnly.length}</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1 mb-3">
              Diese Engine-Reports existieren auf dem Server, fehlen aber in diesem Browser
              (z.&nbsp;B. weil die App während der Analyse auf die eingeschränkte
              Browser-Auswertung ausgewichen ist).
            </p>
            <div className="space-y-2">
              {serverOnly.map((e) => (
                <div key={e.id} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card/50 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{e.fileName ?? e.id}</p>
                    <p className="text-xs text-muted-foreground">
                      {e.transitions} Übergänge · {e.libraryMatches} erkannte Tracks
                      {e.createdAt ? ` · ${new Date(e.createdAt).toLocaleString()}` : ""}
                    </p>
                  </div>
                  <Button size="sm" variant="outline" disabled={importing === e.id} onClick={() => importOne(e)}>
                    {importing === e.id ? "Importiere…" : "Importieren"}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {visible.length === 0 ? (
        <Card className="glass"><CardContent className="p-12 text-center">
          <Music2 className="h-8 w-8 text-muted-foreground mx-auto" />
          <p className="mt-4 text-muted-foreground">No analyses yet. Upload your first transition to get started.</p>
        </CardContent></Card>
      ) : (
        <div className="grid gap-3">
          {visible.map((a) => (
            <Link key={a.id} to="/app/analyses/$id" params={{ id: a.id }}>
              <Card className="glass hover:border-primary/40 transition-colors">
                <CardContent className="flex items-center justify-between p-5">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                      <Music2 className="h-4 w-4 text-accent" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium truncate">{a.fileName}</div>
                      <div className="text-xs text-muted-foreground">
                        {a.bpm ?? "—"} BPM • {a.key ?? "—"} • {new Date(a.createdAt).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {a.scores.beatmatching != null && <Badge variant="secondary">Beat {a.scores.beatmatching}</Badge>}
                    {a.scores.eq != null && <Badge variant="secondary">EQ {a.scores.eq}</Badge>}
                    <div className="font-display text-2xl font-bold w-12 text-right">{a.scores.overall ?? "—"}</div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <NextActionBar
        title="Got a fresh transition? Let's hear it."
        subtitle="Each upload sharpens your coach's read on your style."
        cta="Upload Next Transition"
        to="/app/upload"
      />
    </div>
  );
}
