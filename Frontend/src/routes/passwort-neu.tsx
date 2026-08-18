// Hier landet der Wiederherstellungslink aus der E-Mail.
//
// Der Ablauf hat zwei Stolperstellen, und beide sind in diesem Projekt schon
// einmal teuer gewesen:
//
// 1. Der Link bringt eine SITZUNG mit (im URL-Fragment, `type=recovery`). Der
//    Supabase-Client liest sie selbst aus der Adresse (detectSessionInUrl ist
//    Vorgabe) - aber auth.tsx haette den Nutzer damit schnurstracks ins
//    Dashboard geschoben, weil dort "Sitzung da -> weiter" stand. Deshalb die
//    Weiche in auth.tsx auf PASSWORD_RECOVERY.
// 2. Wenn der Link nicht funktioniert, darf die Seite NICHT aussehen wie im
//    Erfolgsfall. Am 16.08.2026 ist der Google-Versuch genau daran
//    gescheitert: Weiterleitung, keine Sitzung, keine Meldung - der Nutzer
//    stand wieder auf der Anmeldeseite und wusste nichts.

import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Waves, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "@/lib/i18n";
import { TEXTE, RESET_ZIEL } from "@/lib/auth-texte";

export const Route = createFileRoute("/passwort-neu")({
  ssr: false,
  head: () => ({ meta: [{ title: "Passwort zurücksetzen — MixCoach" }] }),
  component: PasswortNeuPage,
});

type Lage = "pruefe" | "bereit" | "kein-link";

function PasswortNeuPage() {
  const navigate = useNavigate();
  const lang = useLang();
  const T = TEXTE[lang];
  const [lage, setLage] = useState<Lage>("pruefe");
  const [passwort, setPasswort] = useState("");
  const [wiederholung, setWiederholung] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [neuAngefragt, setNeuAngefragt] = useState(false);
  // Der Grund, den Supabase im Fragment mitschickt (abgelaufen, schon
  // benutzt). Wird angezeigt statt verschluckt.
  const [grund, setGrund] = useState<string | null>(null);

  useEffect(() => {
    let abgebrochen = false;

    // Supabase legt einen Fehlschlag ins Fragment, nicht in den Query-Teil.
    const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const fehler = fragment.get("error_description") || fragment.get("error");
    if (fehler) setGrund(fehler.replace(/\+/g, " "));

    // Sagt der Anmeldedienst, dass der Link nicht ging, dann GILT das - auch
    // wenn in diesem Browser noch eine alte Sitzung liegt. Sonst klickt jemand
    // einen abgelaufenen Link und bekommt trotzdem das Formular: Die Seite
    // saehe aus wie im Erfolgsfall, obwohl der Link gescheitert ist. Genau
    // dieser Bauplan hat das Projekt schon dreimal Zeit gekostet.
    if (fehler) { setLage("kein-link"); return; }

    // getSession() wartet die Auswertung der Adresse ab - der Client verarbeitet
    // das Fragment beim Aufbau.
    supabase.auth.getSession().then(({ data }) => {
      if (abgebrochen) return;
      setLage(data.session ? "bereit" : "kein-link");
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => {
      if (!abgebrochen && s) setLage("bereit");
    });
    return () => { abgebrochen = true; sub.subscription.unsubscribe(); };
  }, []);

  async function speichern(e: React.FormEvent) {
    e.preventDefault();
    if (passwort.length < 6) { toast.error(T.passwortZuKurz); return; }
    if (passwort !== wiederholung) { toast.error(T.passwortUngleich); return; }
    setBusy(true);
    try {
      const { error } = await supabase.auth.updateUser({ password: passwort });
      if (error) throw error;
      toast.success(T.passwortGesetzt);
      navigate({ to: "/app/dashboard" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save password");
    } finally {
      setBusy(false);
    }
  }

  async function neuenLink(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin + RESET_ZIEL,
      });
      if (error) throw error;
      setNeuAngefragt(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not send link";
      toast.error(/rate|limit|too many|after \d+ seconds/i.test(msg) ? T.zuVieleMails : msg);
    } finally {
      setBusy(false);
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

        <Card className="glass">
          <CardHeader>
            <CardTitle className="text-center text-xl">{T.passwortNeuSetzen}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {lage === "pruefe" && (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            )}

            {lage === "bereit" && (
              <form onSubmit={speichern} className="space-y-3">
                <div>
                  <Label htmlFor="pw">{T.neuesPasswort}</Label>
                  <Input id="pw" type="password" required minLength={6} value={passwort}
                         onChange={(e) => setPasswort(e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="pw2">{T.passwortWiederholen}</Label>
                  <Input id="pw2" type="password" required minLength={6} value={wiederholung}
                         onChange={(e) => setWiederholung(e.target.value)} className="mt-1" />
                </div>
                <Button type="submit" disabled={busy}
                        className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                  {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                  {T.passwortSpeichern}
                </Button>
              </form>
            )}

            {lage === "kein-link" && (
              <>
                <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
                  <p className="font-medium text-foreground">{T.linkAbgelaufenTitel}</p>
                  <p className="mt-1 text-muted-foreground">{T.linkAbgelaufenText}</p>
                  {grund && (
                    <p className="mt-2 font-mono text-xs text-muted-foreground">{grund}</p>
                  )}
                </div>

                {neuAngefragt ? (
                  <div className="rounded-md border border-accent/40 bg-accent/10 p-3 text-sm">
                    <p className="font-medium text-foreground">{T.resetTitel}</p>
                    <p className="mt-1 text-muted-foreground">{T.resetText}</p>
                    <p className="mt-2 text-muted-foreground">{T.resetAusweg}</p>
                  </div>
                ) : (
                  <form onSubmit={neuenLink} className="space-y-3">
                    <div>
                      <Label htmlFor="email">{T.email}</Label>
                      <Input id="email" type="email" required value={email}
                             onChange={(e) => setEmail(e.target.value)} className="mt-1" />
                    </div>
                    <Button type="submit" disabled={busy}
                            className="w-full bg-[image:var(--gradient-primary)] border-0 hover:opacity-90">
                      {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                      {T.neuenLinkAnfordern}
                    </Button>
                  </form>
                )}
              </>
            )}

            <p className="text-center text-sm text-muted-foreground">
              <Link to="/auth" className="text-primary hover:underline">{T.zurueckZurAnmeldung}</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
