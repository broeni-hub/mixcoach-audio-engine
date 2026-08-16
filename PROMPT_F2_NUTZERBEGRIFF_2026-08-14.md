# Arbeitsauftrag — F2: Die Engine bekommt einen Nutzerbegriff

**Für Claude Code · erstellt 14.08.2026 · Nachfolger von
`PROMPT_ARCHITEKTUR_F1_F2_2026-08-13.md` (F1 ist abgeschlossen)**

Lies zuerst `CLAUDE.md`, dann `ARCHITEKTUR_BEWERTUNG_2026-08-13.md` Befund S2,
dann `BEFUNDSTAND_2026-08-14.md`.

---

## Worum es geht

F1 ist gelöst: Eine Analyse hat jetzt genau einen Ort, an dem sie wahr ist, und
einen Weg, auf dem eine Korrektur ankommt.

**F2 ist die zweite und letzte als fundamental eingestufte Lücke:**

> Die Engine kennt keinen Nutzer. Kein `Depends`, kein Token, kein `user_id` an
> keinem der 22 Endpoints. `allow_origins=["*"]` mit `allow_credentials=True`.
> `daten/analysis_results/` ist ein flacher Ordner ohne Mandantentrennung.
>
> Das Frontend ist gleichzeitig **voll mandantenfähig**: Supabase mit `user_id`
> und der Policy `auth.uid() = user_id`. Beide Modelle lassen sich nicht
> gemeinsam hosten.

**F2 blockiert heute nichts.** Lokal, mit einem Nutzer, ist der jetzige Zustand
folgerichtig. Der Grund, es trotzdem jetzt zu tun: Ein Datenmodell mit 51
Reports und einem Nutzer umzustellen kostet Tage. Mit 5000 Reports und fremden
Nutzern kostet es Wochen — und dann steht es zwischen dir und dem Livegang.

Ohne F2 ist `GET /analysis` gehostet eine Liste aller Analysen aller Nutzer,
`GET /analysis/{id}/audio` streamt fremde Set-Aufnahmen, und
`DELETE /analysis/{id}` löscht sie.

---

## Die harte Randbedingung

**Der lokale Doppelklick-Betrieb muss danach genauso funktionieren wie heute.**

Sebastian ist kein Entwickler. Wenn `MixCoach-Start-Mac.command` nach dieser
Änderung eine Anmeldung, ein Terminal oder einen manuell gesetzten Schlüssel
verlangt, ist die Änderung falsch gebaut — auch wenn sie technisch stimmt.

Der Weg dahin ist ein Schalter: **`MIXCOACH_REQUIRE_AUTH`, Vorgabe `0`.** Bei
`0` läuft alles wie heute, mit einem Standard-Besitzer. Bei `1` wird geprüft
und abgelehnt. Beide Zustände müssen belegt werden.

---

## Fünf Fallen — heute am Code gemessen

Das ist der wertvollste Teil dieses Auftrags. Vier davon sind so gebaut, dass
sie **still** scheitern.

### Falle 1 · `<audio>` kann keinen Authorization-Header senden

`app/api/relabel.py:179` erzeugt:

```html
<audio id="au" controls preload="none" src="/analysis/${AID}/audio"></audio>
```

Ein HTML-Media-Element schickt keine eigenen Header. Wird
`GET /analysis/{id}/audio` hinter eine Header-Prüfung gestellt, lädt die
Aufnahme in der zweiten Labelrunde einfach nicht — ohne Fehlermeldung, ohne
Hinweis. **Und genau diese Runde steht noch aus.**

Erleichternd: Die Hauptanwendung nutzt diesen Endpoint **nicht**. Der Player
im Frontend spielt aus IndexedDB (`lib/audio-store.ts:39`, `loadAudioUrl`).
Der einzige Verbraucher ist die Relabel-Seite.

### Falle 2 · Das Frontend hängt heute kein Token an Engine-Aufrufe

`integrations/supabase/auth-attacher.ts` sieht danach aus, ist es aber nicht:
Es ist eine **TanStack-Function-Middleware** und deckt ausschließlich
serverFn-RPCs an den TanStack-Server ab. Die Aufrufe an die FastAPI-Engine
laufen daran vorbei:

```
lib/api/remoteProvider.ts:166   fetch(input, { ...init, signal })   — ohne Header
services/audioEngineClient.ts   — keine Header
```

Wer nur serverseitig prüft und annimmt, das Token komme schon mit, baut eine
Engine, die jeden Aufruf des eigenen Frontends ablehnt.

### Falle 3 · 26 Dateien lesen den Datenstamm

`RESULTS_DIR`, `GROUND_TRUTH_DIR` oder `DATA_ROOT` kommen in **26** Dateien vor
— 9 in `app/`, 17 in `tools/`. Dazu die Trainingskette
(`retrain_model.py`, `build_features.py`, `fit_composite_weights.py`).

Jede Änderung an der Ablagestruktur muss durch alle 26 hindurch. **Deshalb
gehört die Ordnertrennung in diesem Auftrag ausdrücklich nicht dazu** — siehe
„Was nicht dazugehört".

### Falle 4 · Das Archiv wird noch gelesen

`_archiv_2026-08-13/` ist nicht tot: `analyze_timing_bias.py --mode spec` liest
es absichtlich, um die eingefrorenen Zahlen aus
`CLAUDE_CODE_SPEC_2026-07-29.md` reproduzierbar zu halten. Und es enthält das
**einzige** Audio einer Aufnahme (`11da05af`). Was dort liegt, gehört
demselben Besitzer wie der Rest — es darf bei der Migration nicht durchs Raster
fallen.

### Falle 5 · Der verschluckte Fehler

Die teuerste Codezeile dieses Projekts ist `except Exception: pass`. Drei
Vorfälle am 11.08. hatten denselben Bauplan. Ein fehlgeschlagener Auth-Check,
der still zu „keine Daten" wird, wäre die vierte Auflage — und die schwerste,
weil sie wie ein Datenproblem aussieht.

**Jede abgelehnte Anfrage muss sagen, warum.** Der Selbsttest bekommt eine
Zeile dazu.

---

## Die Jobs

### F2.0 · Befunde prüfen und die Signatur klären

Bestätige oder widerlege die fünf Fallen am Code, mit **Datei:Zeile**.

Zusätzlich zu klären, weil es die Umsetzung bestimmt und ich es nicht
zuverlässig sagen kann:

> **Wie sind die JWTs dieses Supabase-Projekts signiert?** Symmetrisch (HS256
> mit dem JWT-Secret) oder asymmetrisch (ES256/RS256 mit JWKS unter
> `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`)? Danach richtet sich, ob die
> Engine einen zusätzlichen geheimen Schlüssel braucht — und ob Sebastian ihn
> eintragen muss.

Prüf das am tatsächlichen Projekt, nicht an der Dokumentationslage. Wenn ein
angemeldeter Nutzer nötig ist, um an ein Beispiel-Token zu kommen, sag das und
halte an.

**Checkpoint:** Bericht in den Chat, dann warten.

### F2.1 · `userId` ins Datenmodell

- Jeder Report und jede Ground-Truth-Datei bekommt ein Feld `userId`.
- **Migration der 51 Reports, 45 Bewertungen und der Archivbestände** auf einen
  Standard-Besitzer. Solange Sebastians `auth.uid()` nicht bekannt ist: der
  sprechende Platzhalter `local-single-user`, der bei der ersten Anmeldung
  einmalig umgeschrieben wird.
- `tools/migriere_besitzer.py`, **`--dry-run` als Vorgabe**, umkehrbar, plus
  `MixCoach-Besitzer-Migrieren.command`.
- Vor und nach der Migration `tools/analyze_timing_bias.py --check` in allen
  drei Sichten. Weicht etwas ab, ist die Ursache zu benennen.

### F2.2 · Prüfen, nicht neu bauen

**Kein zweites Nutzersystem.** Das Frontend hat seit dem 13.08. eine
funktionierende Supabase-Anmeldung. Ihr Token wird mitgeschickt und geprüft.

**Engine-Seite:**

- Eine FastAPI-Abhängigkeit, die den `Authorization`-Header liest, das Token
  nach dem in F2.0 geklärten Verfahren prüft und `user_id` liefert.
- `MIXCOACH_REQUIRE_AUTH=0` (Vorgabe): kein Header nötig, `user_id` ist der
  Standard-Besitzer. `=1`: Prüfung greift, Ablehnung mit Begründung.
- Angewendet auf die 19 Endpoints in `main.py`. **`/health` bleibt offen** —
  der Upload-Preflight (`app.upload.tsx:97`) pingt ihn ohne Sitzung.
- **Der Relabel-Router ist ein Sonderfall** (Falle 1). Er ist Sebastians
  lokales Werkzeug ohne Frontend und ohne Sitzung. Sauberste Lösung: bei
  `MIXCOACH_REQUIRE_AUTH=1` wird er **gar nicht erst eingebunden**, bei `0`
  läuft er wie heute. Ein gehostetes MixCoach hat keine blinde Labelrunde.
  Wenn du einen besseren Weg siehst, leg ihn vor, statt ihn zu bauen.

**Frontend-Seite (Falle 2):**

- Das Token an die Engine-Aufrufe hängen — in `remoteProvider.ts` und
  `services/audioEngineClient.ts`. Eine gemeinsame Stelle, nicht zwei
  Fassungen.
- Ist niemand angemeldet, wird kein Header gesetzt. Bei
  `MIXCOACH_REQUIRE_AUTH=0` ändert sich damit nichts am heutigen Verhalten.

**Selbsttest:** eine Zeile, die sagt, ob die Prüfung an oder aus ist — und wenn
an, ob sie tatsächlich greift.

### F2.3 · CORS

`allow_origins=["*"]` mit `allow_credentials=True` durch eine Liste aus einer
Umgebungsvariablen ersetzen. Vorgabe lokal: `http://localhost:8080` und
`http://127.0.0.1:8080` (das Frontend läuft auf 8080, nicht auf Vites 5173).

### F2.4 · Vorführen, nicht nur testen

**Das ist die Lehre aus F1.** Dort belegten die Tests die Regel, und der Weg
durch die laufende Anwendung fehlte trotzdem — bis eine zweite Runde ihn
nachtrug.

Vorzuführen sind drei Läufe, jeder mit Beleg:

1. **`MixCoach-Start-Mac.command` doppelklicken, `REQUIRE_AUTH` nicht gesetzt.**
   Set hochladen, Report ansehen, Übergang anhören. Alles wie vorher, keine
   Anmeldung, kein Terminal.
2. **`MIXCOACH_REQUIRE_AUTH=1`, nicht angemeldet.** Aufruf wird abgelehnt, die
   Meldung nennt den Grund. Kein stiller Ausfall, kein leerer Bildschirm.
3. **`MIXCOACH_REQUIRE_AUTH=1`, angemeldet.** Aufruf geht durch, die Analyse
   trägt die richtige `userId`.

### F2.5 · Bericht

`SITZUNG_2026-08-14.md` nach dem Muster von `SITZUNG_2026-08-10.md`. **Das ist
kein Nebenpunkt:** Die beiden vorigen Aufträge haben ihn verlangt und keiner
hat ihn geliefert. Die Begründungen stehen ausschließlich in Commit-Meldungen —
sehr guten, aber nicht in dem Format, das die nächste Sitzung liest. Genau
daraus ist am 10.08. ein übersehener Arbeitstag entstanden.

---

## Was ausdrücklich **nicht** dazugehört

- **Keine Ordnertrennung nach Nutzer.** `daten/<userId>/analysis_results/`
  wäre die sauberere Ablage — sie geht aber durch 26 Dateien, die Trainingskette
  und das Archiv (Fallen 3 und 4). Ein `userId`-Feld plus konsequente Filterung
  in der API-Schicht reicht für eine geschlossene Beta vollständig. Die
  Ordnertrennung gehört in den Auftrag, der die Ablage ohnehin anfasst — S4 aus
  der Architekturbewertung.
- **Kein Hosting, kein Server, keine Domain, kein Stripe, keine
  Datenschutzerklärung, kein Löschkonzept.** Das ist Teil 3 der Roadmap.
- **Kein Registrierungs-Flow.** Die Anmeldung existiert.
- **Kein Anfassen von `app/audio/scoring/*`.**
- **Keine Änderung an Erkennung, Modell oder Bewertung.** Dieser Auftrag
  verschiebt keine einzige Messzahl. Tut er es doch, ist etwas schiefgegangen.
- **Kein Entfernen des Browser-Notpfads**, kein Umhängen des LLM-Coaches — das
  steht im Punkt-3-Auftrag.

---

## Akzeptanz

1. Die drei Läufe aus F2.4 sind vorgeführt und belegt.
2. Alle 51 Reports und 45 Bewertungen tragen eine `userId`, das Archiv
   eingeschlossen.
3. **235 Backend-Tests und 15 Frontend-Tests bleiben grün**, plus neue für die
   Auth-Abhängigkeit — mindestens: ohne Token bei `REQUIRE_AUTH=1` abgelehnt,
   mit Token angenommen, bei `=0` beides angenommen.
4. Referenzmetrik in allen drei Sichten unverändert (`dedup`: Recall 70 %,
   Precision 74 %, σ 54,58 s) — oder Abweichung erklärt.
5. Der Selbsttest meldet den Zustand der Auth-Prüfung.
6. `SITZUNG_2026-08-14.md` liegt vor.
7. **Committet und gepusht.** Beim Schreiben dieses Auftrags lagen 10 Commits
   und vier Dokumente ungepusht — darunter der Fortschrittsnachweis, auf den
   seit dem 30.07. hingearbeitet wurde.

## Wo du anhalten musst

- Nach **F2.0**, immer — besonders bei der Frage nach dem Signaturverfahren.
- Bevor du eine **Migration** über Reports oder Ground Truth schreibst, ohne
  dass `--dry-run` die Vorgabe ist.
- Wenn sich zeigt, dass ein Schlüssel oder Zugang nötig ist, den nur Sebastian
  eintragen kann.
- Wenn die Referenzmetrik sich bewegt.
