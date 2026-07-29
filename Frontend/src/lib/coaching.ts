// Client-side coaching engine: loads the DB rule/exercise library once,
// caches it in memory + localStorage, evaluates rules against measurements,
// and produces ranked findings the report and timeline can render.
import type { Measurements } from "./audio-analysis";
import { loadCoachingKbFn, saveAnalysisEventsFn } from "./coaching.functions";

export type Severity = "info" | "warning" | "critical";

export interface Exercise {
  id: string;
  slug: string;
  title: string;
  description: string;
  target_metric: string | null;
  target_delta: number | null;
  difficulty: number;
}

export interface CoachingRule {
  id: string;
  slug: string;
  title: string;
  condition: { all?: Array<{ metric: string; op: string; value: number }> };
  diagnosis: string;
  fix: string;
  severity: Severity;
  exercise_id: string | null;
}

export interface Kb {
  rules: CoachingRule[];
  exercises: Exercise[];
  loadedAt: number;
}

export interface Finding {
  rule: CoachingRule;
  exercise: Exercise | null;
  value: number | null;
  metric: string | null;
}

const CACHE_KEY = "mixcoach.kb.v1";
const TTL_MS = 1000 * 60 * 60 * 6; // 6h

let memory: Kb | null = null;
let inflight: Promise<Kb> | null = null;

function readCache(): Kb | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const kb = JSON.parse(raw) as Kb;
    if (Date.now() - kb.loadedAt > TTL_MS) return null;
    return kb;
  } catch { return null; }
}

function writeCache(kb: Kb) {
  if (typeof window === "undefined") return;
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(kb)); } catch { /* quota */ }
}

export function getCachedKb(): Kb | null {
  if (memory) return memory;
  memory = readCache();
  return memory;
}

export async function loadKb(force = false): Promise<Kb> {
  if (!force) {
    const cached = getCachedKb();
    if (cached) return cached;
  }
  if (inflight) return inflight;
  inflight = (async () => {
    const data = await loadCoachingKbFn();
    const kb: Kb = {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rules: ((data as any).rules ?? []) as CoachingRule[],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      exercises: ((data as any).exercises ?? []) as Exercise[],
      loadedAt: Date.now(),
    };
    memory = kb;
    writeCache(kb);
    inflight = null;
    return kb;
  })();
  return inflight;
}

// Map the measurement keys our rule conditions use → numeric values.
export function metricsFromMeasurements(m: Measurements): Record<string, number> {
  return {
    bpm: m.bpm,
    bpmConfidence: m.bpmConfidence,
    keyConfidence: m.keyConfidence,
    bassStability: m.bassStability,
    dynamicRangeDb: m.dynamicRangeDb,
    loudnessDbfs: m.loudnessDbfs,
    bassPct: m.bands.bass,
    midPct: m.bands.mid,
    highPct: m.bands.high,
    peakCount: m.peakCount,
    durationSec: m.durationSec,
  };
}

function cmp(a: number, op: string, b: number): boolean {
  switch (op) {
    case "<":  return a < b;
    case "<=": return a <= b;
    case ">":  return a > b;
    case ">=": return a >= b;
    case "==": case "=": return a === b;
    case "!=": return a !== b;
    default: return false;
  }
}

export function evaluateRules(kb: Kb, metrics: Record<string, number>): Finding[] {
  const sevRank: Record<Severity, number> = { critical: 0, warning: 1, info: 2 };
  const out: Finding[] = [];
  for (const rule of kb.rules) {
    const clauses = rule.condition?.all ?? [];
    if (clauses.length === 0) continue;
    const ok = clauses.every((c) => {
      const v = metrics[c.metric];
      return typeof v === "number" && cmp(v, c.op, c.value);
    });
    if (!ok) continue;
    const primary = clauses[0];
    const exercise = rule.exercise_id
      ? kb.exercises.find((e) => e.id === rule.exercise_id) ?? null
      : null;
    out.push({
      rule,
      exercise,
      metric: primary?.metric ?? null,
      value: primary ? metrics[primary.metric] ?? null : null,
    });
  }
  out.sort((a, b) => sevRank[a.rule.severity] - sevRank[b.rule.severity]);
  return out;
}

export async function persistFindings(analysisId: string, findings: Finding[]) {
  const events = findings.map((f) => ({
    at_seconds: 0,
    event_type: f.rule.slug,
    severity: f.rule.severity,
    value: f.value,
    message: f.rule.diagnosis,
    rule_id: f.rule.id,
  }));
  try {
    await saveAnalysisEventsFn({ data: { analysis_id: analysisId, events } });
  } catch (err) {
    // Don't fail the whole job if event persistence fails.
    console.warn("[coaching] saveAnalysisEvents failed", err);
  }
}
