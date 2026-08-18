# Arbeitsauftrag — die Anmeldung fertig machen

**Für Claude Code · erstellt 18.08.2026 · Sebastian ist nicht da**

Lies zuerst `CLAUDE.md`, dann `SITZUNG_2026-08-14.md` den Abschnitt zum
Nachweis vom 18.08. (dort stehen die vier Befunde, die diesen Auftrag auslösen).

---

## Worum es geht

Die Live-Schwelle ist seit heute erfüllt — Bedingung 2 ist vorgeführt
(`f46c0b1`). Das Tor führt zur **geschlossenen Beta**, und die trifft zum
ersten Mal Menschen, die nicht Sebastian sind.

Genau dort ist die Anmeldung der schwächste Teil des Produkts. Der Nachweis
von heute hat drei Löcher freigelegt, die alle denselben Menschen treffen — den
ersten fremden Tester:

1. **Es gibt keinen Weg, ein Passwort zurückzusetzen.** Wer sich vertippt, ist
   über die Oberfläche dauerhaft ausgesperrt.
2. **Nach der Registrierung verspricht `auth.tsx:65` eine Bestätigungsmail**
   („confirm the link in your email to sign in"). Am Server steht aber
   `mailer_autoconfirm: true` — die Mail kommt nie, weil sie nicht nötig ist.
   Der Satz schickt jeden neuen Nutzer in eine Wartestellung, die es nicht gibt.
3. **„Invalid login credentials" ist nicht unterscheidbar von „es gibt kein
   Konto".** Genau daran hat Sebastian heute eine Stunde verloren: Er hielt es
   für einen Tippfehler, und es gab schlicht kein Konto.

**Das ist kein Komfort-Thema.** Punkt 3 (Coach) ist bis zum zweiten Rater
blockiert, die Schwelle ist erfüllt — die Anmeldung ist gerade der kleinste
Schritt mit der größten Wirkung.

---

## Weil niemand da ist

Keine Checkpoints. **Anhalten, committen was fertig ist, im Bericht begründen**,
wenn: Tests rot werden und die Ursache nicht in deiner Änderung liegt · du
einen Zugang oder eine Inhaltsentscheidung bräuchtest · sich zeigt, dass eine
der Aufgaben aus J1 gar nicht lokal funktionieren **kann** (siehe J0).

**Ausdrücklich freigegeben:** `Frontend/src/routes/auth.tsx` und eine neue
Route für das Setzen des neuen Passworts. Die Regel „bestehende Frontend-Seiten
nicht verändern" ist für diesen Auftrag aufgehoben — die Seite **ist** der
Gegenstand. Alles andere bleibt unberührt.

---

## J0 · Erst messen, dann bauen — die Frage, die alles entscheidet

**Ein Passwort-Reset läuft über eine E-Mail. Und dieses Projekt hat mit
E-Mail eine Geschichte.** Bevor du einen Ablauf baust, der auf einer Mail
aufsetzt, klär, ob sie überhaupt herauskommt:

- Was sagt `/auth/v1/settings` des Projekts (mit `apikey`-Header) zu
  `mailer_autoconfirm`, `external_email_enabled`, `disable_signup`? Der Wert
  `mailer_autoconfirm: true` ist aus dem Bericht übernommen — **prüf ihn
  selbst**, er bestimmt J2.
- Nimmt `supabase.auth.resetPasswordForEmail()` den Aufruf an, und mit welcher
  Antwort? Nutz dafür das Konto, das du heute für den Nachweis angelegt hast.
- **Was du nicht messen kannst, sagst du:** ob die Mail tatsächlich in einem
  Postfach ankommt, kann hier niemand prüfen. Bau den Ablauf deshalb so, dass
  er **ehrlich zerfällt**, statt den Nutzer hängen zu lassen — siehe J1.
- Der Redirect ist dieselbe Falle wie bei der Registrierung: `auth.tsx:54`
  setzt `emailRedirectTo: window.location.origin`, also
  `http://localhost:8080`. Steht die Adresse nicht in den erlaubten
  Redirect-URLs des Projekts, führt auch der Reset-Link ins Leere. Sag im
  Bericht, ob du das prüfen konntest.

**Ergibt J0, dass Mails aus diesem Projekt lokal grundsätzlich nicht
hinausgehen**, dann ist J1 nicht baubar wie gedacht. Melde das als Befund,
bau J2 und J3 trotzdem (die brauchen keine Mail), und schlag für J1 den
Ausweg vor, statt ihn zu wählen.

---

## J1 · Passwort zurücksetzen

Zwei Hälften, beide nötig:

**a) Anfordern.** Auf der Anmeldeseite ein „Passwort vergessen?" neben dem
Passwortfeld. `resetPasswordForEmail(email, { redirectTo: … })`.

**b) Neu setzen.** Eine Route, auf der der Link landet, mit
`supabase.auth.updateUser({ password })`. Der Supabase-Client liest die Sitzung
aus der URL (`detectSessionInUrl` ist Vorgabe) — prüf, dass das hier greift,
und verlass dich nicht darauf, weil es beim Google-Versuch am 16.08. genau
daran gescheitert ist.

**Die Meldung muss ehrlich sein — und das ist hier heikel:**

- Supabase antwortet auf `resetPasswordForEmail` **immer** freundlich, auch
  wenn es die Adresse nicht gibt. Das ist Absicht und richtig; verrate nicht,
  ob ein Konto existiert.
- Der Nutzer darf trotzdem nicht raten müssen. Also: sag, was passiert *wenn*
  es das Konto gibt, nenn die Wartezeit, und nenn den Ausweg, wenn nichts
  ankommt — inklusive des heute gemessenen Grundes (der eingebaute Mailversand
  ist mengenbegrenzt und nicht für den Produktivbetrieb gedacht).
- **Kein „E-Mail gesendet", wenn du nicht weißt, ob sie gesendet wurde.** Das
  ist derselbe Verstoß wie eine erfundene Messzahl, nur an der Oberfläche.

---

## J2 · Die Bestätigungsmail, die es nicht gibt

`auth.tsx:64-65` setzt nach jeder Registrierung unbedingt
`awaitingConfirm = true` und meldet *„Account created — confirm the link in
your email to sign in."*

Bei `mailer_autoconfirm: true` liefert `signUp` aber **sofort eine Sitzung**.
Der Nutzer ist drin — und liest, dass er warten soll.

**Richtig ist, die Antwort zu lesen statt sie anzunehmen:** Enthält das
Ergebnis von `signUp` eine Session, ist der Nutzer angemeldet → weiterleiten,
keine Wartemeldung. Kommt keine Session, ist eine Bestätigung nötig → dann
gilt der heutige Text, samt „resend". So ist die Meldung in beiden
Server-Einstellungen richtig, ohne dass jemand eine Konstante pflegen muss.

---

## J3 · „Invalid login credentials" — ehrlich, ohne ein Loch aufzureißen

Der Satz kann zweierlei heißen: falsches Passwort **oder** kein Konto. Sebastian
hat heute daran eine Stunde verloren.

**Nicht** auflösen, welcher Fall vorliegt — Supabase verschweigt das
absichtlich, damit niemand fremde Adressen durchprobieren kann. Wer das
„behebt", baut eine Nutzer-Aufzählung ein.

**Stattdessen beide Auswege anbieten**, direkt in der Meldung oder darunter:
„Passwort falsch — oder es gibt zu dieser Adresse noch kein Konto." mit einem
Weg zu **Registrieren** und einem zu **Passwort zurücksetzen**. Der Nutzer
kommt in beiden Fällen weiter, ohne dass die App etwas preisgibt.

---

## J4 · Vorführen, nicht nur testen

**Das ist in diesem Projekt dreimal in zehn Tagen die teuerste Lücke gewesen** —
zuletzt gestern, als die J7-Seite leer blieb, obwohl zehn Tests grün waren und
die Aufgaben serverseitig korrekt gebaut wurden.

Durchlaufen, mit Beleg im Bericht:

1. **Registrierung** mit einer neuen Adresse → landet der Nutzer im Dashboard,
   ohne Wartemeldung? (Erwartung bei `autoconfirm: true`.)
2. **Anmeldung mit falschem Passwort** → nennt die Meldung beide Möglichkeiten
   und bietet beide Auswege?
3. **Passwort vergessen** → wird der Aufruf angenommen, und sagt die Seite
   ehrlich, was jetzt passiert und was zu tun ist, wenn nichts kommt?
4. **Neues Passwort setzen** → soweit ohne Postfach prüfbar. Wo du an die Grenze
   kommst, schreib hin, was Sebastian morgen selbst prüfen muss — als kurze
   Liste, nicht als Fließtext.

---

## J5 · Bericht

Nachtrag in `SITZUNG_2026-08-14.md`, keine neue Datei: was gemessen wurde, was
gebaut, was offen blieb, und was Sebastian selbst prüfen muss.

---

## Was nicht dazugehört

- **Kein F2** (Nutzerbegriff in der Engine), kein Hosting, keine Bezahlschranke.
- **Kein zweiter Anlauf auf B5** (`notMeasured` dynamisch) — der steht als
  eigene Aufgabe an und hat heute schon einmal die Engine lahmgelegt.
- **Keine Coach-Änderungen.** J7 ist gelaufen und sagt unentschieden (13:7,
  p = 0,263); bis zum zweiten Rater wird auf den Übungen nichts aufgebaut.
- **Nichts an Google.** Der Broker liegt auf Lovables Hosting und kann lokal
  nicht funktionieren — gemessen am 16.08., zweimal.
- **Keine Änderung an Erkennung, Modell, Betriebspunkt oder
  `app/audio/scoring/*`.** Dieser Auftrag verschiebt keine Messzahl.

## Abnahme

1. Ein ausgesperrter Nutzer kommt über die Oberfläche wieder hinein — oder die
   Seite sagt ihm ehrlich, warum nicht und was stattdessen zu tun ist.
2. Keine Meldung behauptet etwas, das nicht stattgefunden hat.
3. Die vier Läufe aus J4 sind durchlaufen und belegt.
4. **289 Backend-Tests und die Frontend-Tests grün**, plus neue für die drei
   Fälle. `tsc` bleibt bei 0 Fehlern.
5. Die Warteliste (`WAITLIST_MODE`, `INVITE_KEY`) funktioniert unverändert.
6. Nach jedem Block ein eigener Commit, am Ende gepusht.
