// Cross-device cache: maps an audio file hash to a previously computed
// analysis row. Lookup + write are scoped to auth.uid() via RLS.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

export const lookupHashFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ hash: z.string().min(8) }).parse(d))
  .handler(async ({ data, context }) => {
    const { data: cache, error } = await context.supabase
      .from("analysis_hash_cache")
      .select("analysis_id")
      .eq("user_id", context.userId)
      .eq("hash", data.hash)
      .maybeSingle();
    if (error) throw error;
    if (!cache) return { hit: false as const };
    // Verify the analysis still exists and load its payload.
    const { data: row, error: rowErr } = await context.supabase
      .from("analyses")
      .select("id, payload, archived")
      .eq("id", cache.analysis_id)
      .eq("user_id", context.userId)
      .maybeSingle();
    if (rowErr) throw rowErr;
    if (!row) return { hit: false as const };
    const payload = (row.payload ?? {}) as Record<string, JsonValue>;
    return {
      hit: true as const,
      analysis: { ...payload, id: row.id, archived: row.archived } as Record<string, JsonValue>,
    };
  });

export const saveHashFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) =>
    z.object({ hash: z.string().min(8), analysis_id: z.string().uuid() }).parse(d),
  )
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("analysis_hash_cache")
      .upsert(
        { user_id: context.userId, hash: data.hash, analysis_id: data.analysis_id },
        { onConflict: "user_id,hash" },
      );
    if (error) throw error;
    return { ok: true };
  });
