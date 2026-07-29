import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Flame, Sparkles, Target } from "lucide-react";
import type { NextAction } from "@/lib/retention";

export function NextBestAction({ action }: { action: NextAction }) {
  const Icon = action.tone === "warning" ? Flame : action.tone === "success" ? Sparkles : Target;
  const ring =
    action.tone === "warning"
      ? "border-orange-500/40 bg-orange-500/5"
      : action.tone === "success"
      ? "border-emerald-500/40 bg-emerald-500/5"
      : "border-primary/40 bg-primary/5";
  return (
    <Card className={`border ${ring}`}>
      <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-background/40 p-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Next best action</div>
            <div className="font-display text-lg font-semibold">{action.title}</div>
            <div className="text-sm text-muted-foreground">{action.description}</div>
          </div>
        </div>
        <Button asChild className="bg-[image:var(--gradient-primary)] border-0 glow-purple shrink-0">
          <Link to={action.to}>
            {action.cta} <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
