# Migration auf eigenes Supabase — Plan

Stand 24.09.2026. Anlass: Lovable hat bestätigt, dass es **keine Übergabe**
gibt. Cloud und ein eigenes Supabase-Konto sind getrennte Welten, und einmal
aktiviertes Cloud lässt sich für dieses Projekt nicht mehr entfernen.

Alles unten ist am Repo nachgemessen, nicht geschätzt. Was ich rate, steht
als „geschätzt" dabei.

---

## 0 · Die Entscheidung, die vor dem Plan kommt

Beim Nachmessen kam etwas heraus, das die Sache größer macht als „Datenbank
umziehen":

**Die bei Lovable veröffentlichte App kann der Migration nicht folgen.**
Sie wird von Lovable gebaut, mit Lovables Umgebungsvariablen. `Frontend/.env`
zu ändern betrifft nur den lokalen Lauf. Lovable nennt als Weg zu eigenem
Supabase ausdrücklich „ein neues Projekt oder einen Remix" — also nicht
dieses.

Damit gibt es zwei Formen:

| | Was passiert | Ergebnis |
|---|---|---|
| **A · Remix bei Lovable** | neues Lovable-Projekt, an eigenes Supabase gebunden | Hosting bleibt bei Lovable, Google-Broker unklar |
| **B · Ganz weg von Lovable** | eigenes Supabase + eigenes Hosting für das Frontend | volle Kontrolle, eine Abhängigkeit weniger |

**Empfehlung: B** — aus einem Grund, der nichts mit Lovable zu tun hat:
**Die Engine muss ohnehin gehostet werden** (Wochen 3–4 der Roadmap; heute
gibt es kein Dockerfile und keinen Host, sie läuft nur auf `127.0.0.1:8000`).
Wer schon Infrastruktur aufsetzt, setzt das Frontend mit auf. Das Repo ist
eine gewöhnliche Vite/TanStack-Anwendung; jeder Static-Host trägt sie.

**A ist nicht falsch**, wenn du bei Lovable weiterentwickeln willst. Dann
aber getrennt entscheiden, und dieser Plan gilt nur für den Datenbank-Teil.

### Nachgemessen am 24.09.2026: B ist beim Frontend fast umsonst

Die Sorge war, dass die Build-Kette an Lovable hängt — `vite.config.ts`
besteht aus genau einer Zeile: `@lovable.dev/vite-tanstack-config`. Das ist
aber ein **veröffentlichtes npm-Paket, kein Dienst**.

`npm run build` läuft hier durch, Exit 0, ohne jede Verbindung zu Lovable.
Und was dabei herauskommt, ist bereits ein fertiges Deployment:

```
.output/public    2,0 MB     statische Dateien
.output/server    4,9 MB     Nitro-Worker
.output/server/wrangler.json           ← Cloudflare-Worker, Name gesetzt
[nitro] You can deploy this build using npx nitro deploy --prebuilt
```

Das Frontend selbst zu hosten heißt also: **denselben Befehl laufen lassen
und das Ergebnis hochladen.** Kein Umbau der Build-Kette. Die beiden
Lovable-Pakete bleiben gewöhnliche Abhängigkeiten.

---

## 1 · Was umzieht — und was nicht

| | in der Cloud | kommt mit |
|---|---|---|
| Schema: 16 Tabellen, 22 Policies, 12 Trigger, 11 Indizes, 3 Funktionen | ✓ | **14 Migrationen im Repo** |
| Saatdaten (`coaching_rules`, `exercises`) | ✓ | in 3 der Migrationen als `INSERT` |
| 60 Analysen | ✓ | **aus der Engine** — der Import ist erprobt |
| 45 Korrekturen (Ground Truth) | — | lagen **nie** in der Cloud |
| 6113 Fingerprints, Library | — | lagen **nie** in der Cloud |
| `profiles`: XP, Level, Streak, Genres | ✓ | **nein** — neu, oder aus dem Export nachtragen |
| `coach_feedback`, `feedback_ratings`, `beta_feedback` | ✓ | nur über den Export |
| **Auth-Konten** | ✓ | **doch** — siehe Korrektur unten |

**Nicht genutzt und deshalb egal:** `coaching_rules` und `user_rule_overrides`
kommen im Anwendungscode gar nicht vor — nur in der generierten `types.ts`.
Sie ziehen als leeres Schema mit.

**Betroffene Konten heute: eins.** Fabi und der zweite DJ haben Seiten per
Mail bekommen und die App nie benutzt.

### Korrektur vom 24.09.2026: Konten sind migrierbar

In diesem Plan stand zuerst, Auth-Konten könnten nicht mitkommen, weil
Supabase keine Passwort-Hashes exportiert. **Das gilt für den Nutzer-Export
im Dashboard (CSV) — nicht für den vollständigen Export.**

Nachgesehen im tatsächlichen Lovable-Export
(`mixcoach-ai-mentor_260924.backup`, PostgreSQL custom dump, 859 KB):

```
Schema-Einträge    auth 289 · public 178 · storage 89
TABLE DATA         55 Einträge, darunter COPY auth.users
encrypted_password kommt vor
```

Der Dump enthält also das komplette `auth`-Schema samt Nutzerzeilen **mit
Passwort-Hashes**. Ein Konto hätte mitkommen können.

**Für heute ist das folgenlos** — es ging um ein Konto, und es ist längst neu
angelegt. **Für später ist es wichtig:** Wenn irgendwann echte Nutzer in der
Datenbank sitzen, ist ein Umzug keine Zumutung mehr. Der Plan war an dieser
Stelle zu pessimistisch.

**Zwei Vorbehalte, die bleiben.** Das `auth`-Schema gehört Supabase; eine
Rückspielung dorthin ist heikler als eine gewöhnliche Tabelle und nicht
erprobt. Und um den Dump überhaupt zu lesen, braucht es `pg_restore` — auf
diesem Mac ist weder das noch Homebrew vorhanden.

**Die Datei gehört NICHT ins Repo.** Sie enthält Passwort-Hashes des alten
Projekts. Außerhalb aufbewahren, nicht committen.

---

## 2 · Die Reihenfolge

### Schritt 1 — Eigenes Projekt · du · ~10 min

supabase.com → Konto anlegen → **New project**.
**Region Frankfurt (eu-central-1)** wählen — die Nutzer laden Audio hoch, und
die DSGVO-Frage kommt in Woche 7 sowieso.

Danach brauche ich von dir: Projekt-URL und den **Publishable Key** (der
öffentliche, nicht der Service-Role-Key).

### Schritt 2 — Schema anlegen · ich bereite vor, du klickst · ~15 min

Die 14 Migrationen laufen in Dateinamen-Reihenfolge. Ein Befehl legt sie in
die Zwischenablage, ohne eine zweite Kopie auf der Platte zu erzeugen:

```bash
cat Frontend/supabase/migrations/*.sql | pbcopy
```

Dann im Dashboard: **SQL Editor** → einfügen → **Run**.

Läuft es durch, stehen 16 Tabellen mit Policies, Triggern und Saatdaten.

**Was am 24.09.2026 geprüft ist — und was nicht.** Auf diesem Mac gibt es
kein Postgres, der echte Lauf ist also erst Schritt 2 selbst. Geprüft habe
ich stattdessen den Inhalt:

- **Reihenfolge: sauber.** Keine Datei benutzt eine Tabelle oder einen Typ,
  der erst später entsteht (16 Tabellen, 3 Typen, 0 Fundstellen).
- **Selbsttragend.** Alle drei Trigger-Funktionen (`handle_new_user`,
  `update_updated_at_column`, `log_user_rule_override_change`) werden in den
  Migrationen selbst angelegt.
- **Keine Sonderwünsche.** Kein `CREATE EXTENSION`, kein `CREATE SCHEMA`,
  kein `OWNER TO`, kein Zugriff auf `storage.`. Benutzt werden nur Dinge,
  die jedes Supabase-Projekt mitbringt: `auth.users`, `auth.uid()`,
  `gen_random_uuid()`, die Rollen `authenticated` und `service_role`.

Das Risiko ist damit klein, aber nicht null — eine statische Prüfung ist
kein Lauf. Bricht es ab, schick mir die Fehlermeldung.

### Schritt 3 — Export als Sicherheitsnetz · du · ~5 min

Im Lovable-Projekt: **Cloud → Advanced settings → Export data**.

Nicht, weil wir ihn brauchen — die 60 Analysen kommen aus der Engine. Sondern
für `profiles` und die Bewertungen, falls du sie nachtragen willst. **Vor dem
nächsten Schritt machen**, nicht danach.

### Schritt 4 — Die App umhängen · ich · ~2 min

Zwei Werte in `Frontend/.env`: `VITE_SUPABASE_URL` und
`VITE_SUPABASE_PUBLISHABLE_KEY`. Mehr ist es lokal nicht.

**Und danach den Dev-Server NEU STARTEN.** Vite liest `.env` beim Start.
Am 24.09.2026 habe ich das vergessen: die App lief weiter gegen das alte
Projekt, Sebastian registrierte sich dort, und der Fehler sah aus wie ein
kaputter Token (`PGRST301 - No suitable key was found to decode the JWT`).
Zehn Minuten Umweg für einen Neustart.

Gegenprobe, die ich stattdessen hätte machen sollen — sie zeigt, worauf die
laufende App wirklich zeigt:

```js
await fetch("/src/integrations/supabase/client.ts").then(r => r.text())
```

### Schritt 5 — Anmeldung einrichten · du · ~20 min

**Achtung, hier lauert ein bekannter Fallstrick:** Das jetzige Projekt hat
`mailer_autoconfirm: true` — Konten sind sofort aktiv, es geht keine Mail
raus. **Ein frisches Supabase-Projekt hat Mail-Bestätigung standardmäßig AN.**
Ohne SMTP kommt die Bestätigungsmail nie, und du kommst nicht rein — genau
die Sackgasse von gestern, nur andersherum.

Zwei Wege, einer reicht:

- **Schnell:** Authentication → Sign In / Providers → *Confirm email* **aus**
- **Richtig:** Authentication → Emails → **SMTP** hinterlegen (eigener
  Mailanbieter). Brauchst du in Woche 5 ohnehin für den Passwort-Reset.

Dazu gleich mit erledigen, was du beim alten Projekt nicht konntest:

- **URL Configuration → Redirect URLs:** `http://localhost:8080/**`
- **Site URL** auf die spätere echte Domain

### Schritt 6 — Konto anlegen und Daten zurückholen · du + ich · ~10 min

Registrieren (ein Konto), dann in der App auf **Analysen** — dort holt
„Auf dem Analyse-Server gefunden" die 60 Reports aus der laufenden Engine.
Erprobt: genau so ist der Bestand am 23. und 24.09. zweimal in einen leeren
Browser gekommen.

### Schritt 7 — Google neu bauen · später, eigener Termin

Der Knopf läuft heute über Lovables Broker
(`lovable.auth.signInWithOAuth`), und Lovable behält die OAuth-Anwendung bei
sich. Nach der Migration braucht er:

- eine eigene OAuth-Anwendung in der Google Cloud Console
- Client-ID und Secret in Supabase unter Authentication → Providers → Google
- im Code `supabase.auth.signInWithOAuth` statt des Lovable-Wrappers
- `src/integrations/lovable/index.ts` fällt weg

**Das ist der eigentliche Aufwand der Migration** — nicht die Datenbank.
*Geschätzt ein halber Tag.* Kann warten: E-Mail-Anmeldung funktioniert
sofort.

### Schritt 8 — Lovable-Reste entscheiden · später

`ai.gateway.lovable.dev` hängt an genau einer Stelle:
`coach-feedback.functions.ts`, dem LLM-Coach. Das ist ohnehin eine offene
Entscheidung — mitentscheiden, nicht nebenbei migrieren.

Das Fehler-Reporting (`lovable-error-reporting.ts`) ist folgenlos.

---

## 3 · Was dabei kaputtgeht — vollständig

- **Das Konto.** Einmal neu registrieren — *der bequeme Weg. Mitnehmen wäre
  über den vollständigen Dump möglich gewesen, siehe Korrektur oben.*
- **XP, Level, Streak, Genres** aus `profiles`. Kosmetik, aus dem Export
  nachtragbar.
- **Deine Beta-Bewertungen** („War dieses Feedback nützlich?"). Nur im Export.
- **Google-Anmeldung**, bis Schritt 7 gemacht ist.
- **Die bei Lovable veröffentlichte App** zeigt weiter auf die alte
  Datenbank. Siehe Abschnitt 0.

**Was NICHT kaputtgeht:** Analysen, Korrekturen, Ground Truth, Library,
Modell, Reports. Das alles liegt auf deiner Platte und hat die Cloud nie
gebraucht.

---

## 4 · Der Punkt ohne Wiederkehr

Es gibt keinen. Bis Schritt 4 ist nichts passiert — das alte Projekt läuft
unberührt weiter, Lovable löscht nichts. Zurück geht es, indem die zwei Werte
in `Frontend/.env` wieder auf die alten zeigen.

**Das alte Projekt erst löschen, wenn das neue mindestens eine Woche trägt.**
Und wenn, dann bewusst: es nimmt über `ON DELETE CASCADE` alles mit.

---

## 5 · Aufwand

| | |
|---|---|
| Schritte 1–6 (Datenbank, Anmeldung, Daten zurück) | **~1 Stunde**, davon ~45 min bei dir |
| Schritt 7 (Google) | *geschätzt ein halber Tag* |
| Frontend-Hosting (Form B) | **`npm run build` + hochladen** — nachgemessen, kein Umbau |
| Engine-Hosting | der eigentliche Brocken, Wochen 3–4 |

---

## 6 · Wann

**Vor dem ersten fremden DJ, der sich ein Konto anlegt** — nicht vor der
nächsten Runde verschickter Seiten. Die erzeugt keine Konten.

Der Kostentreiber ist die Zahl der Konten, und die steht heute auf eins.
