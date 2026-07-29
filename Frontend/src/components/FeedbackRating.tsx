// Inline 👍/👎 rating control. Persists to feedback_ratings via server fn.
import { useState } from "react";
import { ThumbsUp, ThumbsDown, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { rateFeedbackFn, clearRatingFn } from "@/lib/feedback-ratings.functions";

interface Props {
  analysisId: string;
  targetKind: "rule" | "coach_item";
  targetRef: string;
  initial?: 1 | -1 | null;
  label?: string;
}

export function FeedbackRating({ analysisId, targetKind, targetRef, initial = null, label }: Props) {
  const [rating, setRating] = useState<1 | -1 | null>(initial);
  const [busy, setBusy] = useState(false);

  const toggle = async (next: 1 | -1) => {
    if (busy) return;
    setBusy(true);
    const previous = rating;
    const goingTo = previous === next ? null : next;
    setRating(goingTo);
    try {
      if (goingTo === null) {
        await clearRatingFn({ data: { analysis_id: analysisId, target_kind: targetKind, target_ref: targetRef } });
      } else {
        await rateFeedbackFn({ data: { analysis_id: analysisId, target_kind: targetKind, target_ref: targetRef, rating: goingTo } });
      }
    } catch (err) {
      console.warn("[rating] failed", err);
      setRating(previous);
      toast.error("Couldn't save your feedback");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-1.5 text-xs">
      {label && <span className="text-muted-foreground mr-1">{label}</span>}
      <button
        type="button"
        onClick={() => toggle(1)}
        disabled={busy}
        aria-label="Helpful"
        aria-pressed={rating === 1}
        className={`h-6 w-6 inline-flex items-center justify-center rounded-md border transition-colors ${rating === 1 ? "border-accent bg-accent/15 text-accent" : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/40"}`}
      >
        {busy && rating === 1 ? <Loader2 className="h-3 w-3 animate-spin" /> : <ThumbsUp className="h-3 w-3" />}
      </button>
      <button
        type="button"
        onClick={() => toggle(-1)}
        disabled={busy}
        aria-label="Not helpful"
        aria-pressed={rating === -1}
        className={`h-6 w-6 inline-flex items-center justify-center rounded-md border transition-colors ${rating === -1 ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/40"}`}
      >
        {busy && rating === -1 ? <Loader2 className="h-3 w-3 animate-spin" /> : <ThumbsDown className="h-3 w-3" />}
      </button>
    </div>
  );
}
