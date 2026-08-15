// Eine Achse ohne einen einzigen Messwert darf nicht wie eine gemessene
// aussehen.
//
// Vier der sechs Achsen sind in JEDEM der 51 Reports leer (beatmatching,
// eq, timing, creativity - je 0/51). Vorher zeigte die Karriere-Seite fuer
// sie "Lv 1 · 0 XP", einen Fortschrittsbalken auf 0 % und einen "Weak
// spot" - das liest sich als "gemessen, und du stehst ganz unten".
// Gemessen wurde aber nichts.

import { describe, it, expect } from "vitest";

import { computeSkillStats, SKILLS } from "../progression";
import type { AppState } from "../store";

function zustand(scores: Record<string, number | null>): AppState {
  // computeSkillStats liest nur state.analyses[].scores - der Rest des
  // AppState ist fuer diesen Test ohne Belang. Ueber unknown, weil das
  // Teilobjekt den vollen Typ absichtlich nicht erfuellt.
  return {
    analyses: [{ id: "a", scores }, { id: "b", scores }],
  } as unknown as AppState;
}

const NUR_FLOW = {
  beatmatching: null, eq: null, timing: null, creativity: null,
  flow: 70, musicality: 80, overall: 75,
};

describe("computeSkillStats: nicht gemessen ist nicht null", () => {
  it("markiert leere Achsen als nicht gemessen", () => {
    const stats = computeSkillStats(zustand(NUR_FLOW));
    const leer = stats.filter((s) => !s.measured).map((s) => s.def.scoreField);
    expect(leer.sort()).toEqual(["beatmatching", "creativity", "eq", "timing"]);
  });

  it("gibt jeder leeren Achse einen Grund", () => {
    const stats = computeSkillStats(zustand(NUR_FLOW));
    for (const s of stats.filter((x) => !x.measured)) {
      expect(s.notMeasuredReason, `${s.def.scoreField} ohne Grund`).toBeTruthy();
    }
  });

  it("nennt bei beatmatching und timing den K1-Grund", () => {
    const stats = computeSkillStats(zustand(NUR_FLOW));
    for (const feld of ["beatmatching", "timing"]) {
      const s = stats.find((x) => x.def.scoreField === feld)!;
      expect(s.notMeasuredReason).toContain("K1");
    }
  });

  it("laesst befuellte Achsen unberuehrt", () => {
    const stats = computeSkillStats(zustand(NUR_FLOW));
    const gemessen = stats.filter((s) => s.measured).map((s) => s.def.scoreField);
    expect(gemessen.sort()).toEqual(["flow", "musicality"]);
    for (const s of stats.filter((x) => x.measured)) {
      expect(s.notMeasuredReason).toBeUndefined();
      expect(s.sampleCount).toBeGreaterThan(0);
    }
  });

  it("zaehlt sampleCount fuer leere Achsen auf 0", () => {
    const stats = computeSkillStats(zustand(NUR_FLOW));
    for (const s of stats.filter((x) => !x.measured)) {
      expect(s.sampleCount).toBe(0);
    }
  });

  it("kennt einen Grund fuer jede Achse, die leer sein kann", () => {
    // Schutz gegen eine neue Achse ohne Begruendungstext.
    const alleLeer = Object.fromEntries(SKILLS.map((d) => [d.scoreField, null]));
    const stats = computeSkillStats(zustand(alleLeer as never));
    for (const s of stats) {
      expect(s.measured).toBe(false);
      expect(s.notMeasuredReason, `${s.def.scoreField} ohne Grund`).toBeTruthy();
    }
  });
});
