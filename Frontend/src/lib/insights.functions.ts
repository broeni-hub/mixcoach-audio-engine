// Aggregates analysis_events into "recurring weakness" patterns per user.
// A pattern = same rule_id appearing across multiple analyses. The query
// returns frequency, severity, last seen, trend (recent vs older), plus
// the linked exercise so the UI can recommend a concrete next drill.
import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export type Severity = "info" | "warning" | "critical";

export interface RecurringPattern {
  ruleId: string;
  ruleSlug: string;
  ruleTitle: string;
  diagnosis: string;
  fix: string;
  severity: Severity;
  count: number;            // total occurrences across analyses
  analysisCount: number;    // distinct analyses it appears in
  lastSeen: string;         // ISO
  firstSeen: string;
  recent: number;           // count in last 7 days
  older: number;            // count before last 7 days
  trend: "rising" | "steady" | "fading";
  exercise: {
    id: string;
    slug: string;
    title: string;
    description: string;
    difficulty: number;
  } | null;
}

interface EventRow {
  rule_id: string | null;
  severity: Severity;
  created_at: string;
}

interface RuleRow {
  id: string;
  slug: string;
  title: string;
  diagnosis: string;
  fix: string;
  severity: Severity;
  exercise_id: string | null;
}

interface ExerciseRow {
  id: string;
  slug: string;
  title: string;
  description: string;
  difficulty: number;
}

export const getRecurringWeaknessesFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    // Pull all events for this user, then aggregate in JS — simpler than a
    // multi-join SQL view and fine until users have thousands of analyses.
    const { data: rawEvents, error: evErr } = await context.supabase
      .from("analysis_events")
      .select("rule_id, severity, created_at, analysis_id")
      .eq("user_id", context.userId)
      .not("rule_id", "is", null)
      .in("severity", ["warning", "critical"])
      .order("created_at", { ascending: false })
      .limit(2000);
    if (evErr) throw evErr;
    const events = (rawEvents ?? []) as Array<EventRow & { analysis_id: string }>;
    if (events.length === 0) return { patterns: [] as RecurringPattern[], totalEvents: 0 };

    const ruleIds = Array.from(new Set(events.map((e) => e.rule_id!).filter(Boolean)));
    const [{ data: rules }, { data: exercises }] = await Promise.all([
      context.supabase
        .from("coaching_rules")
        .select("id, slug, title, diagnosis, fix, severity, exercise_id")
        .in("id", ruleIds),
      context.supabase
        .from("exercises")
        .select("id, slug, title, description, difficulty"),
    ]);
    const ruleMap = new Map<string, RuleRow>((rules ?? []).map((r) => [r.id, r as RuleRow]));
    const exMap = new Map<string, ExerciseRow>((exercises ?? []).map((e) => [e.id, e as ExerciseRow]));

    const sevenDaysAgo = Date.now() - 7 * 86400 * 1000;
    const grouped = new Map<string, {
      events: Array<EventRow & { analysis_id: string }>;
      analyses: Set<string>;
    }>();
    for (const e of events) {
      if (!e.rule_id) continue;
      let bucket = grouped.get(e.rule_id);
      if (!bucket) {
        bucket = { events: [], analyses: new Set() };
        grouped.set(e.rule_id, bucket);
      }
      bucket.events.push(e);
      bucket.analyses.add(e.analysis_id);
    }

    const patterns: RecurringPattern[] = [];
    for (const [ruleId, bucket] of grouped) {
      // "Recurring" = appears in 2+ distinct analyses.
      if (bucket.analyses.size < 2) continue;
      const rule = ruleMap.get(ruleId);
      if (!rule) continue;
      const sorted = bucket.events
        .map((e) => new Date(e.created_at).getTime())
        .sort((a, b) => a - b);
      const recent = bucket.events.filter((e) => new Date(e.created_at).getTime() >= sevenDaysAgo).length;
      const older = bucket.events.length - recent;
      const trend: RecurringPattern["trend"] =
        recent > older ? "rising" : recent === 0 ? "fading" : "steady";
      const exercise = rule.exercise_id ? exMap.get(rule.exercise_id) ?? null : null;
      patterns.push({
        ruleId,
        ruleSlug: rule.slug,
        ruleTitle: rule.title,
        diagnosis: rule.diagnosis,
        fix: rule.fix,
        severity: rule.severity,
        count: bucket.events.length,
        analysisCount: bucket.analyses.size,
        firstSeen: new Date(sorted[0]).toISOString(),
        lastSeen: new Date(sorted[sorted.length - 1]).toISOString(),
        recent,
        older,
        trend,
        exercise: exercise
          ? {
              id: exercise.id,
              slug: exercise.slug,
              title: exercise.title,
              description: exercise.description,
              difficulty: exercise.difficulty,
            }
          : null,
      });
    }

    // Sort: critical first, then by count, then by recency.
    const sevRank: Record<Severity, number> = { critical: 0, warning: 1, info: 2 };
    patterns.sort((a, b) => {
      if (sevRank[a.severity] !== sevRank[b.severity]) return sevRank[a.severity] - sevRank[b.severity];
      if (b.count !== a.count) return b.count - a.count;
      return new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime();
    });

    return { patterns, totalEvents: events.length };
  });

export interface PatternEventDetail {
  id: string;
  atSeconds: number;
  severity: Severity;
  value: number | null;
  message: string | null;
  createdAt: string;
}
export interface PatternAnalysisDetail {
  analysisId: string;
  filename: string;
  analysisCreatedAt: string;
  bpm: number | null;
  keyName: string | null;
  firstSeen: string;
  lastSeen: string;
  occurrences: number;
  events: PatternEventDetail[];
}
export interface PatternDetail {
  ruleId: string;
  ruleTitle: string;
  diagnosis: string;
  fix: string;
  severity: Severity;
  totalOccurrences: number;
  analyses: PatternAnalysisDetail[];
}

export const getPatternDetailFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: { ruleId: string }) => d)
  .handler(async ({ data, context }): Promise<PatternDetail | null> => {
    const { data: rule, error: rErr } = await context.supabase
      .from("coaching_rules")
      .select("id, title, diagnosis, fix, severity")
      .eq("id", data.ruleId)
      .maybeSingle();
    if (rErr) throw rErr;
    if (!rule) return null;

    const { data: evs, error: eErr } = await context.supabase
      .from("analysis_events")
      .select("id, analysis_id, at_seconds, severity, value, message, created_at")
      .eq("user_id", context.userId)
      .eq("rule_id", data.ruleId)
      .order("created_at", { ascending: false })
      .limit(500);
    if (eErr) throw eErr;
    const events = evs ?? [];
    if (events.length === 0) {
      return {
        ruleId: rule.id,
        ruleTitle: rule.title,
        diagnosis: rule.diagnosis,
        fix: rule.fix,
        severity: rule.severity as Severity,
        totalOccurrences: 0,
        analyses: [],
      };
    }

    const analysisIds = Array.from(new Set(events.map((e) => e.analysis_id)));
    const { data: analyses } = await context.supabase
      .from("analyses")
      .select("id, filename, created_at, bpm, key_name")
      .in("id", analysisIds);
    const aMap = new Map((analyses ?? []).map((a) => [a.id, a]));

    const grouped = new Map<string, PatternEventDetail[]>();
    for (const e of events) {
      const list = grouped.get(e.analysis_id) ?? [];
      list.push({
        id: e.id,
        atSeconds: Number(e.at_seconds ?? 0),
        severity: e.severity as Severity,
        value: e.value === null ? null : Number(e.value),
        message: e.message,
        createdAt: e.created_at,
      });
      grouped.set(e.analysis_id, list);
    }

    const analysisDetails: PatternAnalysisDetail[] = [];
    for (const [aid, evList] of grouped) {
      const a = aMap.get(aid);
      const sorted = [...evList].sort(
        (x, y) => new Date(x.createdAt).getTime() - new Date(y.createdAt).getTime(),
      );
      analysisDetails.push({
        analysisId: aid,
        filename: a?.filename ?? "Unknown mix",
        analysisCreatedAt: a?.created_at ?? sorted[0].createdAt,
        bpm: a?.bpm === null || a?.bpm === undefined ? null : Number(a.bpm),
        keyName: a?.key_name ?? null,
        firstSeen: sorted[0].createdAt,
        lastSeen: sorted[sorted.length - 1].createdAt,
        occurrences: evList.length,
        events: sorted,
      });
    }
    analysisDetails.sort(
      (a, b) => new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime(),
    );

    return {
      ruleId: rule.id,
      ruleTitle: rule.title,
      diagnosis: rule.diagnosis,
      fix: rule.fix,
      severity: rule.severity as Severity,
      totalOccurrences: events.length,
      analyses: analysisDetails,
    };
  });
