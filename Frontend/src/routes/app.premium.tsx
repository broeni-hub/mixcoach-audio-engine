import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, Crown, Sparkles, CreditCard, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { PLAN_LIMITS, PRO_PRICE_MONTHLY_USD, startUpgradeCheckout, usePlan, useMonthlyUsage } from "@/lib/billing";

export const Route = createFileRoute("/app/premium")({
  head: () => ({ meta: [{ title: "Upgrade — MixCoach" }] }),
  component: Premium,
});

const PRO_FEATURES = [
  "Unlimited single-transition analyses",
  "Full DJ-set analysis (every transition scanned)",
  "Advanced coach feedback (deep diagnosis + fixes)",
  "Full progress history & analytics",
  "6-skill skill tree",
  "Personalised weekly training plan",
];

function Premium() {
  const { isPro, setPlan } = usePlan();
  const { used, cap } = useMonthlyUsage();

  async function onUpgrade() {
    const result = await startUpgradeCheckout("pro");
    if (result.url) {
      window.location.href = result.url;
      return;
    }
    // Stripe not wired yet — flip plan locally for the private beta so the
    // user can test Pro features. Replace with real checkout once Stripe lands.
    setPlan("pro");
    toast.success("You're on Pro (beta). Billing will activate before launch.");
  }

  return (
    <div className="max-w-3xl mx-auto animate-fade-in space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/20 px-3 py-1 text-xs text-primary">
          <Sparkles className="h-3 w-3" /> MixCoach Pro
        </div>
        <h1 className="mt-4 font-display text-4xl font-bold">Unlock your full potential</h1>
        <p className="mt-3 text-muted-foreground">
          Free covers {PLAN_LIMITS.free.monthlySingleAnalyses} transitions a month. Pro is unlimited and unlocks the full coach.
        </p>
        {!isPro && (
          <p className="mt-2 text-xs text-muted-foreground">
            You've used <span className="text-foreground font-semibold">{used} / {cap}</span> free analyses this month.
          </p>
        )}
      </div>

      <Card className="glass glow-purple relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[3px] bg-[image:var(--gradient-rk)]" />
        <CardContent className="p-8">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Crown className="h-3 w-3 text-primary" /> Pro
              </div>
              <div className="flex items-end gap-2 mt-1">
                <span className="font-display text-5xl font-bold">${PRO_PRICE_MONTHLY_USD}</span>
                <span className="text-muted-foreground mb-2">/ month</span>
              </div>
            </div>
            <Button
              size="lg"
              disabled={isPro}
              onClick={onUpgrade}
              className="bg-[image:var(--gradient-primary)] border-0 hover:opacity-90"
            >
              <Crown className="h-4 w-4" /> {isPro ? "You're on Pro" : "Upgrade to Pro"}
            </Button>
          </div>
          <ul className="mt-8 grid sm:grid-cols-2 gap-3">
            {PRO_FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm">
                <Check className="h-4 w-4 text-accent" /> {f}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Billing placeholder — Stripe-ready architecture, no integration yet. */}
      <Card className="glass">
        <CardContent className="p-6">
          <div className="flex items-start gap-3">
            <div className="h-9 w-9 rounded-lg border border-border bg-card/60 flex items-center justify-center">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="flex-1">
              <p className="font-semibold">Billing</p>
              <p className="text-sm text-muted-foreground mt-1">
                {isPro
                  ? "You're on Pro through the private beta. A managed checkout and invoices arrive when billing activates."
                  : "Card payments arrive when billing activates. During the private beta you can switch to Pro to test the full experience."}
              </p>
              <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-accent" /> Stripe-ready</span>
                <span>·</span>
                <Link to="/pricing" className="hover:text-foreground underline-offset-4 hover:underline">See public pricing</Link>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
