import { useEffect, useState } from "react";
import type { AnalysisResult } from "./analysis";
import {
  setArchivedFn,
  deleteAnalysisFn,
  deleteAllAnalysesFn,
  deleteArchivedAnalysesFn,
} from "./analyses.functions";
import { getAnalysisProvider } from "./api/provider";
import { loestAb, mitNutzerstand } from "./scoring-version";

// "fire and forget" gilt fuer den EINZELNEN Aufruf - die lokale Anzeige soll
// nicht an einem DB-Fehler haengen. Es gilt NICHT fuer die Diagnose: schlaegt
// das dauerhaft fehl, laufen lokaler Stand und Datenbank auseinander, ohne
// dass es jemand sieht. Deshalb wird die Ursache benannt statt nur gemeldet.
function fireAndForget<T>(p: Promise<T>) {
  p.catch((e) => console.warn(
    "[mixcoach] Aenderung NICHT in die Cloud uebernommen - lokaler Stand und " +
    "Datenbank laufen auseinander. Pruefen: SUPABASE_SERVICE_ROLE_KEY in " +
    "Frontend/.env, und ob jemand angemeldet ist (DEV_BYPASS_AUTH in " +
    "routes/app.tsx). Fehler:", e,
  ));
}

// Engine-sourced analyses have a result file on the audio-engine backend
// (analysis_results/{id}.json) that needs archiving too, not just the
// local/Supabase state — otherwise it reappears on the next export_labels_v3.py run.
function archiveOnEngine(ids: string[]) {
  ids.forEach((id) => fireAndForget(getAnalysisProvider().deleteAnalysis?.(id) ?? Promise.resolve()));
}

const KEY = "mixcoach.state.v1";

export interface UserProfile {
  name: string;
  level: string;
  xp: number;
  streak: number;
  genres: string[];
  equipment: string[];
  experience: "Beginner" | "Intermediate" | "Advanced";
  plan: "free" | "premium";
}

export interface AppState {
  profile: UserProfile;
  analyses: AnalysisResult[];
  archivedIds: string[];
  achievements: string[]; // ids
  completedChallenges: string[];
}

export const LEVELS = [
  "Beginner", "Bedroom DJ", "Warm-Up DJ", "Club Ready",
  "Resident DJ", "Festival Ready", "Master Selector", "Legend",
];

const defaultState: AppState = {
  profile: {
    name: "DJ",
    level: "Bedroom DJ",
    xp: 120,
    streak: 3,
    genres: ["Melodic House", "Tech House"],
    equipment: ["Pioneer DDJ-FLX4"],
    experience: "Beginner",
    plan: "free",
  },
  analyses: [],
  archivedIds: [],
  achievements: [],
  completedChallenges: [],
};

function read(): AppState {
  if (typeof window === "undefined") return defaultState;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaultState;
    return { ...defaultState, ...JSON.parse(raw) };
  } catch { return defaultState; }
}

function write(s: AppState) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(s));
  window.dispatchEvent(new Event("mixcoach:update"));
}

export function useAppState(): [AppState, (updater: (s: AppState) => AppState) => void] {
  const [state, setState] = useState<AppState>(defaultState);
  useEffect(() => {
    setState(read());
    const onUpdate = () => setState(read());
    window.addEventListener("mixcoach:update", onUpdate);
    window.addEventListener("storage", onUpdate);
    return () => {
      window.removeEventListener("mixcoach:update", onUpdate);
      window.removeEventListener("storage", onUpdate);
    };
  }, []);
  const update = (updater: (s: AppState) => AppState) => {
    const next = updater(read());
    write(next);
    setState(next);
  };
  return [state, update];
}

export function addAnalysis(result: AnalysisResult) {
  const s = read();

  // Idempotent: dieselbe Analyse (per id) nicht doppelt anlegen - aber eine
  // NEUERE Fassung derselben Analyse loest die alte ab. Vorher stand hier ein
  // blankes `return`, und damit war jede einmal gespeicherte Analyse
  // unkorrigierbar (siehe scoring-version.ts).
  const idx = s.analyses.findIndex((a) => a.id === result.id);
  if (idx >= 0) {
    if (!loestAb(s.analyses[idx], result)) return;
    const analyses = s.analyses.slice();
    analyses[idx] = mitNutzerstand(result, s.analyses[idx]);
    // Kein XP beim Ersetzen: die Analyse ist nicht neu, sie ist nur richtiger
    // geworden. Sonst waere jede Korrektur eine Punktequelle.
    write({ ...s, analyses });
    return;
  }

  const xpGain = Math.round((result.scores.overall ?? 0) / 2);
  const next: AppState = {
    ...s,
    analyses: [result, ...s.analyses],
    profile: { ...s.profile, xp: s.profile.xp + xpGain },
  };
  write(next);
}

export function archiveAnalysis(id: string) {
  const s = read();
  if (!s.archivedIds.includes(id)) {
    write({ ...s, archivedIds: [...s.archivedIds, id] });
  }
  fireAndForget(setArchivedFn({ data: { id, archived: true } }));
}

export function unarchiveAnalysis(id: string) {
  const s = read();
  write({ ...s, archivedIds: s.archivedIds.filter((x) => x !== id) });
  fireAndForget(setArchivedFn({ data: { id, archived: false } }));
}

export function deleteAnalysis(id: string) {
  const s = read();
  const target = s.analyses.find((a) => a.id === id);
  write({
    ...s,
    analyses: s.analyses.filter((a) => a.id !== id),
    archivedIds: s.archivedIds.filter((x) => x !== id),
  });
  fireAndForget(deleteAnalysisFn({ data: { id } }));
  if (target?.source === "engine") archiveOnEngine([id]);
}

export function deleteAnalyses(ids: string[]) {
  const set = new Set(ids);
  const s = read();
  const engineIds = s.analyses.filter((a) => set.has(a.id) && a.source === "engine").map((a) => a.id);
  write({
    ...s,
    analyses: s.analyses.filter((a) => !set.has(a.id)),
    archivedIds: s.archivedIds.filter((x) => !set.has(x)),
  });
  ids.forEach((id) => fireAndForget(deleteAnalysisFn({ data: { id } })));
  archiveOnEngine(engineIds);
}

export function clearAllAnalyses() {
  const s = read();
  const engineIds = s.analyses.filter((a) => a.source === "engine").map((a) => a.id);
  write({ ...s, analyses: [], archivedIds: [] });
  fireAndForget(deleteAllAnalysesFn());
  archiveOnEngine(engineIds);
}

export function clearArchivedAnalyses() {
  const s = read();
  const archived = new Set(s.archivedIds);
  const engineIds = s.analyses.filter((a) => archived.has(a.id) && a.source === "engine").map((a) => a.id);
  write({
    ...s,
    analyses: s.analyses.filter((a) => !archived.has(a.id)),
    archivedIds: [],
  });
  fireAndForget(deleteArchivedAnalysesFn());
  archiveOnEngine(engineIds);
}

export const ACHIEVEMENTS = [
  { id: "first-upload", title: "First Upload", desc: "You uploaded your first transition." },
  { id: "score-90", title: "Club-Ready Moment", desc: "A transition that would land cleanly in any club." },
  { id: "ten-uploads", title: "Ten Sessions In", desc: "You uploaded ten transitions — the habit is real." },
  { id: "hundred-uploads", title: "A Hundred Deep", desc: "A hundred transitions in. This is what serious practice looks like." },
  { id: "perfect-beatmatch", title: "Rock-Solid Timing", desc: "Your tracks stayed perfectly locked together." },
  { id: "perfect-harmonic", title: "Perfect Track Pairing", desc: "Your track choices sat together beautifully." },
  { id: "streak-7", title: "Seven Days in a Row", desc: "You showed up to practice every day for a week." },
];

export function computeAchievements(s: AppState): string[] {
  const ids: string[] = [];
  if (s.analyses.length >= 1) ids.push("first-upload");
  if (s.analyses.some((a) => (a.scores.overall ?? 0) >= 90)) ids.push("score-90");
  if (s.analyses.length >= 10) ids.push("ten-uploads");
  if (s.analyses.length >= 100) ids.push("hundred-uploads");
  if (s.analyses.some((a) => (a.scores.beatmatching ?? 0) >= 95)) ids.push("perfect-beatmatch");
  if (s.analyses.some((a) => (a.scores.musicality ?? 0) >= 95)) ids.push("perfect-harmonic");
  if (s.profile.streak >= 7) ids.push("streak-7");
  return ids;
}

export function levelFromXp(xp: number): { name: string; index: number; next: number; progress: number } {
  const xpPerLevel = 250;
  const index = Math.min(LEVELS.length - 1, Math.floor(xp / xpPerLevel));
  const next = (index + 1) * xpPerLevel;
  const progress = Math.min(100, ((xp - index * xpPerLevel) / xpPerLevel) * 100);
  return { name: LEVELS[index], index, next, progress };
}
