// Die statische Uebungsbibliothek darf kein Ziel versprechen, das MixCoach
// nicht nachpruefen kann.
//
// 6 der 10 Uebungen nennen im successCriteria eine Groesse, die die Analyse
// nicht berechnet - "Phrase alignment score >= 85", "EQ score >= 85",
// "Creativity score >= 80", "BPM drift <= 1.5 %". Sie sind als solche
// markiert. Der Test haelt fest, dass die Markierung nicht wieder
// verschwindet und dass keine neue Uebung unmarkiert danebenrutscht.

import { describe, it, expect } from "vitest";

import { EXERCISE_LIBRARY, KRITERIUM_NICHT_PRUEFBAR } from "../coach";

// Groessen, die die Analyse nicht liefert. Wer ein Kriterium darauf baut,
// verspricht etwas, das niemand nachpruefen kann.
const NICHT_BERECHNET = [
  /phrase alignment score/i,
  /\beq score\b/i,
  /creativity score/i,
  /bpm drift/i,
  /timing feels/i,
];

describe("EXERCISE_LIBRARY: kein unpruefbares Versprechen", () => {
  it("markiert jede Uebung, deren Kriterium auf einer nicht berechneten Groesse ruht", () => {
    const uebersehen: string[] = [];
    for (const ex of EXERCISE_LIBRARY) {
      const text = ex.successCriteria.join(" | ");
      const trifft = NICHT_BERECHNET.some((r) => r.test(text));
      if (trifft && ex.criterionVerifiable !== false) {
        uebersehen.push(`${ex.id}: ${text}`);
      }
    }
    expect(uebersehen, "unmarkiert trotz nicht berechneter Groesse").toEqual([]);
  });

  it("markiert genau die sechs bekannten", () => {
    const markiert = EXERCISE_LIBRARY
      .filter((e) => e.criterionVerifiable === false)
      .map((e) => e.id)
      .sort();
    expect(markiert).toEqual([
      "bass-patience", "bass-swap", "freestyle-review",
      "phrase-16", "sync-hold", "warmup-flow",
    ]);
  });

  it("gibt jeder markierten Uebung einen nachvollziehbaren Grund", () => {
    for (const ex of EXERCISE_LIBRARY.filter((e) => e.criterionVerifiable === false)) {
      expect(ex.criterionNote, `${ex.id} ohne Grund`).toBeTruthy();
      // Der Grund muss die Groesse benennen, nicht nur "geht nicht".
      expect(ex.criterionNote!.length, `${ex.id}: Grund zu duenn`).toBeGreaterThan(25);
    }
  });

  it("laesst die vier tragfaehigen unmarkiert", () => {
    const ohne = EXERCISE_LIBRARY
      .filter((e) => e.criterionVerifiable !== false)
      .map((e) => e.id)
      .sort();
    expect(ohne).toEqual(["energy-buildup", "key-lock", "monthly-review", "vocal-clash"]);
  });

  it("haelt den Hinweistext bereit und er sagt, wer einschaetzt", () => {
    expect(KRITERIUM_NICHT_PRUEFBAR).toMatch(/nicht nachprüfen/);
    expect(KRITERIUM_NICHT_PRUEFBAR).toMatch(/selbst/);
  });

  it("aendert die Kriterien nicht - nur die Kennzeichnung", () => {
    // Der Inhalt ist Sebastians Entscheidung. Bis dahin bleibt der Text
    // stehen, wie er ist.
    const phrase = EXERCISE_LIBRARY.find((e) => e.id === "phrase-16")!;
    expect(phrase.successCriteria).toContain("Phrase alignment score ≥ 85");
  });
});
