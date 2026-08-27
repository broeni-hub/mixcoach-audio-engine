/** Wann darf neben einer Fortschritts-Achse ein Pfeil stehen?
 *
 *  Ein Pfeil behauptet eine Richtung. Die gibt es nur, wenn sich die GANZE
 *  Reihe in eine bewegt — nicht, wenn `delta` von null verschieden ist.
 *  `delta` vergleicht die letzten drei Aufnahmen mit den drei davor und
 *  täuscht in beide Richtungen. Beide Fälle stehen im echten Bestand vom
 *  27.08.2026 nebeneinander, und beide sind hier festgehalten.
 */
import { describe, expect, it } from "vitest";
import { zeigtPfeil, type LoudnessTrend } from "../coach-profile";

const trend = (t: Partial<LoudnessTrend>): LoudnessTrend => ({
  current: 10, delta: null, lowerIsBetter: true, recordings: 14,
  currentSharePct: null, deltaSharePct: null, ...t,
});

describe("zeigtPfeil", () => {
  it("zeigt keinen Pfeil, wenn die Reihe keine Richtung hat", () => {
    // Der echte Beat-Jitter: das Fenster meldet −3,8 ms, die ganze Reihe
    // korreliert mit −0,004. Ein grüner Pfeil wäre eine Erfindung.
    expect(zeigtPfeil(trend({
      delta: -3.8, rankCorrelation: -0.004, developmentVisible: false,
    }))).toBe(false);
  });

  it("zeigt einen Pfeil, wenn die Reihe eine Richtung hat", () => {
    expect(zeigtPfeil(trend({
      delta: -0.9, rankCorrelation: -0.732, developmentVisible: true,
    }))).toBe(true);
  });

  it("zeigt keinen Pfeil bei delta 0, auch wenn die Reihe faellt", () => {
    // Der echte Pegelsprung: delta 0,0 bei r = −0,73. Es gibt eine
    // Entwicklung, aber dieses Fenster zeigt sie nicht - also kein Pfeil,
    // der eine Zahl behauptet, die 0 ist.
    expect(zeigtPfeil(trend({
      delta: 0, rankCorrelation: -0.732, developmentVisible: true,
    }))).toBe(false);
  });

  it("zeigt keinen Pfeil ohne Angabe zur Entwicklung", () => {
    // Aeltere Antworten der Engine kennen das Feld nicht. Im Zweifel
    // schweigen, nicht behaupten.
    expect(zeigtPfeil(trend({ delta: -2.0 }))).toBe(false);
  });

  it("kommt mit fehlendem Trend zurecht", () => {
    expect(zeigtPfeil(undefined)).toBe(false);
    expect(zeigtPfeil(null)).toBe(false);
  });
});
