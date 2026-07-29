import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Sparkles, Trophy } from "lucide-react";

export interface CelebrationModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  kind: "level-up" | "achievement";
  title: string;
  subtitle?: string;
  description?: string;
  cta?: { label: string; onClick: () => void };
}

export function CelebrationModal({ open, onOpenChange, kind, title, subtitle, description, cta }: CelebrationModalProps) {
  const Icon = kind === "level-up" ? Sparkles : Trophy;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-primary/30 bg-background/95 sm:max-w-md">
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="rounded-full bg-[image:var(--gradient-primary)] p-5 glow-purple">
            <Icon className="h-10 w-10 text-white" />
          </div>
          <DialogHeader className="gap-1 text-center sm:text-center">
            <div className="text-xs uppercase tracking-[0.2em] text-primary">
              {kind === "level-up" ? "Level Up" : "Achievement Unlocked"}
            </div>
            <DialogTitle className="font-display text-2xl">{title}</DialogTitle>
            {subtitle && <div className="text-sm text-muted-foreground">{subtitle}</div>}
          </DialogHeader>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
          <Button
            onClick={() => { cta?.onClick(); onOpenChange(false); }}
            className="bg-[image:var(--gradient-primary)] border-0 glow-purple"
          >
            {cta?.label ?? "Nice"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
