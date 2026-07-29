// Transition taxonomy: shared types, colors, icons. The classifier lives in
// the provider layer (today a heuristic over existing set-analysis output;
// tomorrow a Python model). The UI imports only this file.

import {
  Sliders,
  ArrowLeftRight,
  Waves,
  Scissors,
  Volume2,
  Filter,
  Repeat,
  Zap,
  Mic,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";

export type TransitionType =
  | "eq_blend"
  | "bass_swap"
  | "long_blend"
  | "hard_cut"
  | "echo_out"
  | "filter"
  | "loop"
  | "drop_swap"
  | "vocal_overlay"
  | "unknown";

export const TRANSITION_TYPES: TransitionType[] = [
  "eq_blend",
  "bass_swap",
  "long_blend",
  "hard_cut",
  "echo_out",
  "filter",
  "loop",
  "drop_swap",
  "vocal_overlay",
  "unknown",
];

interface TransitionMeta {
  label: string;
  description: string;
  icon: LucideIcon;
  /** Tailwind-friendly tone using design-system tokens. */
  color: string; // text color
  bg: string;
  border: string;
}

export const TRANSITION_META: Record<TransitionType, TransitionMeta> = {
  eq_blend: {
    label: "EQ Blend",
    description: "Three-band EQ swap across a long overlap",
    icon: Sliders,
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/40",
  },
  bass_swap: {
    label: "Bass Swap",
    description: "Classic low-EQ cut on outgoing, low-EQ up on incoming",
    icon: ArrowLeftRight,
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-primary/40",
  },
  long_blend: {
    label: "Long Blend",
    description: "32+ bars of overlap, subtle mix",
    icon: Waves,
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  hard_cut: {
    label: "Hard Cut",
    description: "Instant switch on a phrase boundary",
    icon: Scissors,
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-primary/40",
  },
  echo_out: {
    label: "Echo Out",
    description: "Delay/reverb tail covers the transition",
    icon: Volume2,
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  filter: {
    label: "Filter Transition",
    description: "High- or low-pass filter sweep",
    icon: Filter,
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  loop: {
    label: "Loop Transition",
    description: "Beat loop bridges the swap",
    icon: Repeat,
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-primary/30",
  },
  drop_swap: {
    label: "Drop Swap",
    description: "Swap exactly on a drop",
    icon: Zap,
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-primary/40",
  },
  vocal_overlay: {
    label: "Vocal Overlay",
    description: "Vocal phrase of A rides over intro of B",
    icon: Mic,
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  unknown: {
    label: "Mix Point",
    description: "Detected transition, classifier unsure",
    icon: HelpCircle,
    color: "text-muted-foreground",
    bg: "bg-card/40",
    border: "border-border",
  },
};

/** Heuristic classifier — runs in the local provider until a real model
 *  takes over. Inputs come from set-analysis output. */
export function classifyTransition(t: {
  duration_sec?: number;
  energy_dip_pct?: number;
  bpm_drift?: number;
  phrase_alignment_score?: number;
  label?: string;
}): TransitionType {
  const dur = t.duration_sec ?? 16;
  const dip = t.energy_dip_pct ?? 20;
  const drift = Math.abs(t.bpm_drift ?? 0);

  if (dur < 4 && dip < 10) return "hard_cut";
  if (dur < 4 && dip > 30) return "drop_swap";
  if (dur > 48) return "long_blend";
  if (dip > 45) return "echo_out";
  if (dip > 25 && dur >= 8 && dur <= 24) return "bass_swap";
  if (dip < 15 && dur >= 16) return "eq_blend";
  if (drift > 1.5) return "filter";
  return "unknown";
}
