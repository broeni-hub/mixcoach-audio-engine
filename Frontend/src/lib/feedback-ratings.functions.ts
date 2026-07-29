// 👍/👎 ratings per analysis, against either a rule-engine finding (target_kind="rule")
// or a single LLM coach item (target_kind="coach_item"). One rating per
// (user, analysis, target_kind, target_ref) thanks to the table's unique key.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

const Target = z.object({
  analysis_id: z.string().uuid(),
  target_kind: z.enum(["rule", "coach_item"]),
  target_ref: z.string().min(1).max(120),
});

export const rateFeedbackFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) =>
    Target.extend({
      rating: z.union([z.literal(1), z.literal(-1)]),
      comment: z.string().max(500).optional(),
    }).parse(data),
  )
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("feedback_ratings")
      .upsert(
        {
          user_id: context.userId,
          analysis_id: data.analysis_id,
          target_kind: data.target_kind,
          target_ref: data.target_ref,
          rating: data.rating,
          comment: data.comment ?? null,
        },
        { onConflict: "user_id,analysis_id,target_kind,target_ref" },
      );
    if (error) throw error;
    return { ok: true };
  });

export const clearRatingFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => Target.parse(data))
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("feedback_ratings")
      .delete()
      .eq("user_id", context.userId)
      .eq("analysis_id", data.analysis_id)
      .eq("target_kind", data.target_kind)
      .eq("target_ref", data.target_ref);
    if (error) throw error;
    return { ok: true };
  });

export const listRatingsForAnalysisFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ analysis_id: z.string().uuid() }).parse(data))
  .handler(async ({ data, context }) => {
    const { data: rows, error } = await context.supabase
      .from("feedback_ratings")
      .select("target_kind, target_ref, rating, comment, updated_at")
      .eq("user_id", context.userId)
      .eq("analysis_id", data.analysis_id);
    if (error) throw error;
    return rows ?? [];
  });
