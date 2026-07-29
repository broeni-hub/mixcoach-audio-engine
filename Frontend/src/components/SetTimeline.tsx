// Professional set-wide timeline visualization. Renders one tick per
// transition along a horizontal ruler with timestamps. Markers are colored
// by transition type and clickable.

import { useMemo } from "react";
import { Link } from "@tanstack/react-router";
import type { SetTransition } from "@/lib/set-analysis";
import { classifyTransition, TRANSITION_META, type TransitionType } from "@/lib/api/transitionTypes";

interface Props {
  analysisId: string;
  totalDurationSec: number;
  transitions: SetTransition[];
}

interface EnrichedTransition extends SetTransition {
  type: TransitionType;
}

export function SetTimeline({ analysisId, totalDurationSec, transitions }: Props) {
  const enriched: EnrichedTransition[] = useMemo(
    () =>
      transitions.map((t) => ({
        ...t,
        type: classifyTransition({
          duration_sec: Math.max(0, t.end_sec - t.start_sec),
          energy_dip_pct: t.energy_dip_pct,
          bpm_drift: t.bpm_drift,
          phrase_alignment_score: t.phrase_alignment_score,
          label: t.label,
        }),
      })),
    [transitions],
  );

  const ticks = useMemo(() => buildTicks(totalDurationSec), [totalDurationSec]);

  return (
    <div className="space-y-4">
      {/* Ruler */}
      <div className="relative h-20 rounded-xl border border-border bg-card/40 overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[2px] bg-[image:var(--gradient-rk)] opacity-60" />
        {/* tick marks */}
        {ticks.map((t) => (
          <div
            key={t.sec}
            className="absolute top-0 bottom-0 border-l border-border/40"
            style={{ left: `${(t.sec / totalDurationSec) * 100}%` }}
          >
            <span className="absolute -top-[1px] left-1 text-[10px] font-mono text-muted-foreground">
              {fmt(t.sec)}
            </span>
          </div>
        ))}
        {/* transition markers */}
        {enriched.map((t) => {
          const meta = TRANSITION_META[t.type];
          const Icon = meta.icon;
          const left = (t.mid_sec / Math.max(1, totalDurationSec)) * 100;
          return (
            <Link
              key={t.index}
              to="/app/analyses/$id/transitions/$tIdx"
              params={{ id: analysisId, tIdx: String(t.index) }}
              className="group absolute top-7 -translate-x-1/2"
              style={{ left: `${left}%` }}
              title={`${meta.label} • T${t.index} @ ${fmt(t.mid_sec)} • score ${t.quality_score}`}
            >
              <span
                className={`flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-mono backdrop-blur-sm transition-all hover:scale-110 ${meta.border} ${meta.bg} ${meta.color}`}
              >
                <Icon className="h-3 w-3" />
                {t.quality_score}
              </span>
              <span
                className={`mx-auto block h-6 w-px ${meta.color.replace("text-", "bg-")} opacity-60`}
              />
            </Link>
          );
        })}
      </div>

      {/* Detail list */}
      <ul className="space-y-2">
        {enriched.map((t) => {
          const meta = TRANSITION_META[t.type];
          const Icon = meta.icon;
          return (
            <li key={t.index}>
              <Link
                to="/app/analyses/$id/transitions/$tIdx"
                params={{ id: analysisId, tIdx: String(t.index) }}
                className={`flex items-center gap-3 rounded-lg border ${meta.border} ${meta.bg} px-3 py-2.5 text-sm transition-colors hover:bg-card`}
              >
                <span className={`h-7 w-7 rounded-md ${meta.bg} ${meta.color} flex items-center justify-center border ${meta.border}`}>
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <span className="font-mono text-xs w-14 text-muted-foreground">{fmt(t.mid_sec)}</span>
                <span className={`font-medium ${meta.color}`}>{meta.label}</span>
                <span className="text-xs text-muted-foreground">
                  {t.bpm_before || "?"} → {t.bpm_after || "?"} BPM
                  {t.bpm_drift > 0 && <> • drift {t.bpm_drift.toFixed(2)}</>}
                  {" • "}phrase {t.phrase_alignment_score}/100
                </span>
                <span className="ml-auto font-display text-lg font-bold w-10 text-right">{t.quality_score}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function fmt(s: number): string {
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(Math.floor(s % 60)).padStart(2, "0");
  return `${mm}:${ss}`;
}

function buildTicks(total: number): { sec: number }[] {
  const target = 6;
  const stepRaw = total / target;
  // Snap to a friendly minute multiple
  const candidates = [30, 60, 120, 300, 600];
  const step = candidates.find((c) => c >= stepRaw) ?? candidates[candidates.length - 1];
  const out: { sec: number }[] = [];
  for (let s = 0; s <= total; s += step) out.push({ sec: s });
  return out;
}
