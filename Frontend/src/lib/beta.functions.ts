// Server fns for private-beta UX: feedback, waitlist, invite codes,
// post-analysis usefulness ratings.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { createClient } from "@supabase/supabase-js";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import type { Database } from "@/integrations/supabase/types";

export const submitBetaFeedbackFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) =>
    z.object({
      kind: z.enum(["feedback", "bug", "feature"]),
      subject: z.string().max(200).optional(),
      message: z.string().min(1).max(4000),
      url: z.string().max(500).optional(),
      user_agent: z.string().max(500).optional(),
    }).parse(data),
  )
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase.from("beta_feedback").insert({
      user_id: context.userId,
      kind: data.kind,
      subject: data.subject ?? null,
      message: data.message,
      url: data.url ?? null,
      user_agent: data.user_agent ?? null,
    });
    if (error) throw error;
    return { ok: true };
  });

export const submitAnalysisFeedbackFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) =>
    z.object({
      analysis_id: z.string().min(1).max(120),
      usefulness: z.enum(["very", "somewhat", "not"]),
      comment: z.string().max(2000).optional(),
    }).parse(data),
  )
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("analysis_feedback")
      .upsert(
        {
          user_id: context.userId,
          analysis_id: data.analysis_id,
          usefulness: data.usefulness,
          comment: data.comment ?? null,
        },
        { onConflict: "user_id,analysis_id" },
      );
    if (error) throw error;
    return { ok: true };
  });

export const getAnalysisFeedbackFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ analysis_id: z.string() }).parse(data))
  .handler(async ({ data, context }) => {
    const { data: row } = await context.supabase
      .from("analysis_feedback")
      .select("usefulness, comment")
      .eq("user_id", context.userId)
      .eq("analysis_id", data.analysis_id)
      .maybeSingle();
    return row ?? null;
  });

// Public — anyone can join the waitlist or verify an invite code.
function pubClient() {
  return createClient<Database>(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_PUBLISHABLE_KEY!,
    { auth: { storage: undefined, persistSession: false, autoRefreshToken: false } },
  );
}

export const joinWaitlistFn = createServerFn({ method: "POST" })
  .inputValidator((data) =>
    z.object({
      email: z.string().email().max(320),
      name: z.string().max(120).optional(),
      source: z.string().max(80).optional(),
    }).parse(data),
  )
  .handler(async ({ data }) => {
    const supabase = pubClient();
    const { error } = await supabase.from("waitlist").insert({
      email: data.email,
      name: data.name ?? null,
      source: data.source ?? null,
    });
    if (error && !/duplicate|unique/i.test(error.message)) throw error;
    return { ok: true };
  });

export const verifyInviteCodeFn = createServerFn({ method: "POST" })
  .inputValidator((data) => z.object({ code: z.string().min(3).max(64) }).parse(data))
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: row } = await supabaseAdmin
      .from("invite_codes")
      .select("code, max_uses, used_count")
      .eq("code", data.code.trim().toUpperCase())
      .maybeSingle();
    const valid = !!row && row.used_count < row.max_uses;
    return { valid };
  });
