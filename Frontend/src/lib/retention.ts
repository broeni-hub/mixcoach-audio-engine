// Retention & growth helpers: streaks, monthly reports, DJ DNA, community.
// Pure frontend — derives everything from AppState.
import type { AppState } from "./store";
import type { AnalysisResult, AnalysisScores } from "./analysis";

const DAY = 86_400_000;

// ---------- Streak ----------
export interface StreakInfo {
  current: number;
  longest: number;
  trainedToday: boolean;
  weekDays: { date: Date; label: string; trained: boolean; isToday: boolean }[];
  trainedThisWeek: number;
  missedThisWeek: number;
  freezesAvailable: number;
  nextReward: { at: number; label: string; xp: number };
}

function startOfDay(d: Date) { const x = new Date(d); x.setHours(0,0,0,0); return x; }

export function computeStreak(state: AppState): StreakInfo {
  const days = new Set(
    state.analyses.map((a) => startOfDay(new Date(a.createdAt)).getTime()),
  );
  const today = startOfDay(new Date()).getTime();
  let current = 0;
  let cursor = today;
  // grace: if no training today, allow streak to count up to yesterday
  if (!days.has(cursor)) cursor -= DAY;
  while (days.has(cursor)) { current++; cursor -= DAY; }

  // longest
  const sorted = [...days].sort((a, b) => a - b);
  let longest = 0, run = 0, prev = 0;
  for (const t of sorted) {
    run = (prev && t - prev === DAY) ? run + 1 : 1;
    longest = Math.max(longest, run);
    prev = t;
  }

  // current week (Mon-Sun)
  const now = new Date();
  const dow = (now.getDay() + 6) % 7; // 0 = Monday
  const monday = startOfDay(new Date(now.getTime() - dow * DAY));
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday.getTime() + i * DAY);
    return {
      date: d,
      label: ["Mo","Tu","We","Th","Fr","Sa","Su"][i],
      trained: days.has(d.getTime()),
      isToday: d.getTime() === today,
    };
  });
  const trainedThisWeek = weekDays.filter((d) => d.trained).length;
  const todayIdx = weekDays.findIndex((d) => d.isToday);
  const missedThisWeek = weekDays
    .slice(0, todayIdx + 1)
    .filter((d) => !d.trained).length;

  const rewards = [3, 7, 14, 30, 60, 100];
  const next = rewards.find((r) => r > current) ?? current + 7;
  const nextReward = {
    at: next,
    label: next <= 7 ? "Streak Starter badge" : next <= 14 ? "Bronze Streak badge" : next <= 30 ? "Silver Streak badge" : "Gold Streak badge",
    xp: next * 10,
  };

  return {
    current,
    longest,
    trainedToday: days.has(today),
    weekDays,
    trainedThisWeek,
    missedThisWeek,
    freezesAvailable: 1,
    nextReward,
  };
}

// ---------- Monthly Report ----------
const SKILL_KEYS = ["beatmatching","eq","timing","flow","musicality","creativity"] as const;
type SkillKey = typeof SKILL_KEYS[number];

const SKILL_LABEL: Record<SkillKey, string> = {
  beatmatching: "Your Timing",
  eq: "Clean Mixing",
  timing: "Transition Flow",
  flow: "Crowd Momentum",
  musicality: "Track Pairing",
  creativity: "Your Signature",
};

function avgScores(items: AnalysisResult[]): Partial<AnalysisScores> {
  if (!items.length) return {};
  const sum: Record<string, number> = {};
  for (const a of items) for (const k of [...SKILL_KEYS, "overall"]) sum[k] = (sum[k] ?? 0) + (a.scores as any)[k];
  const out: any = {};
  for (const k of Object.keys(sum)) out[k] = Math.round(sum[k] / items.length);
  return out;
}

export interface MonthlyReport {
  monthLabel: string;
  monthStart: Date;
  uploads: number;
  avgOverallNow: number;
  avgOverallPrev: number;
  improvementDelta: number;
  skillDeltas: { key: SkillKey; label: string; now: number; prev: number; delta: number }[];
  bestTransition: AnalysisResult | null;
  weakest: { key: SkillKey; label: string; value: number } | null;
  summary: string;
  nextFocus: string;
}

export function computeMonthlyReport(state: AppState, offset = 0): MonthlyReport {
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth() - offset, 1);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() - offset + 1, 1);
  const prevStart = new Date(now.getFullYear(), now.getMonth() - offset - 1, 1);

  const inRange = (a: AnalysisResult, s: Date, e: Date) => {
    const t = new Date(a.createdAt).getTime();
    return t >= s.getTime() && t < e.getTime();
  };
  const cur = state.analyses.filter((a) => inRange(a, monthStart, monthEnd));
  const prev = state.analyses.filter((a) => inRange(a, prevStart, monthStart));

  const curAvg = avgScores(cur);
  const prevAvg = avgScores(prev);

  const skillDeltas = SKILL_KEYS.map((k) => {
    const n = (curAvg as any)[k] ?? 0;
    const p = (prevAvg as any)[k] ?? 0;
    return { key: k, label: SKILL_LABEL[k], now: n, prev: p, delta: n - p };
  }).sort((a, b) => b.delta - a.delta);

  const best = cur.reduce<AnalysisResult | null>(
    (acc, a) => (!acc || (a.scores.overall ?? -1) > (acc.scores.overall ?? -1) ? a : acc),
    null,
  );
  const weakestEntry = SKILL_KEYS
    .map((k) => ({ key: k, label: SKILL_LABEL[k], value: (curAvg as any)[k] ?? 0 }))
    .filter((s) => s.value > 0)
    .sort((a, b) => a.value - b.value)[0] ?? null;

  const avgNow = (curAvg as any).overall ?? 0;
  const avgPrev = (prevAvg as any).overall ?? 0;
  const delta = avgNow - avgPrev;

  let summary = "Not enough sessions yet — upload a few more this month and I can show you how things are moving.";
  if (cur.length >= 1) {
    if (avgPrev > 0) {
      summary = `Your mixes are sounding ${
        delta >= 3 ? "noticeably better than last month — clear progress." :
        delta >= 0 ? "about as confident as last month — you're holding ground." :
        "a bit less tight than last month — let's rebuild momentum."
      } ${skillDeltas[0]?.delta > 1 ? `Your ${skillDeltas[0].label.toLowerCase()} is where the biggest jump happened.` : ""}`;
    } else {
      summary = `You uploaded ${cur.length} session${cur.length === 1 ? "" : "s"} this month — a baseline I can actually measure against next month.`;
    }
  }

  const nextFocus = weakestEntry
    ? `${weakestEntry.label} is the area to put your attention on next month.`
    : "Keep uploading and your next focus area will become obvious.";

  return {
    monthLabel: monthStart.toLocaleString(undefined, { month: "long", year: "numeric" }),
    monthStart,
    uploads: cur.length,
    avgOverallNow: avgNow,
    avgOverallPrev: avgPrev,
    improvementDelta: delta,
    skillDeltas,
    bestTransition: best,
    weakest: weakestEntry,
    summary,
    nextFocus,
  };
}

// ---------- DJ DNA ----------
export type Archetype =
  | "Smooth Blender" | "Energy Builder" | "Technical Mixer"
  | "Creative Risk Taker" | "Groove Keeper" | "Peak-Time Driver";

export interface DjDna {
  mainGenre: string;
  mixStyle: string;
  strengths: { key: SkillKey; label: string; value: number }[];
  weaknesses: { key: SkillKey; label: string; value: number }[];
  signatureTransition: string;
  archetype: Archetype;
  tagline: string;
  archetypeDescription: string;
  archetypeStory: string;
}


const ARCHETYPE_COPY: Record<Archetype, { description: string; story: string }> = {
  "Smooth Blender": {
    description: "You favour long, seamless blends where the listener never notices the switch.",
    story: "You have a calm, patient hand. Long blends feel natural because you let tracks breathe. You build trust with the listener by never rushing the switch. Your biggest strength is continuity. The next step is learning when to break the smoothness with a single bold moment.",
  },
  "Energy Builder": {
    description: "You ride the curve — every transition lifts the dance floor a notch.",
    story: "You live for the climb. Every transition lifts the room higher, and you know how to stack tension. Your biggest strength is momentum. The next step is mastering the subtle down-moments that make peaks feel bigger.",
  },
  "Technical Mixer": {
    description: "Your timing and your clean mixing are your superpower. Everything lines up.",
    story: "You trust precision. Your timing, your clean mixing, and your phrase work are where you shine. Your biggest strength is clean execution. The next step is loosening up occasionally to let some human feel in.",
  },
  "Creative Risk Taker": {
    description: "You break rules to make moments — unexpected key shifts and bold edits.",
    story: "You love taking creative risks and surprising listeners with unexpected blends. Your biggest strength is creating memorable moments. The next step is improving consistency without losing your identity.",
  },
  "Groove Keeper": {
    description: "You protect the pocket. The groove never falters under your hand.",
    story: "You protect the pocket above all. The rhythm never falters under your hand, and dancers feel safe with you. Your biggest strength is reliability. The next step is adding more dynamic energy shifts without disturbing the groove.",
  },
  "Peak-Time Driver": {
    description: "You live for the drop — sharp cuts, big payoffs, no apologies.",
    story: "You are built for peak time. Big drops, sharp cuts, and explosive payoffs are your language. Your biggest strength is impact. The next step is building the patience to earn those moments earlier in the set.",
  },
};


export function computeDjDna(state: AppState): DjDna {
  const items = state.analyses;
  const avg = avgScores(items) as any;
  const ranked = SKILL_KEYS
    .map((k) => ({ key: k, label: SKILL_LABEL[k], value: avg[k] ?? 0 }))
    .sort((a, b) => b.value - a.value);

  const strengths = ranked.slice(0, 2);
  const weaknesses = ranked.slice(-2).reverse();

  // Determine signature transition from average transition length
  const lengths = items.map((a) => a.transitionLength).filter((n): n is number => n != null && n > 0);
  const avgLen = lengths.length ? lengths.reduce((s, n) => s + n, 0) / lengths.length : 16;
  const signatureTransition =
    avgLen >= 32 ? "Long Blend (32+ bars)" :
    avgLen >= 16 ? "Classic 16-Bar Blend" :
    avgLen >= 8  ? "Short Cut (8 bars)" :
                   "Quick Cut / Cut Mix";

  // Archetype: highest-skill bias + length
  const top = ranked[0]?.key;
  let archetype: Archetype = "Groove Keeper";
  if (top === "beatmatching" || top === "eq") archetype = "Technical Mixer";
  else if (top === "flow") archetype = avgLen >= 24 ? "Smooth Blender" : "Energy Builder";
  else if (top === "creativity") archetype = "Creative Risk Taker";
  else if (top === "musicality") archetype = "Smooth Blender";
  else if (top === "timing") archetype = "Groove Keeper";

  // Override for peak-time vibe: high creativity + flow + short transitions
  if ((avg.flow ?? 0) >= 80 && (avg.creativity ?? 0) >= 75 && avgLen < 16) archetype = "Peak-Time Driver";

  const mainGenre = state.profile.genres[0] ?? "Melodic House";
  const mixStyle =
    avgLen >= 24 ? "Long, hypnotic blends" :
    avgLen >= 12 ? "Phrase-aligned 16-bar mixing" :
                   "Tight, energetic cuts";

  return {
    mainGenre,
    mixStyle,
    strengths,
    weaknesses,
    signatureTransition,
    archetype,
    tagline: `${mainGenre} · ${archetype}`,
    archetypeDescription: ARCHETYPE_COPY[archetype].description,
    archetypeStory: ARCHETYPE_COPY[archetype].story,
  };
}

// ---------- Community Challenges (preview) ----------
export interface CommunityChallenge {
  id: string;
  title: string;
  description: string;
  badge: string;
  premium: boolean;
  eta: string;
}

export const COMMUNITY_CHALLENGES: CommunityChallenge[] = [
  { id: "eq-weekly", title: "Cleanest Mix of the Week", description: "Upload a three-band swap that sounds genuinely clean and uncrowded.", badge: "Clean Mixer", premium: false, eta: "Coming soon" },
  { id: "bass-swap", title: "Best Bass Swap", description: "The cleanest low-end handover between two tracks — voted by the community.", badge: "Bass Architect", premium: true, eta: "Coming soon" },
  { id: "long-blend", title: "Smoothest Long Blend", description: "Hold two tracks together for 32+ bars without losing the groove or the levels.", badge: "Long Blend Master", premium: true, eta: "Coming soon" },
  { id: "no-vocal-clash", title: "No Vocal Clash Challenge", description: "Mix two vocal tracks so cleanly that the leads never bump into each other.", badge: "Vocal Conductor", premium: false, eta: "Coming soon" },
];

// ---------- Next Best Action ----------
export interface NextAction {
  title: string;
  description: string;
  cta: string;
  to: string;
  tone: "primary" | "warning" | "success";
}

export function nextBestAction(state: AppState): NextAction {
  const last = state.analyses[0];
  if (!last) {
    return {
      title: "Let's hear your first transition",
      description: "Two tracks or a short set — upload anything and I'll take it from there.",
      cta: "Upload now",
      to: "/app/upload",
      tone: "primary",
    };
  }
  const streak = computeStreak(state);
  if (!streak.trainedToday) {
    return {
      title: "Keep your streak alive",
      description: `${streak.current} days in a row — one quick drill keeps the run going.`,
      cta: "Train today",
      to: "/app/training",
      tone: "warning",
    };
  }
  const dna = computeDjDna(state);
  const weak = dna.weaknesses[0];
  if (weak) {
    return {
      title: `Work on your ${weak.label.toLowerCase()}`,
      description: `This is the area holding the rest of your sets back. Let's give it a focused session.`,
      cta: "Start drill",
      to: "/app/training",
      tone: "primary",
    };
  }
  return {
    title: "See your monthly progress",
    description: "Fresh report card with skill deltas and next focus.",
    cta: "Open report",
    to: "/app/monthly",
    tone: "success",
  };
}
