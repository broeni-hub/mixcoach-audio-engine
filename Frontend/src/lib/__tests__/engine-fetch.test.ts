/** Jeder Aufruf an die Engine geht über engineFetch.
 *
 *  Der wichtigste Test ist "kein roher fetch an die Engine": er liest den
 *  Quelltext und findet eine Stelle, die den Helfer umgeht. Bei dreizehn
 *  Aufrufstellen in acht Dateien ist es sonst eine Frage der Zeit, bis eine
 *  vergessen wird — und dann bekommt der Nutzer ein 401 an genau einer
 *  Stelle der App, während der Rest läuft. Genau diese Sorte Fehler hat in
 *  diesem Projekt mehrfach Tage gekostet.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/integrations/supabase/client", () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

import { supabase } from "@/integrations/supabase/client";
import { engineFetch, engineToken } from "../api/engineFetch";

const sitzung = (token: string | null) =>
  (supabase.auth.getSession as ReturnType<typeof vi.fn>).mockResolvedValue({
    data: { session: token ? { access_token: token } : null },
  });

describe("engineFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}")));
    // Die Testumgebung ist node, dort gibt es kein window - und engineToken()
    // steigt genau daran aus (serverseitig gibt es keine Sitzung). Für den
    // Browser-Fall muss es hier stehen.
    vi.stubGlobal("window", {});
  });

  it("hängt das Token an, wenn eine Sitzung da ist", async () => {
    sitzung("tok-123");
    await engineFetch("http://127.0.0.1:8000/analysis");
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer tok-123");
  });

  it("ruft ohne Header auf, wenn keine Sitzung da ist", async () => {
    sitzung(null);
    await engineFetch("http://127.0.0.1:8000/analysis");
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    // Bei MIXCOACH_AUTH=aus - der Vorgabe - braucht ihn niemand.
    expect(init === undefined || !new Headers(init?.headers).has("Authorization")).toBe(true);
  });

  it("überschreibt einen ausdrücklich gesetzten Header nicht", async () => {
    sitzung("tok-123");
    await engineFetch("http://127.0.0.1:8000/analysis", {
      headers: { Authorization: "Bearer eigener" },
    });
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer eigener");
  });

  it("behält Methode und Rumpf", async () => {
    sitzung("tok-123");
    await engineFetch("http://127.0.0.1:8000/x", { method: "POST", body: "{}" });
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.body).toBe("{}");
  });

  it("gibt null zurück, wenn Supabase wirft", async () => {
    (supabase.auth.getSession as ReturnType<typeof vi.fn>)
      .mockRejectedValue(new Error("kaputt"));
    // Kein Token zu bekommen darf den Aufruf nicht verhindern.
    await expect(engineToken()).resolves.toBeNull();
  });
});

describe("kein roher fetch an die Engine", () => {
  function dateien(ordner: string): string[] {
    return readdirSync(ordner).flatMap((name) => {
      const pfad = join(ordner, name);
      if (statSync(pfad).isDirectory()) {
        return name === "__tests__" || name === "node_modules" ? [] : dateien(pfad);
      }
      return /\.(ts|tsx)$/.test(name) ? [pfad] : [];
    });
  }

  it("findet keine Aufrufstelle, die engineFetch umgeht", () => {
    // Ein roher fetch auf eine zusammengesetzte Engine-URL. Der Helfer
    // selbst darf das - er IST die eine Stelle.
    const verdaechtig = /(?<!engine)\bfetch\(\s*`\$\{(base|url|this\.baseUrl)\}/;
    const treffer: string[] = [];

    for (const pfad of dateien("src")) {
      if (pfad.endsWith(join("api", "engineFetch.ts"))) continue;
      readFileSync(pfad, "utf-8").split("\n").forEach((zeile, i) => {
        if (verdaechtig.test(zeile)) treffer.push(`${pfad}:${i + 1}: ${zeile.trim()}`);
      });
    }

    expect(treffer, `diese Stellen umgehen engineFetch:\n${treffer.join("\n")}`)
      .toEqual([]);
  });
});
