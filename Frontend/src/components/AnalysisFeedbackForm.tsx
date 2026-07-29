// Post-analysis 3-option usefulness rating + optional comment.
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Check, Loader2, ThumbsUp, Meh, ThumbsDown } from "lucide-react";
import { toast } from "sonner";
import { getAnalysisFeedbackFn, submitAnalysisFeedbackFn } from "@/lib/beta.functions";

type Usefulness = "very" | "somewhat" | "not";

const OPTIONS: { value: Usefulness; label: string; icon: typeof ThumbsUp; tone: string }[] = [
  { value: "very",     label: "Very useful",     icon: ThumbsUp,   tone: "border-accent/60 text-accent hover:bg-accent/10 data-[on=true]:bg-accent/15" },
  { value: "somewhat", label: "Somewhat useful", icon: Meh,        tone: "border-border text-foreground hover:bg-foreground/5 data-[on=true]:bg-foreground/10" },
  { value: "not",      label: "Not useful",      icon: ThumbsDown, tone: "border-primary/60 text-primary hover:bg-primary/10 data-[on=true]:bg-primary/15" },
];

export function AnalysisFeedbackForm({ analysisId }: { analysisId: string }) {
  const [value, setValue] = useState<Usefulness | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getAnalysisFeedbackFn({ data: { analysis_id: analysisId } })
      .then((row) => {
        if (cancelled || !row) return;
        setValue(row.usefulness as Usefulness);
        setComment(row.comment ?? "");
        setSaved(true);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [analysisId]);

  async function submit(next: Usefulness, finalComment?: string) {
    setBusy(true);
    try {
      await submitAnalysisFeedbackFn({
        data: { analysis_id: analysisId, usefulness: next, comment: (finalComment ?? comment).trim() || undefined },
      });
      setValue(next);
      setSaved(true);
      toast.success("Thanks for the feedback");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="glass border-accent/30">
      <CardHeader>
        <p className="eyebrow text-[10px] text-accent">Beta feedback</p>
        <CardTitle>Was this feedback useful?</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {OPTIONS.map((o) => {
            const on = value === o.value;
            return (
              <button
                key={o.value}
                type="button"
                data-on={on}
                disabled={busy}
                onClick={() => submit(o.value)}
                className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm font-medium transition-colors ${o.tone}`}
              >
                <o.icon className="h-4 w-4" /> {o.label}
                {on && <Check className="h-3 w-3 ml-1" />}
              </button>
            );
          })}
        </div>

        {value && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">What was wrong or missing? (optional)</p>
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Tell us what the coach got wrong, what you wish it caught, or what would have helped."
            />
            <div className="flex items-center justify-between mt-2">
              <p className="text-[11px] text-muted-foreground">
                {saved ? "Saved — you can update anytime." : "Will be sent with your rating."}
              </p>
              <Button size="sm" disabled={busy} onClick={() => submit(value, comment)} variant="outline">
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} Save comment
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
