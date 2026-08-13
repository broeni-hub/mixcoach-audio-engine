// LLM-generated coach feedback card. Loads existing feedback from DB, shows
// summary + numbered priority items, each with its own 👍/👎. If no feedback
// exists yet (e.g. older analysis from before the LLM layer), offers a
// "Generate" button that calls the server fn on demand.
import { useEffect, useState } from "react";
import { Sparkles, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FeedbackRating } from "@/components/FeedbackRating";
import { generateCoachFeedbackFn, getCoachFeedbackFn } from "@/lib/coach-feedback.functions";
import { listRatingsForAnalysisFn } from "@/lib/feedback-ratings.functions";
import type { AnalysisResult } from "@/lib/analysis";
import { toast } from "sonner";

interface CoachItem {
  id: string;
  priority: number;
  title: string;
  what: string;
  why: string;
  how: string;
  related_rule_slug: string | null;
}
interface CoachFeedback {
  summary: string;
  items: CoachItem[];
  model: string;
}

export function CoachFeedbackCard({ analysis }: { analysis: AnalysisResult }) {
  const [feedback, setFeedback] = useState<CoachFeedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [ratings, setRatings] = useState<Record<string, 1 | -1>>({});

  const loadRatings = async () => {
    try {
      const rows = await listRatingsForAnalysisFn({ data: { analysis_id: analysis.id } });
      const map: Record<string, 1 | -1> = {};
      for (const r of rows ?? []) {
        const key = `${r.target_kind}:${r.target_ref}`;
        map[key] = r.rating as 1 | -1;
      }
      setRatings(map);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const row = await getCoachFeedbackFn({ data: { analysis_id: analysis.id } });
        if (!cancelled && row) setFeedback({ summary: row.summary, items: (row.items as unknown as CoachItem[]) ?? [], model: row.model });
      } catch (err) {
        console.warn("[coach] load failed", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    void loadRatings();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis.id]);

  const generate = async () => {
    setGenerating(true);
    try {
      // Reconstruct payload from the stored analysis result.
      const findings = (analysis.findings ?? []).map((f) => ({
        rule_slug: f.rule_slug, title: f.title, diagnosis: f.diagnosis, fix: f.fix,
        severity: f.severity, metric: f.metric, value: f.value,
      }));
      // null heisst "nicht gemessen" - der Prompt laesst die Zeile dann weg.
      // Hier standen bis zum 13.08.2026 feste Zahlen (bpm_confidence 0.8,
      // key_confidence 0.6, bass_stability 70, dynamic_range_db 8,
      // loudness_dbfs -12, peak_count 0), weil das Schema Pflichtzahlen
      // verlangte. Der Report der Engine enthaelt diese Groessen nicht; sie
      // waren erfunden und standen im Prompt unter "Measurements". Die
      // Ehrlichkeitslinie gilt auch dort, wo nur ein Modell mitliest.
      const m = {
        bpm: analysis.bpm, bpm_confidence: null,
        key: analysis.key, key_confidence: null,
        bass_pct: analysis.frequency?.bass ?? null,
        mid_pct: analysis.frequency?.mid ?? null,
        high_pct: analysis.frequency?.high ?? null,
        bass_stability: null, dynamic_range_db: null, loudness_dbfs: null,
        peak_count: null, duration_sec: analysis.transitionLength,
      };
      const res = await generateCoachFeedbackFn({
        data: {
          analysis_id: analysis.id,
          filename: analysis.fileName,
          track_b_filename: analysis.trackB?.fileName ?? null,
          level: "intermediate",
          measurements: m,
          findings,
          transition: analysis.transition,
        },
      });
      setFeedback(res);
      toast.success("Coach feedback ready");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading personalised coach feedback…
      </div>
    );
  }

  if (!feedback) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card/40 p-4">
        <p className="text-sm text-muted-foreground">No personalised coach feedback yet for this mix.</p>
        <Button size="sm" className="mt-3" onClick={generate} disabled={generating}>
          {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
          Generate now
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-foreground/90 leading-relaxed flex-1">{feedback.summary}</p>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className="text-[10px]">{feedback.model.split("/").pop()}</Badge>
          <Button size="icon" variant="ghost" onClick={generate} disabled={generating} aria-label="Regenerate">
            {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          </Button>
        </div>
      </div>
      <ol className="space-y-3">
        {feedback.items
          .slice()
          .sort((a, b) => a.priority - b.priority)
          .map((item) => {
            const key = `coach_item:${item.id}`;
            return (
              <li key={item.id} className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-baseline gap-3 min-w-0">
                    <span className="font-display text-primary font-bold tabular-nums shrink-0">{String(item.priority).padStart(2, "0")}</span>
                    <h4 className="font-display font-semibold leading-tight">{item.title}</h4>
                  </div>
                  <FeedbackRating
                    analysisId={analysis.id}
                    targetKind="coach_item"
                    targetRef={item.id}
                    initial={ratings[key] ?? null}
                  />
                </div>
                <dl className="mt-3 space-y-1.5 text-sm text-foreground/85">
                  <div><dt className="inline text-muted-foreground uppercase tracking-wider text-[10px] mr-2">What</dt><dd className="inline">{item.what}</dd></div>
                  <div><dt className="inline text-muted-foreground uppercase tracking-wider text-[10px] mr-2">Why</dt><dd className="inline">{item.why}</dd></div>
                  <div><dt className="inline text-accent uppercase tracking-wider text-[10px] mr-2">Drill</dt><dd className="inline">{item.how}</dd></div>
                </dl>
              </li>
            );
          })}
      </ol>

      {analysis.findings && analysis.findings.length > 0 && (
        <details className="rounded-lg border border-border bg-card/40">
          <summary className="cursor-pointer p-3 text-xs uppercase tracking-wider text-muted-foreground">
            Rule-engine findings ({analysis.findings.length}) — rate each
          </summary>
          <ul className="divide-y divide-border">
            {analysis.findings.map((f) => {
              const key = `rule:${f.rule_id}`;
              return (
                <li key={f.rule_id} className="p-3 flex items-start justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <div className="font-medium">{f.title} <Badge variant="secondary" className="ml-1 text-[10px] uppercase">{f.severity}</Badge></div>
                    <div className="text-muted-foreground text-xs mt-0.5">{f.diagnosis}</div>
                  </div>
                  <FeedbackRating
                    analysisId={analysis.id}
                    targetKind="rule"
                    targetRef={f.rule_id}
                    initial={ratings[key] ?? null}
                  />
                </li>
              );
            })}
          </ul>
        </details>
      )}
    </div>
  );
}
