# H1 — erst die Anmeldung klären, dann Bedingung 2

**Stand 17.08.2026.** Ziel: die letzte offene Bedingung der Live-Schwelle
vorführen. Vorher muss geklärt sein, warum die Anmeldung am 16.08. nicht ging —
sonst probierst du dasselbe noch einmal.

---

## Was wir schon wissen

- **Google kann lokal nicht funktionieren.** Gemessen am 16.08.: Der
  OAuth-Broker liegt unter `/~oauth/initiate` auf Lovables Hosting, der lokale
  Server kennt die Route nicht (404, während `/auth` 200 liefert). Daran ändert
  kein Code etwas. **Nimm den Google-Knopf nicht.**
- **Die Warteliste ist aus.** `VITE_WAITLIST_MODE` steht nicht in deiner
  `.env`, das Registrierungsformular ist also sichtbar. Das ist nicht der
  Blocker.
- **E-Mail und Passwort ist der einzige Weg, der lokal gehen kann.**

**Und eine Verwechslung, die dich sonst auf die falsche Fährte führt:** In den
Report-Dateien steht ein Feld `userId` (bei 51 von 52 `local-single-user`). Das
stammt aus der Besitzer-Migration, **nicht** aus der Anmeldung — die Engine
kennt gar keinen Nutzer. Bedingung 2 hängt allein an der `user_id` in der
Supabase-Tabelle, und die kommt vom angemeldeten Konto. Dass die Analyse von
gestern `null` trägt, ist erwartbar und kein Fehler.

---

## Schritt 1 · Der Test, der alles entscheidet — 5 Minuten

MixCoach starten, zur Anmeldeseite, **„Create your account"**, E-Mail und
Passwort eingeben, absenden.

Es gibt genau drei Ausgänge, und jeder bedeutet etwas anderes:

**A — Du landest direkt im Dashboard.**
E-Mail-Bestätigung ist im Projekt ausgeschaltet. Bedingung 2 ist zwanzig
Minuten entfernt. **Weiter bei Schritt 3.**

**B — Meldung „Account created — confirm the link in your email".**
Bestätigung ist an. **Weiter bei Schritt 2.**

**C — Eine Fehlermeldung.**
Die ist die Diagnose, bitte notieren. Häufige Fälle:
- *„Signups not allowed"* → Registrierung ist im Supabase-Projekt abgeschaltet.
- *„rate limit" / „too many requests"* → später erneut, der eingebaute
  Mailversand ist mengenbegrenzt.
- Etwas anderes → schick es mir, es steht so in der Meldung, dass es
  verwertbar ist.

---

## Schritt 2 · Wenn eine Bestätigungsmail nötig ist

Hier können **zwei** Dinge schiefgehen, und von außen sehen sie gleich aus —
es kommt nichts an.

**a) Die Mail kommt nicht.** Lovables eingebauter Versand ist auf wenige
Nachrichten pro Stunde begrenzt und nicht für den Produktivbetrieb gedacht.
Erst den Spam-Ordner prüfen, dann den Knopf „resend" auf der Anmeldeseite. Wenn
die Meldung „Too many emails for now" erscheint: eine Stunde warten.

**b) Die Mail kommt, aber der Link führt ins Leere — der wahrscheinlichere
Fall.** `auth.tsx:54` setzt

```
emailRedirectTo: window.location.origin      →   http://localhost:8080
```

Diese Adresse muss im Supabase-Projekt als erlaubte Redirect-URL eingetragen
sein, sonst bricht der Bestätigungslink ab. Nachsehen unter:

> Supabase-Projekt → **Authentication → URL Configuration → Redirect URLs**
> Dort muss `http://localhost:8080/**` stehen. Wenn nicht: eintragen,
> speichern, „resend" drücken.

**Wenn du dort nichts eintragen kannst, weil das Projekt Lovable gehört:**
Dann ist das derselbe Befund wie bei Google — die Anmeldung hängt an fremder
Infrastruktur, und zwar an der zweiten Stelle. Sag Bescheid und mach hier
Schluss; das ist dann kein Handgriff mehr, sondern ein eigener Auftrag, und es
gehört in die Planung von Teil 3.

---

## Schritt 3 · Bedingung 2 vorführen — 20 Minuten

Sobald du angemeldet bist:

1. **Ein Set analysieren.** Neu, nach der Anmeldung — nur dann bekommt die
   Supabase-Zeile deine `user_id`. Die Analyse von gestern Abend
   (`MixCoach2.WAV`) ist ohne Anmeldung entstanden und kommt vermutlich nicht
   mit; das ist kein Fehler.
2. **Prüfen, dass sie in der Analysen-Liste steht** und sich öffnen lässt.
3. **Browser-Profil wechseln** — in Chrome oben rechts aufs Profilbild, „Als
   Gast" oder ein zweites Profil. Ein anderer Browser tut es genauso.
4. **Dort mit demselben Konto anmelden.**

**Was du sehen solltest:** Die Analyse steht in der Liste. Nicht nur der Name —
öffne sie und prüf, ob die Übergänge, die Übung und die Beobachtungen da sind.

**Wenn sie fehlt:** Konsole öffnen (`Cmd + Alt + J`), nach einer Meldung
suchen, die mit `[mixcoach]` beginnt, und sie mir schicken. Sie ist seit dem
11.08. absichtlich so gebaut, dass sie die tatsächliche Ursache beim Namen
nennt statt allgemein zu warnen.

---

## Danach

Geht Schritt 3 durch, ist **die Live-Schwelle zum ersten Mal vollständig
erfüllt** — alle drei Bedingungen, jede vorgeführt statt behauptet. Sag
Bescheid, dann ziehe ich das Review nach und wir gehen an J7.

Scheitert es an Schritt 2b, ist das kein Rückschlag, sondern der zweite Beleg
für K6: Das Anmeldesystem gehört nicht dem Projekt. Dann gehört diese Frage
vor die Hosting-Planung, nicht dahinter.
