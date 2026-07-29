// Serverseitig gespeicherte Engine-Reports (GET /analysis) - zum
// Wiederfinden von Analysen, die im Browser-Store fehlen. Real passiert
// (MixCoach2.WAV, 2026-07-17): die Engine analysierte 10 Uebergaenge,
// die App zeigte aber einen Browser-Fallback-Report mit fast keinen -
// der gute Report war aus der App heraus unerreichbar.

import { getEngineBaseUrl } from "./api/remoteProvider";

export interface ServerAnalysisEntry {
  id: string;
  fileName: string | null;
  createdAt: string | null;
  transitions: number;
  libraryMatches: number;
}

export async function fetchServerAnalyses(): Promise<ServerAnalysisEntry[] | null> {
  const base = getEngineBaseUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/analysis`, { signal: AbortSignal.timeout(6000) });
    if (!res.ok) return null;
    const data = (await res.json()) as { analyses?: ServerAnalysisEntry[] };
    return data.analyses ?? [];
  } catch {
    return null;
  }
}
