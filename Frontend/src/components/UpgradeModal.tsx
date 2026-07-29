import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Check, Crown } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { onOpenUpgradeModal, PRO_PRICE_MONTHLY_USD } from "@/lib/billing";

const PRO_FEATURES = [
  "Unlimited single-transition analyses",
  "Full DJ-set analysis (every transition scanned)",
  "Advanced coach feedback (deep diagnosis + fixes)",
  "Full progress history & analytics",
  "Skill tree across all 6 DJ skills",
  "Personalised weekly training plan",
];

export function UpgradeModal() {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<string | undefined>();

  useEffect(() => onOpenUpgradeModal((r) => { setReason(r); setOpen(true); }), []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="mx-auto h-12 w-12 rounded-xl bg-[image:var(--gradient-primary)] flex items-center justify-center glow-purple">
            <Crown className="h-6 w-6 text-white" />
          </div>
          <DialogTitle className="text-center text-2xl font-display mt-2">
            Upgrade to MixCoach Pro
          </DialogTitle>
          <DialogDescription className="text-center">
            {reason ?? "Unlock unlimited analyses and the full coaching system."}
          </DialogDescription>
        </DialogHeader>

        <ul className="space-y-2 my-2">
          {PRO_FEATURES.map((f) => (
            <li key={f} className="flex items-start gap-2 text-sm">
              <Check className="h-4 w-4 text-accent mt-0.5 shrink-0" /> {f}
            </li>
          ))}
        </ul>

        <div className="flex items-end gap-2 justify-center pt-2">
          <span className="font-display text-4xl font-bold">${PRO_PRICE_MONTHLY_USD}</span>
          <span className="text-muted-foreground mb-1">/month</span>
        </div>

        <Button
          asChild
          size="lg"
          className="w-full mt-2 bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90"
        >
          <Link to="/app/premium" onClick={() => setOpen(false)}>Upgrade now</Link>
        </Button>
        <p className="text-center text-[11px] text-muted-foreground">
          Beta: billing rolls out shortly. No card required to test.
        </p>
      </DialogContent>
    </Dialog>
  );
}
