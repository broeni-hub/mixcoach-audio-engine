// Server functions for persisting MixCoach analyses to Lovable Cloud.
// All functions require an authenticated user; RLS scopes rows to auth.uid().
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

export interface DbAnalysisRow {
  id: string;
  archived: boolean;
  fileName?: string;
  createdAt?: string;
  bpm?: number;
  key?: string;
  scores?: { overall?: number; beatmatching?: number; eq?: number; [k: string]: unknown };
  [key: string]: JsonValue | unknown;
}

function rowToPayload(row: { id: string; payload: unknown; archived: boolean }): DbAnalysisRow {
  const p = (row.payload ?? {}) as Record<string, JsonValue>;
  return { ...(p as Record<string, JsonValue>), id: row.id, archived: row.archived };
}

export const listAnalysesFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { data, error } = await context.supabase
      .from("analyses")
      .select("id, payload, archived, created_at")
      .eq("user_id", context.userId)
      .order("created_at", { ascending: false });
    if (error) throw error;
    const rows = (data ?? []).map(rowToPayload);
    return rows as unknown as Array<Record<string, JsonValue>>;
  });

const upsertSchema = z.object({
  id: z.string().uuid(),
  filename: z.string(),
  bpm: z.number().nullable().optional(),
  bpm_confidence: z.number().nullable().optional(),
  key_name: z.string().nullable().optional(),
  key_confidence: z.number().nullable().optional(),
  bass_pct: z.number().nullable().optional(),
  mid_pct: z.number().nullable().optional(),
  high_pct: z.number().nullable().optional(),
  bass_stability: z.number().nullable().optional(),
  dynamic_range_db: z.number().nullable().optional(),
  loudness_dbfs: z.number().nullable().optional(),
  peak_count: z.number().nullable().optional(),
  duration_seconds: z.number().nullable().optional(),
  scores: z.any().default({}),
  curves: z.any().default({}),
  coach_summary: z.string().nullable().optional(),
  track_b_filename: z.string().nullable().optional(),
  track_b_bpm: z.number().nullable().optional(),
  track_b_key: z.string().nullable().optional(),
  cue_point_sec: z.number().nullable().optional(),
  transition_metrics: z.any().optional(),
  payload: z.any(),
  archived: z.boolean().default(false),
});

export const upsertAnalysisFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => upsertSchema.parse(data))
  .handler(async ({ data, context }) => {
    // Cast JSON-shaped fields once; Supabase's generated Json type is recursive
    // and doesn't accept Record<string, unknown> directly.
    const row = { ...data, user_id: context.userId } as unknown as Record<string, unknown>;
    const { error } = await context.supabase
      .from("analyses")
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .upsert(row as any, { onConflict: "id" });
    if (error) throw error;
    return { ok: true };
  });

export const setArchivedFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ id: z.string().uuid(), archived: z.boolean() }).parse(data))
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("analyses")
      .update({ archived: data.archived })
      .eq("id", data.id)
      .eq("user_id", context.userId);
    if (error) throw error;
    return { ok: true };
  });

export const deleteAnalysisFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ id: z.string().uuid() }).parse(data))
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("analyses")
      .delete()
      .eq("id", data.id)
      .eq("user_id", context.userId);
    if (error) throw error;
    return { ok: true };
  });

export const deleteAllAnalysesFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { error } = await context.supabase
      .from("analyses")
      .delete()
      .eq("user_id", context.userId);
    if (error) throw error;
    return { ok: true };
  });

export const deleteArchivedAnalysesFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { error } = await context.supabase
      .from("analyses")
      .delete()
      .eq("user_id", context.userId)
      .eq("archived", true);
    if (error) throw error;
    return { ok: true };
  });
