// Floating beta menu: feedback / report bug / feature request.
import { useState } from "react";
import { MessageCircle, Bug, Lightbulb, Send, Loader2, MessageSquarePlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { submitBetaFeedbackFn } from "@/lib/beta.functions";

type Kind = "feedback" | "bug" | "feature";

const META: Record<Kind, { title: string; icon: typeof Bug; placeholder: string; eyebrow: string }> = {
  feedback: { title: "Send beta feedback", icon: MessageCircle, placeholder: "What's working? What's confusing? Be brutally honest.", eyebrow: "We read every word" },
  bug:      { title: "Report an issue",    icon: Bug,          placeholder: "What happened? What were you doing? What did you expect?", eyebrow: "Bug report" },
  feature:  { title: "Request a feature",  icon: Lightbulb,    placeholder: "What would make MixCoach indispensable for you?", eyebrow: "Feature request" },
};

export function BetaMenu() {
  const [open, setOpen] = useState<Kind | null>(null);
  return (
    <>
      <div className="fixed bottom-5 right-5 z-40">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              className="rounded-full shadow-lg bg-[image:var(--gradient-primary)] border-0 hover:opacity-90 uppercase tracking-wider text-[11px] font-semibold"
            >
              <MessageSquarePlus className="h-4 w-4" /> Beta
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Private beta · help us improve
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setOpen("feedback")}>
              <MessageCircle className="h-4 w-4" /> Send feedback
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setOpen("bug")}>
              <Bug className="h-4 w-4" /> Report an issue
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setOpen("feature")}>
              <Lightbulb className="h-4 w-4" /> Request a feature
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <FeedbackDialog kind={open} onClose={() => setOpen(null)} />
    </>
  );
}

function FeedbackDialog({ kind, onClose }: { kind: Kind | null; onClose: () => void }) {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const m = kind ? META[kind] : null;

  async function submit() {
    if (!kind || message.trim().length === 0) return;
    setBusy(true);
    try {
      await submitBetaFeedbackFn({
        data: {
          kind,
          subject: subject.trim() || undefined,
          message: message.trim(),
          url: typeof window !== "undefined" ? window.location.href : undefined,
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 500) : undefined,
        },
      });
      toast.success("Thanks — we got it.");
      setSubject(""); setMessage("");
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't send");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={!!kind} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        {m && (
          <>
            <DialogHeader>
              <p className="eyebrow text-[10px] text-accent">{m.eyebrow}</p>
              <DialogTitle className="flex items-center gap-2">
                <m.icon className="h-4 w-4" /> {m.title}
              </DialogTitle>
              <DialogDescription>
                You're in the MixCoach private beta. Your input shapes what ships next.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div>
                <Label htmlFor="subj">Subject (optional)</Label>
                <Input id="subj" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} className="mt-1" />
              </div>
              <div>
                <Label htmlFor="msg">Details</Label>
                <Textarea id="msg" value={message} onChange={(e) => setMessage(e.target.value)} rows={6} placeholder={m.placeholder} maxLength={4000} className="mt-1" />
                <p className="text-[11px] text-muted-foreground mt-1">{message.length}/4000</p>
              </div>
              <Button onClick={submit} disabled={busy || message.trim().length === 0} className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Send
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
