import { useEffect, useMemo, useRef, useState } from "react";
import { Play, Pause, Upload, Repeat, Flag, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { loadAudioUrl, saveAudio } from "@/lib/audio-store";
import { reportPlayerPosition } from "@/lib/player-bus";
import { useLang } from "@/lib/i18n";

export interface WaveformMarker {
  time: string; // mm:ss
  label: string;
  type: "good" | "warning" | "info";
}

interface Props {
  analysisId?: string;
  peaks: { t: number; value: number }[]; // 0..100 per second
  markers?: WaveformMarker[];
  height?: number;
  /** Audio-URL vom Backend (Streaming mit Range-Support). Wird verwendet,
   *  wenn kein lokal gespeichertes Audio vorliegt. */
  remoteAudioUrl?: string | null;
  /** Wenn gesetzt: Button "Übergang fehlt hier" meldet die aktuelle
   *  Playhead-Position als von der Engine verpassten Übergang. */
  onMarkMissed?: (sec: number) => void;
}

function parseTime(s: string): number {
  const [m, sec] = s.split(":").map(Number);
  return (m || 0) * 60 + (sec || 0);
}

function formatTime(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function Waveform({ analysisId, peaks, markers = [], height = 120, remoteAudioUrl = null, onMarkMissed }: Props) {
  const lang = useLang();
  const [hover, setHover] = useState<WaveformMarker | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Loop selection
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [loopRange, setLoopRange] = useState<{ start: number; end: number } | null>(null);
  const [dragState, setDragState] = useState<
    | null
    | { mode: "create"; anchor: number; current: number }
    | { mode: "move-start" | "move-end" }
  >(null);
  const barsContainerRef = useRef<HTMLDivElement | null>(null);

  const peakDuration = peaks.length ? peaks[peaks.length - 1].t + 1 : 1;
  const duration = audioDuration || peakDuration;
  const max = useMemo(() => Math.max(1, ...peaks.map((p) => p.value)), [peaks]);

  // Audio-Quelle: 1. lokal gespeichert (IndexedDB), 2. Backend-Stream.
  useEffect(() => {
    if (!analysisId) {
      if (remoteAudioUrl) setAudioUrl(remoteAudioUrl);
      return;
    }
    let blobUrl: string | null = null;
    loadAudioUrl(analysisId).then((u) => {
      blobUrl = u;
      setAudioUrl(u ?? remoteAudioUrl ?? null);
    });
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [analysisId, remoteAudioUrl]);

  // Externe "Anhoeren"-Buttons (z.B. am Uebergang) steuern den Player
  // ueber ein Window-Event: springt zur Stelle und spielt ab.
  useEffect(() => {
    const onListen = (e: Event) => {
      const sec = (e as CustomEvent<{ sec: number }>).detail?.sec;
      const el = audioRef.current;
      if (typeof sec !== "number" || !el) return;
      el.currentTime = Math.max(0, sec);
      setCurrentTime(Math.max(0, sec));
      void el.play();
      setPlaying(true);
      el.scrollIntoView?.({ behavior: "smooth", block: "center" });
    };
    window.addEventListener("mixcoach:listen", onListen);
    return () => window.removeEventListener("mixcoach:listen", onListen);
  }, []);

  // Audio element wiring
  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => {
      const t = el.currentTime;
      reportPlayerPosition(t);
      // Loop enforcement
      if (loopEnabled && loopRange && t >= loopRange.end - 0.02) {
        el.currentTime = loopRange.start;
        setCurrentTime(loopRange.start);
        return;
      }
      setCurrentTime(t);
    };
    const onMeta = () => setAudioDuration(el.duration || 0);
    const onEnd = () => {
      if (loopEnabled && loopRange) {
        el.currentTime = loopRange.start;
        void el.play();
        return;
      }
      setPlaying(false);
    };
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnd);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnd);
    };
  }, [audioUrl, loopEnabled, loopRange]);

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      // If loop active and outside range, snap to start
      if (loopEnabled && loopRange && (el.currentTime < loopRange.start || el.currentTime >= loopRange.end)) {
        el.currentTime = loopRange.start;
      }
      void el.play();
      setPlaying(true);
    }
  };

  const seekToFraction = (frac: number) => {
    const el = audioRef.current;
    const t = Math.max(0, Math.min(duration, frac * duration));
    setCurrentTime(t);
    if (el) el.currentTime = t;
  };

  const onReupload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !analysisId) return;
    await saveAudio(analysisId, file);
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
  };

  const fractionFromEvent = (e: React.MouseEvent | MouseEvent) => {
    const el = barsContainerRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  };

  const onBarsMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioUrl) return;
    // Shift+drag = create selection; plain click = seek
    if (e.shiftKey) {
      const frac = fractionFromEvent(e);
      const t = frac * duration;
      setLoopRange({ start: t, end: t });
      setLoopEnabled(true);
      setDragState({ mode: "create", anchor: t, current: t });
      e.preventDefault();
    }
  };

  // Global mouse handling for drags
  useEffect(() => {
    if (!dragState) return;
    const onMove = (e: MouseEvent) => {
      const frac = fractionFromEvent(e);
      const t = frac * duration;
      if (dragState.mode === "create") {
        const a = dragState.anchor;
        setLoopRange({ start: Math.min(a, t), end: Math.max(a, t) });
        setDragState({ mode: "create", anchor: a, current: t });
      } else if (dragState.mode === "move-start") {
        setLoopRange((r) => (r ? { start: Math.min(t, r.end - 0.1), end: r.end } : r));
      } else if (dragState.mode === "move-end") {
        setLoopRange((r) => (r ? { start: r.start, end: Math.max(t, r.start + 0.1) } : r));
      }
    };
    const onUp = () => setDragState(null);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragState, duration]);

  const onBarsClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioUrl) return;
    if (e.shiftKey || dragState) return; // handled by drag
    seekToFraction(fractionFromEvent(e));
  };

  const setLoopFromMarkers = () => {
    if (markers.length < 2) return;
    const sorted = [...markers].map((m) => parseTime(m.time)).sort((a, b) => a - b);
    setLoopRange({ start: sorted[0], end: sorted[sorted.length - 1] });
    setLoopEnabled(true);
  };

  const clearLoop = () => {
    setLoopRange(null);
    setLoopEnabled(false);
  };

  // Down/up-sample to ~160 bars
  const targetBars = 160;
  const bars = useMemo(() => {
    if (peaks.length === 0) return [];
    if (peaks.length <= targetBars) return peaks.map((p) => p.value);
    const step = peaks.length / targetBars;
    const out: number[] = [];
    for (let i = 0; i < targetBars; i++) {
      const start = Math.floor(i * step);
      const end = Math.floor((i + 1) * step);
      let m = 0;
      for (let j = start; j < end; j++) if (peaks[j].value > m) m = peaks[j].value;
      out.push(m);
    }
    return out;
  }, [peaks]);

  const colorFor = (type: WaveformMarker["type"]) =>
    type === "good"
      ? "oklch(0.78 0.18 230)"
      : type === "warning"
      ? "oklch(0.65 0.24 295)"
      : "oklch(0.7 0.02 270)";

  const playPct = duration > 0 ? (currentTime / duration) * 100 : 0;
  const playedFraction = duration > 0 ? currentTime / duration : 0;
  const loopStartPct = loopRange && duration > 0 ? (loopRange.start / duration) * 100 : 0;
  const loopEndPct = loopRange && duration > 0 ? (loopRange.end / duration) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Transport */}
      <div className="flex items-center gap-3 flex-wrap">
        <Button
          size="icon"
          variant={audioUrl ? "default" : "outline"}
          onClick={toggle}
          disabled={!audioUrl}
          className={audioUrl ? "bg-[image:var(--gradient-primary)] border-0 hover:opacity-90" : ""}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <div className="text-xs font-mono text-muted-foreground tabular-nums">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        {audioUrl && (
          <div className="flex items-center gap-2 ml-2">
            <Button
              size="sm"
              variant={loopEnabled ? "default" : "outline"}
              onClick={() => {
                if (!loopRange) {
                  // Default: 8-sec loop around current time
                  const start = Math.max(0, currentTime - 0);
                  const end = Math.min(duration, start + 8);
                  setLoopRange({ start, end });
                }
                setLoopEnabled((v) => !v);
              }}
              className={loopEnabled ? "bg-[image:var(--gradient-primary)] border-0" : ""}
            >
              <Repeat className="h-3.5 w-3.5" /> Loop {loopEnabled ? "on" : "off"}
            </Button>
            {markers.length >= 2 && (
              <Button size="sm" variant="ghost" onClick={setLoopFromMarkers}>
                Loop transitions
              </Button>
            )}
            {loopRange && (
              <>
                <span className="text-xs font-mono text-muted-foreground tabular-nums">
                  {formatTime(loopRange.start)} – {formatTime(loopRange.end)} (
                  {formatTime(Math.max(0, loopRange.end - loopRange.start))})
                </span>
                <Button size="icon" variant="ghost" onClick={clearLoop} aria-label="Clear loop">
                  <X className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        )}

        {!audioUrl && (
          <>
            <span className="text-xs text-muted-foreground">Track audio not stored locally</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="ml-auto"
            >
              <Upload className="h-3.5 w-3.5" /> Attach audio
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={onReupload}
            />
          </>
        )}
        {audioUrl && onMarkMissed && (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto"
            onClick={() => onMarkMissed(currentTime)}
            title="Die Engine hat an dieser Stelle einen Trackwechsel übersehen"
          >
            <Flag className="h-3.5 w-3.5" /> {lang === "de" ? "Übergang fehlt hier" : "Transition missing here"} ({formatTime(currentTime)})
          </Button>
        )}
        {audioUrl && <audio ref={audioRef} src={audioUrl} preload="metadata" />}
      </div>

      <div
        ref={barsContainerRef}
        className={`relative w-full rounded-md border border-border bg-card/40 overflow-hidden select-none ${
          audioUrl ? "cursor-pointer" : ""
        }`}
        style={{ height }}
        onMouseLeave={() => setHover(null)}
        onMouseDown={onBarsMouseDown}
        onClick={onBarsClick}
      >
        {/* Center axis */}
        <div className="absolute inset-x-0 top-1/2 h-px bg-border/60" />

        {/* Loop region highlight */}
        {loopRange && (
          <div
            className="absolute top-0 bottom-0 pointer-events-none"
            style={{
              left: `${loopStartPct}%`,
              width: `${Math.max(0, loopEndPct - loopStartPct)}%`,
              background: loopEnabled
                ? "oklch(0.65 0.24 295 / 0.18)"
                : "oklch(0.7 0.02 270 / 0.12)",
              borderLeft: "1px dashed oklch(0.78 0.18 230 / 0.7)",
              borderRight: "1px dashed oklch(0.78 0.18 230 / 0.7)",
            }}
          />
        )}

        {/* Bars */}
        <div className="absolute inset-0 flex items-center gap-[2px] px-1 pointer-events-none">
          {bars.map((v, i) => {
            const h = Math.max(2, (v / max) * (height - 8));
            const barFrac = (i + 0.5) / bars.length;
            const played = audioUrl && barFrac <= playedFraction;
            const barTime = barFrac * duration;
            const inLoop = loopRange && barTime >= loopRange.start && barTime <= loopRange.end;
            return (
              <div
                key={i}
                className="flex-1 rounded-sm bg-[image:var(--gradient-rk)]"
                style={{
                  height: h,
                  opacity: played ? 1 : inLoop ? 0.8 : 0.5,
                }}
              />
            );
          })}
        </div>

        {/* Loop handles */}
        {loopRange && audioUrl && (
          <>
            <div
              role="slider"
              aria-label="Loop start"
              className="absolute top-0 bottom-0 w-1.5 -translate-x-1/2 cursor-ew-resize z-10"
              style={{
                left: `${loopStartPct}%`,
                background: "oklch(0.78 0.18 230)",
                boxShadow: "0 0 8px oklch(0.78 0.18 230 / 0.8)",
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
                e.preventDefault();
                setDragState({ mode: "move-start" });
              }}
              onClick={(e) => e.stopPropagation()}
            />
            <div
              role="slider"
              aria-label="Loop end"
              className="absolute top-0 bottom-0 w-1.5 -translate-x-1/2 cursor-ew-resize z-10"
              style={{
                left: `${loopEndPct}%`,
                background: "oklch(0.78 0.18 230)",
                boxShadow: "0 0 8px oklch(0.78 0.18 230 / 0.8)",
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
                e.preventDefault();
                setDragState({ mode: "move-end" });
              }}
              onClick={(e) => e.stopPropagation()}
            />
          </>
        )}

        {/* Playhead */}
        {audioUrl && (
          <div
            className="absolute top-0 bottom-0 w-px bg-foreground/80 pointer-events-none"
            style={{ left: `${playPct}%`, boxShadow: "0 0 8px oklch(1 0 0 / 0.6)" }}
          />
        )}

        {/* Markers */}
        {markers.map((m, i) => {
          const sec = parseTime(m.time);
          const left = `${Math.min(100, Math.max(0, (sec / duration) * 100))}%`;
          const color = colorFor(m.type);
          return (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-px cursor-pointer"
              style={{ left, background: color, boxShadow: `0 0 8px ${color}` }}
              onMouseEnter={() => setHover(m)}
              onClick={(e) => {
                e.stopPropagation();
                if (audioUrl) seekToFraction(sec / duration);
              }}
            >
              <div
                className="absolute -top-1 -translate-x-1/2 h-2 w-2 rounded-full"
                style={{ left: 0, background: color }}
              />
              <div
                className="absolute -bottom-1 -translate-x-1/2 h-2 w-2 rounded-full"
                style={{ left: 0, background: color }}
              />
            </div>
          );
        })}

        {/* Hover tooltip */}
        {hover && (
          <div
            className="pointer-events-none absolute top-2 z-10 -translate-x-1/2 rounded-md border border-border bg-background/95 px-2 py-1 text-xs shadow-lg backdrop-blur"
            style={{ left: `${(parseTime(hover.time) / duration) * 100}%` }}
          >
            <span className="font-mono text-muted-foreground">{hover.time}</span>{" "}
            <span>{hover.label}</span>
          </div>
        )}
      </div>

      {/* Time axis */}
      <div className="flex justify-between text-[10px] font-mono text-muted-foreground px-1">
        <span>0:00</span>
        <span>{formatTime(duration / 2)}</span>
        <span>{formatTime(duration)}</span>
      </div>

      {/* Help / Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground pt-1">
        {markers.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: colorFor("good") }} />
              Good moment
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: colorFor("warning") }} />
              Transition issue
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: colorFor("info") }} />
              Info
            </span>
          </div>
        ) : <span />}
        {audioUrl && (
          <span className="text-[11px]">
            Tip: <kbd className="px-1 py-0.5 rounded border border-border bg-card/60 font-mono">Shift</kbd> + drag to set a loop · drag handles to refine
          </span>
        )}
      </div>
    </div>
  );
}
