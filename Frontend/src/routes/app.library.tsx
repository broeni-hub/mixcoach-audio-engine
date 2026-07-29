import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Disc3, Upload, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "@/lib/i18n";
import {
  getLibraryStatus,
  getLibraryTracks,
  uploadRekordboxXml,
  type LibraryStatus,
  type LibraryTrack,
} from "@/lib/library";

export const Route = createFileRoute("/app/library")({
  head: () => ({ meta: [{ title: "Track-Library — MixCoach" }] }),
  component: LibraryPage,
});

const PAGE_TEXTS = {
  de: {
    subtitle: "Deine Tracks machen die Übergangs-Erkennung nahezu exakt — inklusive echter Tracknamen im Report.",
    importTitle: "rekordbox-Sammlung importieren",
    step1a: "In rekordbox: ", step1b: "Datei → Sammlung im xml-Format exportieren",
    step2: "Die erzeugte XML-Datei hier auswählen",
    step3: "MixCoach liest deine Tracks direkt von der Festplatte — nichts wird hochgeladen",
    running: "Import läuft…", pick: "rekordbox-XML auswählen",
    progress: (done: number, total: number) => `${done} / ${total} Tracks verarbeitet`,
    failed: (n: number) => ` · ${n} fehlgeschlagen`,
    current: (t: string) => ` · gerade: ${t}`,
    last: (done: number, skipped: number) => `Letzter Import: ${done} neu, ${skipped} unverändert`,
    lastFailed: (n: number) => `${n} fehlgeschlagen`,
    fpTitle: "Fingerprints",
    empty: "Noch keine Tracks importiert. Nach dem Import erkennt MixCoach automatisch, welcher Track wann in deinen Sets läuft.",
    toastOk: (n: number) => `${n} Tracks gefunden — Fingerprinting läuft im Hintergrund.`,
    toastDone: "Import abgeschlossen.", toastErr: "Import fehlgeschlagen.",
  },
  en: {
    subtitle: "Your tracks make transition detection near-exact — including real track names in the report.",
    importTitle: "Import rekordbox collection",
    step1a: "In rekordbox: ", step1b: "File → Export collection in xml format",
    step2: "Select the generated XML file here",
    step3: "MixCoach reads your tracks straight from disk — nothing is uploaded",
    running: "Import running…", pick: "Choose rekordbox XML",
    progress: (done: number, total: number) => `${done} / ${total} tracks processed`,
    failed: (n: number) => ` · ${n} failed`,
    current: (t: string) => ` · current: ${t}`,
    last: (done: number, skipped: number) => `Last import: ${done} new, ${skipped} unchanged`,
    lastFailed: (n: number) => `${n} failed`,
    fpTitle: "Fingerprints",
    empty: "No tracks imported yet. After importing, MixCoach automatically recognizes which track plays when in your sets.",
    toastOk: (n: number) => `${n} tracks found — fingerprinting runs in the background.`,
    toastDone: "Import finished.", toastErr: "Import failed.",
  },
} as const;

function LibraryPage() {
  const lang = useLang();
  const T = PAGE_TEXTS[lang];
  const [status, setStatus] = useState<LibraryStatus | null>(null);
  const [tracks, setTracks] = useState<LibraryTrack[]>([]);
  const [count, setCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const wasRunning = useRef(false);

  const refreshTracks = useCallback(async () => {
    const data = await getLibraryTracks();
    if (data) {
      setCount(data.count);
      setTracks(data.tracks);
    }
  }, []);

  useEffect(() => {
    refreshTracks();
    getLibraryStatus().then(setStatus);
  }, [refreshTracks]);

  // Waehrend eines Imports alle 2s den Fortschritt holen.
  useEffect(() => {
    if (!status?.running) return;
    const timer = setInterval(async () => {
      const s = await getLibraryStatus();
      if (s) setStatus(s);
    }, 2000);
    return () => clearInterval(timer);
  }, [status?.running]);

  // Wenn der Import gerade fertig wurde: Liste neu laden.
  useEffect(() => {
    if (status?.running) wasRunning.current = true;
    else if (wasRunning.current) {
      wasRunning.current = false;
      refreshTracks();
      toast.success(T.toastDone);
    }
  }, [status?.running, refreshTracks]);

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const { found } = await uploadRekordboxXml(file);
      toast.success(T.toastOk(found));
      const s = await getLibraryStatus();
      if (s) setStatus(s);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : T.toastErr);
    } finally {
      setUploading(false);
    }
  }

  const progressPct = status && status.total > 0
    ? Math.round(((status.done + status.skipped + status.failed) / status.total) * 100)
    : 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Disc3 className="h-7 w-7 text-primary" />
        <div>
          <h1 className="font-display text-2xl font-bold">Track-Library</h1>
          <p className="text-sm text-muted-foreground">
            {T.subtitle}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{T.importTitle}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ol className="list-decimal pl-5 text-sm text-muted-foreground space-y-1">
            <li>{T.step1a}<span className="text-foreground font-medium">{T.step1b}</span></li>
            <li>{T.step2}</li>
            <li>{T.step3}</li>
          </ol>

          <input ref={fileRef} type="file" accept=".xml" className="hidden" onChange={onPickFile} />
          <Button
            onClick={() => fileRef.current?.click()}
            disabled={uploading || status?.running === true}
          >
            {uploading || status?.running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {status?.running ? T.running : T.pick}
          </Button>

          {status?.running && (
            <div className="space-y-2">
              <div className="h-2 rounded bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {T.progress(status.done + status.skipped, status.total)}
                {status.failed > 0 && T.failed(status.failed)}
                {status.current && T.current(status.current)}
              </p>
            </div>
          )}

          {!status?.running && status && status.total > 0 && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              {T.last(status.done, status.skipped)}
              {status.failed > 0 && (
                <span className="flex items-center gap-1 text-amber-500">
                  <AlertTriangle className="h-3.5 w-3.5" /> {T.lastFailed(status.failed)}
                </span>
              )}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            {T.fpTitle}
            <Badge variant="secondary">{count}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {tracks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {T.empty}
            </p>
          ) : (
            <ul className="max-h-96 overflow-y-auto divide-y divide-border text-sm">
              {tracks.map((t) => (
                <li key={t.id} className="flex items-center justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{t.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.artist || "—"}</p>
                  </div>
                  <div className="shrink-0 text-right text-xs text-muted-foreground">
                    {t.bpm ? `${Math.round(t.bpm)} BPM` : ""}
                    {t.key ? ` · ${t.key}` : ""}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
