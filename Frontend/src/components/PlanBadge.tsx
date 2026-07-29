import { Crown, Sparkles } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { usePlan } from "@/lib/billing";

export function PlanBadge({ asLink = true }: { asLink?: boolean }) {
  const { isPro } = usePlan();
  const content = isPro ? (
    <>
      <Crown className="h-3 w-3" /> PRO
    </>
  ) : (
    <>
      <Sparkles className="h-3 w-3" /> FREE
    </>
  );
  const cls = `inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
    isPro
      ? "border-primary/60 bg-[image:var(--gradient-primary)] text-white"
      : "border-border bg-card/60 text-muted-foreground"
  }`;
  if (asLink && !isPro) {
    return (
      <Link to="/app/premium" className={cls}>
        {content}
      </Link>
    );
  }
  return <span className={cls}>{content}</span>;
}
