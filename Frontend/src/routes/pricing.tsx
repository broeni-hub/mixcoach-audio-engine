import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, Crown, Sparkles, X } from "lucide-react";
import { PLAN_LIMITS, PRO_PRICE_MONTHLY_USD } from "@/lib/billing";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing — MixCoach" },
      { name: "description", content: "Free plan or Pro at $12/mo. Unlock unlimited transitions, full-set analysis, and your personal DJ coach." },
    ],
  }),
  component: PricingPage,
});

const FREE_FEATURES = [
  { text: "3 single-transition analyses / month", on: true },
  { text: "Basic coach feedback",                 on: true },
  { text: "Recent history",                       on: true },
  { text: "Full DJ-set analysis",                 on: false },
  { text: "Advanced coach feedback",              on: false },
  { text: "Skill tree + weekly training plan",    on: false },
];

const PRO_FEATURES = [
  { text: "Unlimited single-transition analyses", on: true },
  { text: "Full DJ-set analysis (every transition)", on: true },
  { text: "Advanced coach feedback (deep diagnosis)", on: true },
  { text: "Full progress history & analytics", on: true },
  { text: "6-skill skill tree", on: true },
  { text: "Personalised weekly training plan", on: true },
];

function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-16">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/20 px-3 py-1 text-xs text-primary">
            <Sparkles className="h-3 w-3" /> Private beta · simple pricing
          </div>
          <h1 className="mt-4 font-display text-4xl md:text-5xl font-bold">
            Coaching that grows with you
          </h1>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
            Start free. Upgrade to Pro when you're ready to scan full sets and unlock your personal coach.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mt-12">
          <Card className="glass">
            <CardContent className="p-8">
              <p className="eyebrow text-xs text-muted-foreground">Free</p>
              <div className="flex items-end gap-2 mt-1">
                <span className="font-display text-5xl font-bold">$0</span>
                <span className="text-muted-foreground mb-2">/ forever</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Test the coach on up to {PLAN_LIMITS.free.monthlySingleAnalyses} transitions per month.
              </p>
              <Button asChild variant="outline" className="w-full mt-6">
                <Link to="/auth">Start free</Link>
              </Button>
              <ul className="mt-6 space-y-2">
                {FREE_FEATURES.map((f) => (
                  <li key={f.text} className="flex items-start gap-2 text-sm">
                    {f.on ? <Check className="h-4 w-4 text-accent mt-0.5" /> : <X className="h-4 w-4 text-muted-foreground/60 mt-0.5" />}
                    <span className={f.on ? "" : "text-muted-foreground line-through"}>{f.text}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="glass border-primary/40 glow-purple relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
            <CardContent className="p-8">
              <div className="flex items-center justify-between">
                <p className="eyebrow text-xs text-primary">Pro</p>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/20 text-primary px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  <Crown className="h-3 w-3" /> Most popular
                </span>
              </div>
              <div className="flex items-end gap-2 mt-1">
                <span className="font-display text-5xl font-bold">${PRO_PRICE_MONTHLY_USD}</span>
                <span className="text-muted-foreground mb-2">/ month</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                The full MixCoach experience. Cancel any time.
              </p>
              <Button asChild className="w-full mt-6 bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                <Link to="/app/premium">Upgrade to Pro</Link>
              </Button>
              <ul className="mt-6 space-y-2">
                {PRO_FEATURES.map((f) => (
                  <li key={f.text} className="flex items-start gap-2 text-sm">
                    <Check className="h-4 w-4 text-accent mt-0.5" /> {f.text}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-8">
          Billing is being rolled out during the private beta. No credit card required to test today.
        </p>
      </div>
    </div>
  );
}
