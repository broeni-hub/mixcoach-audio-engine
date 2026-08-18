// Texte der Anmeldeseite, DE/EN - nach dem Muster der uebrigen Komponenten
// (kleine Woerterbuecher direkt beim Gegenstand, siehe lib/i18n.tsx).
//
// Warum sie hier stehen und nicht in auth.tsx: Diese Saetze sind der
// Gegenstand des Auftrags vom 18.08.2026, nicht Beiwerk. Drei von ihnen haben
// vorher etwas behauptet, das nicht stattgefunden hat - und jede dieser
// Behauptungen hat jemanden Zeit gekostet:
//
//   "confirm the link in your email"  Bei mailer_autoconfirm=true kommt diese
//                                     Mail nie. Der Nutzer war laengst drin
//                                     und wartete trotzdem.
//   "Invalid login credentials"       Heisst auch "es gibt kein Konto". Kostete
//                                     am 18.08. eine Stunde Fehlersuche.
//   (fehlte ganz)                     Kein Weg, ein Passwort zurueckzusetzen.
//
// Die Ehrlichkeitslinie gilt an der Oberflaeche genauso wie bei den Messwerten:
// nichts anzeigen, was nicht stattgefunden hat.

/** Wohin der Wiederherstellungslink zeigen soll. Eine Stelle, zwei Nutzer:
 *  auth.tsx beim Anfordern, die Route selbst beim Einloesen. */
export const RESET_ZIEL = "/passwort-neu";

export const TEXTE = {
  de: {
    willkommen: "Willkommen zurück",
    kontoAnlegen: "Konto anlegen",
    passwortNeuSetzen: "Passwort zurücksetzen",
    mitGoogle: "Weiter mit Google",
    oder: "oder",
    anzeigename: "Anzeigename",
    email: "E-Mail",
    passwort: "Passwort",
    neuesPasswort: "Neues Passwort",
    anmelden: "Anmelden",
    linkAnfordern: "Link anfordern",
    passwortSpeichern: "Passwort speichern",
    passwortVergessen: "Passwort vergessen?",
    zurueckZurAnmeldung: "Zurück zur Anmeldung",
    neuHier: "Neu bei MixCoach?",
    schonKonto: "Schon ein Konto?",

    kontoAngelegtDrin: "Konto angelegt — du bist angemeldet.",
    kontoAngelegtBestaetigen:
      "Konto angelegt. Bestätige den Link in deiner E-Mail, um dich anzumelden.",
    nichtBestaetigt:
      "E-Mail noch nicht bestätigt. Schau in dein Postfach — oder lass den Link unten erneut schicken.",
    zuVieleMails:
      "Zu viele E-Mails in kurzer Zeit. Der eingebaute Mailversand erlaubt nur eine Anfrage pro Minute — warte kurz und versuch es noch einmal.",
    anmeldungAbgelehnt:
      "Passwort falsch — oder es gibt zu dieser Adresse noch kein Konto.",

    beideWegeTitel: "Zwei Möglichkeiten, und die App weiß nicht, welche zutrifft:",
    beideWegeErklaerung:
      "Entweder stimmt das Passwort nicht, oder zu dieser Adresse existiert noch kein Konto. Welches von beidem, sagt der Anmeldedienst absichtlich nicht — sonst könnte jemand durchprobieren, wer hier ein Konto hat.",

    wartenTitel: "Warten auf den Bestätigungslink.",
    wartenText: "Er kann ein paar Minuten brauchen und landet manchmal im Spam.",
    erneutSenden: "Bestätigungs-E-Mail erneut senden",
    erneutGesendet: "Bestätigungs-E-Mail erneut angefordert.",

    // Bewusst NICHT "E-Mail gesendet": ob eine Mail hinausgeht, weiss der
    // Browser nicht. Angenommen wurde der Auftrag - mehr ist nicht belegt.
    resetTitel: "Anfrage ist raus.",
    resetText:
      "Falls es zu dieser Adresse ein Konto gibt, ist eine E-Mail mit einem Link unterwegs. Sie kann ein paar Minuten brauchen und landet manchmal im Spam.",
    resetAusweg:
      "Kommt nichts an: Der eingebaute Mailversand ist mengenbegrenzt (eine Anfrage pro Minute) und nicht für den Dauerbetrieb gedacht. Warte ein paar Minuten und fordere den Link erneut an — oder leg dir mit einer anderen Adresse ein neues Konto an.",

    linkAbgelaufenTitel: "Dieser Link führt nicht weiter.",
    linkAbgelaufenText:
      "Er ist abgelaufen, wurde schon benutzt, oder die Adresse wurde ohne den Link von der E-Mail aus geöffnet. Fordere unten einen neuen an.",
    passwortZuKurz: "Das Passwort braucht mindestens 6 Zeichen.",
    passwortUngleich: "Die beiden Eingaben stimmen nicht überein.",
    passwortGesetzt: "Neues Passwort gespeichert — du bist angemeldet.",
    passwortWiederholen: "Neues Passwort wiederholen",
    neuenLinkAnfordern: "Neuen Link anfordern",
  },
  en: {
    willkommen: "Welcome back",
    kontoAnlegen: "Create your account",
    passwortNeuSetzen: "Reset your password",
    mitGoogle: "Continue with Google",
    oder: "or",
    anzeigename: "Display name",
    email: "Email",
    passwort: "Password",
    neuesPasswort: "New password",
    anmelden: "Sign in",
    linkAnfordern: "Send the link",
    passwortSpeichern: "Save password",
    passwortVergessen: "Forgot your password?",
    zurueckZurAnmeldung: "Back to sign in",
    neuHier: "New to MixCoach?",
    schonKonto: "Already have an account?",

    kontoAngelegtDrin: "Account created — you're signed in.",
    kontoAngelegtBestaetigen:
      "Account created. Confirm the link in your email to sign in.",
    nichtBestaetigt:
      "Email not confirmed yet. Check your inbox — or resend the link below.",
    zuVieleMails:
      "Too many emails in a short time. The built-in mail service allows one request per minute — wait a moment and try again.",
    anmeldungAbgelehnt:
      "Wrong password — or there's no account for this address yet.",

    beideWegeTitel: "Two possibilities, and the app can't tell which one it is:",
    beideWegeErklaerung:
      "Either the password is wrong, or no account exists for this address. The sign-in service deliberately won't say which — otherwise someone could probe who has an account here.",

    wartenTitel: "Waiting for the confirmation link.",
    wartenText: "It can take a few minutes, and it sometimes lands in spam.",
    erneutSenden: "Send the confirmation email again",
    erneutGesendet: "Confirmation email requested again.",

    resetTitel: "Request submitted.",
    resetText:
      "If an account exists for this address, an email with a link is on its way. It can take a few minutes, and it sometimes lands in spam.",
    resetAusweg:
      "If nothing arrives: the built-in mail service is rate-limited (one request per minute) and isn't meant for sustained use. Wait a few minutes and request the link again — or create a new account with a different address.",

    linkAbgelaufenTitel: "This link doesn't lead anywhere.",
    linkAbgelaufenText:
      "It has expired, was already used, or this page was opened without following the link from the email. Request a new one below.",
    passwortZuKurz: "The password needs at least 6 characters.",
    passwortUngleich: "The two entries don't match.",
    passwortGesetzt: "New password saved — you're signed in.",
    passwortWiederholen: "Repeat new password",
    neuenLinkAnfordern: "Request a new link",
  },
} as const;
