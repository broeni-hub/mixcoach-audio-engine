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
import { useLang } from "@/lib/i18n";
import { TEXTE, RESET_ZIEL } from "@/lib/auth-texte";
import { lageNachRegistrierung, deuteAnmeldefehler, istWiederherstellung } from "@/lib/auth-logik";

const INVITE_KEY = "mixcoach.inviteCode.v1";

export const Route = createFileRoute("/auth")({
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const lang = useLang();
  const T = TEXTE[lang];
  const [mode, setMode] = useState<"signin" | "signup" | "reset">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  // Wird gesetzt, sobald feststeht, dass eine Bestaetigungsmail im Spiel ist -
  // nach der Registrierung oder nach einem Login-Versuch vor der Bestaetigung.
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  // Nach einer abgelehnten Anmeldung: Supabase sagt absichtlich NICHT, ob das
  // Passwort falsch ist oder das Konto fehlt (sonst koennte jemand fremde
  // Adressen durchprobieren). Der Nutzer darf trotzdem nicht raten - deshalb
  // beide Auswege nebeneinander, statt den Fall aufzuloesen.
  const [beideWege, setBeideWege] = useState(false);
  // Gesetzt, sobald resetPasswordForEmail angenommen wurde. Bewusst NICHT
  // "E-Mail gesendet" - das weiss der Browser nicht (siehe auth-texte.ts).
  const [resetAngefragt, setResetAngefragt] = useState(false);
  const [hasInvite, setHasInvite] = useState<boolean>(() =>
    typeof window === "undefined" ? !WAITLIST_MODE : !WAITLIST_MODE || !!localStorage.getItem(INVITE_KEY),
  );

  useEffect(() => {
    // Ein Wiederherstellungslink erzeugt eine SITZUNG - und ohne diese Weiche
    // wuerde die Zeile darunter den Nutzer schnurstracks ins Dashboard
    // schieben, statt ihn sein Passwort setzen zu lassen. Der Link landet nur
    // dann hier, wenn die Adresse nicht in der Redirect-Allowlist des
    // Supabase-Projekts steht und auf die SITE_URL zurueckfaellt; dass das
    // passieren kann, ist von hier aus nicht pruefbar (siehe Bericht).
    const wiederherstellung = () =>
      typeof window !== "undefined" && istWiederherstellung(window.location.hash);

    supabase.auth.getSession().then(({ data }) => {
      if (wiederherstellung()) { navigate({ to: "/passwort-neu" }); return; }
      if (data.session) navigate({ to: "/app/dashboard" });
    });
    const { data: sub } = supabase.auth.onAuthStateChange((e, s) => {
      if (e === "PASSWORD_RECOVERY" || wiederherstellung()) {
        navigate({ to: "/passwort-neu" });
        return;
      }
      if (s) navigate({ to: "/app/dashboard" });
    });
    return () => sub.subscription.unsubscribe();
  }, [navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "reset") {
        // Supabase antwortet hier IMMER freundlich, auch wenn es die Adresse
        // gar nicht gibt (am 18.08.2026 nachgemessen: HTTP 200, leerer Koerper,
        // fuer existierende wie erfundene Adresse gleich). Das ist Absicht und
        // richtig - sonst liesse sich durchprobieren, wer ein Konto hat.
        // Deshalb steht in der Meldung "falls es ein Konto gibt", nicht "Mail
        // gesendet".
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: window.location.origin + RESET_ZIEL,
        });
        if (error) throw error;
        setResetAngefragt(true);
        setBeideWege(false);
        return;
      }

      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin,
            data: { display_name: name || email.split("@")[0] },
          },
        });
        if (error) throw error;

        // Die ANTWORT entscheidet, nicht eine Annahme. Steht am Projekt
        // mailer_autoconfirm=true (am 18.08.2026 an /auth/v1/settings
        // nachgemessen), liefert signUp sofort eine Sitzung - der Nutzer ist
        // drin. Bis dahin stand hier unbedingt "confirm the link in your
        // email", und jeder neue Tester wartete auf eine Mail, die es nicht
        // gibt. So ist der Text in BEIDEN Servereinstellungen richtig, ohne
        // dass jemand eine Konstante pflegen muss.
        if (lageNachRegistrierung(data) === "angemeldet") {
          toast.success(T.kontoAngelegtDrin);
          // onAuthStateChange leitet weiter.
        } else {
          setAwaitingConfirm(true);
          toast.success(T.kontoAngelegtBestaetigen);
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      // Supabase meldet das englisch und technisch. Die Faelle sind haeufig
      // genug, um sie zu uebersetzen und den Ausweg gleich anzubieten.
      switch (deuteAnmeldefehler(msg)) {
        case "nicht-bestaetigt":
          setAwaitingConfirm(true);
          toast.error(T.nichtBestaetigt);
          break;
        case "zu-viele-mails":
          // Am 18.08.2026 gemessen: der zweite recover-Aufruf innerhalb einer
          // Minute liefert 429 over_email_send_rate_limit. Ohne diese Meldung
          // ist das von "Mail unterwegs" nicht zu unterscheiden.
          toast.error(T.zuVieleMails);
          break;
        case "beide-wege":
          setBeideWege(true);
          toast.error(T.anmeldungAbgelehnt);
          break;
        default:
          toast.error(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  async function onResendConfirm() {
    if (!email) {
      toast.error(lang === "de" ? "Gib zuerst deine E-Mail-Adresse ein." : "Enter your email address first.");
      return;
    }
    setBusy(true);
    try {
      const { error } = await supabase.auth.resend({ type: "signup", email });
      if (error) throw error;
      toast.success(T.erneutGesendet);
    } catch (err) {
      // Der wahrscheinlichste Fehler ist ein Rate-Limit: der eingebaute
      // Mailversand von Supabase ist auf wenige Nachrichten pro Stunde
      // begrenzt und nicht fuer den Produktivbetrieb gedacht. Bei mehreren
      // Testern gleichzeitig laeuft man dagegen - und ohne diese Meldung
      // waere es ununterscheidbar von "Mail unterwegs".
      const msg = err instanceof Error ? err.message : "Could not resend";
      toast.error(
        /rate|limit|too many/i.test(msg)
          ? T.zuVieleMails
          : msg,
      );
    } finally {
      setBusy(false);
    }
  }

  /**
   * Anmeldung mit Google - ueber den OAuth-Broker von Lovable.
   *
   * WARUM NICHT DIREKT UEBER SUPABASE: das Supabase-Projekt gehoert Lovable.
   * Am 16.08.2026 nachgemessen an /auth/v1/settings und /auth/v1/authorize:
   *
   *   external.google = true          Google ist im Projekt eingeschaltet
   *   authorize       = 400           "Unsupported provider: missing OAuth secret"
   *
   * Eingeschaltet, aber ohne Zugangsdaten - das ist kein halbfertiger
   * Zustand, sondern Absicht. Lovable behaelt die OAuth-Anwendung bei sich
   * und liefert nur fertige Tokens, die der Wrapper per
   * supabase.auth.setSession() einsetzt. In das Projekt laesst sich also
   * gar kein Secret eintragen, und supabase.auth.signInWithOAuth kann dort
   * nie funktionieren. (Ich hatte genau das kurzzeitig eingebaut - falsch,
   * siehe Commit 5519a9b und dessen Revert.)
   *
   * WAS DAS FUER LOKAL HEISST: der Broker liegt unter /~oauth/initiate auf
   * der eigenen Domain und wird von Lovables Hosting bereitgestellt. Der
   * Vite-Dev-Server kennt die Route nicht - nachgemessen: HTTP 404, waehrend
   * /auth 200 liefert. Google kann lokal also NICHT gehen, und zwar aus
   * einem Grund, an dem kein Code etwas aendert.
   *
   * Genau das sagt der Knopf jetzt, statt still nichts zu tun. Vorher ist
   * der Nutzer weitergeleitet worden, kam ohne Sitzung zurueck und stand
   * wieder auf der Anmeldeseite - ohne eine einzige Meldung. Der
   * verschluckte Fehler ist in diesem Projekt die teuerste Codezeile.
   */
  async function onGoogle() {
    const lokal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(window.location.hostname);
    if (lokal) {
      toast.error(
        "Google-Anmeldung gibt es nur in der veröffentlichten App — der "
        + "OAuth-Dienst läuft bei Lovable und ist lokal nicht erreichbar. "
        + "Hier bitte mit E-Mail und Passwort anmelden.",
      );
      return;
    }

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
              {mode === "signin" ? T.willkommen : mode === "signup" ? T.kontoAnlegen : T.passwortNeuSetzen}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {mode !== "reset" && (
              <>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={onGoogle}
                  disabled={googleBusy}
                >
                  {googleBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <GoogleIcon />}
                  {T.mitGoogle}
                </Button>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
                  <div className="relative flex justify-center text-xs"><span className="bg-card px-2 text-muted-foreground">{T.oder}</span></div>
                </div>
              </>
            )}

            <form onSubmit={onSubmit} className="space-y-3">
              {mode === "signup" && (
                <div>
                  <Label htmlFor="name">{T.anzeigename}</Label>
                  <Input id="name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1" placeholder="DJ Alias" />
                </div>
              )}
              <div>
                <Label htmlFor="email">{T.email}</Label>
                <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1" />
              </div>
              {mode !== "reset" && (
                <div>
                  <div className="flex items-baseline justify-between">
                    <Label htmlFor="password">{T.passwort}</Label>
                    {mode === "signin" && (
                      <button
                        type="button"
                        onClick={() => { setMode("reset"); setBeideWege(false); setResetAngefragt(false); }}
                        className="text-xs text-primary hover:underline"
                      >
                        {T.passwortVergessen}
                      </button>
                    )}
                  </div>
                  <Input id="password" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1" />
                </div>
              )}
              <Button type="submit" disabled={busy} className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                {mode === "signin" ? T.anmelden : mode === "signup" ? T.kontoAnlegen : T.linkAnfordern}
              </Button>
            </form>

            {/* Erscheint erst, wenn eine Bestaetigungsmail tatsaechlich im
                Spiel ist - sonst waere es ein Hinweis auf ein Problem, das
                gar nicht besteht. */}
            {awaitingConfirm && (
              <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
                <p className="text-muted-foreground">
                  <strong className="text-foreground">{T.wartenTitel}</strong> {T.wartenText}
                </p>
                <button
                  type="button"
                  onClick={onResendConfirm}
                  disabled={busy}
                  className="mt-2 text-primary hover:underline disabled:opacity-50"
                >
                  {T.erneutSenden}
                </button>
              </div>
            )}

            {/* J3: Der Anmeldedienst sagt absichtlich nicht, welcher der beiden
                Faelle vorliegt. Wir loesen das nicht auf - wir bieten beide
                Auswege an, damit der Nutzer so oder so weiterkommt. */}
            {beideWege && mode === "signin" && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
                <p className="font-medium text-foreground">{T.beideWegeTitel}</p>
                <p className="mt-1 text-muted-foreground">{T.beideWegeErklaerung}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => { setMode("signup"); setBeideWege(false); }}
                  >
                    {T.kontoAnlegen}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => { setMode("reset"); setBeideWege(false); }}
                  >
                    {T.passwortNeuSetzen}
                  </Button>
                </div>
              </div>
            )}

            {/* J1a: "Anfrage ist raus" - NICHT "E-Mail gesendet". Ob eine Mail
                hinausgeht, weiss der Browser nicht; angenommen wurde nur der
                Auftrag. Und der Ausweg steht gleich dabei, mit dem am
                18.08.2026 gemessenen Grund (429 nach dem zweiten Aufruf). */}
            {resetAngefragt && (
              <div className="rounded-md border border-accent/40 bg-accent/10 p-3 text-sm">
                <p className="font-medium text-foreground">{T.resetTitel}</p>
                <p className="mt-1 text-muted-foreground">{T.resetText}</p>
                <p className="mt-2 text-muted-foreground">{T.resetAusweg}</p>
              </div>
            )}

            <p className="text-center text-sm text-muted-foreground">
              {mode === "reset" ? (
                <button
                  type="button"
                  onClick={() => { setMode("signin"); setResetAngefragt(false); }}
                  className="text-primary hover:underline"
                >
                  {T.zurueckZurAnmeldung}
                </button>
              ) : (
                <>
                  {mode === "signin" ? T.neuHier : T.schonKonto}{" "}
                  <button
                    type="button"
                    onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setBeideWege(false); }}
                    className="text-primary hover:underline"
                  >
                    {mode === "signin" ? T.kontoAnlegen : T.anmelden}
                  </button>
                </>
              )}
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
