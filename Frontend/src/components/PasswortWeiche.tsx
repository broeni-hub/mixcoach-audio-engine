import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

import { supabase } from "@/integrations/supabase/client";
import { sollZurPasswortSeite } from "@/lib/auth-logik";
import { RESET_ZIEL } from "@/lib/auth-texte";

/**
 * Bringt einen Wiederherstellungs-Link auf die Passwort-Seite, egal wo er
 * ankommt.
 *
 * DER FALL, DEN ES ZU LOESEN GILT (23.09.2026)
 * -------------------------------------------
 * Der Link aus der Reset-Mail zeigt nicht direkt auf die App, sondern auf
 * `/auth/v1/verify` bei Supabase. Von dort geht es weiter an `redirect_to` -
 * ABER nur, wenn diese Adresse in der Redirect-Allowlist des Projekts steht.
 * Sonst nimmt Supabase still die SITE_URL. Und die SITE_URL ist die
 * Landingpage, nicht `/auth`.
 *
 * Genau das ist passiert: Klick auf den Link, Startseite, kein Weg zum neuen
 * Passwort. Die Weiche gab es, aber nur in `auth.tsx` - also an einer Route,
 * die der Link in diesem Fall nie erreicht.
 *
 * WARUM NICHT EINFACH DIE ALLOWLIST
 * ---------------------------------
 * Die gehoert trotzdem in Ordnung gebracht. Aber sie ist eine
 * Kontoeinstellung ausserhalb dieses Repos, und dieselbe Falle steht bei
 * jeder weiteren Adresse wieder auf - Produktion, Vorschau-Deploy, ein
 * anderer Port. Eine Weiche an der Wurzel kostet nichts und faengt alle.
 *
 * ZWEI WEGE, WEIL EINER NICHT REICHT
 * ----------------------------------
 * `detectSessionInUrl` steht auf der Vorgabe true. Der Supabase-Client liest
 * das Fragment beim Laden also selbst aus und raeumt es aus der Adresse -
 * unter Umstaenden, bevor dieser Effekt laeuft. Dann findet die Pruefung auf
 * `window.location.hash` nichts mehr. Deshalb zusaetzlich das Ereignis
 * PASSWORD_RECOVERY, das der Client in genau diesem Fall feuert. Derselbe
 * Doppelgriff wie in `auth.tsx`.
 *
 * Die Entscheidung selbst steht in `auth-logik.ts:sollZurPasswortSeite` -
 * eine Regel, zwei Aufrufer. Hier steht nur der Weg dorthin.
 */
export function PasswortWeiche() {
  const navigate = useNavigate();

  useEffect(() => {
    if (typeof window === "undefined") return;

    const hin = () => navigate({ to: RESET_ZIEL });

    if (sollZurPasswortSeite(window.location.pathname, window.location.hash)) {
      hin();
      return;
    }

    const { data: sub } = supabase.auth.onAuthStateChange((ereignis) => {
      if (ereignis === "PASSWORD_RECOVERY"
          && window.location.pathname !== RESET_ZIEL) {
        hin();
      }
    });
    return () => sub.subscription.unsubscribe();
  }, [navigate]);

  return null;
}
