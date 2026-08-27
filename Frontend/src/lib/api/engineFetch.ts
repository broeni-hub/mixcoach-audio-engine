/** Ein Ort für jeden Aufruf an die Audio-Engine (F2, zweiter Teil).
 *
 *  WARUM ES DIESE DATEI GIBT
 *  -------------------------
 *  Seit dem 27.08.2026 kann die Engine Zugangskontrolle verlangen
 *  (`MIXCOACH_AUTH=an`, siehe `app/auth.py`). Dann braucht JEDER Aufruf einen
 *  `Authorization: Bearer <supabase access token>`. Vorher lagen die Aufrufe
 *  als blanke `fetch()` in acht Dateien verstreut — bei acht Stellen ist es
 *  eine Frage der Zeit, bis eine vergessen wird, und dann bekommt der Nutzer
 *  ein 401 an genau einer Stelle der App.
 *
 *  Dieselbe Überlegung wie auf der Engine-Seite: dort hängt die Prüfung an
 *  der ganzen App statt an einzelnen Endpoints, damit ein neuer Endpoint von
 *  selbst geschützt ist. Hier hängt der Token an einer Funktion, damit ein
 *  neuer Aufruf ihn von selbst mitbringt.
 *
 *  WAS PASSIERT, WENN KEINE SITZUNG DA IST
 *  ---------------------------------------
 *  Dann wird ohne Header aufgerufen. Das ist Absicht und kein Versehen: bei
 *  `MIXCOACH_AUTH=aus` — der Vorgabe für den lokalen Betrieb — läuft alles
 *  wie bisher. Ein Fehler entsteht erst, wenn die Engine den Token verlangt
 *  und keiner da ist, und dann ist 401 die richtige Antwort.
 *
 *  SERVERSEITIG GIBT ES KEINEN TOKEN
 *  ---------------------------------
 *  `supabase.auth.getSession()` liest die Sitzung aus dem Browser. In einer
 *  Server-Funktion (TanStack `createServerFn`) gibt es sie nicht; solche
 *  Aufrufe laufen ohne Header und bekämen bei `MIXCOACH_AUTH=an` ein 401.
 *
 *  Nachgesehen am 27.08.2026: **es gibt heute keinen solchen Aufruf.** Alle
 *  dreizehn Engine-Aufrufe laufen im Browser — auch `server-analyses.ts`,
 *  dessen Name das Gegenteil nahelegt (gemeint sind serverseitig
 *  GESPEICHERTE Reports, nicht ein serverseitiger Aufruf; es steckt kein
 *  `createServerFn` darin). Der Vorbehalt steht hier trotzdem, weil der
 *  erste Aufruf aus einer Server-Funktion genau hier auflaufen wird.
 */
import { supabase } from "@/integrations/supabase/client";

/** Das Zugangs-Token der laufenden Sitzung, oder null. */
export async function engineToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    // Kein Token zu bekommen ist kein Grund, den Aufruf zu verhindern -
    // bei MIXCOACH_AUTH=aus braucht ihn niemand.
    return null;
  }
}

/** Wie `fetch`, hängt aber das Supabase-Token an, wenn es eines gibt. */
export async function engineFetch(input: string, init?: RequestInit): Promise<Response> {
  const token = await engineToken();
  if (!token) return fetch(input, init);

  const headers = new Headers(init?.headers);
  // Ein ausdrücklich mitgegebener Header gewinnt - sonst könnte diese
  // Funktion einen bewusst gesetzten Wert stillschweigend überschreiben.
  if (!headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(input, { ...init, headers });
}
