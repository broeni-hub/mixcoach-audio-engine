// Track-Library: rekordbox-Import fuer die Fingerprint-Erkennung.
// Der DJ exportiert seine Sammlung als XML; das Backend liest die
// Audio-Dateien direkt von der Platte und legt Fingerprints ab.

import { getEngineBaseUrl } from "./api/remoteProvider";

export interface LibraryStatus {
  running: boolean;
  total: number;
  done: number;
  failed: number;
  skipped: number;
  current: string | null;
  last_error: string | null;
}

export interface LibraryTrack {
  id: string;
  title: string;
  artist: string;
  bpm: number | null;
  key: string | null;
  duration: number | null;
  path: string;
}

function base(): string | null {
  return getEngineBaseUrl();
}

export async function getLibraryStatus(): Promise<LibraryStatus | null> {
  const url = base();
  if (!url) return null;
  try {
    const res = await fetch(`${url}/library/status`);
    if (!res.ok) return null;
    return (await res.json()) as LibraryStatus;
  } catch {
    return null;
  }
}

export async function getLibraryTracks(): Promise<{ count: number; tracks: LibraryTrack[] } | null> {
  const url = base();
  if (!url) return null;
  try {
    const res = await fetch(`${url}/library/tracks`);
    if (!res.ok) return null;
    return (await res.json()) as { count: number; tracks: LibraryTrack[] };
  } catch {
    return null;
  }
}

export async function uploadRekordboxXml(file: File): Promise<{ found: number }> {
  const url = base();
  if (!url) throw new Error("Audio-Engine nicht erreichbar.");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${url}/library/rekordbox`, { method: "POST", body: form });
  if (!res.ok) {
    let detail = "Import fehlgeschlagen.";
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* leer */ }
    throw new Error(detail);
  }
  return (await res.json()) as { found: number };
}
