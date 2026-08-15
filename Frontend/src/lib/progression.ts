// MixCoach progression system: skills, career path, achievements.
// Derived from AppState — structured so a real backend can replace the
// derivation without touching the UI.

import type { AppState } from "./store";
import type { AnalysisResult } from "./analysis";

// ---------- Skills ----------

export type SkillKey =
  | "beatmatching"
  | "eq"
  | "energy"
  | "phrase"
  | "musicality"
  | "creativity";

export interface SkillDef {
  key: SkillKey;
  title: string;
  blurb: string;
  /** maps to AnalysisResult.scores field */
  scoreField: keyof AnalysisResult["scores"];
  weaknessCopy: string;
  exercise: { title: string; description: string; xp: number };
}

export const SKILLS: SkillDef[] = [
  {
    key: "beatmatching",
    title: "Your Timing",
    blurb: "Keeping both tracks locked together so the groove never wobbles.",
    scoreField: "beatmatching",
    weaknessCopy: "Your tracks slowly drift apart on the longer blends.",
    exercise: {
      title: "Hold both tracks in sync for a full minute",
      description: "Match them by ear, then ride the pitch so they stay locked together for 60 seconds — no sync button.",
      xp: 30,
    },
  },
  {
    key: "eq",
    title: "Clean Mixing",
    blurb: "Making room for each track so nothing feels muddy or crowded.",
    scoreField: "eq",
    weaknessCopy: "Both basslines often play together and the low end gets crowded.",
    exercise: {
      title: "Five clean bass swaps in a row",
      description: "Swap basslines right on the downbeat — the new track takes over the low end the moment you let go of the old one.",
      xp: 40,
    },
  },
  {
    key: "energy",
    title: "Crowd Momentum",
    blurb: "Keeping the floor moving and lifting the room without losing it mid-mix.",
    scoreField: "flow",
    weaknessCopy: "The room loses momentum in the middle of your transitions.",
    exercise: {
      title: "Lift the room across three tracks",
      description: "Mix three tracks in a row, each one a little more intense, and never let the energy dip between them.",
      xp: 35,
    },
  },
  {
    key: "phrase",
    title: "Transition Flow",
    blurb: "Letting the drops and breakdowns land exactly when they should.",
    scoreField: "timing",
    weaknessCopy: "Your drops land a bar early or late instead of right in the pocket.",
    exercise: {
      title: "Land the drop right on bar 17",
      description: "Cue the new track so its drop arrives exactly on bar 17 of the outgoing one — feel the phrase, don't count it.",
      xp: 40,
    },
  },
  {
    key: "musicality",
    title: "Track Pairing",
    blurb: "Picking tracks that sound like they were meant to play together.",
    scoreField: "musicality",
    weaknessCopy: "Vocals and lead melodies sometimes clash with each other.",
    exercise: {
      title: "Mix four tracks that share a key",
      description: "Build a four-track blend using only neighbouring keys on the Camelot wheel — listen for how naturally they sit together.",
      xp: 35,
    },
  },
  {
    key: "creativity",
    title: "Your Signature",
    blurb: "Loops, effects and little surprises that make a set feel like yours.",
    scoreField: "creativity",
    weaknessCopy: "Your transitions all feel a little too safe and similar.",
    exercise: {
      title: "Bridge two tracks with a loop",
      description: "Use a short loop roll to connect two tracks that have nothing in common — make the gap feel intentional.",
      xp: 45,
    },
  },
];

export interface SkillStat {
  def: SkillDef;
  level: number;
  xp: number;
  xpToNext: number;
  progress: number; // 0..100 within current level
  avgScore: number; // 0..100 across history
  recentDelta: number; // recent avg − older avg
  sampleCount: number;
  /** Gibt es ueberhaupt einen gemessenen Wert auf dieser Achse?
   *
   *  Vier der sechs Achsen sind in JEDEM der 51 Reports leer
   *  (beatmatching, eq, timing, creativity - je 0/51). Ohne dieses Feld
   *  zeigt die Oberflaeche fuer sie Level 1 und 0 % Fortschritt, und das
   *  liest sich wie "gemessen, und du bist ganz unten" statt wie "nicht
   *  gemessen". Dieselbe Ehrlichkeitslinie wie bei notMeasured im Report
   *  und bei den Beobachtungen. */
  measured: boolean;
  /** Warum die Achse leer ist - kurz, fuer die Anzeige daneben. */
  notMeasuredReason?: string;
  weakness: string;
  exercise: SkillDef["exercise"];
}

/** Warum eine Achse nichts zeigt. Nach scoreField, nicht nach Anzeigename. */
const NICHT_GEMESSEN: Record<string, string> = {
  beatmatching: "seit 31.07.2026 bewusst ohne Wert: bpm_drift ist in 89 % der "
    + "Übergänge exakt 0,0 und unterscheidet keine zwei DJs (K1)",
  timing: "seit 31.07.2026 bewusst ohne Wert: das Phrasenraster wandert weiter "
    + "als die Größe, die es messen soll (K1)",
  eq: "wird von der Analyse noch nicht berechnet",
  creativity: "wird von der Analyse noch nicht berechnet",
};

const SKILL_XP_PER_LEVEL = 200;

function avg(nums: number[]): number {
  if (nums.length === 0) return 0;
  return nums.reduce((s, n) => s + n, 0) / nums.length;
}

export function computeSkillStats(state: AppState): SkillStat[] {
  const all = state.analyses;
  const recent = all.slice(0, Math.min(5, all.length));
  const older = all.slice(5);

  return SKILLS.map((def) => {
    // ACHTUNG, hier steckte ein stiller Fehler: Number(null) ist 0, und
    // Number.isFinite(0) ist true. Die vier nie befuellten Achsen bekamen
    // damit fuer JEDE Analyse eine 0 als Messwert - die Karriere-Seite
    // meldete "Samples: 51" fuer etwas, das nie gemessen wurde, und der
    // Durchschnitt wurde von erfundenen Nullen gebildet. Erst pruefen, ob
    // ueberhaupt eine Zahl dasteht, dann umwandeln.
    const werte = (liste: typeof all) => liste
      .map((a) => a.scores[def.scoreField])
      .filter((n): n is number => typeof n === "number" && Number.isFinite(n));

    const scores = werte(all);
    const avgScore = Math.round(avg(scores));
    const recentAvg = avg(werte(recent));
    const olderAvg = avg(werte(older));
    const recentDelta = older.length > 0 && recent.length > 0
      ? Math.round(recentAvg - olderAvg)
      : 0;

    // XP gained per analysis from this skill = score / 4
    const xp = Math.round(scores.reduce((s, n) => s + n / 4, 0));
    const level = Math.floor(xp / SKILL_XP_PER_LEVEL) + 1;
    const inLevel = xp - (level - 1) * SKILL_XP_PER_LEVEL;
    const xpToNext = SKILL_XP_PER_LEVEL - inLevel;
    const progress = Math.round((inLevel / SKILL_XP_PER_LEVEL) * 100);

    const measured = scores.length > 0;
    return {
      def,
      level,
      xp,
      xpToNext,
      progress,
      avgScore,
      recentDelta,
      sampleCount: scores.length,
      measured,
      // Rueckfalltext, damit keine Achse je ein blankes "Nicht gemessen"
      // ohne Grund zeigt - auch eine, die heute immer befuellt ist.
      notMeasuredReason: measured
        ? undefined
        : (NICHT_GEMESSEN[def.scoreField]
           ?? "für die vorliegenden Aufnahmen wurde dieser Wert nicht berechnet"),
      weakness: def.weaknessCopy,
      exercise: def.exercise,
    };
  });
}

// ---------- Career path ----------

export interface CareerStage {
  index: number;
  title: string;
  tagline: string;
  story: string;
  xpRequired: number;
}

export const CAREER_PATH: CareerStage[] = [
  { index: 0, title: "Bedroom DJ", tagline: "Just you, the gear, and the headphones.",
    story: "You are learning consistency. Locking tracks together by ear, finishing your mixes, and building the habit of practising on purpose are what matter right now.",
    xpRequired: 0 },
  { index: 1, title: "House Party DJ", tagline: "Reading a room of friends for the first time.",
    story: "You can control small crowds. You read the room, keep energy steady, and recover when a transition does not go as planned.",
    xpRequired: 250 },
  { index: 2, title: "Warm-Up DJ", tagline: "Setting the tone before the main act.",
    story: "You can warm up a floor without stealing the headline. Longer blends, patient track selection, and lower energy are your tools.",
    xpRequired: 600 },
  { index: 3, title: "Bar DJ", tagline: "Holding the room across a long, varied night.",
    story: "You can maintain energy over an entire night. You move between genres, read the bar, and keep people dancing without a single peak-hour banger.",
    xpRequired: 1100 },
  { index: 4, title: "Club Ready", tagline: "Transitions tight enough for a proper booth.",
    story: "Your transitions are clean enough for a real club system. Clean EQ, confident phrasing, and almost no trainwrecks define this level.",
    xpRequired: 1800 },
  { index: 5, title: "Resident DJ", tagline: "A signature sound your venue books on repeat.",
    story: "You can carry a night from open to close. The venue trusts you, dancers know your sound, and your sets feel like a coherent journey.",
    xpRequired: 2700 },
  { index: 6, title: "Festival Support", tagline: "Big stage, big sound, no room for mistakes.",
    story: "You are playing to rooms where every drop must land. Timing, sound selection, and stage presence are now under pressure.",
    xpRequired: 4000 },
  { index: 7, title: "Festival Headliner", tagline: "The set the crowd came to see.",
    story: "You understand pacing, confidence, and storytelling. Your set builds a narrative that holds thousands of people from the first record to the last.",
    xpRequired: 6000 },
  { index: 8, title: "Master Selector", tagline: "Track choice that defines a scene.",
    story: "Your selections matter as much as your technique. DJs study your tracklists because your taste shapes the conversation around a sound.",
    xpRequired: 9000 },
  { index: 9, title: "Legend", tagline: "Other DJs study your sets.",
    story: "Your name carries weight. You have a body of work, a recognizable voice, and your influence shows up in the next generation of DJs.",
    xpRequired: 13000 },
];

export interface CareerProgress {
  current: CareerStage;
  next: CareerStage | null;
  xp: number;
  xpIntoStage: number;
  xpForStage: number;
  progress: number; // 0..100 toward next
  xpToNext: number;
}

export function computeCareer(xp: number): CareerProgress {
  let current = CAREER_PATH[0];
  for (const stage of CAREER_PATH) {
    if (xp >= stage.xpRequired) current = stage;
  }
  const next = CAREER_PATH[current.index + 1] ?? null;
  if (!next) {
    return {
      current, next: null, xp,
      xpIntoStage: xp - current.xpRequired,
      xpForStage: 0,
      progress: 100,
      xpToNext: 0,
    };
  }
  const xpForStage = next.xpRequired - current.xpRequired;
  const xpIntoStage = xp - current.xpRequired;
  return {
    current,
    next,
    xp,
    xpIntoStage,
    xpForStage,
    progress: Math.min(100, Math.round((xpIntoStage / xpForStage) * 100)),
    xpToNext: Math.max(0, next.xpRequired - xp),
  };
}

// ---------- Achievements ----------

export interface AchievementDef {
  id: string;
  title: string;
  desc: string;
  tier: "bronze" | "silver" | "gold";
  check: (s: AppState) => boolean;
}

export const ACHIEVEMENT_DEFS: AchievementDef[] = [
  { id: "first-upload", title: "First Upload", desc: "You uploaded your first track or set.", tier: "bronze",
    check: (s) => s.analyses.length >= 1 },
  { id: "score-80", title: "Solid Mix", desc: "One of your transitions sounded properly tight.", tier: "bronze",
    check: (s) => s.analyses.some((a) => (a.scores.overall ?? 0) >= 80) },
  { id: "score-90", title: "Club-Ready Moment", desc: "A transition that would land cleanly in any club.", tier: "silver",
    check: (s) => s.analyses.some((a) => (a.scores.overall ?? 0) >= 90) },
  { id: "streak-7", title: "Seven Days in a Row", desc: "You showed up to practice every day for a week.", tier: "silver",
    check: (s) => s.profile.streak >= 7 },
  { id: "perfect-beatmatch", title: "Rock-Solid Timing", desc: "Your tracks stayed perfectly locked together.", tier: "gold",
    check: (s) => s.analyses.some((a) => (a.scores.beatmatching ?? 0) >= 95) },
  { id: "clean-bass-swap", title: "Clean Bass Swap", desc: "Your low end stayed clear through the swap.", tier: "silver",
    check: (s) => s.analyses.some((a) => (a.scores.eq ?? 0) >= 90) },
  { id: "no-vocal-clash", title: "No Vocal Clash", desc: "Your vocals stayed out of each other's way.", tier: "silver",
    check: (s) => s.analyses.some((a) => (a.scores.musicality ?? 0) >= 90) },
  { id: "ten-analyses", title: "Ten Sessions In", desc: "You uploaded ten transitions — the habit is forming.", tier: "bronze",
    check: (s) => s.analyses.length >= 10 },
  { id: "fifty-analyses", title: "Fifty Sessions In", desc: "Fifty transitions reviewed. This is real work.", tier: "gold",
    check: (s) => s.analyses.length >= 50 },
  { id: "club-ready", title: "Club-Ready Streak", desc: "Your last five transitions all sounded clean and confident.", tier: "gold",
    check: (s) => {
      const r = s.analyses.slice(0, 5);
      if (r.length < 5) return false;
      return r.reduce((sum, a) => sum + (a.scores.overall ?? 0), 0) / r.length >= 85;
    } },
];

export function computeUnlockedAchievements(s: AppState): Set<string> {
  return new Set(ACHIEVEMENT_DEFS.filter((d) => d.check(s)).map((d) => d.id));
}
