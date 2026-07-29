import type { ReactNode } from "react";
import { Lock, Crown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { openUpgradeModal, usePlan } from "@/lib/billing";

interface Props {
  children: ReactNode;
  title?: string;
  description?: string;
  reason?: string;
  // When true, the locked content is hidden behind a frosted blur overlay so
  // users can sense what's there. When false, only the lock card is shown.
  preview?: boolean;
}

export function LockedFeature({
  children, title = "Pro feature", description = "Upgrade to unlock this.",
  reason, preview = true,
}: Props) {
  const { isPro } = usePlan();
  if (isPro) return <>{children}</>;
  return (
    <div className="relative rounded-2xl overflow-hidden border border-border bg-card/40">
      {preview && (
        <div aria-hidden className="pointer-events-none select-none blur-md opacity-40 max-h-[420px] overflow-hidden">
          {children}
        </div>
      )}
      <div className={`${preview ? "absolute inset-0" : ""} flex items-center justify-center p-6`}>
        <div className="text-center max-w-sm rounded-2xl border border-primary/40 bg-background/95 backdrop-blur p-6 glow-purple">
          <div className="mx-auto h-10 w-10 rounded-xl bg-[image:var(--gradient-primary)] flex items-center justify-center">
            <Lock className="h-5 w-5 text-white" />
          </div>
          <p className="eyebrow text-[10px] text-primary mt-3">MixCoach Pro</p>
          <h3 className="font-display text-lg font-bold mt-1">{title}</h3>
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
          <Button
            size="sm"
            onClick={() => openUpgradeModal(reason)}
            className="mt-4 bg-[image:var(--gradient-primary)] border-0 hover:opacity-90"
          >
            <Crown className="h-4 w-4" /> Upgrade to Pro
          </Button>
        </div>
      </div>
    </div>
  );
}
