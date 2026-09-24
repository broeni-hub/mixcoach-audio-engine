// Der Vergleich gegen die sechs Profi-Sets muss bis zur Seite durchkommen.
//
// Bis zum 24.09.2026 gab es ihn nur in tools/set_report.py - der Seite, die
// ein fremder DJ per Mail bekommt. Die App kannte ihren eigenen Massstab
// nicht, und dadurch war die verschickte Seite ein zweites Produkt statt
// einer Darstellung des ersten.
//
// Derselbe Fehlertyp wie bei den Uebungs-Belegen (report-view-uebungen):
// ein Feld, das der Mapper nicht durchreicht, faellt nirgends auf.

import { describe, it, expect } from "vitest";

import { toReportView } from "../report-view";
import type { AnalysisResult } from "../analysis";

function analyse(teil: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "abc", fileName: "REC001.WAV", createdAt: "2026-09-24T10:00:00Z",
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

// So, wie app/coach/referenz.py:vergleich() ihn liefert.
const JITTER = {
  metrik: "beat_jitter_ms",
  wert: 11.2,
  einheit: "ms",
  min: 5.8,
  max: 11.9,
  innerhalb: true,
  schwelle: 15.0,
  uebergaenge: 13,
  referenzSets: 6,
};

describe("toReportView: referenz", () => {
  it("reicht den Vergleich vollstaendig durch", () => {
    const view = toReportView(analyse({ referenz: [JITTER] } as Partial<AnalysisResult>));
    expect(view.referenz).toHaveLength(1);
    expect(view.referenz![0]).toEqual(JITTER);
  });

  it("verliert die Spanne nicht", () => {
    // Der eigentliche Punkt: min UND max muessen ankommen. Bis zum
    // 23.09.2026 stand in set_report.py nur der Median, und jeder Wert
    // darueber las sich als Rueckstand - ein Test-DJ hat das zu Recht
    // beanstandet.
    const view = toReportView(analyse({ referenz: [JITTER] } as Partial<AnalysisResult>));
    const r = view.referenz![0];
    expect(r.min).toBe(5.8);
    expect(r.max).toBe(11.9);
    expect(r.innerhalb).toBe(true);
  });

  it("macht aus fehlendem innerhalb kein 'true'", () => {
    // undefined heisst 'nicht entscheidbar', nicht 'liegt drin'.
    const ohne = { ...JITTER, innerhalb: undefined } as unknown as typeof JITTER;
    const view = toReportView(analyse({ referenz: [ohne] } as Partial<AnalysisResult>));
    expect(view.referenz![0].innerhalb).toBeNull();
  });

  it("gibt eine leere Liste, wenn der Report den Vergleich nicht kennt", () => {
    // Reports von vor dem 24.09.2026. Die Karte rendert dann nichts -
    // kein Platzhalter, keine erfundene Spanne.
    const view = toReportView(analyse());
    expect(view.referenz).toEqual([]);
  });
});
