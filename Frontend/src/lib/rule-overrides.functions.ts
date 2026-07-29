// Per-user overrides + notes for shared coaching rules.
import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { z } from "zod";

export interface RuleOverride {
  ruleId: string;
  customDiagnosis: string | null;
  customFix: string | null;
  note: string | null;
  updatedAt: string | null;
}

export const getRuleOverrideFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: { ruleId: string }) => z.object({ ruleId: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }): Promise<RuleOverride> => {
    const { data: row, error } = await context.supabase
      .from("user_rule_overrides")
      .select("rule_id, custom_diagnosis, custom_fix, note, updated_at")
      .eq("user_id", context.userId)
      .eq("rule_id", data.ruleId)
      .maybeSingle();
    if (error) throw error;
    if (!row) {
      return { ruleId: data.ruleId, customDiagnosis: null, customFix: null, note: null, updatedAt: null };
    }
    return {
      ruleId: row.rule_id,
      customDiagnosis: row.custom_diagnosis,
      customFix: row.custom_fix,
      note: row.note,
      updatedAt: row.updated_at,
    };
  });

const upsertSchema = z.object({
  ruleId: z.string().uuid(),
  customDiagnosis: z.string().trim().max(2000).nullable(),
  customFix: z.string().trim().max(2000).nullable(),
  note: z.string().trim().max(2000).nullable(),
});

export const upsertRuleOverrideFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: unknown) => upsertSchema.parse(d))
  .handler(async ({ data, context }): Promise<RuleOverride> => {
    const payload = {
      user_id: context.userId,
      rule_id: data.ruleId,
      custom_diagnosis: data.customDiagnosis && data.customDiagnosis.length > 0 ? data.customDiagnosis : null,
      custom_fix: data.customFix && data.customFix.length > 0 ? data.customFix : null,
      note: data.note && data.note.length > 0 ? data.note : null,
    };
    const { data: row, error } = await context.supabase
      .from("user_rule_overrides")
      .upsert(payload, { onConflict: "user_id,rule_id" })
      .select("rule_id, custom_diagnosis, custom_fix, note, updated_at")
      .single();
    if (error) throw error;
    return {
      ruleId: row.rule_id,
      customDiagnosis: row.custom_diagnosis,
      customFix: row.custom_fix,
      note: row.note,
      updatedAt: row.updated_at,
    };
  });

export const deleteRuleOverrideFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: { ruleId: string }) => z.object({ ruleId: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase
      .from("user_rule_overrides")
      .delete()
      .eq("user_id", context.userId)
      .eq("rule_id", data.ruleId);
    if (error) throw error;
    return { ok: true };
  });

export interface RuleOverrideHistoryEntry {
  id: string;
  action: "create" | "update" | "delete";
  changedAt: string;
  changedBy: string;
  changedByEmail: string | null;
  prevDiagnosis: string | null;
  newDiagnosis: string | null;
  prevFix: string | null;
  newFix: string | null;
  prevNote: string | null;
  newNote: string | null;
}

export const getRuleOverrideHistoryFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: { ruleId: string }) => z.object({ ruleId: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }): Promise<RuleOverrideHistoryEntry[]> => {
    const { data: rows, error } = await context.supabase
      .from("user_rule_override_history")
      .select("id, action, changed_at, changed_by, changed_by_email, prev_diagnosis, new_diagnosis, prev_fix, new_fix, prev_note, new_note")
      .eq("user_id", context.userId)
      .eq("rule_id", data.ruleId)
      .order("changed_at", { ascending: false })
      .limit(100);
    if (error) throw error;
    return (rows ?? []).map((r) => ({
      id: r.id,
      action: r.action as "create" | "update" | "delete",
      changedAt: r.changed_at,
      changedBy: r.changed_by,
      changedByEmail: r.changed_by_email,
      prevDiagnosis: r.prev_diagnosis,
      newDiagnosis: r.new_diagnosis,
      prevFix: r.prev_fix,
      newFix: r.new_fix,
      prevNote: r.prev_note,
      newNote: r.new_note,
    }));
  });
