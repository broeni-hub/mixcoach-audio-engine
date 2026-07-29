// Track-Spur: zeigt, WELCHER Library-Track WANN im Set lief -
// als farbige Baender auf der Zeitachse plus Liste mit Anhoeren-Knopf.
// Datenquelle: result.library.matches (Fingerprint-Erkennung).

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Disc3, Play } from "lucide-react";
import { useLang } from "@/lib/i18n";

interface Match {
  title: string | null;
  artist: string | null;
  start: number;
  end: number;
  score: number;
}

const TEXTS = {
  de: {
    title: "Erkannte Tracks",
    subtitle: (n: number, lib: number) =>
      `${n} Tracks aus deiner Library (${lib.toLocaleString("de-DE")} Fingerprints) sicher wiedererkannt. Unbenannte Abschnitte: kein Library-Track erkennbar — dort arbeitet die ML-Erkennung.`,
    listen: "Anhören",
    none: "In diesem Set wurde kein Track aus deiner Library sicher erkannt.",
  },
  en: {
    title: "Recognized tracks",
    subtitle: (n: number, lib: number) =>
      `${n} tracks from your library (${lib.toLocaleString("en-US")} fingerprints) confidently recognized. Unnamed sections: no library track detectable — ML detection covers those.`,
    listen: "Listen",
    none: "No track from your library was confidently recognized in this set.",
  },
} as const;

const BAND_COLORS = [
  "bg-violet-500/40 border-violet-400/60",
  "bg-sky-500/40 border-sky-400/60",
  "bg-emerald-500/40 border-emerald-400/60",
  "bg-amber-500/40 border-amber-400/60",
  "bg-rose-500/40 border-rose-400/60",
  "bg-teal-500/40 border-teal-400/60",
];

function fmt(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function listenAt(sec: number) {
  window.dispatchEvent(
    new CustomEvent("mixcoach:listen", { detail: { sec: Math.max(0, sec - 5) } }),
  );
}

export function TrackLane({ matches, totalDurationSec, tracksInLibrary }: {
  matches: Match[];
  totalDurationSec: number;
  tracksInLibrary: number;
}) {
  const lang = useLang();
  const T = TEXTS[lang];

  if (!matches.length) return null;

  const total = Math.max(1, totalDurationSec);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Disc3 className="h-4 w-4 text-primary" />
          {T.title}
          <Badge variant="secondary">{matches.length}</Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground">{T.subtitle(matches.length, tracksInLibrary)}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Zeitachse mit Track-Baendern */}
        <div className="relative h-9 rounded-md bg-muted/40 overflow-hidden">
          {matches.map((m, i) => {
            const left = (m.start / total) * 100;
            const width = Math.max(1.5, ((m.end - m.start) / total) * 100);
            return (
              <button
                key={i}
                onClick={() => listenAt(m.start)}
                title={`${m.artist ?? ""} – ${m.title ?? ""} (${fmt(m.start)}–${fmt(m.end)})`}
                className={`absolute top-1 bottom-1 rounded border ${BAND_COLORS[i % BAND_COLORS.length]} hover:brightness-125 transition-all overflow-hidden`}
                style={{ left: `${left}%`, width: `${width}%` }}
              >
                <span className="block truncate px-1 text-[9px] leading-7 text-foreground/90">
                  {m.title ?? "?"}
                </span>
              </button>
            );
          })}
        </div>

        {/* Liste */}
        <ul className="divide-y divide-border text-sm">
          {matches.map((m, i) => (
            <li key={i} className="flex items-center gap-3 py-2">
              <span className={`h-3 w-3 rounded-sm border shrink-0 ${BAND_COLORS[i % BAND_COLORS.length]}`} />
              <span className="font-mono text-xs text-muted-foreground shrink-0 w-24">
                {fmt(m.start)}–{fmt(m.end)}
              </span>
              <span className="min-w-0 flex-1 truncate">
                <span className="font-medium">{m.title ?? "?"}</span>
                {m.artist ? <span className="text-muted-foreground"> — {m.artist}</span> : null}
              </span>
              <button
                onClick={() => listenAt(m.start)}
                title={T.listen}
                className="h-7 w-7 rounded-md border border-border bg-background/40 hover:bg-background flex items-center justify-center shrink-0"
              >
                <Play className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
