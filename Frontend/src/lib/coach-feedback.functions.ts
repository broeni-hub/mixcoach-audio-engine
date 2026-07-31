// LLM-powered coaching. Takes the real audio measurements + rule-engine
// findings + (optional) transition metrics, asks Gemini via Lovable AI
// Gateway for 3 prioritised, concrete improvements. Output is grounded in
// the measurements we already computed — the model is told NOT to invent
// numbers or events that aren't in the input.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { generateText } from "ai";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { createLovableAiGatewayProvider } from "./ai-gateway.server";

const COACH_MODEL = "google/gemini-3-flash-preview";

const FindingZ = z.object({
  rule_slug: z.string(),
  title: z.string(),
  diagnosis: z.string(),
  fix: z.string(),
  severity: z.enum(["info", "warning", "critical"]),
  metric: z.string().nullable().optional(),
  value: z.number().nullable().optional(),
});

const MeasurementsZ = z.object({
  bpm: z.number(),
  bpm_confidence: z.number(),
  key: z.string(),
  key_confidence: z.number(),
  bass_pct: z.number(),
  mid_pct: z.number(),
  high_pct: z.number(),
  bass_stability: z.number(),
  dynamic_range_db: z.number(),
  loudness_dbfs: z.number(),
  peak_count: z.number(),
  duration_sec: z.number(),
});

const TransitionZ = z
  .object({
    cue_point_sec: z.number(),
    overlap_sec: z.number(),
    bpm_a: z.number(),
    bpm_b: z.number(),
    bpm_drift: z.number(),
    key_a: z.string(),
    key_b: z.string(),
    camelot_distance: z.number(),
    harmonic_label: z.string(),
    bass_clash_score: z.number(),
    phrase_alignment_score: z.number(),
  })
  .optional();

const InputZ = z.object({
  analysis_id: z.string().uuid(),
  filename: z.string(),
  track_b_filename: z.string().nullable().optional(),
  level: z.string().default("intermediate"),
  measurements: MeasurementsZ,
  findings: z.array(FindingZ).default([]),
  transition: TransitionZ,
});

const OutputZ = z.object({
  summary: z.string(),
  items: z.array(
    z.object({
      priority: z.number(),
      title: z.string(),
      what: z.string(),
      why: z.string(),
      how: z.string(),
      related_rule_slug: z.string().nullable().optional(),
    }),
  ),
});

function detectTruncation(response: string) {
  const text = response.trim();
  const openBraces = (text.match(/\{/g) || []).length;
  const closeBraces = (text.match(/\}/g) || []).length;
  const openBrackets = (text.match(/\[/g) || []).length;
  const closeBrackets = (text.match(/\]/g) || []).length;

  return (
    openBraces !== closeBraces ||
    openBrackets !== closeBrackets ||
    /(?:\.\.\.|…|\[truncated\]|\[continued\])$/i.test(text)
  );
}

function extractJsonFromResponse(response: string): unknown {
  const withoutFences = response
    .replace(/```json\s*/gi, "")
    .replace(/```\s*/g, "")
    .trim();
  const objectStart = withoutFences.indexOf("{");
  const objectEnd = withoutFences.lastIndexOf("}");

  if (objectStart === -1 || objectEnd === -1 || objectEnd <= objectStart) {
    throw new Error("No JSON object found in coach response");
  }

  const jsonText = withoutFences.slice(objectStart, objectEnd + 1);
  try {
    return JSON.parse(jsonText);
  } catch {
    return JSON.parse(
      jsonText
        .replace(/,\s*}/g, "}")
        .replace(/,\s*]/g, "]")
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, ""),
    );
  }
}

function normalizeCoachOutput(output: z.infer<typeof OutputZ>) {
  return {
    summary: output.summary,
    items: output.items.slice(0, 3).map((item, index) => ({
      priority: Number.isFinite(item.priority) ? item.priority : index + 1,
      title: item.title,
      what: item.what,
      why: item.why,
      how: item.how,
      related_rule_slug: item.related_rule_slug ?? "",
    })),
  };
}

function buildFallbackCoachOutput(data: z.infer<typeof InputZ>): ReturnType<typeof normalizeCoachOutput> {
  const { measurements: m, findings, transition: t } = data;
  const primaryFinding = findings[0];
  // bpm_drift und phrase_alignment_score sind hier am 31.07.2026 entfallen.
  // Sie in einen LLM-Prompt zu geben ist der schaerfste Fall: das Modell
  // formuliert daraus selbstbewusste Ratschlaege, und die Ueberschrift des
  // Prompts lautet ausgerechnet "STRICT GROUNDING RULES (violations =
  // hallucination)". Begruendung: NOT_YET_MEASURED, analysis_mapper.py.
  const transitionFocus = t
    ? `Your transition shows ${t.bass_clash_score}/100 bass clash.`
    : `Your mix measures ${m.bpm} BPM with ${m.bass_stability}/100 bass stability and ${m.dynamic_range_db} dB dynamic range.`;

  return {
    summary: `${transitionFocus} Focus the next practice pass on the highest-impact measurable weakness instead of changing several things at once.`,
    items: [
      {
        priority: 1,
        title: primaryFinding?.title ?? "Tighten the transition foundation",
        what: primaryFinding
          ? `${primaryFinding.diagnosis} The measured value was ${primaryFinding.value ?? "available in the report"} for ${primaryFinding.metric ?? primaryFinding.rule_slug}.`
          : t
            ? `The transition currently has ${t.bass_clash_score}/100 bass clash.`
            : `The track analysis shows ${m.bass_stability}/100 bass stability and ${m.loudness_dbfs} dBFS loudness.`,
        why: t
          ? "Small timing, phrase, or low-end mismatches become most obvious during the overlap, where both tracks compete for space."
          : "A stable foundation makes later transition practice easier because timing and energy changes become more predictable.",
        how: primaryFinding?.fix ?? "Loop the transition window and repeat 8-bar passes, changing only one control move each time until the measured issue improves.",
        related_rule_slug: primaryFinding?.rule_slug ?? "",
      },
    ],
  };
}

function buildPrompt(data: z.infer<typeof InputZ>) {
  const { measurements: m, findings, transition: t } = data;
  const findingLines = findings
    .slice(0, 8)
    .map(
      (f, i) =>
        `${i + 1}. [${f.severity}] ${f.title} (rule:${f.rule_slug}, metric:${f.metric ?? "-"}=${f.value ?? "-"}) — diagnosis: ${f.diagnosis} — fix: ${f.fix}`,
    )
    .join("\n") || "(no rule-engine findings triggered)";

  const transitionBlock = t
    ? `
Transition (Track A → Track B):
- Cue point: ${t.cue_point_sec.toFixed(1)}s, overlap window: ${t.overlap_sec.toFixed(1)}s
- BPM: A=${t.bpm_a} vs B=${t.bpm_b}
- Key: A=${t.key_a} vs B=${t.key_b} (Camelot distance ${t.camelot_distance}, ${t.harmonic_label})
- Bass clash score: ${t.bass_clash_score}/100 (lower is better)
- NOT measured for this transition: tempo drift and phrase alignment. Do not
  comment on beatmatching accuracy or phrase/bar alignment - there is no
  reliable measurement behind them.`
    : "";

  return `You are a senior DJ coach for ${data.level} DJs. Give brutally specific, actionable feedback grounded ONLY in the measurements below.

STRICT GROUNDING RULES (violations = hallucination):
- NEVER invent numbers, BPM values, key names, timestamps, bar counts, or events that are not literally in the data below.
- NEVER claim the user "improved", "got worse", or "changed" anything — you only see ONE snapshot, no history.
- NEVER reference crowd reaction, mood, genre, energy "story", or anything you cannot derive from the numbers.
- If BPM confidence < 50% or key confidence < 40%, explicitly hedge ("the detected key may be wrong").
- If a value isn't in the data, do not mention it. Prefer fewer, accurate sentences over padded ones.
- Use a direct second-person voice.

Track A: "${data.filename}"${data.track_b_filename ? `\nTrack B: "${data.track_b_filename}"` : ""}

Measurements:
- BPM ${m.bpm} (confidence ${(m.bpm_confidence * 100).toFixed(0)}%), Key ${m.key} (confidence ${(m.key_confidence * 100).toFixed(0)}%)
- Frequency mix: bass ${m.bass_pct}% / mid ${m.mid_pct}% / high ${m.high_pct}%
- Bass stability ${m.bass_stability}/100, dynamic range ${m.dynamic_range_db} dB, loudness ${m.loudness_dbfs} dBFS, ${m.peak_count} energy peaks over ${m.duration_sec.toFixed(0)}s
${transitionBlock}

Triggered coaching rules:
${findingLines}

Your job:
1) Write a 2-3 sentence "summary" of the mix quality grounded in the numbers above.
2) Return 1-3 prioritised "items". Priority 1 is the single most impactful fix. Each item MUST cite at least one concrete number from the measurements or transition block. If a triggered rule applies, set "related_rule_slug" to that rule's slug; otherwise null.

Return only valid JSON in this exact shape:
{
  "summary": "2-3 grounded sentences",
  "items": [
    {
      "priority": 1,
      "title": "short fix title",
      "what": "what you noticed, with one measured value",
      "why": "why it matters for the transition",
      "how": "one concrete practice action",
      "related_rule_slug": "matching rule slug, or null"
    }
  ]
}

Do not repeat the rule text verbatim — re-phrase it with the user's specific numbers. Do not output markdown fences, commentary, or any text outside the JSON object.`;
}

// Reduced/stricter prompt used when the first attempt fails Zod validation.
// Drops the optional related_rule_slug field, asks for exactly 1 item, and
// hammers on JSON-only output to maximise the chance of a valid response.
function buildRetryPrompt(data: z.infer<typeof InputZ>, previousError: string) {
  const { measurements: m, findings, transition: t } = data;
  const topFinding = findings[0];
  const transitionLine = t
    ? `Transition: A=${t.bpm_a}, B=${t.bpm_b} BPM, Camelot distance ${t.camelot_distance} (${t.harmonic_label}), bass clash ${t.bass_clash_score}/100. Tempo drift and phrase alignment are NOT measured - do not comment on them.`
    : `Single track: BPM ${m.bpm}, key ${m.key}, bass stability ${m.bass_stability}/100, loudness ${m.loudness_dbfs} dBFS.`;
  const findingLine = topFinding
    ? `Top triggered rule: ${topFinding.title} — ${topFinding.diagnosis} Fix hint: ${topFinding.fix}`
    : "No specific rule triggered.";

  return `You are a DJ coach. Your previous answer was rejected by a strict JSON parser with: "${previousError.slice(0, 200)}".

You MUST now reply with ONLY a minified JSON object. No markdown, no code fences, no prose before or after. Every field is a non-empty string except "priority" which is the number 1.

Schema (all 5 fields required, exactly 1 item):
{"summary":"<2 short sentences grounded in the numbers below>","items":[{"priority":1,"title":"<short fix title>","what":"<what you noticed, cite one measured number>","why":"<why it matters>","how":"<one concrete practice action>"}]}

Context for ${data.level} DJ on "${data.filename}":
${transitionLine}
${findingLine}

Rules:
- Do NOT invent numbers. Use only numbers from the context above.
- Do NOT include any field other than the ones in the schema.
- Do NOT wrap the JSON in quotes, markdown, or commentary.`;
}

export const generateCoachFeedbackFn = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => InputZ.parse(data))
  .handler(async ({ data, context }) => {
    const key = process.env.LOVABLE_API_KEY;
    if (!key) throw new Error("Missing LOVABLE_API_KEY");

    const gateway = createLovableAiGatewayProvider(key);
    let output: ReturnType<typeof normalizeCoachOutput> | undefined;
    const promptMeta = { level: data.level, has_transition: !!data.transition };

    const attempts: Array<{ label: "primary" | "retry-reduced"; build: (prevErr: string) => string; maxOutputTokens: number }> = [
      { label: "primary", build: () => buildPrompt(data), maxOutputTokens: 2048 },
      { label: "retry-reduced", build: (prev) => buildRetryPrompt(data, prev), maxOutputTokens: 1024 },
    ];

    let lastError = "";
    for (const attempt of attempts) {
      const settings = {
        maxOutputTokens: attempt.maxOutputTokens,
        output: "manual-json",
        schema: "OutputZ.v2",
        attempt: attempt.label,
      };
      let rawText = "";
      let rawObject: unknown = undefined;
      let finishReason: string | undefined;
      let zodIssues: unknown = null;

      try {
        const res = await generateText({
          model: gateway(COACH_MODEL),
          prompt: attempt.build(lastError),
          maxOutputTokens: attempt.maxOutputTokens,
        });
        rawText = res.text ?? "";
        finishReason = res.finishReason;
        if (!rawText.trim()) throw new Error("Empty coach response");
        if (finishReason === "length" || detectTruncation(rawText)) {
          throw new Error("Coach response was truncated before valid JSON completed");
        }

        rawObject = extractJsonFromResponse(rawText);
        const parsed = OutputZ.safeParse(rawObject);
        if (!parsed.success) {
          zodIssues = parsed.error.issues;
          throw new Error(
            `Schema validation failed: ${parsed.error.issues
              .map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`)
              .join("; ")}`,
          );
        }
        output = normalizeCoachOutput(parsed.data);
        break; // success
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const errorName = err instanceof Error ? err.name : undefined;
        const errorStack = err instanceof Error ? err.stack : undefined;
        lastError = msg;

        console.error(`[coach-feedback] ${attempt.label} attempt failed`, {
          analysis_id: data.analysis_id,
          error: msg,
          errorName,
          finishReason,
          rawTextLength: rawText.length,
          rawTextPreview: rawText.slice(0, 4000),
          rawObject,
          zodIssues,
        });

        try {
          const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
          const { error: failErr } = await supabaseAdmin
            .from("coach_feedback_failures")
            .insert({
              analysis_id: data.analysis_id,
              user_id: context.userId,
              model: COACH_MODEL,
              settings,
              prompt_meta: { ...promptMeta, attempt: attempt.label },
              raw_text: rawText.slice(0, 20000),
              raw_text_length: rawText.length,
              raw_object: (rawObject ?? null) as never,
              finish_reason: finishReason ?? null,
              error_name: errorName ?? null,
              error_message: msg,
              error_stack: errorStack ?? null,
              zod_issues: zodIssues as never,
            });
          if (failErr) console.warn("[coach-feedback] failure log insert failed", failErr.message);
        } catch (logErr) {
          console.warn("[coach-feedback] failure log threw", logErr);
        }
      }
    }

    if (!output) {
      console.warn("[coach-feedback] all attempts failed, using deterministic fallback");
      output = buildFallbackCoachOutput(data);
    }

    // Persist for later viewing + ratings.
    const items = output.items.map((it, i) => ({ ...it, id: `item-${i + 1}` }));
    const { error } = await context.supabase
      .from("coach_feedback")
      .upsert(
        {
          analysis_id: data.analysis_id,
          user_id: context.userId,
          model: COACH_MODEL,
          summary: output.summary,
          items,
          prompt_meta: { level: data.level, has_transition: !!data.transition },
        },
        { onConflict: "analysis_id,user_id" },
      );
    if (error) {
      console.warn("[coach-feedback] persist failed", error.message);
    }

    return { summary: output.summary, items, model: COACH_MODEL };
  });

export const getCoachFeedbackFn = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ analysis_id: z.string().uuid() }).parse(data))
  .handler(async ({ data, context }) => {
    const { data: row, error } = await context.supabase
      .from("coach_feedback")
      .select("summary, items, model, created_at")
      .eq("analysis_id", data.analysis_id)
      .eq("user_id", context.userId)
      .maybeSingle();
    if (error) throw error;
    return row;
  });
