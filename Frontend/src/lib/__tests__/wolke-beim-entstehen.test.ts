// Erreicht eine Analyse die Wolke, wenn sie ENTSTEHT - oder erst irgendwann?
//
// Bis zum 18.08.2026 lautete die Antwort: erst irgendwann. persistAnalysis()
// hatte im ganzen Frontend genau einen Aufrufer, analysis-engine.ts:286, und
// der lag in runPipeline() - dem Browser-Notpfad, den der Preflight in
// app.upload.tsx gar nicht erst laufen laesst. Der benutzte Weg, die Engine,
// endete in analysis.processing.$jobId.tsx bei addAnalysis(), und das schrieb
// ausschliesslich in localStorage.
//
// Praktische Folge: wer angemeldet ein Set analysierte und danach das Geraet
// wechselte, fand dort nichts. Von aussen sah das aus, als ueberlebte die
// Historie keinen Geraetewechsel - Bedingung 2 der Live-Schwelle. Es war aber
// kein fehlendes Feature, sondern eine Kette, die eine Stelle vor dem Ziel
// abriss.
//
// Diese Tests halten fest: JEDER Weg in den Store schiebt hoch, eine
// Berichtigung ebenso, ein unveraenderter Stand nicht (sonst entstuende mit
// syncAnalysesWithDb() eine Schleife), und es gibt nur EINE Stelle, die
// hochschiebt.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const KEY = "mixcoach.state.v1";
const hier = dirname(fileURLToPath(import.meta.url));

// Kein jsdom in diesem Projekt - localStorage und window werden gestellt.
// Gleiche Vorlage wie korrekturweg.test.ts, aus demselben Grund.
function speicherStellen() {
  const daten = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => daten.get(k) ?? null,
    setItem: (k: string, v: string) => void daten.set(k, v),
    removeItem: (k: string) => void daten.delete(k),
    clear: () => daten.clear(),
  });
  vi.stubGlobal("window", {
    dispatchEvent: () => true,
    addEventListener: () => {},
    removeEventListener: () => {},
    location: { hostname: "localhost", origin: "http://localhost" },
  });
  return daten;
}

// Die Wolke wird gestellt: der Test prueft, DASS und WOMIT hochgeschoben
// wird, nicht ob Supabase antwortet.
const hochgeschoben = vi.fn<(a: unknown, archiviert: boolean) => Promise<string>>();
vi.mock("../sync", () => ({
  persistAnalysis: (a: unknown, archiviert = false) => hochgeschoben(a, archiviert),
  syncAnalysesWithDb: vi.fn(),
  clearSyncMarker: vi.fn(),
}));

type Report = {
  id: string;
  scoringVersion?: number;
  reportRevision?: number;
  scores: { overall: number };
  marke: string;
};

function report(marke: string, v?: { version?: number; revision?: number }): Report {
  return {
    id: "11111111-2222-3333-4444-555555555555",
    scoringVersion: v?.version,
    reportRevision: v?.revision,
    scores: { overall: 50 },
    marke,
  };
}

function zustandSetzen(analyses: Report[], archivedIds: string[] = []) {
  localStorage.setItem(KEY, JSON.stringify({ analyses, archivedIds }));
}

async function store() {
  return await import("../store");
}

describe("addAnalysis: die Wolke beim Entstehen", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    speicherStellen();
    hochgeschoben.mockReset();
    hochgeschoben.mockResolvedValue("gespeichert");
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("schiebt eine neu entstandene Analyse hoch", async () => {
    zustandSetzen([]);
    const { addAnalysis } = await store();

    await addAnalysis(report("neu", { version: 3 }) as never);

    expect(hochgeschoben).toHaveBeenCalledTimes(1);
    expect((hochgeschoben.mock.calls[0][0] as Report).marke).toBe("neu");
    expect(hochgeschoben.mock.calls[0][1]).toBe(false);
  });

  it("schiebt auch eine BERICHTIGUNG hoch, nicht nur den Neuzugang", async () => {
    // Sonst behaelt die Wolke die alte Fassung, und genau dort laufen
    // lokaler Stand und Datenbank auseinander, wo korrigiert wurde.
    zustandSetzen([report("alt", { version: 3, revision: 1 })]);
    const { addAnalysis } = await store();

    await addAnalysis(report("berichtigt", { version: 3, revision: 2 }) as never);

    expect(hochgeschoben).toHaveBeenCalledTimes(1);
    expect((hochgeschoben.mock.calls[0][0] as Report).marke).toBe("berichtigt");
  });

  it("schiebt NICHT hoch, wenn der eingehende Stand nichts abloest", async () => {
    // Der Riegel gegen die Schleife: syncAnalysesWithDb() holt Zeilen aus der
    // DB; kaeme jede davon hier wieder als Upload heraus, liefe es rund.
    zustandSetzen([report("alt", { version: 3 })]);
    const { addAnalysis } = await store();

    await addAnalysis(report("gleich alt", { version: 3 }) as never);

    expect(hochgeschoben).not.toHaveBeenCalled();
  });

  it("nimmt den archivierten Zustand mit hoch", async () => {
    const a = report("alt", { version: 1 });
    zustandSetzen([a], [a.id]);
    const { addAnalysis } = await store();

    await addAnalysis(report("neuer", { version: 3 }) as never);

    expect(hochgeschoben.mock.calls[0][1]).toBe(true);
  });

  it("vergibt bei einer Auffrischung keine Punkte, schiebt aber hoch", async () => {
    zustandSetzen([]);
    const { addAnalysis } = await store();

    await addAnalysis(report("von der Platte", { version: 3 }) as never, { xp: false });

    expect(hochgeschoben).toHaveBeenCalledTimes(1);
    const gespeichert = JSON.parse(localStorage.getItem(KEY) || "{}");
    expect(gespeichert.profile.xp).toBe(120); // Startwert, kein Zuwachs
  });

  it("vergibt beim Neuzugang weiterhin Punkte", async () => {
    zustandSetzen([]);
    const { addAnalysis } = await store();

    await addAnalysis(report("neu", { version: 3 }) as never);

    const gespeichert = JSON.parse(localStorage.getItem(KEY) || "{}");
    expect(gespeichert.profile.xp).toBe(120 + 25); // overall 50 -> 25
  });
});

describe("mergeRemoteAnalysisIntoStore: derselbe eine Punkt", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    speicherStellen();
    hochgeschoben.mockReset();
    hochgeschoben.mockResolvedValue("gespeichert");
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("schiebt eine von der Platte aufgefrischte Berichtigung in die Wolke", async () => {
    // Der Weg, auf dem eine Korrektur tatsaechlich ankommt (Report-Seite,
    // Analysen-Liste). Vorher endete sie im localStorage.
    zustandSetzen([report("alt", { version: 3, revision: 1 })]);
    const { mergeRemoteAnalysisIntoStore } = await import("../analysis-engine");

    mergeRemoteAnalysisIntoStore(report("berichtigt", { version: 3, revision: 2 }) as never);
    await vi.waitFor(() => expect(hochgeschoben).toHaveBeenCalledTimes(1));

    const gespeichert = JSON.parse(localStorage.getItem(KEY) || "{}");
    expect(gespeichert.analyses[0].marke).toBe("berichtigt");
    expect(gespeichert.profile.xp).toBe(120); // Auffrischung, keine Punkte
  });
});

describe("es gibt nur EINE Stelle, die hochschiebt", () => {
  // Der Bauplan, an dem dieses Projekt dreimal Tage verloren hat: dieselbe
  // Sache an zwei Orten, einer laeuft davon. Deshalb als Regel festgehalten
  // und nicht nur als Kommentar.
  /** Kommentare raus - der Waechter prueft Code, nicht Prosa. Ohne das
   *  schlaegt schon die Begruendung an, warum der zweite Aufruf weg ist. */
  function ohneKommentare(quelltext: string): string {
    return quelltext
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
  }

  it("ruft niemand ausser store.ts persistAnalysis auf", () => {
    const dateien = ["analysis-engine.ts", "store.ts", "sync.ts"]
      .map((n) => [n, ohneKommentare(readFileSync(join(hier, "..", n), "utf-8"))] as const);

    const aufrufer = dateien
      .filter(([name, inhalt]) => name !== "sync.ts" && /persistAnalysis\s*\(/.test(inhalt))
      .map(([name]) => name);

    // store.ts ruft ueber den dynamischen Import auf - das ist der eine Ort.
    expect(aufrufer).toEqual(["store.ts"]);
  });
});
