// Drei Sätze auf der Anmeldeseite haben etwas behauptet, das nicht
// stattgefunden hat. Diese Tests halten fest, dass sie es nicht wieder tun.
//
// Der Anlass, alles am 18.08.2026 gemessen:
//
//   1. Nach der Registrierung stand unbedingt "confirm the link in your
//      email". Am Projekt steht mailer_autoconfirm: true - die Mail kommt nie,
//      weil sie nicht nötig ist. Der Nutzer war drin und wartete trotzdem.
//   2. "Invalid login credentials" heißt auch "es gibt kein Konto". Sebastian
//      hat daran eine Stunde verloren.
//   3. Es gab überhaupt keinen Weg, ein Passwort zurückzusetzen - und der
//      Wiederherstellungslink hätte den Nutzer ins Dashboard geschoben, statt
//      ihn sein Passwort setzen zu lassen.

import { describe, it, expect } from "vitest";

import {
  lageNachRegistrierung,
  deuteAnmeldefehler,
  istWiederherstellung,
} from "../auth-logik";
import { TEXTE } from "../auth-texte";

describe("nach der Registrierung entscheidet die Antwort, nicht die Annahme", () => {
  it("mit Sitzung ist der Nutzer angemeldet - keine Wartemeldung", () => {
    expect(lageNachRegistrierung({ session: { access_token: "x" } })).toBe("angemeldet");
  });

  it("ohne Sitzung ist eine Bestaetigung noetig", () => {
    expect(lageNachRegistrierung({ session: null })).toBe("bestaetigung-noetig");
    expect(lageNachRegistrierung({})).toBe("bestaetigung-noetig");
    expect(lageNachRegistrierung(null)).toBe("bestaetigung-noetig");
  });
});

describe("eine abgelehnte Anmeldung wird gedeutet, nicht aufgeloest", () => {
  it("erkennt die zwei Moeglichkeiten und nennt sie beide", () => {
    expect(deuteAnmeldefehler("Invalid login credentials")).toBe("beide-wege");
    expect(deuteAnmeldefehler("invalid_credentials")).toBe("beide-wege");

    // Der Text muss beide Faelle nennen - sonst raet der Nutzer.
    for (const lang of ["de", "en"] as const) {
      const t = TEXTE[lang].anmeldungAbgelehnt.toLowerCase();
      expect(t).toMatch(/oder|or/);
      expect(t).toMatch(/konto|account/);
    }
  });

  it("verraet NICHT, welcher der beiden Faelle vorliegt", () => {
    // Wer das aufloest, baut eine Nutzer-Aufzaehlung ein: dann laesst sich
    // durchprobieren, wer hier ein Konto hat.
    for (const lang of ["de", "en"] as const) {
      const t = TEXTE[lang].anmeldungAbgelehnt;
      expect(t).not.toMatch(/kein Konto vorhanden|no such account|account does not exist/i);
      expect(t).not.toMatch(/Konto existiert nicht/i);
    }
  });

  it("erkennt das Ratenlimit des Mailversands", () => {
    // Der Wortlaut, den Supabase am 18.08.2026 wirklich geliefert hat.
    expect(deuteAnmeldefehler(
      "For security purposes, you can only request this after 59 seconds.",
    )).toBe("zu-viele-mails");
    expect(deuteAnmeldefehler("over_email_send_rate_limit")).toBe("zu-viele-mails");
  });

  it("erkennt die fehlende Bestaetigung", () => {
    expect(deuteAnmeldefehler("Email not confirmed")).toBe("nicht-bestaetigt");
  });

  it("laesst Unbekanntes unbekannt, statt es zu raten", () => {
    expect(deuteAnmeldefehler("Failed to fetch")).toBe("unbekannt");
    expect(deuteAnmeldefehler("")).toBe("unbekannt");
  });
});

describe("der Wiederherstellungslink darf nicht ins Dashboard fuehren", () => {
  it("erkennt das Fragment aus der E-Mail", () => {
    expect(istWiederherstellung("#access_token=abc&type=recovery")).toBe(true);
    expect(istWiederherstellung("#type=recovery&expires_in=3600")).toBe(true);
  });

  it("haelt eine gewoehnliche Anmeldung davon getrennt", () => {
    expect(istWiederherstellung("")).toBe(false);
    expect(istWiederherstellung("#access_token=abc&type=signup")).toBe(false);
    expect(istWiederherstellung("#type=recovery_alt")).toBe(false);
  });
});

describe("die Ehrlichkeitslinie gilt auch an der Oberflaeche", () => {
  it("behauptet nach dem Zuruecksetzen NICHT, eine Mail sei gesendet worden", () => {
    // Ob eine Mail hinausgeht, weiss der Browser nicht - Supabase antwortet
    // absichtlich immer gleich (am 18.08.2026 gemessen: HTTP 200, leerer
    // Koerper, fuer existierende wie erfundene Adresse). "Gesendet" waere
    // derselbe Verstoss wie eine erfundene Messzahl, nur an der Oberflaeche.
    expect(TEXTE.de.resetTitel).not.toMatch(/gesendet|verschickt/i);
    expect(TEXTE.en.resetTitel).not.toMatch(/\bsent\b/i);
    // Stattdessen: die Bedingung steht drin.
    expect(TEXTE.de.resetText).toMatch(/falls/i);
    expect(TEXTE.en.resetText).toMatch(/\bif\b/i);
  });

  it("nennt den Ausweg samt gemessenem Grund, wenn nichts ankommt", () => {
    expect(TEXTE.de.resetAusweg).toMatch(/mengenbegrenzt|pro Minute/i);
    expect(TEXTE.en.resetAusweg).toMatch(/rate-limited|per minute/i);
  });

  it("haelt beide Sprachen vollstaendig", () => {
    const de = Object.keys(TEXTE.de).sort();
    const en = Object.keys(TEXTE.en).sort();
    expect(en).toEqual(de);
    for (const k of de) {
      expect((TEXTE.de as Record<string, string>)[k].length, `de.${k} leer`).toBeGreaterThan(0);
      expect((TEXTE.en as Record<string, string>)[k].length, `en.${k} leer`).toBeGreaterThan(0);
    }
  });
});
