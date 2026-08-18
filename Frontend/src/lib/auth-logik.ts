// Die drei Entscheidungen der Anmeldeseite - als Regeln, nicht als if-Kette
// mitten in einer Komponente.
//
// Warum getrennt: In diesem Projekt gibt es kein jsdom, Komponenten sind also
// nicht prüfbar. Genau diese drei Stellen haben aber am 18.08.2026 Zeit
// gekostet, und eine Regel ohne Test ist hier eine Regel auf Zeit. Als reine
// Funktionen sind sie prüfbar wie scoring-version.ts.

/** Was nach einer erfolgreichen Registrierung wirklich gilt. */
export type Registrierungslage = "angemeldet" | "bestaetigung-noetig";

/**
 * Die ANTWORT lesen, nicht die Servereinstellung annehmen.
 *
 * Bis zum 18.08.2026 stand in auth.tsx unbedingt `setAwaitingConfirm(true)`
 * samt „confirm the link in your email". Am Projekt steht aber
 * `mailer_autoconfirm: true` (an /auth/v1/settings nachgemessen) - dann
 * liefert signUp sofort eine Sitzung, der Nutzer ist drin und liest trotzdem,
 * er solle warten. Auf eine Mail, die nie kommt, weil sie nicht nötig ist.
 *
 * Am Vorhandensein der Sitzung entschieden, ist der Text in BEIDEN
 * Einstellungen richtig - und niemand muss eine Konstante pflegen, die mit dem
 * Server auseinanderlaufen kann.
 */
export function lageNachRegistrierung(
  antwort: { session?: unknown } | null | undefined,
): Registrierungslage {
  return antwort?.session ? "angemeldet" : "bestaetigung-noetig";
}

/** Wie eine abgelehnte Anmeldung zu deuten ist. */
export type Anmeldefehler =
  | "nicht-bestaetigt"
  | "zu-viele-mails"
  | "beide-wege"
  | "unbekannt";

/**
 * `beide-wege` ist der Fall, der am 18.08.2026 eine Stunde gekostet hat:
 * „Invalid login credentials" heißt entweder falsches Passwort ODER es gibt
 * kein Konto. Sebastian hielt es für einen Tippfehler; es gab schlicht kein
 * Konto.
 *
 * Aufgelöst wird das NICHT. Supabase verschweigt den Unterschied absichtlich -
 * wer ihn sichtbar macht, baut eine Nutzer-Aufzählung ein: Dann lässt sich
 * durchprobieren, wer hier ein Konto hat. Die Oberfläche bietet stattdessen
 * beide Auswege an.
 */
export function deuteAnmeldefehler(meldung: string): Anmeldefehler {
  const m = meldung ?? "";
  // Zuerst das Ratenlimit: seine Meldung ("...you can only request this after
  // 59 seconds") enthält keines der anderen Stichwörter, aber die Reihenfolge
  // festzuhalten ist billiger als sie später zu suchen.
  if (/rate|limit|too many|after \d+ seconds?/i.test(m)) return "zu-viele-mails";
  if (/not confirmed|confirm/i.test(m)) return "nicht-bestaetigt";
  if (/invalid login credentials|invalid_credentials/i.test(m)) return "beide-wege";
  return "unbekannt";
}

/**
 * Trägt die Adresse ein Wiederherstellungs-Fragment?
 *
 * Der Link aus der E-Mail bringt eine Sitzung mit. Ohne diese Weiche schiebt
 * auth.tsx den Nutzer ins Dashboard („Sitzung da -> weiter"), statt ihn sein
 * Passwort setzen zu lassen. Der Fall tritt auf, wenn die Zieladresse nicht in
 * der Redirect-Allowlist des Supabase-Projekts steht und der Link auf die
 * SITE_URL zurückfällt.
 */
export function istWiederherstellung(hash: string): boolean {
  return /(^|[#&])type=recovery(&|$)/.test(hash ?? "");
}
