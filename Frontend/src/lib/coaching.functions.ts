// Server functions for the shared coaching knowledge base + per-analysis events.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export const loadCoachingKbFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const [rules, exercises] = await Promise.all([
      context.supabase
        .from("coaching_rules")
        .select("id, slug, title, condition, diagnosis, fix, severity, exercise_id")
        .eq("enabled", true),
      context.supabase
        .from("exercises")
        .select("id, slug, title, description, target_metric, target_delta, difficulty"),
    ]);
    if (rules.error) throw rules.error;
    if (exercises.error) throw exercises.error;
    return {
      rules: rules.data ?? [],
      exercises: exercises.data ?? [],
    };
  });

const eventSchema = z.object({
  analysis_id: z.string().uuid(),
  events: z.array(
    z.object({
      at_seconds: z.number(),
      event_type: z.string(),
      severity: z.enum(["info", "warning", "critical"]).default("info"),
      value: z.number().nullable().optional(),
      message: z.string().nullable().optional(),
      rule_id: z.string().uuid().nullable().optional(),
    }),
  ),
});

export const saveAnalysisEventsFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => eventSchema.parse(data))
  .handler(async ({ data, context }) => {
    if (data.events.length === 0) return { ok: true, inserted: 0 };
    // Replace prior events for idempotency on re-analysis.
    await context.supabase
      .from("analysis_events")
      .delete()
      .eq("analysis_id", data.analysis_id)
      .eq("user_id", context.userId);
    const rows = data.events.map((e) => ({
      ...e,
      analysis_id: data.analysis_id,
      user_id: context.userId,
    }));
    const { error } = await context.supabase
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .from("analysis_events").insert(rows as any);
    if (error) throw error;
    return { ok: true, inserted: rows.length };
  });
