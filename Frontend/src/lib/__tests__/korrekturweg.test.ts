// Der Korrekturweg: erreicht eine Aenderung auf der Platte den Browser?
//
// Bis zum 13.08.2026 lautete die Antwort nein. Drei Stellen stiegen aus,
// sobald sie eine id schon kannten - analysis-engine.ts (zweimal) und
// store.ts -, und sync.ts liess die DB bedingungslos gewinnen. Eine einmal
// angesehene Analyse war damit eingefroren: es gab keinen Weg, einen
// falschen Report zu berichtigen, ausser den Cache zu loeschen.
//
// Diese Tests halten die Regel fest: eine HOEHERE scoringVersion loest ab,
// Gleichstand bleibt, ein ungestempelter Eingang loest nie ab. Und in allen
// Faellen ueberlebt der nutzereigene Zustand.

import { describe, it, expect, beforeEach, vi } from "vitest";

import { UNSTAMPED, versionVon, revisionVon, loestAb, mitNutzerstand } from "../scoring-version";

const KEY = "mixcoach.state.v1";

// Kein jsdom in diesem Projekt - localStorage und window werden gestellt.
function speicherStellen() {
  const daten = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => daten.get(k) ?? null,
    setItem: (k: string, v: string) => void daten.set(k, v),
    removeItem: (k: string) => void daten.delete(k),
    clear: () => daten.clear(),
  });
  // addEventListener wird gebraucht, weil api/provider.ts sich schon beim
  // Import auf "mixcoach:engine-status" anmeldet (ueber store.ts mitgezogen).
  // location ebenso: remoteProvider.getBaseUrl() liest beim Import
  // window.location.hostname. Ohne diese Felder haengt der Test an der
  // Import-Reihenfolge - ist window noch gar nicht gestellt, greift dort der
  // "typeof window === undefined"-Zweig und alles geht gut.
  vi.stubGlobal("window", {
    dispatchEvent: () => true,
    addEventListener: () => {},
    removeEventListener: () => {},
    location: { hostname: "localhost", origin: "http://localhost" },
  });
  return daten;
}

type Report = { id: string; scoringVersion?: number; scores: { overall: number }; marke: string };

function report(marke: string, version?: number): Report {
  return { id: "abc", scoringVersion: version, scores: { overall: 50 }, marke };
}

function zustandSetzen(gespeichert: Report, archivedIds: string[] = []) {
  localStorage.setItem(KEY, JSON.stringify({ analyses: [gespeichert], archivedIds }));
}

function gespeicherterZustand() {
  return JSON.parse(localStorage.getItem(KEY) || "{}");
}

describe("scoring-version: die Regel selbst", () => {
  it("liest die Version, fehlend gilt als ungestempelt", () => {
    expect(versionVon({ scoringVersion: 3 })).toBe(3);
    expect(versionVon({})).toBe(UNSTAMPED);
    expect(versionVon(null)).toBe(UNSTAMPED);
    expect(versionVon({ scoringVersion: null })).toBe(UNSTAMPED);
  });

  it("loest ohne Revisionen nur bei echt hoeherer Version ab", () => {
    expect(loestAb({}, { scoringVersion: 3 })).toBe(true);
    expect(loestAb({ scoringVersion: 3 }, { scoringVersion: 3 })).toBe(false);
    expect(loestAb({ scoringVersion: 3 }, {})).toBe(false);
    expect(loestAb({ scoringVersion: 3 }, { scoringVersion: 2 })).toBe(false);
  });

  it("liest die Revision, fehlend gilt als 0", () => {
    expect(revisionVon({ reportRevision: 2 })).toBe(2);
    expect(revisionVon({})).toBe(0);
    expect(revisionVon({ reportRevision: null })).toBe(0);
  });

  it("die hoehere Revision entscheidet vor der Version", () => {
    // Der Kern von B: eine Datenkorrektur darf die scoringVersion nicht
    // erhoehen, muss aber trotzdem ankommen.
    expect(loestAb({ scoringVersion: 3, reportRevision: 1 },
                   { scoringVersion: 3, reportRevision: 2 })).toBe(true);
    expect(loestAb({ scoringVersion: 3, reportRevision: 2 },
                   { scoringVersion: 3, reportRevision: 1 })).toBe(false);
    expect(loestAb({ scoringVersion: 3, reportRevision: 2 },
                   { scoringVersion: 3, reportRevision: 2 })).toBe(false);
  });

  it("eine gesenkte Version kommt mit hoeherer Revision trotzdem an", () => {
    // Die sechs Reports, deren unbelegter Stempel 3 entfernt wurde. Nach
    // reiner Versionsordnung waeren sie fuer immer unkorrigierbar gewesen.
    expect(loestAb({ scoringVersion: 3, reportRevision: 0 },
                   { reportRevision: 2 })).toBe(true);
  });

  it("ein Altbestand ohne Revision verdraengt keine hoehere Version", () => {
    expect(loestAb({ scoringVersion: 3 }, { scoringVersion: 2 })).toBe(false);
  });

  it("nimmt den archived-Zustand auf den neuen Stand mit", () => {
    expect(mitNutzerstand({ a: 1 }, { a: 0, archived: true })).toEqual({ a: 1, archived: true });
    expect(mitNutzerstand({ a: 1 }, { a: 0 })).toEqual({ a: 1 });
  });
});

describe("mergeRemoteAnalysisIntoStore", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    speicherStellen();
    vi.resetModules();
  });

  async function merge(eingehend: Report) {
    const { mergeRemoteAnalysisIntoStore } = await import("../analysis-engine");
    mergeRemoteAnalysisIntoStore(eingehend as never);
  }

  it("ungestempelt im Store + gestempelt von der Engine -> wird ersetzt", async () => {
    zustandSetzen(report("alt"), ["abc"]);
    await merge(report("neu", 3));

    const s = gespeicherterZustand();
    expect(s.analyses).toHaveLength(1);
    expect(s.analyses[0].marke).toBe("neu");
    expect(s.analyses[0].scoringVersion).toBe(3);
    expect(s.archivedIds).toEqual(["abc"]);
  });

  it("gestempelt (3) + gestempelt (3) -> bleibt", async () => {
    zustandSetzen(report("alt", 3), ["abc"]);
    await merge(report("neu", 3));

    const s = gespeicherterZustand();
    expect(s.analyses[0].marke).toBe("alt");
    expect(s.archivedIds).toEqual(["abc"]);
  });

  it("gestempelt (3) + ungestempelt von der Engine -> bleibt", async () => {
    zustandSetzen(report("alt", 3), ["abc"]);
    await merge(report("neu"));

    const s = gespeicherterZustand();
    expect(s.analyses[0].marke).toBe("alt");
    expect(s.archivedIds).toEqual(["abc"]);
  });

  it("unbekannte id wird weiterhin einfach aufgenommen", async () => {
    localStorage.setItem(KEY, JSON.stringify({ analyses: [], archivedIds: [] }));
    await merge(report("neu", 3));
    expect(gespeicherterZustand().analyses).toHaveLength(1);
  });

  it("nimmt archived beim Ersetzen mit", async () => {
    const alt = { ...report("alt"), archived: true };
    localStorage.setItem(KEY, JSON.stringify({ analyses: [alt], archivedIds: [] }));
    await merge(report("neu", 3));

    const s = gespeicherterZustand();
    expect(s.analyses[0].marke).toBe("neu");
    expect(s.analyses[0].archived).toBe(true);
  });
});
