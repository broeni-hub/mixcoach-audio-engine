// Premium full-set transition explorer. Renders a horizontal timeline with
// score-colored markers, filter chips, and an in-place detail panel for the
// selected transition. This is the main product surface for full-set reports.

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { fetchFeedback, sendVerdict, type Verdict } from "@/lib/groundtruth";
import { getPlayerPosition } from "@/lib/player-bus";
import { Link } from "@tanstack/react-router";
import {
  Filter as FilterIcon,
  Clock,
  ChevronRight,
  Sparkles,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Gauge,
  Play,
  ThumbsUp,
  ThumbsDown,
  X,
} from "lucide-react";

/** Springt im Waveform-Player zur Stelle und spielt ab (10s Vorlauf,
 *  damit der DJ den Uebergang im Kontext hoert). */
const FEEDBACK_TEXTS = {
  de: {
    correctToast: "Danke! Als echten Übergang bestätigt.",
    fpToast: "Danke! Als Fehlalarm markiert — das trainiert die Erkennung.",
    timingToast: (t: string) => `Danke! Echte Startstelle ${t} gespeichert — präziser geht's nicht.`,
    errToast: "Feedback konnte nicht gespeichert werden (Backend erreichbar?).",
    seekFirst: "Erst im Player die echte Startstelle ansteuern",
    seekFirstDesc: "Spiele den Track bis zu der Stelle, wo der Übergang wirklich beginnt — dann diesen Button klicken.",
    question: "Erkennung korrekt?",
    yes: "Stimmt",
    yesTitle: "Ja, hier ist wirklich ein Trackwechsel",
    no: "Kein Übergang",
    noTitle: "Nein, das ist kein Trackwechsel (z.B. Break im selben Track)",
    timing: "Startet woanders",
    timingTitle: "Der Übergang ist echt, beginnt aber woanders: Steuere im Player die echte Startstelle an und klicke dann hier.",
    listen: "Anhören",
    from: "ab",
  },
  en: {
    correctToast: "Thanks! Confirmed as a real transition.",
    fpToast: "Thanks! Marked as a false alarm — this trains the detection.",
    timingToast: (t: string) => `Thanks! True start ${t} saved — it doesn't get more precise.`,
    errToast: "Feedback could not be saved (backend reachable?).",
    seekFirst: "First seek to the true start in the player",
    seekFirstDesc: "Play the track to the point where the transition really begins — then click this button.",
    question: "Detection correct?",
    yes: "Correct",
    yesTitle: "Yes, this really is a track change",
    no: "Not a transition",
    noTitle: "No, this is not a track change (e.g. a break within the same track)",
    timing: "Starts elsewhere",
    timingTitle: "The transition is real but starts elsewhere: seek to the true start in the player, then click here.",
    listen: "Listen",
    from: "from",
  },
} as const;

function listenAt(sec: number) {
  window.dispatchEvent(
    new CustomEvent("mixcoach:listen", { detail: { sec: Math.max(0, sec - 10) } }),
  );
}
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SetTransition } from "@/lib/set-analysis";
import { useLang } from "@/lib/i18n";
import {
  classifyTransition,
  TRANSITION_META,
  type TransitionType,
} from "@/lib/api/transitionTypes";

// ---- Types ---------------------------------------------------------------

interface Props {
  analysisId: string;
  totalDurationSec: number;
  transitions: SetTransition[];
}

/** Kleine Ground-Truth-Leiste: DJ bestaetigt oder verwirft den erkannten
 *  Uebergang. Jede Antwort trainiert die Erkennungs-Engine. */
function VerdictButtons({ analysisId, index, midSec, verdicts, onChange }: {
  analysisId: string;
  index: number;
  midSec: number;
  verdicts: Record<string, { verdict: Verdict }>;
  onChange: (index: number, verdict: Verdict) => void;
}) {
  const current = verdicts[String(index)]?.verdict;

  const lang = useLang();
  const F = FEEDBACK_TEXTS[lang];

  const submit = async (verdict: Verdict, correctedSec?: number) => {
    const ok = await sendVerdict(analysisId, index, midSec, verdict, correctedSec);
    if (ok) {
      onChange(index, verdict);
      if (verdict === "correct") toast.success(F.correctToast);
      else if (verdict === "not_a_transition") toast.success(F.fpToast);
      else {
        const mm = Math.floor((correctedSec ?? 0) / 60);
        const ss = Math.floor((correctedSec ?? 0) % 60).toString().padStart(2, "0");
        toast.success(F.timingToast(`${mm}:${ss}`));
      }
    } else {
      toast.error(F.errToast);
    }
  };

  const submitTimingOff = () => {
    const { sec, hasAudio } = getPlayerPosition();
    if (!hasAudio || sec <= 0) {
      toast.message(F.seekFirst, { description: F.seekFirstDesc });
      return;
    }
    void submit("timing_off", sec);
  };

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground mr-1">{F.question}</span>
      <Button
        size="sm"
        variant={current === "correct" ? "default" : "outline"}
        className={current === "correct" ? "bg-emerald-500/80 hover:bg-emerald-500 border-0" : ""}
        onClick={() => submit("correct")}
        title={F.yesTitle}
      >
        <ThumbsUp className="h-3.5 w-3.5" /> {F.yes}
      </Button>
      <Button
        size="sm"
        variant={current === "not_a_transition" ? "default" : "outline"}
        className={current === "not_a_transition" ? "bg-orange-500/80 hover:bg-orange-500 border-0" : ""}
        onClick={() => submit("not_a_transition")}
        title={F.noTitle}
      >
        <ThumbsDown className="h-3.5 w-3.5" /> {F.no}
      </Button>
      <Button
        size="sm"
        variant={current === "timing_off" ? "default" : "outline"}
        className={current === "timing_off" ? "bg-sky-500/80 hover:bg-sky-500 border-0" : ""}
        onClick={submitTimingOff}
        title={F.timingTitle}
      >
        <Clock className="h-3.5 w-3.5" /> {F.timing}
      </Button>
    </div>
  );
}

interface Enriched extends SetTransition {
  type: TransitionType;
  confidence: number;
  mainIssue: string;
  strengths: string[];
  weaknesses: string[];
  timelineEvents: { time: string; label: string; tone: "good" | "warning" | "info" }[];
  aiFeedback: string;
  exercise: { title: string; description: string; xp: number };
}

type FilterKey = "all" | "weak" | "vocal" | "bass" | "low_conf";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Show all" },
  { key: "weak", label: "Only weak" },
  { key: "vocal", label: "Vocal issues" },
  { key: "bass", label: "Bass swap issues" },
  { key: "low_conf", label: "Low confidence" },
];

// ---- Score → color -------------------------------------------------------

function scoreTone(score: number) {
  if (score >= 85) return {
    label: "Green",
    text: "text-emerald-300",
    bg: "bg-emerald-400/15",
    border: "border-emerald-400/50",
    dot: "bg-emerald-400",
    ring: "ring-emerald-400/40",
  };
  if (score >= 70) return {
    label: "Yellow",
    text: "text-yellow-300",
    bg: "bg-yellow-400/15",
    border: "border-yellow-400/50",
    dot: "bg-yellow-400",
    ring: "ring-yellow-400/40",
  };
  if (score >= 55) return {
    label: "Orange",
    text: "text-orange-300",
    bg: "bg-orange-400/15",
    border: "border-orange-400/50",
    dot: "bg-orange-400",
    ring: "ring-orange-400/40",
  };
  return {
    label: "Red",
    text: "text-red-300",
    bg: "bg-red-500/15",
    border: "border-red-500/50",
    dot: "bg-red-500",
    ring: "ring-red-500/40",
  };
}

// ---- Enrichment ----------------------------------------------------------

// phrase_alignment_score und bpm_drift fliessen seit 31.07.2026 nicht mehr
// in Anzeige, Ratschlag oder Konfidenz ein - beide messen nicht, was ihr
// Name sagt (Begruendung und Zahlen: NOT_YET_MEASURED in
// app/api/analysis_mapper.py). Sie blieben hier ohnehin wirkungslos: die
// Bedingung phrase > 0 traf auf 258 von 258 Uebergaengen zu, |drift| < 5
// auf 250 von 258 - zwei Konstanten, die die Konfidenz nur aufgeblaeht
// haben. Die verbleibenden drei Terme sind auf 100 normiert.
function deriveConfidence(t: SetTransition): number {
  let c = 0;
  if (t.bpm_before > 0) c += 35;
  if (t.bpm_after > 0) c += 35;
  if (t.bass_overlap_score < 60) c += 30;
  return Math.max(0, Math.min(100, c));
}

function deriveMainIssue(t: SetTransition, type: TransitionType): string {
  const candidates: { label: string; severity: number }[] = [];
  // Kein Ratschlag mehr aus bpm_drift und phrase_alignment_score. "Off-phrase"
  // feuerte auf 44 % ALLER Uebergaenge, aus einem Raster, das am erkannten
  // Segmentanfang haengt - und der streut um ~3,4 Phrasen.
  if (t.bass_overlap_score > 65) candidates.push({ label: "Bass clash — both low ends played together", severity: t.bass_overlap_score });
  if (t.energy_dip_pct > 65) candidates.push({ label: "Energy collapses through the swap", severity: t.energy_dip_pct });
  if (t.energy_dip_pct < 8 && type !== "hard_cut") candidates.push({ label: "No energy contour — transition feels flat", severity: 60 });
  if (candidates.length === 0) {
    if (t.quality_score >= 85) return "No major issues — clean transition.";
    return "Minor inconsistencies in the blend.";
  }
  candidates.sort((a, b) => b.severity - a.severity);
  return candidates[0].label;
}

function deriveStrengthsWeaknesses(t: SetTransition, type: TransitionType): { strengths: string[]; weaknesses: string[] } {
  const strengths: string[] = [];
  const weaknesses: string[] = [];
  // "Tempo locked - drift under 1 BPM" wurde auf 96 % aller Uebergaenge
  // vergeben, weil bpm_drift in 89 % exakt 0 ist - ein Lob dafuer, dass der
  // Tempo-Schaetzer zweimal dieselbe Zahl geliefert hat. "Cue point lands on
  // a phrase boundary" auf 33 %, der Gegenvorwurf auf 44 %. Beides entfernt.
  if (t.bass_overlap_score < 40) strengths.push("Clean low-end handover, no bass clash.");
  else if (t.bass_overlap_score > 70) weaknesses.push("Bass overlap caused mud in the low end.");
  if (t.energy_dip_pct >= 25 && t.energy_dip_pct <= 50) strengths.push("Healthy energy dip — gives the blend room.");
  if (t.energy_dip_pct > 65) weaknesses.push("Energy drops too far through the swap.");
  if (type === "long_blend" && t.quality_score >= 75) strengths.push("Long blend held steady through 32+ bars.");
  if (type === "drop_swap" && t.quality_score >= 80) strengths.push("Drop-swap landed on the kick.");
  return { strengths, weaknesses };
}

function deriveAiFeedback(t: SetTransition, type: TransitionType, issue: string): string {
  const meta = TRANSITION_META[type];
  const grade =
    t.quality_score >= 85 ? "This is a clean transition."
    : t.quality_score >= 70 ? "Solid transition with room to tighten."
    : t.quality_score >= 55 ? "Workable, but the audience felt the seams."
    : "This one didn't land — worth re-cueing in practice.";
  return `${grade} You used a ${meta.label.toLowerCase()} pattern (${meta.description.toLowerCase()}). Main issue: ${issue.toLowerCase()} Focus your next session on locking this single fix; the rest of the swap is in your hands.`;
}

function deriveExercise(t: SetTransition, type: TransitionType): { title: string; description: string; xp: number } {
  // Sync-Drill und 16-Bar-Cue-Locking entfielen am 31.07.2026: beide wurden
  // aus bpm_drift bzw. phrase_alignment_score abgeleitet. Eine UEBUNG aus
  // einer Groesse zuzuweisen, die nicht misst, ist der schwerste Fall der
  // Ehrlichkeitsverletzung - der DJ investiert Zeit in ein Problem, das die
  // Engine nicht belegen kann.
  if (t.bass_overlap_score > 65) return {
    title: "Bass Swap Control",
    description: "Practice killing the low EQ on Deck A before raising the low EQ on Deck B. No overlap allowed.",
    xp: 35,
  };
  if (type === "long_blend") return {
    title: "32-Bar Endurance Blend",
    description: "Hold a full 32-bar blend without touching EQ. Get used to letting two tracks breathe together.",
    xp: 40,
  };
  if (type === "echo_out") return {
    title: "Echo Tail Timing",
    description: "Drop the outgoing track exactly when the echo tail hits 50% wet. Practice on five different transitions.",
    xp: 30,
  };
  return {
    title: "Replay & Re-Cue",
    description: "Re-cue this exact transition three times and listen back. Identify what changed each pass.",
    xp: 20,
  };
}

function deriveTimelineEvents(t: SetTransition): Enriched["timelineEvents"] {
  const ev: Enriched["timelineEvents"] = [];
  ev.push({ time: fmt(t.start_sec), label: "Outgoing track holds the floor", tone: "info" });
  if (t.energy_dip_pct > 25) ev.push({ time: fmt(t.start_sec + (t.end_sec - t.start_sec) * 0.4), label: `Energy dip ${t.energy_dip_pct}%`, tone: t.energy_dip_pct > 60 ? "warning" : "info" });
  if (t.bass_overlap_score > 60) ev.push({ time: fmt(t.mid_sec), label: "Bass overlap detected", tone: "warning" });
  if (t.loudness_jump_db != null && Math.abs(t.loudness_jump_db) >= 2)
    ev.push({ time: fmt(t.start_sec ?? t.mid_sec), label: `Pegelsprung ${t.loudness_jump_db > 0 ? "+" : ""}${t.loudness_jump_db.toFixed(1)} dB`, tone: Math.abs(t.loudness_jump_db) >= 4 ? "warning" : "info" });
  ev.push({ time: fmt(t.mid_sec), label: `Mix point · ${t.bpm_before || "?"} → ${t.bpm_after || "?"} BPM`, tone: t.label === "smooth" ? "good" : "info" });
  ev.push({ time: fmt(t.end_sec), label: "Incoming track owns the mix", tone: "good" });
  return ev;
}

function enrich(t: SetTransition): Enriched {
  const type = classifyTransition({
    duration_sec: Math.max(0, t.end_sec - t.start_sec),
    energy_dip_pct: t.energy_dip_pct,
    bpm_drift: t.bpm_drift,
    phrase_alignment_score: t.phrase_alignment_score,
    label: t.label,
  });
  const mainIssue = deriveMainIssue(t, type);
  const { strengths, weaknesses } = deriveStrengthsWeaknesses(t, type);
  return {
    ...t,
    type,
    confidence: deriveConfidence(t),
    mainIssue,
    strengths,
    weaknesses,
    timelineEvents: deriveTimelineEvents(t),
    aiFeedback: deriveAiFeedback(t, type, mainIssue),
    exercise: deriveExercise(t, type),
  };
}

// ---- Filters -------------------------------------------------------------

function applyFilter(items: Enriched[], key: FilterKey): Enriched[] {
  switch (key) {
    case "weak": return items.filter((t) => t.quality_score < 70);
    // Der Zusatz "|| phrase_alignment_score < 45" ist entfallen: er zog
    // Uebergaenge in den Vocal-Filter, die mit Gesang nichts zu tun haben.
    case "vocal": return items.filter((t) => t.type === "vocal_overlay");
    case "bass": return items.filter((t) => t.type === "bass_swap" && t.quality_score < 80 || t.bass_overlap_score > 65);
    case "low_conf": return items.filter((t) => t.confidence < 60);
    default: return items;
  }
}

// ---- Component -----------------------------------------------------------

export function SetTransitionsExplorer({ analysisId, totalDurationSec, transitions }: Props) {
  const lang = useLang();
  const F = FEEDBACK_TEXTS[lang];
  const enriched = useMemo(() => transitions.map(enrich), [transitions]);
  const [filter, setFilter] = useState<FilterKey>("all");

  // Ground-Truth-Feedback: gespeicherten Stand vom Backend holen.
  const [verdicts, setVerdicts] = useState<Record<string, { verdict: Verdict }>>({});
  useEffect(() => {
    let cancelled = false;
    void fetchFeedback(analysisId).then((f) => {
      if (!cancelled && f) setVerdicts(f.verdicts ?? {});
    });
    return () => { cancelled = true; };
  }, [analysisId]);
  const onVerdictChange = (index: number, verdict: Verdict) =>
    setVerdicts((v) => ({ ...v, [String(index)]: { verdict } }));
  const [selectedIdx, setSelectedIdx] = useState<number | null>(
    enriched.length > 0 ? enriched[0].index : null,
  );

  const filtered = useMemo(() => applyFilter(enriched, filter), [enriched, filter]);
  const selected = enriched.find((t) => t.index === selectedIdx) ?? null;

  const ticks = useMemo(() => buildTicks(totalDurationSec), [totalDurationSec]);

  const counts: Record<FilterKey, number> = {
    all: enriched.length,
    weak: applyFilter(enriched, "weak").length,
    vocal: applyFilter(enriched, "vocal").length,
    bass: applyFilter(enriched, "bass").length,
    low_conf: applyFilter(enriched, "low_conf").length,
  };

  return (
    <div className="space-y-5">
      {/* Filter chips */}
      <div className="flex flex-wrap items-center gap-2">
        <FilterIcon className="h-4 w-4 text-muted-foreground" />
        {FILTERS.map((f) => {
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                active
                  ? "border-primary/60 bg-primary/15 text-primary"
                  : "border-border bg-card/40 text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              {f.label} <span className="ml-1 opacity-60">({counts[f.key]})</span>
            </button>
          );
        })}
      </div>

      {/* Horizontal timeline */}
      <div className="relative h-32 rounded-xl border border-border bg-gradient-to-b from-card/60 to-card/20 overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[2px] bg-[image:var(--gradient-rk)] opacity-70" />
        {/* baseline */}
        <div className="absolute left-0 right-0 top-1/2 h-px bg-border/60" />
        {/* tick marks */}
        {ticks.map((t) => (
          <div
            key={t.sec}
            className="absolute top-0 bottom-0 border-l border-border/30"
            style={{ left: `${(t.sec / Math.max(1, totalDurationSec)) * 100}%` }}
          >
            <span className="absolute bottom-1 left-1 text-[10px] font-mono text-muted-foreground">
              {fmt(t.sec)}
            </span>
          </div>
        ))}
        {/* markers */}
        {filtered.map((t) => {
          const tone = scoreTone(t.quality_score);
          const meta = TRANSITION_META[t.type];
          const Icon = meta.icon;
          const left = ((t.start_sec ?? t.mid_sec) / Math.max(1, totalDurationSec)) * 100;
          const active = selected?.index === t.index;
          return (
            <button
              key={t.index}
              onClick={() => setSelectedIdx(t.index)}
              className="group absolute top-2 -translate-x-1/2 flex flex-col items-center focus:outline-none"
              style={{ left: `${left}%` }}
              title={`T${t.index} · ${meta.label} · ${t.quality_score}/100`}
            >
              <span
                className={`flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-mono backdrop-blur-sm transition-all ${tone.bg} ${tone.border} ${tone.text} ${
                  active ? `ring-2 ${tone.ring} scale-105` : "hover:scale-110"
                }`}
              >
                <Icon className="h-3 w-3" />
                <span className="font-bold">{t.quality_score}</span>
              </span>
              <span className="mt-1 text-[10px] font-mono text-muted-foreground/80 group-hover:text-foreground">
                {fmt(t.start_sec ?? t.mid_sec)}
              </span>
              <span className={`mt-0.5 h-3 w-px ${tone.dot}`} />
            </button>
          );
        })}
        {filtered.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
            No transitions match this filter.
          </div>
        )}
      </div>

      {/* List + detail */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* List */}
        <ul className="lg:col-span-2 space-y-2 max-h-[560px] overflow-y-auto pr-1">
          {filtered.map((t) => {
            const tone = scoreTone(t.quality_score);
            const meta = TRANSITION_META[t.type];
            const Icon = meta.icon;
            const active = selected?.index === t.index;
            return (
              <li key={t.index}>
                <button
                  onClick={() => setSelectedIdx(t.index)}
                  className={`w-full text-left rounded-lg border p-3 transition-all ${
                    active
                      ? `${tone.border} ${tone.bg} ring-1 ${tone.ring}`
                      : "border-border bg-card/40 hover:bg-card hover:border-border"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`h-9 w-9 rounded-md ${tone.bg} ${tone.text} border ${tone.border} flex items-center justify-center shrink-0`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground">{F.from} {fmt(t.start_sec ?? t.mid_sec)}</span>
                        <span className="text-sm font-semibold truncate">T{t.index} · {meta.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{t.mainIssue}</p>
                      {t.loudness_jump_db != null && Math.abs(t.loudness_jump_db) >= 2 && (
                        <span className={`mt-0.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-mono ${Math.abs(t.loudness_jump_db) >= 4 ? "bg-red-500/15 text-red-400" : "bg-amber-500/15 text-amber-500"}`}>
                          {t.loudness_jump_db > 0 ? "+" : ""}{t.loudness_jump_db.toFixed(1)} dB
                        </span>
                      )}
                      {(t.track_out || t.track_in) && (
                        <p className="text-xs truncate mt-0.5 text-primary">
                          {t.position_estimated && (
                            <span className="text-amber-500" title="Position in einer Erkennungslücke geschätzt">≈ </span>
                          )}
                          {t.track_out ?? "?"} → {t.track_in ?? "?"}
                        </p>
                      )}
                    </div>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Uebergang T${t.index} anhoeren`}
                      title={F.listen}
                      onClick={(e) => { e.stopPropagation(); listenAt(t.start_sec); }}
                      onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); listenAt(t.start_sec); } }}
                      className="h-8 w-8 rounded-md border border-border bg-background/40 hover:bg-background flex items-center justify-center shrink-0"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </span>
                    <div className="text-right shrink-0">
                      <div className={`font-display text-xl font-bold leading-none ${tone.text}`}>{t.quality_score}</div>
                      <div className="text-[10px] text-muted-foreground mt-1">conf {t.confidence}</div>
                    </div>
                    <ChevronRight className={`h-4 w-4 shrink-0 ${active ? tone.text : "text-muted-foreground/50"}`} />
                  </div>
                </button>
              </li>
            );
          })}
        </ul>

        {/* Detail panel */}
        <div className="lg:col-span-3">
          {selected ? (
            <TransitionDetailPanel
              analysisId={analysisId}
              t={selected}
              onClose={() => setSelectedIdx(null)}
              verdicts={verdicts}
              onVerdictChange={onVerdictChange}
            />
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-card/30 p-10 text-center text-sm text-muted-foreground">
              Pick a transition from the timeline to see the breakdown.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---- Detail panel --------------------------------------------------------

function TransitionDetailPanel({
  analysisId, t, onClose, verdicts, onVerdictChange,
}: {
  analysisId: string; t: Enriched; onClose: () => void;
  verdicts: Record<string, { verdict: Verdict }>;
  onVerdictChange: (index: number, verdict: Verdict) => void;
}) {
  const lang = useLang();
  const F = FEEDBACK_TEXTS[lang];
  const tone = scoreTone(t.quality_score);
  const meta = TRANSITION_META[t.type];
  const Icon = meta.icon;
  const duration = Math.max(0, t.end_sec - t.start_sec);

  return (
    <div className={`rounded-xl border ${tone.border} bg-card/60 overflow-hidden`}>
      <div className={`px-5 py-4 ${tone.bg} border-b ${tone.border} flex items-start justify-between gap-3`}>
        <div className="flex items-start gap-3">
          <span className={`h-10 w-10 rounded-md border ${tone.border} ${tone.text} bg-background/40 flex items-center justify-center shrink-0`}>
            <Icon className="h-5 w-5" />
          </span>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-display text-lg font-bold">T{t.index} · {meta.label}</h3>
              <Badge variant="outline" className={`${tone.text} ${tone.border}`}>{tone.label}</Badge>
              {t.detection === "fingerprint" && !t.position_estimated && (
                <Badge
                  variant="outline"
                  className="text-primary border-primary/40"
                  title="Per Library-Fingerprint erkannt: Tracks und Übergangszeitpunkt stammen aus dem Abgleich mit deiner eigenen Sammlung (sekundengenau), nicht aus einer Schätzung."
                >
                  Fingerprint
                </Badge>
              )}
              {t.position_estimated && (
                <Badge
                  variant="outline"
                  className="text-amber-500 border-amber-500/40"
                  title={`Der Trackwechsel ist sicher erkannt (zwei verschiedene Tracks aus deiner Sammlung). Zwischen den erkannten Abschnitten liegt aber eine Lücke${t.gap_seconds ? ` von ${Math.round(t.gap_seconds)} s` : ""} ohne Fingerprint – die genaue Position des Übergangs in dieser Lücke ist geschätzt (Lückenmitte), nicht sekundengenau.`}
                >
                  ≈ Position geschätzt
                </Badge>
              )}
            </div>
            {(t.track_out || t.track_in) && (
              <p className="text-sm text-primary mt-1 truncate max-w-[420px]">
                {t.track_out ?? "?"} → {t.track_in ?? "?"}
              </p>
            )}
            {t.possible_unrecognized_track && (
              <p className="text-xs text-amber-500/90 mt-1 max-w-[420px]">
                Große Lücke{t.gap_seconds ? ` (${Math.round(t.gap_seconds)} s)` : ""} – hier lief evtl. noch ein weiterer, nicht erkannter Track. Der Übergang könnte in Wirklichkeit mehrere Wechsel sein.
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">{meta.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            onClick={() => listenAt(t.start_sec)}
            className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90"
            title={`Ab ${fmt(Math.max(0, t.start_sec - 10))} abspielen`}
          >
            <Play className="h-3.5 w-3.5" /> {F.listen}
          </Button>
          <VerdictButtons
            analysisId={analysisId}
            index={t.index}
            midSec={t.mid_sec}
            verdicts={verdicts}
            onChange={onVerdictChange}
          />
          <div className="text-right">
            <div className={`font-display text-3xl font-bold leading-none ${tone.text}`}>{t.quality_score}</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-1">Score</div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Meta grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <MetaCell icon={Clock} label="Start" value={fmt(t.start_sec)} />
          <MetaCell icon={Clock} label="End" value={fmt(t.end_sec)} />
          <MetaCell icon={Activity} label="Duration" value={`${Math.round(duration)}s`} />
          <MetaCell icon={Gauge} label="Confidence" value={`${t.confidence}%`} />
        </div>

        {/* Main issue */}
        <div className={`rounded-lg border ${tone.border} ${tone.bg} p-3`}>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Main issue</p>
          <p className={`text-sm font-medium mt-1 ${tone.text}`}>{t.mainIssue}</p>
        </div>

        {/* Timeline events */}
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Timeline events</p>
          <ol className="space-y-1.5">
            {t.timelineEvents.map((e, i) => {
              const c =
                e.tone === "good" ? "text-emerald-300 border-emerald-400/40 bg-emerald-400/10"
                : e.tone === "warning" ? "text-orange-300 border-orange-400/40 bg-orange-400/10"
                : "text-muted-foreground border-border bg-card/40";
              return (
                <li key={i} className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-mono ${c}`}>
                    <Clock className="h-3 w-3" /> {e.time}
                  </span>
                  <span className="text-xs">{e.label}</span>
                </li>
              );
            })}
          </ol>
        </div>

        {/* Coach feedback: ECHTER Backend-Satz mit Messwerten (DE/EN),
            der abgeleitete Demo-Text nur noch als Fallback. */}
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
          <p className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-primary">
            <Sparkles className="h-3.5 w-3.5" /> Coach feedback
          </p>
          <p className="text-sm mt-2 leading-relaxed">
            {(lang === "en" ? (t.feedback_en ?? t.feedback) : t.feedback) ?? t.aiFeedback}
          </p>
        </div>

        <div className="flex justify-end">
          <Button asChild size="sm" variant="outline">
            <Link
              to="/app/analyses/$id/transitions/$tIdx"
              params={{ id: analysisId, tIdx: String(t.index) }}
            >
              Open full transition view <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

function MetaCell({ icon: Icon, label, value }: { icon: typeof Clock; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/40 p-2.5">
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div className="font-display text-sm font-bold mt-1">{value}</div>
    </div>
  );
}

// ---- utils ---------------------------------------------------------------

function fmt(s: number): string {
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(Math.floor(s % 60)).padStart(2, "0");
  return `${mm}:${ss}`;
}

function buildTicks(total: number): { sec: number }[] {
  if (total <= 0) return [];
  const target = 6;
  const stepRaw = total / target;
  const candidates = [30, 60, 120, 300, 600, 900];
  const step = candidates.find((c) => c >= stepRaw) ?? candidates[candidates.length - 1];
  const out: { sec: number }[] = [];
  for (let s = 0; s <= total; s += step) out.push({ sec: s });
  return out;
}
