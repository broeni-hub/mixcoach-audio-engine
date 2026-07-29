import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Waves, Loader2, KeyRound, Check } from "lucide-react";
import { toast } from "sonner";
import { WAITLIST_MODE } from "@/lib/billing";
import { joinWaitlistFn, verifyInviteCodeFn } from "@/lib/beta.functions";

const INVITE_KEY = "mixcoach.inviteCode.v1";

export const Route = createFileRoute("/auth")({
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [hasInvite, setHasInvite] = useState<boolean>(() =>
    typeof window === "undefined" ? !WAITLIST_MODE : !WAITLIST_MODE || !!localStorage.getItem(INVITE_KEY),
  );

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) navigate({ to: "/app/dashboard" });
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => {
      if (s) navigate({ to: "/app/dashboard" });
    });
    return () => sub.subscription.unsubscribe();
  }, [navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin,
            data: { display_name: name || email.split("@")[0] },
          },
        });
        if (error) throw error;
        toast.success("Account created. Check your email to confirm.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  async function onGoogle() {
    setGoogleBusy(true);
    try {
      const result = await lovable.auth.signInWithOAuth("google", {
        redirect_uri: window.location.origin,
      });
      if (result.error) {
        toast.error(result.error.message || "Google sign-in failed");
        setGoogleBusy(false);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Google sign-in failed");
      setGoogleBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="h-10 w-10 rounded-lg bg-[image:var(--gradient-primary)] flex items-center justify-center glow-purple">
            <Waves className="h-5 w-5 text-white" />
          </div>
          <span className="font-display font-bold text-2xl tracking-tight">MixCoach</span>
        </Link>
        {WAITLIST_MODE && !hasInvite ? (
          <WaitlistCard onInvite={() => setHasInvite(true)} />
        ) : (
        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-center text-xl">
              {mode === "signin" ? "Welcome back" : "Create your account"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={onGoogle}
              disabled={googleBusy}
            >
              {googleBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <GoogleIcon />}
              Continue with Google
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
              <div className="relative flex justify-center text-xs"><span className="bg-card px-2 text-muted-foreground">or</span></div>
            </div>

            <form onSubmit={onSubmit} className="space-y-3">
              {mode === "signup" && (
                <div>
                  <Label htmlFor="name">Display name</Label>
                  <Input id="name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1" placeholder="DJ Alias" />
                </div>
              )}
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1" />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1" />
              </div>
              <Button type="submit" disabled={busy} className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                {mode === "signin" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <p className="text-center text-sm text-muted-foreground">
              {mode === "signin" ? "New to MixCoach?" : "Already have an account?"}{" "}
              <button
                type="button"
                onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
                className="text-primary hover:underline"
              >
                {mode === "signin" ? "Create an account" : "Sign in"}
              </button>
            </p>
          </CardContent>
        </Card>
        )}
      </div>
    </div>
  );
}

function WaitlistCard({ onInvite }: { onInvite: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [joined, setJoined] = useState(false);

  async function join(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await joinWaitlistFn({ data: { email, name: name || undefined, source: "auth" } });
      setJoined(true);
      toast.success("You're on the waitlist.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't join waitlist");
    } finally {
      setBusy(false);
    }
  }

  async function redeem() {
    if (!code.trim()) return;
    setBusy(true);
    try {
      const { valid } = await verifyInviteCodeFn({ data: { code: code.trim() } });
      if (!valid) { toast.error("Invalid invite code"); return; }
      localStorage.setItem(INVITE_KEY, code.trim().toUpperCase());
      toast.success("Invite accepted. Welcome.");
      onInvite();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't verify code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="glass glow-purple">
      <CardHeader>
        <div className="mx-auto h-10 w-10 rounded-xl bg-[image:var(--gradient-primary)] flex items-center justify-center">
          <KeyRound className="h-5 w-5 text-white" />
        </div>
        <CardTitle className="text-center text-xl mt-2">MixCoach is in private beta</CardTitle>
        <p className="text-center text-sm text-muted-foreground">
          Join the waitlist — or enter your invite code to get straight in.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {joined ? (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-accent/40 bg-accent/10 px-3 py-3 text-sm text-accent">
            <Check className="h-4 w-4" /> You're on the list. We'll be in touch.
          </div>
        ) : (
          <form onSubmit={join} className="space-y-3">
            <div>
              <Label htmlFor="wname">Name (optional)</Label>
              <Input id="wname" value={name} onChange={(e) => setName(e.target.value)} className="mt-1" placeholder="DJ Alias" />
            </div>
            <div>
              <Label htmlFor="wemail">Email</Label>
              <Input id="wemail" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1" />
            </div>
            <Button type="submit" disabled={busy} className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} Join the waitlist
            </Button>
          </form>
        )}

        <div className="relative">
          <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
          <div className="relative flex justify-center text-xs"><span className="bg-card px-2 text-muted-foreground">already invited?</span></div>
        </div>

        <div className="flex gap-2">
          <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="INVITE-CODE" />
          <Button type="button" variant="outline" onClick={redeem} disabled={busy || !code.trim()}>
            Redeem
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}


function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}
