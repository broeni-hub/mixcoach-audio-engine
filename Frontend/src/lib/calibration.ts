// Retrain-Automatik-Status: wie nah ist der DJ am naechsten automatischen
// Modell-Training? Jedes Feedback bringt ihn naeher - macht die
// (unglamouroese, aber entscheidende) Label-Arbeit sichtbar und lohnend.

import { getEngineBaseUrl } from "./api/remoteProvider";

export interface CalibrationStatus {
  newSets: number;
  threshold: number;
  totalLabeled: number;
  ready: boolean;
  lastRetrainAt: string | null;
  activeModel: { recall: number | null; precision: number | null; f1: number | null };
  modelExists: boolean;
}

export async function fetchCalibrationStatus(): Promise<CalibrationStatus | null> {
  const base = getEngineBaseUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/calibration/status`, { signal: AbortSignal.timeout(6000) });
    if (!res.ok) return null;
    return (await res.json()) as CalibrationStatus;
  } catch {
    return null;
  }
}
