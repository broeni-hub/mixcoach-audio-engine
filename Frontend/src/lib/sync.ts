// One-shot sync of localStorage analyses with the Cloud DB after sign-in.
// Strategy: pull all DB rows, push any local-only rows up, then replace
// the local cache with the union. DB is the source of truth.
import type { AnalysisResult } from "./analysis";
import { listAnalysesFn, upsertAnalysisFn } from "./analyses.functions";
import { loestAb, mitNutzerstand } from "./scoring-version";

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

export async function persistAnalysis(a: AnalysisResult, archived = false) {
  try {
    await upsertAnalysisFn({ data: toUpsertPayload(a, archived) });
  } catch (e) {
    // Non-fatal fuer diesen Aufruf - der lokale Cache hat die Analyse noch.
    // Aber es ist NICHT folgenlos: schlaegt das dauerhaft fehl, existiert die
    // Historie nur in diesem Browser, und "die Historie ueberlebt einen
    // Geraetewechsel" ist Bedingung 2 der Live-Schwelle.
    //
    // Die zwei Ursachen, die es am 11.08.2026 tatsaechlich waren, stehen hier
    // beim Namen - eine allgemeine Warnung haette monatelang niemand gedeutet:
    //   - SUPABASE_SERVICE_ROLE_KEY fehlt in Frontend/.env -> der Server-Client
    //     wirft, jede Server-Funktion scheitert
    //   - DEV_BYPASS_AUTH in routes/app.tsx -> niemand ist angemeldet, und
    //     analyses.user_id ist NOT NULL
    console.warn(
      "[mixcoach] Analyse NICHT in die Cloud gespeichert - sie existiert nur " +
      "in diesem Browser. Haeufigste Ursachen: SUPABASE_SERVICE_ROLE_KEY fehlt " +
      "in Frontend/.env, oder niemand ist angemeldet (DEV_BYPASS_AUTH in " +
      "routes/app.tsx). Fehler:", e,
    );
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
