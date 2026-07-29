// Personal Coach engine. Pure functions over AppState so every screen
// derives the same insights. The coach answers three questions on every
// invocation: what improved, what is weak, what should I practice next.
//
// All copy is generated from real analysis history (scores, weaknesses,
// setTransitions, frequency balance) plus profile context (experience,
// genres, equipment). No mock strings.

import type { AppState } from "./store";
import type { AnalysisResult } from "./analysis";
import { SKILLS, computeSkillStats, type SkillKey, type SkillStat } from "./progression";

export type Difficulty = "Beginner" | "Intermediate" | "Advanced";

export interface CoachExercise {
  id: string;
  name: string;
  targetSkill: SkillKey;
  targetSkillTitle: string;
  difficulty: Difficulty;
  durationMin: number;
  xp: number;
  instructions: string[];
  uploadAsk: string;
  successCriteria: string[];
}

// ---------- Exercise library ----------

export const EXERCISE_LIBRARY: CoachExercise[] = [
  {
    id: "phrase-16",
    name: "16-Bar Phrase Challenge",
    targetSkill: "phrase",
    targetSkillTitle: "Transition Flow",
    difficulty: "Intermediate",
    durationMin: 25,
    xp: 40,
    instructions: [
      "Pick two tracks in the same key family.",
      "Cue the incoming track so its drop lands on bar 17 of the outgoing track.",
      "Run the blend three times, record the third take.",
    ],
    uploadAsk: "Upload the full transition (≥ 60s) covering the bar before and after the drop.",
    successCriteria: ["Phrase alignment score ≥ 85", "Drop lands within ±1 beat of bar 17"],
  },
  {
    id: "bass-swap",
    name: "16-Bar Bass Swap",
    targetSkill: "eq",
    targetSkillTitle: "Clean Mixing",
    difficulty: "Intermediate",
    durationMin: 20,
    xp: 35,
    instructions: [
      "Hold Track A's lows wide open until the final 8 bars before the drop.",
      "On the downbeat, kill Track A lows and bring Track B lows in one motion.",
      "Repeat 5 times in a row — same two tracks.",
    ],
    uploadAsk: "Upload the 8 bars before and after the swap.",
    successCriteria: ["No low-end overlap longer than 1 beat", "EQ score ≥ 85"],
  },
  {
    id: "bass-patience",
    name: "Bass Patience Drill",
    targetSkill: "eq",
    targetSkillTitle: "Clean Mixing",
    difficulty: "Beginner",
    durationMin: 15,
    xp: 25,
    instructions: [
      "Start a long blend with the incoming bass at -∞.",
      "Wait the full 32 bars before you touch the low EQ.",
      "Swap only on the very last downbeat before the drop.",
    ],
    uploadAsk: "Upload a long blend (≥ 60s) where bass swap happens late.",
    successCriteria: ["Zero bass overlap before bar 24", "EQ score ≥ 75"],
  },
  {
    id: "vocal-clash",
    name: "Vocal Clash Avoidance",
    targetSkill: "musicality",
    targetSkillTitle: "Track Pairing",
    difficulty: "Beginner",
    durationMin: 15,
    xp: 30,
    instructions: [
      "Map vocal positions on both tracks before you mix.",
      "Schedule the blend so the outgoing vocal finishes before the incoming vocal begins.",
      "If they must overlap, duck the outgoing mids by 6 dB.",
    ],
    uploadAsk: "Upload a transition that contains a vocal on at least one of the tracks.",
    successCriteria: ["No two lead vocals fighting each other for more than two bars", "Your track pairing feels natural"],
  },
  {
    id: "energy-buildup",
    name: "Energy Build-Up",
    targetSkill: "energy",
    targetSkillTitle: "Crowd Momentum",
    difficulty: "Intermediate",
    durationMin: 30,
    xp: 40,
    instructions: [
      "Pick three tracks, each a step up in intensity.",
      "Mix them in sequence so perceived energy never dips between blends.",
      "Use high-pass automation on the outgoing track to lift, not drop, the energy.",
    ],
    uploadAsk: "Upload the full 3-track sequence.",
    successCriteria: ["The room never feels like it lost momentum between tracks", "Your sets feel like they are building"],
  },
  {
    id: "warmup-flow",
    name: "Club Warm-Up Flow",
    targetSkill: "energy",
    targetSkillTitle: "Crowd Momentum",
    difficulty: "Advanced",
    durationMin: 45,
    xp: 60,
    instructions: [
      "Build a 20-minute warm-up: start around 118 BPM, end no higher than 124.",
      "Hold energy below 80% of peak across the whole set.",
      "Use long, EQ-only blends — no FX-only transitions.",
    ],
    uploadAsk: "Upload the full warm-up set (15-30 min).",
    successCriteria: ["BPM drift ≤ 1.5%", "Avg energy stays in warm-up band"],
  },
  {
    id: "freestyle-review",
    name: "Freestyle Set Review",
    targetSkill: "creativity",
    targetSkillTitle: "Creativity",
    difficulty: "Advanced",
    durationMin: 60,
    xp: 70,
    instructions: [
      "Record a 30-minute set with no preplanned tracklist.",
      "Use at least three FX moments and one loop-roll bridge.",
      "Review the analysis honestly — flag transitions that felt safe.",
    ],
    uploadAsk: "Upload the recorded freestyle set.",
    successCriteria: ["Creativity score ≥ 80", "At least 3 distinct transition types"],
  },
  {
    id: "sync-hold",
    name: "60-Second Sync Hold",
    targetSkill: "beatmatching",
    targetSkillTitle: "Your Timing",
    difficulty: "Beginner",
    durationMin: 15,
    xp: 25,
    instructions: [
      "Beatmatch by ear with sync OFF.",
      "Hold both tracks in phase for 60 seconds straight, correcting drift with the platter.",
      "Repeat 4 times.",
    ],
    uploadAsk: "Upload the 60-second hold (both tracks audible).",
    successCriteria: ["Your tracks stay locked together for the full minute", "Your timing feels rock-solid"],
  },
  {
    id: "monthly-review",
    name: "Weekly Review",
    targetSkill: "musicality",
    targetSkillTitle: "Track Pairing",
    difficulty: "Beginner",
    durationMin: 20,
    xp: 20,
    instructions: [
      "Open your last 4 analyses side by side.",
      "Write down the one mistake that shows up in three of them.",
      "Plan next week's drills around that mistake.",
    ],
    uploadAsk: "Nothing to upload — reflection session.",
    successCriteria: ["One concrete weakness written down", "Three drills scheduled"],
  },
  {
    id: "key-lock",
    name: "Camelot Neighbour Mix",
    targetSkill: "musicality",
    targetSkillTitle: "Track Pairing",
    difficulty: "Intermediate",
    durationMin: 25,
    xp: 35,
    instructions: [
      "Pick 4 tracks, each a Camelot neighbour of the previous one.",
      "Mix all four in sequence, no FX, no key shifts.",
      "Listen for tonal clashes; if you hear one, restart.",
    ],
    uploadAsk: "Upload the full 4-track sequence.",
    successCriteria: ["No tracks clashing in key", "Your track pairing feels intentional"],
  },
];

export function exerciseById(id: string): CoachExercise | undefined {
  return EXERCISE_LIBRARY.find((e) => e.id === id);
}

const SKILL_DRILLS: Record<SkillKey, string[]> = {
  beatmatching: ["sync-hold"],
  eq: ["bass-swap", "bass-patience"],
  energy: ["energy-buildup", "warmup-flow"],
  phrase: ["phrase-16"],
  musicality: ["vocal-clash", "key-lock"],
  creativity: ["freestyle-review"],
};

function pickDrillForSkill(key: SkillKey, experience: Difficulty): CoachExercise {
  const ids = SKILL_DRILLS[key] ?? [];
  const candidates = ids.map((id) => exerciseById(id)).filter((e): e is CoachExercise => !!e);
  if (candidates.length === 0) return EXERCISE_LIBRARY[0];
  const tier = experience === "Beginner" ? 0 : experience === "Intermediate" ? 1 : 2;
  const ranked = candidates
    .map((c) => ({ c, d: c.difficulty === "Beginner" ? 0 : c.difficulty === "Intermediate" ? 1 : 2 }))
    .sort((a, b) => Math.abs(a.d - tier) - Math.abs(b.d - tier));
  return ranked[0].c;
}

export function recommendForSkill(key: SkillKey, experience: Difficulty = "Intermediate"): CoachExercise {
  return pickDrillForSkill(key, experience);
}

// ---------- Pattern detection ----------

export interface DetectedPattern {
  /** Stable ID for telemetry / overrides */
  id: string;
  /** Human title — one short sentence */
  title: string;
  /** Number of times the pattern was observed across history */
  count: number;
  /** Targeted skill, used to pick the recommended drill */
  skill: SkillKey;
}

export function detectPatterns(state: AppState): DetectedPattern[] {
  const out: Record<string, DetectedPattern> = {};
  const bump = (id: string, title: string, skill: SkillKey) => {
    if (!out[id]) out[id] = { id, title, count: 0, skill };
    out[id].count += 1;
  };

  for (const a of state.analyses) {
    // 1. Long blends with early bass introduction.
    for (const t of a.setTransitions ?? []) {
      const dur = Math.max(0, t.end_sec - t.start_sec);
      if (dur >= 24 && t.bass_overlap_score > 60) {
        bump(
          "early-bass-long-blend",
          "You bring the new bass in a bit too early on long blends.",
          "eq",
        );
      }
      if (t.bpm_drift > 2) {
        bump(
          "bpm-drift",
          "Your tracks tend to drift out of sync once a blend gets going.",
          "beatmatching",
        );
      }
      if (t.phrase_alignment_score > 0 && t.phrase_alignment_score < 50) {
        bump(
          "off-phrase",
          "Your drops are landing off the phrase instead of right in the pocket.",
          "phrase",
        );
      }
      if (t.energy_dip_pct > 60) {
        bump(
          "energy-collapse",
          "The room loses momentum right in the middle of your transitions.",
          "energy",
        );
      }
    }
    // 2. Frequency balance over the whole analysis.
    if (a.frequency?.bass != null && a.frequency.bass > 75) {
      bump("bass-heavy", "Your mixes lean bass-heavy and the mids and highs get buried.", "eq");
    }
    // 3. Recurring weakness copy from the analyzer.
    for (const w of a.weaknesses ?? []) {
      const lower = w.toLowerCase();
      if (lower.includes("vocal")) bump("vocal-clash", "Your vocals stack on top of each other on busier transitions.", "musicality");
      if (lower.includes("key") || lower.includes("clash")) bump("key-clash", "Your track keys are clashing on the melodic moments.", "musicality");
      if (lower.includes("energy")) bump("energy-flat", "Your sets flatten out instead of building toward something.", "energy");
    }
  }

  return Object.values(out).sort((a, b) => b.count - a.count);
}

// ---------- Honest weakness copy (per skill, scored 0-100) ----------

const WEAKNESS_COPY: Record<SkillKey, (avg: number) => string> = {
  beatmatching: (s) =>
    s < 60
      ? "Your tracks are drifting apart pretty quickly once a blend starts — sync is masking it instead of solving it."
      : s < 75
      ? "Your timing feels great at the start, then loosens up on the longer blends past 30 seconds."
      : "Your timing is rock solid. Push into harder genre jumps to keep stretching it.",
  eq: (s) =>
    s < 60
      ? "You're pulling the bass out too early. Let the outgoing track keep its low end until the very last bars before the drop."
      : s < 75
      ? "Your swaps sound clean, but the mids start piling up on longer blends. Ease the outgoing mids out a few bars sooner."
      : "Your mixes sound clean and uncrowded. Add some subtle high-pass moves for extra polish.",
  energy: (s) =>
    s < 60
      ? "The room loses momentum between your tracks. A gentle high-pass sweep on the outgoing track can hold the floor up."
      : s < 75
      ? "Your momentum holds through the blend, but the next track feels too similar. Step the intensity up at least once between tracks."
      : "Your sets feel intentionally paced. Keep trusting it.",
  phrase: (s) =>
    s < 60
      ? "Your drops are landing a bar or two off. Count phrases out loud while you cue — feel where the 16 lands."
      : s < 75
      ? "Your transitions flow well, except on tracks with unusual intros. Listen for the kick pattern instead of trusting the count."
      : "Your transitions land exactly where they should. Try mixing across genres with different phrase shapes.",
  musicality: (s) =>
    s < 60
      ? "Your tracks are clashing in key. Stick to neighbouring keys on the Camelot wheel for the next week and the tension disappears."
      : s < 75
      ? "Your track choices feel safe, but the vocals are bumping into each other. Map the vocal moments before you cue."
      : "Your tracks pair beautifully. Try one bold key jump per set on purpose.",
  creativity: (s) =>
    s < 60
      ? "Every transition follows the same recipe. Add one loop or FX moment per set this week and your sound starts feeling like yours."
      : s < 75
      ? "You have ideas — they just arrive a little late. Pre-mark your FX moments before you record."
      : "Your signature is showing up consistently. Don't smooth it out.",
};

export function weaknessFor(skill: SkillStat): string {
  return WEAKNESS_COPY[skill.def.key](skill.avgScore || 50);
}

// ---------- Weekly plan ----------

export interface WeeklyPlanDay {
  day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun";
  fullDay: string;
  exercise: CoachExercise;
  rationale: string;
}

const DAY_NAMES: { day: WeeklyPlanDay["day"]; full: string }[] = [
  { day: "Mon", full: "Monday" },
  { day: "Tue", full: "Tuesday" },
  { day: "Wed", full: "Wednesday" },
  { day: "Thu", full: "Thursday" },
  { day: "Fri", full: "Friday" },
  { day: "Sat", full: "Saturday" },
  { day: "Sun", full: "Sunday" },
];

/** Builds a 7-day plan weighted to the user's two weakest skills, with the
 *  weekend reserved for integration (freestyle or warmup) and Sunday for
 *  reflection. Difficulty is matched to user experience. */
export function weeklyPlan(state: AppState): WeeklyPlanDay[] {
  const skills = computeSkillStats(state);
  const exp = state.profile.experience as Difficulty;
  const sorted = [...skills].sort((a, b) => a.avgScore - b.avgScore);
  const weak = sorted[0];
  const second = sorted[1] ?? sorted[0];

  // No history yet → onboarding plan.
  if (!weak || weak.sampleCount === 0) {
    const intro = ["sync-hold", "bass-patience", "phrase-16", "vocal-clash", "energy-buildup", "freestyle-review", "monthly-review"];
    return DAY_NAMES.map((d, i) => ({
      day: d.day,
      fullDay: d.full,
      exercise: exerciseById(intro[i])!,
      rationale: "Baseline week — one upload per drill so the coach can read your form.",
    }));
  }

  const weakDrill = pickDrillForSkill(weak.def.key, exp);
  const secondDrill = pickDrillForSkill(second.def.key, exp);
  const integration = exp === "Advanced" ? exerciseById("freestyle-review")! : exerciseById("energy-buildup")!;
  const longForm = exp === "Advanced" ? exerciseById("warmup-flow")! : exerciseById("energy-buildup")!;
  const review = exerciseById("monthly-review")!;

  const plan: { exercise: CoachExercise; rationale: string }[] = [
    { exercise: weakDrill, rationale: `${weak.def.title} is your lowest skill at ${weak.avgScore}/100. Start the week on it.` },
    { exercise: secondDrill, rationale: `${second.def.title} (${second.avgScore}/100) is the second lever.` },
    { exercise: weakDrill, rationale: `Second pass on ${weak.def.title} — same drill, different tracks.` },
    { exercise: secondDrill, rationale: `Reinforce ${second.def.title} before integration.` },
    { exercise: weakDrill, rationale: `Third weekly rep on ${weak.def.title}. Repetition beats variety.` },
    { exercise: integration, rationale: `Integrate the week into a multi-track flow.` },
    { exercise: review, rationale: `Reflect on the week's analyses and lock the lesson.` },
  ];

  // If the user is past the rebuild stage, swap Saturday for a long-form set.
  if (weak.avgScore >= 70) plan[5] = { exercise: longForm, rationale: `${weak.def.title} is solid — push into longer sets.` };

  return DAY_NAMES.map((d, i) => ({
    day: d.day,
    fullDay: d.full,
    exercise: plan[i].exercise,
    rationale: plan[i].rationale,
  }));
}

// ---------- Coach insight bundle ----------

export interface CoachInsightBundle {
  greeting: string;
  weeklySummary: string;

  /** Section 1 — Current Focus */
  currentFocus: { title: string; detail: string; skill: SkillStat | null };
  /** Section 2 — Recent Improvement */
  recentImprovement: { title: string; detail: string } | null;
  /** Section 3 — Pattern Detected */
  patternDetected: { title: string; detail: string; pattern: DetectedPattern } | null;
  /** Section 4 — Recommended Training */
  recommendedTraining: { title: string; detail: string; exercise: CoachExercise };
  /** Section 5 — Honest Coach Note */
  honestNote: string;

  // Compat fields (older surfaces still read these)
  mainWeakness: { title: string; detail: string; skill: SkillStat } | null;
  focusNext7Days: string;
  nextExercise: CoachExercise;
  motivational: string;

  context: {
    genres: string[];
    equipment: string[];
    experience: AppState["profile"]["experience"];
    analysisCount: number;
    streak: number;
  };
}

function pickGreeting(name: string) {
  const h = new Date().getHours();
  const part = h < 5 ? "Still up" : h < 12 ? "Morning" : h < 18 ? "Afternoon" : "Evening";
  return `${part}, ${name}`;
}

function avg(xs: number[]): number {
  return xs.length ? Math.round(xs.reduce((s, n) => s + n, 0) / xs.length) : 0;
}

function recentDeltaPct(state: AppState, field: keyof AnalysisResult["scores"]): { delta: number; recentN: number } {
  const all = state.analyses;
  const recent = all.slice(0, Math.min(5, all.length));
  const older = all.slice(5, Math.min(15, all.length));
  if (recent.length === 0 || older.length === 0) return { delta: 0, recentN: recent.length };
  const r = avg(recent.map((a) => Number(a.scores[field])).filter(Number.isFinite));
  const o = avg(older.map((a) => Number(a.scores[field])).filter(Number.isFinite));
  if (o === 0) return { delta: 0, recentN: recent.length };
  return { delta: Math.round(((r - o) / o) * 100), recentN: recent.length };
}

export function buildCoachInsight(state: AppState): CoachInsightBundle {
  const skills = computeSkillStats(state);
  const sortedByWeakness = [...skills].sort((a, b) => a.avgScore - b.avgScore);
  const weakest = sortedByWeakness[0]?.sampleCount ? sortedByWeakness[0] : null;
  const exp = state.profile.experience as Difficulty;

  // Improvement: pick skill with the largest positive pct delta over the
  // last 5 analyses vs the prior window.
  const improvements = skills
    .map((s) => ({ s, ...recentDeltaPct(state, s.def.scoreField) }))
    .filter((x) => x.recentN >= 2 && x.delta > 0)
    .sort((a, b) => b.delta - a.delta);
  const topImprove = improvements[0] ?? null;

  const last7 = state.analyses.filter(
    (a) => Date.now() - new Date(a.createdAt).getTime() < 7 * 86400_000,
  );
  const weekAvg = avg(last7.map((a) => a.scores.overall).filter((v): v is number => v != null));

  // ---- Sections ---------------------------------------------------------

  // 1. Current Focus
  const currentFocus = weakest
    ? {
        title: `${weakest.def.title} is what's holding the rest of your sets back right now.`,
        detail: weaknessFor(weakest),
        skill: weakest,
      }
    : {
        title: "Let's hear you mix.",
        detail: "Upload one transition or a short set so I have something real to work with.",
        skill: null,
      };

  // 2. Recent Improvement
  const recentImprovement = topImprove
    ? {
        title: `Your ${topImprove.s.def.title.toLowerCase()} feels noticeably better than it did a few sessions ago.`,
        detail: `Whatever you changed — keep doing it. Your last ${topImprove.recentN} uploads sound clearly more confident here.`,
      }
    : null;

  // 3. Pattern Detected
  const patterns = detectPatterns(state);
  const topPattern = patterns[0];
  const patternDetected = topPattern
    ? {
        title: topPattern.title,
        detail: `I'm hearing this in ${topPattern.count} of your transition${topPattern.count === 1 ? "" : "s"}. It's the main thing costing you on ${SKILLS.find((s) => s.key === topPattern.skill)?.title ?? "this skill"}.`,
        pattern: topPattern,
      }
    : null;

  // 4. Recommended Training — based on detected pattern, else weakest skill
  const trainSkillKey: SkillKey = topPattern?.skill ?? weakest?.def.key ?? "phrase";
  const trainEx = pickDrillForSkill(trainSkillKey, exp);
  const recommendedTraining = {
    title: `Spend ${trainEx.durationMin} minutes on "${trainEx.name}" this week.`,
    detail: `+${trainEx.xp} XP when you finish. ${trainEx.instructions[0]}`,
    exercise: trainEx,
  };

  // 5. Honest Coach Note — tone: direct, helpful, professional, motivating
  const genre = state.profile.genres[0];
  const gearSuffix = state.profile.equipment[0] ? ` Your ${state.profile.equipment[0]} is more than enough for this.` : "";
  const honestNote =
    state.analyses.length === 0
      ? `Honest take: I haven't heard you mix yet. Upload one transition tonight — rough is fine — and we go from there.${gearSuffix}`
      : weakest && weakest.avgScore < 60
      ? `Honest take: ${weakest.def.title.toLowerCase()} is holding the rest of your sets back${genre ? `, especially in ${genre}` : ""}. Don't chase fancy transitions until this feels natural. Three focused sessions this week beats a month of freestyling.${gearSuffix}`
      : weakest && weakest.avgScore < 75
      ? `Honest take: you're past the basics but not quite club-ready yet. The next jump comes from picking ${weakest.def.title.toLowerCase()} and drilling it on the same two tracks until it feels boring.${gearSuffix}`
      : `Honest take: your fundamentals sound clean${genre ? ` for ${genre}` : ""}. Time to take risks — try one transition per set you'd normally skip. Plateaus break when you mix uncomfortable.${gearSuffix}`;

  // ---- Compat fields ----------------------------------------------------

  const weeklySummary =
    last7.length === 0
      ? "Nothing uploaded this week yet. One transition tonight and we have something to talk about."
      : `${last7.length} session${last7.length === 1 ? "" : "s"} this week. ${
          weekAvg >= 80
            ? "Your mixes are sounding club-ready — keep the pressure on."
            : weekAvg >= 65
            ? "You're in a solid groove. The next jump comes from drilling one weak spot."
            : "Time to slow down and lock in the basics before chasing complex blends."
        }`;

  const focus = weakest
    ? `Spend the next 7 days on ${weakest.def.title.toLowerCase()}. Run "${trainEx.name}" at least three times — same two tracks, every take recorded.`
    : `Let's start with one full upload. Once I've heard you, the plan gets specific.`;

  return {
    greeting: pickGreeting(state.profile.name || "DJ"),
    weeklySummary,
    currentFocus,
    recentImprovement,
    patternDetected,
    recommendedTraining,
    honestNote,
    mainWeakness: weakest
      ? { title: weakest.def.title, detail: weaknessFor(weakest), skill: weakest }
      : null,
    focusNext7Days: focus,
    nextExercise: trainEx,
    motivational: honestNote,
    context: {
      genres: state.profile.genres,
      equipment: state.profile.equipment,
      experience: state.profile.experience,
      analysisCount: state.analyses.length,
      streak: state.profile.streak,
    },
  };
}

// Used right after an analysis completes
export function recommendNextExerciseFor(result: AnalysisResult): CoachExercise {
  // null = nicht gemessen -> darf nicht als "schwaechster Skill" gelten.
  const skillScores: Record<SkillKey, number | null> = {
    beatmatching: result.scores.beatmatching,
    eq: result.scores.eq,
    energy: result.scores.flow,
    phrase: result.scores.timing,
    musicality: result.scores.musicality,
    creativity: result.scores.creativity,
  };
  const measuredEntries = Object.entries(skillScores).filter(
    (e): e is [string, number] => e[1] != null,
  );
  const weakestKey = ((measuredEntries.sort((a, b) => a[1] - b[1])[0]?.[0]) ?? "phrase") as SkillKey;
  return pickDrillForSkill(weakestKey, "Intermediate");
}
