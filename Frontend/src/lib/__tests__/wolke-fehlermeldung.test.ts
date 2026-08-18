// Eine Fehlermeldung, die die falsche Ursache nennt, kostet mehr Zeit als
// gar keine.
//
// Am 18.08.2026 scheiterte das Hochschieben mit Postgres-Code 42501. Die
// Meldung sprach von fehlenden Umgebungsvariablen und abgelaufenen Token -
// beides war in Ordnung. Die Ursache war Row Level Security, und die stand
// nicht drin. Bis das jemand nachgesehen hatte, war eine Stunde weg.
//
// Postgres unterscheidet zwei Lagen im Wortlaut, und nur eine davon ist ein
// Defekt:
//
//   mit "(USING expression)"  -> die id ist vergeben, die Zeile gehoert einem
//                                anderen Konto. RLS arbeitet RICHTIG.
//   ohne den Zusatz           -> auth.uid() passt nicht zu user_id, die
//                                Anmeldekette stimmt nicht.

import { describe, it, expect, beforeEach, vi } from "vitest";

const upsert = vi.fn();

vi.mock("../analyses.functions", () => ({
  upsertAnalysisFn: (...a: unknown[]) => upsert(...a),
  listAnalysesFn: vi.fn(),
}));

vi.mock("@/integrations/supabase/client", () => ({
  supabase: {
    auth: {
      getSession: async () => ({ data: { session: { user: { id: "u1" } } }, error: null }),
    },
  },
}));

function analyse() {
  return {
    id: "11111111-2222-3333-4444-555555555555",
    fileName: "MixCoach6.WAV",
    scores: { overall: 50 },
  } as never;
}

function rlsFehler(message: string) {
  return Object.assign(new Error(message), { code: "42501" });
}

describe("persistAnalysis: die Meldung nennt die Ursache", () => {
  let gewarnt: string[];

  beforeEach(() => {
    vi.resetModules();
    upsert.mockReset();
    gewarnt = [];
    vi.stubGlobal("window", { dispatchEvent: () => true, addEventListener: () => {}, removeEventListener: () => {} });
    vi.spyOn(console, "warn").mockImplementation((...a: unknown[]) => {
      gewarnt.push(a.map(String).join(" "));
    });
  });

  it("erkennt die fremde Zeile und sagt, dass RLS richtig arbeitet", async () => {
    upsert.mockRejectedValue(rlsFehler(
      'new row violates row-level security policy (USING expression) for table "analyses"',
    ));
    const { persistAnalysis } = await import("../sync");

    expect(await persistAnalysis(analyse())).toBe("fehlgeschlagen");
    const text = gewarnt.join(" ");
    expect(text).toMatch(/ANDEREN Konto/);
    expect(text).toMatch(/RLS arbeitet/);
    expect(text).toContain("MixCoach6.WAV");
    // Die alte, hier falsche Faehrte darf nicht mehr auftauchen.
    expect(text).not.toMatch(/SUPABASE_URL/);
  });

  it("erkennt die kaputte Anmeldekette und schickt nicht zu RLS", async () => {
    upsert.mockRejectedValue(rlsFehler(
      'new row violates row-level security policy for table "analyses"',
    ));
    const { persistAnalysis } = await import("../sync");

    expect(await persistAnalysis(analyse())).toBe("fehlgeschlagen");
    const text = gewarnt.join(" ");
    expect(text).toMatch(/auth\.uid\(\) passt nicht/);
    expect(text).not.toMatch(/ANDEREN Konto/);
  });

  it("laesst alles andere bei der allgemeinen Meldung", async () => {
    upsert.mockRejectedValue(new Error("Failed to fetch"));
    const { persistAnalysis } = await import("../sync");

    expect(await persistAnalysis(analyse())).toBe("fehlgeschlagen");
    expect(gewarnt.join(" ")).toMatch(/SUPABASE_URL/);
  });

  it("meldet Erfolg als gespeichert", async () => {
    upsert.mockResolvedValue({ ok: true });
    const { persistAnalysis } = await import("../sync");

    expect(await persistAnalysis(analyse())).toBe("gespeichert");
    expect(gewarnt).toEqual([]);
  });
});
