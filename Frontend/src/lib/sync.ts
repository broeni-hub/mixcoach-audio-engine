// One-shot sync of localStorage analyses with the Cloud DB after sign-in.
// Strategy: pull all DB rows, push any local-only rows up, then replace
// the local cache with the union. DB is the source of truth.
import type { AnalysisResult } from "./analysis";
import { listAnalysesFn, upsertAnalysisFn } from "./analyses.functions";
import { loestAb, mitNutzerstand } from "./scoring-version";
import { supabase } from "@/integrations/supabase/client";

type Stored = AnalysisResult & { archived?: boolean };

function toUpsertPayload(a: AnalysisResult, archived: boolean) {
  return {
    id: a.id,
    filename: a.fileName,
    bpm: a.bpm ?? null,
    key_name: a.key ?? null,
    bass_pct: a.frequency?.bass ?? null,
    mid_pct: a.frequency?.mid ?? null,
    high_pct: a.frequency?.high ?? null,
    duration_seconds: a.transitionLength ?? null,
    scores: (a.scores ?? {}) as unknown as Record<string, unknown>,
    curves: { energy: a.energyCurve, volume: a.volumeCurve } as Record<string, unknown>,
    coach_summary: a.feedback?.exercise ?? null,
    track_b_filename: a.trackB?.fileName ?? null,
    track_b_bpm: a.trackB?.bpm ?? null,
    track_b_key: a.trackB?.key ?? null,
    cue_point_sec: a.transition?.cue_point_sec ?? null,
    transition_metrics: (a.transition ?? {}) as unknown as Record<string, unknown>,
    payload: a as unknown as Record<string, unknown>,
    archived,
  };
}

/**
 * Was beim Hochschieben herauskam. Drei Faelle, und nur EINER davon ist ein
 * Fehler - deshalb sind es drei Werte und kein boolean.
 */
export type Hochschiebe_Ergebnis = "gespeichert" | "keine-sitzung" | "fehlgeschlagen";

/**
 * Steht eine angemeldete Sitzung? Antwortet mit dem Grund, wenn nicht.
 *
 * Der Grund ist nicht Zierde: ohne ihn sieht "keine Sitzung" identisch aus,
 * egal ob niemand angemeldet ist (normal) oder der Supabase-Client mangels
 * VITE_SUPABASE_URL gar nicht erst entsteht (kaputt). Genau diese zwei Faelle
 * auseinanderzuhalten hat am 11.08.2026 einen Tag gekostet.
 */
async function sitzung(): Promise<{ da: boolean; grund?: string }> {
  if (typeof window === "undefined") return { da: false, grund: "kein Browser (SSR)" };
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error) return { da: false, grund: `Supabase meldet: ${error.message}` };
    return data.session ? { da: true } : { da: false };
  } catch (e) {
    // createSupabaseClient() wirft, wenn VITE_SUPABASE_URL oder
    // VITE_SUPABASE_PUBLISHABLE_KEY in Frontend/.env fehlen.
    return { da: false, grund: `Supabase-Client nicht aufgebaut: ${(e as Error).message}` };
  }
}

/**
 * Der EINE Weg, auf dem eine Analyse in `public.analyses` landet.
 *
 * Aufgerufen von store.ts:addAnalysis() - also bei JEDER neu entstandenen und
 * jeder abgeloesten Analyse - und von syncAnalysesWithDb() fuer den Nachzug
 * beim Anmelden. Zwei Anlaesse, eine Stelle.
 *
 * Bis zum 18.08.2026 hing der einzige Aufruf in analysis-engine.ts:runPipeline(),
 * dem Browser-Notpfad, den app.upload.tsx per Preflight gar nicht erst laufen
 * laesst. Eine ueber die Engine analysierte Aufnahme erreichte die Wolke damit
 * NIE beim Entstehen, sondern fruehestens beim naechsten Anmelden - wer danach
 * das Geraet wechselte, fand dort nichts. Von aussen sah das aus, als
 * ueberlebte die Historie keinen Geraetewechsel (Bedingung 2 der Live-Schwelle).
 */
export async function persistAnalysis(
  a: AnalysisResult,
  archived = false,
): Promise<Hochschiebe_Ergebnis> {
  const s = await sitzung();
  if (!s.da) {
    // NICHT angemeldet ist kein Fehler, sondern ein gueltiger Zustand:
    // analyses.user_id ist NOT NULL und RLS scoped auf auth.uid(), es gibt
    // also niemanden, an dem die Zeile haengen koennte. Deshalb info statt
    // warn - und trotzdem mit Grund, damit niemand raten muss.
    console.info(
      "[mixcoach] Analyse bleibt vorerst lokal - " +
      (s.grund ?? "niemand ist angemeldet") + ". Kein Fehler: ohne Sitzung " +
      "gibt es keinen Nutzer, an dem die Zeile haengen koennte " +
      "(analyses.user_id ist NOT NULL). Beim naechsten Anmelden holt " +
      "syncAnalysesWithDb() sie nach.",
    );
    return "keine-sitzung";
  }

  try {
    await upsertAnalysisFn({ data: toUpsertPayload(a, archived) });
    return "gespeichert";
  } catch (e) {
    // 42501 = insufficient_privilege. Zwei verschiedene Lagen, und die
    // Unterscheidung steht im Wortlaut, den Postgres mitschickt:
    //
    //   "... (USING expression) ..."  -> Es GIBT schon eine Zeile mit dieser
    //      id, und sie gehoert einem anderen Konto. Postgres meldet diese
    //      Variante ausschliesslich beim ON CONFLICT DO UPDATE, wenn die
    //      vorhandene Zeile unter der USING-Bedingung unsichtbar ist. Das ist
    //      KEIN Defekt - RLS arbeitet richtig. Der Weg dahin: dieselbe
    //      Analyse-id wurde unter einem anderen Konto hochgeschoben.
    //   ohne den Zusatz              -> WITH CHECK schlaegt fehl, auth.uid()
    //      passt nicht zu user_id. Dann stimmt die Anmeldekette nicht.
    //
    // Am 18.08.2026 hat genau das eine Stunde gekostet, weil hier nur von
    // fehlenden Umgebungsvariablen die Rede war - und die waren in Ordnung.
    const meldung = (e as { message?: string })?.message ?? String(e);
    const code = (e as { code?: string })?.code;
    if (code === "42501" || /row-level security/i.test(meldung)) {
      const fremd = /USING expression/i.test(meldung);
      console.warn(
        fremd
          ? "[mixcoach] Analyse NICHT gespeichert: unter dieser id existiert " +
            "bereits eine Zeile, die einem ANDEREN Konto gehoert. RLS arbeitet " +
            "hier richtig - dieselbe Analyse wurde schon einmal von einem " +
            "anderen Nutzer hochgeschoben. Abhilfe: mit dem urspruenglichen " +
            "Konto anmelden. Analyse: " + a.fileName + " (" + a.id + ")"
          : "[mixcoach] Analyse NICHT gespeichert: die Datenbank ordnet die " +
            "Zeile keinem Nutzer zu (auth.uid() passt nicht zu user_id). Das " +
            "ist die Anmeldekette, nicht die Analyse - Token pruefen, ggf. neu " +
            "anmelden. Analyse: " + a.fileName + " (" + a.id + ")",
        e,
      );
      return "fehlgeschlagen";
    }

    // Non-fatal fuer diesen Aufruf - der lokale Cache hat die Analyse noch.
    // Aber es ist NICHT folgenlos: schlaegt das dauerhaft fehl, existiert die
    // Historie nur in diesem Browser, und "die Historie ueberlebt einen
    // Geraetewechsel" ist Bedingung 2 der Live-Schwelle.
    //
    // Die Ursachen stehen beim Namen - eine allgemeine Warnung haette
    // monatelang niemand gedeutet. Hier stand bis zum 18.08.2026
    // SUPABASE_SERVICE_ROLE_KEY; das war seit dem Umbau auf
    // requireSupabaseAuth die falsche Faehrte: upsertAnalysisFn laeuft ueber
    // den Publishable Key plus das Bearer-Token des Nutzers, den
    // Service-Role-Key benutzen nur beta.functions.ts und
    // coach-feedback.functions.ts. "Nicht angemeldet" faengt jetzt der
    // Zweig darueber ab, es bleiben die Server- und Token-Ursachen.
    console.warn(
      "[mixcoach] Analyse NICHT in die Cloud gespeichert - sie existiert nur " +
      "in diesem Browser. Verbleibende Ursachen (RLS ist oben schon " +
      "abgefangen): SUPABASE_URL oder SUPABASE_PUBLISHABLE_KEY fehlen in " +
      "Frontend/.env (requireSupabaseAuth wirft dann beim Start), das " +
      "Zugangstoken ist abgelaufen - dann hilft neu anmelden -, oder die " +
      "Engine/das Netz ist weg. Fehler:", e,
    );
    return "fehlgeschlagen";
  }
}

const SYNC_KEY = "mixcoach.sync.user";
const STATE_KEY = "mixcoach.state.v1";

interface StoreShape {
  analyses: Stored[];
  archivedIds: string[];
  [k: string]: unknown;
}

function readStore(): StoreShape {
  try {
    return JSON.parse(localStorage.getItem(STATE_KEY) || "{}") as StoreShape;
  } catch {
    return { analyses: [], archivedIds: [] };
  }
}

function writeStore(next: StoreShape) {
  localStorage.setItem(STATE_KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("mixcoach:update"));
}

export async function syncAnalysesWithDb(userId: string) {
  if (typeof window === "undefined") return;

  // If a different user signed in on this browser, drop the previous user's
  // cached analyses before merging — never push them up to the new account.
  const prevUser = localStorage.getItem(SYNC_KEY);
  if (prevUser && prevUser !== userId) {
    const s = readStore();
    writeStore({ ...s, analyses: [], archivedIds: [] });
    localStorage.removeItem(SYNC_KEY);
  }

  const store = readStore();
  const localAll: Stored[] = Array.isArray(store.analyses) ? store.analyses : [];
  const localArchived = new Set<string>(Array.isArray(store.archivedIds) ? store.archivedIds : []);

  let remote: Array<Record<string, unknown> & { id: string; archived: boolean }> = [];
  try {
    remote = (await listAnalysesFn()) as typeof remote;
  } catch (e) {
    console.warn("[mixcoach] DB list failed, keeping local cache", e);
    return;
  }
  const remoteIds = new Set(remote.map((r) => r.id));

  // Push local-only rows to DB.
  const localOnly = localAll.filter((a) => !remoteIds.has(a.id));
  await Promise.all(
    localOnly.map((a) => persistAnalysis(a, localArchived.has(a.id))),
  );

  // Merge: bei gemeinsamen ids gewinnt die HOEHERE scoringVersion, bei
  // Gleichstand weiter die DB. Bis zum 13.08.2026 gewann die DB
  // bedingungslos, ohne jede Pruefung, ob ihre Kopie ueberhaupt neuer ist -
  // ein frisch korrigierter lokaler Stand konnte damit beim naechsten Sync
  // von einer aelteren Cloud-Fassung ueberschrieben werden, und die
  // Korrektur war wieder weg.
  const dbAnalyses: Stored[] = remote.map((r) => r as unknown as Stored);
  const lokalById = new Map<string, Stored>(localAll.map((a) => [a.id, a]));
  const mergedById = new Map<string, Stored>();
  for (const db of dbAnalyses) {
    const lokal = lokalById.get(db.id);
    // `archived` haengt am Objekt und ist Nutzerzustand, keine Messung -
    // beim Austausch mitnehmen, sonst taucht Archiviertes wieder auf.
    mergedById.set(db.id, lokal && loestAb(db, lokal) ? mitNutzerstand(lokal, db) : db);
  }
  for (const a of localOnly) mergedById.set(a.id, a);

  const merged = Array.from(mergedById.values()).sort((a, b) => {
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });
  const archivedIds = merged.filter((a) => a.archived || localArchived.has(a.id)).map((a) => a.id);

  writeStore({ ...store, analyses: merged, archivedIds });
  localStorage.setItem(SYNC_KEY, userId);
}

export function clearSyncMarker() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SYNC_KEY);
}
