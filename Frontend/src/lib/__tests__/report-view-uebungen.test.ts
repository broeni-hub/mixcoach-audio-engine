// Der Beleg einer Uebung muss bis zur Seite durchkommen.
//
// toReportView() hat bis zum 15.08.2026 nur title/description/xp
// uebernommen. metric, value, target, atSec und transitionIndex fielen
// still weg - die Zahl stand zwar im Beschreibungstext, aber die Seite
// konnte nichts damit anfangen: kein Anspringen, keine Anzeige des
// Belegs, keine Moeglichkeit zu pruefen, ob die Zahl zum Uebergang passt.
//
// Ein weggeworfenes Feld faellt nirgends auf. Deshalb dieser Test.

import { describe, it, expect } from "vitest";

import { toReportView } from "../report-view";
import type { AnalysisResult } from "../analysis";

function analyse(teil: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "abc", fileName: "REC001.WAV", createdAt: "2026-08-14T10:00:00Z",
    bpm: 126, key: "8A", transitionLength: 120,
    energyCurve: [], volumeCurve: [], frequency: null,
    scores: { beatmatching: null, eq: null, timing: null, creativity: null,
              flow: 70, musicality: 80, overall: 75 },
    timeline: [], strengths: [], weaknesses: [],
    feedback: { worked: [], improve: [], exercise: "", confidence: 0 },
    exercises: [],
    ...teil,
  } as AnalysisResult;
}

const UEBUNG = {
  title: "Pegel angleichen bei 18:46",
  description: "Bei 18:46 (Übergang 6) kam der neue Track 5,4 dB lauter rein. "
    + "Mix ihn nochmal, Ziel: unter 1,0 dB.",
  xp: 30,
  atSec: 1110.0,
  transitionIndex: 6,
  metric: "loudness_jump_db",
  value: 5.4,
  target: 1.0,
};

describe("toReportView: der Beleg kommt durch", () => {
  it("uebernimmt metric, value und target", () => {
    const view = toReportView(analyse({ exercises: [UEBUNG] }));
    const ex = view.exercises![0];
    expect(ex.metric).toBe("loudness_jump_db");
    expect(ex.value).toBe(5.4);
    expect(ex.target).toBe(1.0);
  });

  it("uebernimmt die Sprungmarke", () => {
    const view = toReportView(analyse({ exercises: [UEBUNG] }));
    const ex = view.exercises![0];
    expect(ex.atSec).toBe(1110.0);
    expect(ex.transitionIndex).toBe(6);
  });

  it("laesst Titel, Text und XP unveraendert", () => {
    const view = toReportView(analyse({ exercises: [UEBUNG] }));
    const ex = view.exercises![0];
    expect(ex.title).toBe(UEBUNG.title);
    expect(ex.description).toBe(UEBUNG.description);
    expect(ex.xp).toBe(30);
  });

  it("kommt mit alten Reports ohne diese Felder zurecht", () => {
    // Reports von vor dem 14.08.2026 trugen eine feste Vorlage ohne Beleg.
    const alt = { title: "Transition Review", description: "Listen ...", xp: 40 };
    const view = toReportView(analyse({ exercises: [alt] }));
    const ex = view.exercises![0];
    expect(ex.title).toBe("Transition Review");
    expect(ex.atSec).toBeUndefined();
    expect(ex.metric).toBeUndefined();
  });

  it("macht aus einer fehlenden Zahl kein null", () => {
    // atSec?: number - ein null waere ein Typbruch und wuerde in der
    // Seite als "0:00 anhoeren" erscheinen.
    const view = toReportView(analyse({
      exercises: [{ ...UEBUNG, atSec: undefined, value: undefined }],
    }));
    const ex = view.exercises![0];
    expect(ex.atSec).toBeUndefined();
    expect(ex.value).toBeUndefined();
  });
});

describe("toReportView: Beobachtungen bleiben getrennt", () => {
  const BEOBACHTUNG = {
    text: "Bei 6:38: 6A → 10A, 4 Schritte auf dem Camelot-Rad. "
      + "Ob dich das stört, ist an deinen Bewertungen nicht ablesbar.",
    atSec: 398.0, transitionIndex: 2, metric: "camelot_distance", value: 4,
  };

  it("landen in observations, nicht in exercises", () => {
    const view = toReportView(analyse({
      exercises: [UEBUNG], observations: [BEOBACHTUNG],
    }));
    expect(view.exercises).toHaveLength(1);
    expect(view.observations).toHaveLength(1);
    expect(view.observations![0].text).toContain("Camelot-Rad");
    // Keine Beobachtung darf als Uebung durchgehen.
    expect(view.exercises!.some((e) => e.description.includes("Camelot-Rad"))).toBe(false);
  });

  it("sind auch ohne Beobachtungen eine leere Liste, nicht undefined", () => {
    const view = toReportView(analyse({ exercises: [UEBUNG] }));
    expect(view.observations).toEqual([]);
  });

  it("tragen ihre Sprungmarke ebenfalls", () => {
    const view = toReportView(analyse({ observations: [BEOBACHTUNG] }));
    expect(view.observations![0].atSec).toBe(398.0);
    expect(view.observations![0].metric).toBe("camelot_distance");
  });
});
