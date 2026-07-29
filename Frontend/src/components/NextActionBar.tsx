import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface NextActionBarProps {
  /** One short sentence — answers "What should I do next?" */
  title: string;
  /** Optional supporting sentence — keep under 12 words */
  subtitle?: string;
  /** Button label, e.g. "Start Today's Training" */
  cta: string;
  /** Internal route to navigate to */
  to: string;
}

/**
 * Persistent end-of-page CTA. Every primary screen ends with one of these so
 * the user is never left wondering what to do next. Tone: confident, single
 * verb-led action. Never show more than one primary action.
 */
export function NextActionBar({ title, subtitle, cta, to }: NextActionBarProps) {
  return (
    <Card className="glass mt-10 overflow-hidden border-primary/20">
      <div className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between md:p-7">
        <div className="space-y-1">
          <div className="text-xs font-medium uppercase tracking-wider text-primary/80">
            What's next
          </div>
          <h3 className="font-display text-xl font-semibold tracking-tight">{title}</h3>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <Button asChild size="lg" className="shrink-0">
          <Link to={to}>
            {cta}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </Card>
  );
}
