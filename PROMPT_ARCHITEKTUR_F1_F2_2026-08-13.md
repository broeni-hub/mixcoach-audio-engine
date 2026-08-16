# Arbeitsauftrag — die zwei fundamentalen Architektur-Änderungen

**Für Claude Code · erstellt 13.08.2026 · Grundlage: `ARCHITEKTUR_BEWERTUNG_2026-08-13.md`**

Lies zuerst `CLAUDE.md`, dann `ARCHITEKTUR_BEWERTUNG_2026-08-13.md` Abschnitt 3
und 5, dann `PROJEKT_REVIEW_2026-08-13.md` Abschnitt 5a.

---

## Worum es geht

Die Architekturbewertung hat genau zwei Befunde als **fundamental** eingestuft —
fundamental heißt: nicht durch Konfiguration lösbar, sondern nur durch eine
Änderung am Datenmodell.

> **F1 · Eine Analyse hat keinen Ort, an dem sie wahr ist.**
> Dieselbe Analyse liegt dreifach vor (Engine-Platte, `localStorage`, Supabase),
> es gibt zwei konkurrierende Ergebnis-Stämme auf der Platte, und ein einmal
> angesehener Report wird **nie wieder** von der Engine gelesen. Es existiert
> kein Weg, einen falschen Report zu berichtigen.

> **F2 · Die Engine kennt keinen Nutzer.**
> Kein Auth an keinem der 19 Endpoints, `allow_origins=["*"]`, ein flacher
> Ergebnisordner. Das Frontend ist über Supabase-RLS voll mandantenfähig. Beide
> Modelle lassen sich nicht gemeinsam hosten.

**F1 blockiert heute.** Solange es keinen Korrekturweg gibt, erreicht keine
Verbesserung der Messung die 50 bestehenden Reports — die Ehrlichkeitslinie
bleibt auf künftige Analysen beschränkt, und Bedingung 1 der Live-Schwelle ist
unerreichbar.

**F2 blockiert heute nicht**, ist aber jetzt am billigsten: Ein Datenmodell mit
50 Reports und einem Nutzer umzustellen kostet Tage, mit 5000 Reports und
fremden Nutzern Wochen.

**Wenn die Zeit nur für eines reicht: F1 allein ist ein vollständiges,
abschließbares Ergebnis.** Halte dann nach F1 an und melde das.

---

## Reihenfolge — verbindlich

```
F1 vollständig  →  CHECKPOINT  →  F2
```

**Nicht vermischen.** F2 verschiebt Dateien und ändert Ablagepfade. Wer das tut,
solange noch zwei Ergebnis-Stämme nebeneinander liegen, vervielfacht die
Verwirrung statt sie aufzulösen.

Und: **Dieser Auftrag läuft vor `PROMPT_PUNKT3_COACH_2026-08-13.md`.** Dessen
Job 2b (Backfill über die 50 Reports) ist ohne F1 wirkungslos — er korrigiert
Dateien, die niemand mehr liest.

---

## Regeln für diesen Auftrag

Aus `CLAUDE.md`, unverändert gültig:

- **`app/audio/scoring/*` nicht anfassen.**
- **Ehrlichkeitslinie:** nichts anzeigen, was nicht gemessen wurde.
- **Kein Feature still im Live-Pfad**, das langsam ist oder unsichere Ergebnisse
  liefert.
- Kommentare und Doku auf Deutsch.
- **Sebastian ist kein Entwickler.** Jede Migration braucht eine
  `.command`-Datei zum Doppelklicken, nach dem Muster von
  `MixCoach-Modell-Zurueck.command` (die zeigt vorher an, was passiert, und
  fragt nach).

Zusätzlich, speziell hier — **das sind Migrationen über die Trainingsgrundlage
des Modells**, nicht über beliebige Dateien:

- **Jede Migration zuerst mit `--dry-run`**, und `--dry-run` ist die Vorgabe.
- **Nichts löschen, ohne vorher zusammenzuführen.** Siehe F1.1 — im als
  „veraltet" geführten Ordner steckt Arbeit, die im maßgeblichen fehlt.
- **Vor und nach jeder Migration `tools/analyze_timing_bias.py --check`
  laufen lassen** und die Zahlen gegenüberstellen. Ändert sich σ, Recall oder
  Precision, muss die Ursache benannt werden — eine Aufräumarbeit darf die
  Referenzmetrik nicht stillschweigend verschieben.
- 226 Tests bleiben grün.

---

# F1 · Eine Analyse hat genau einen Ort, an dem sie wahr ist

## F1.0 · Bestandsaufnahme mit Belegpflicht

Prüfe die folgenden sechs Aussagen am Code und an den Daten. Belege jede
Bestätigung mit **Datei:Zeile** oder einer ausgezählten Zahl. Was falsch ist,
sag es und halte an.

1. `analysis-engine.ts:151` (`mergeRemoteAnalysisIntoStore`) und `store.ts:111`
   (`addAnalysis`) steigen beide bei bekannter `id` aus — die Engine-Datei wird
   nach dem ersten Ansehen nie wieder gelesen.
2. `sync.ts:syncAnalysesWithDb` merged mit „DB gewinnt", ohne jede Prüfung, ob
   die DB-Kopie neuer ist.
3. `analysis_mapper.py` schreibt seit dem 13.08. `scoring_stamp()`
   (`scoringVersion: 3`) in jeden neuen Report. **Kein einziger** der 50
   gespeicherten Reports trägt den Stempel.
4. `scoring_version.py` kennt bereits `UNSTAMPED = 0` und `vergleichbar()`, das
   ungestempelte Reports bewusst als nicht vergleichbar führt.
5. Es gibt **zwei Ergebnis-Stämme**, beide in git:
   `daten/analysis_results/` (50 JSON, 66 getrackt) und
   `audio-engine/mixcoach-audio-engine/analysis_results/` (93 JSON, 113
   getrackt, 628 MB).
6. Es gibt **zwei Ground-Truth-Stämme**: `daten/ground_truth/` (45) und
   `audio-engine/mixcoach-audio-engine/ground_truth/` (24). Alle 24 sind
   namensgleich in beiden; **18 byteidentisch, 6 abweichend**. Und die
   Abweichung geht in **beide** Richtungen — Beispiel
   `a5ee0fde-765d-489a-a336-0c74060e3e0b.json`:

   ```
   daten/   missed: [85.4,          1279.72, 1848.85]
   engine/  missed: [85.4, 119.39,  1279.72, 1848.85]
   ```

   Der als veraltet geführte Ordner enthält eine Bewertung, die im maßgeblichen
   fehlt. Das ist Sebastians Handarbeit.

**Checkpoint:** Bericht in den Chat, dann warten.

## F1.1 · Die zwei Stämme zusammenführen — nicht löschen

`tools/staemme_zusammenfuehren.py`, `--dry-run` als Vorgabe, plus
`MixCoach-Staemme-Zusammenfuehren.command`.

**Ground Truth** (der heikle Teil, weil hier Handarbeit drinsteckt):

- `missed`: **Vereinigungsmenge** beider Seiten, auf 0,01 s gerundet entdoppelt.
- `verdicts` je Index: identisch → übernehmen. Abweichend → **nicht raten**.
  Sammle alle Konflikte in `daten/ground_truth/KONFLIKTE.md` mit beiden Ständen,
  `updatedAt` beider Dateien und dem betroffenen Übergang, und **leg sie
  Sebastian vor**. Bis zur Entscheidung gilt der Stand aus `daten/`.
- `updatedAt`: den späteren übernehmen.
- Ergebnis nach `daten/ground_truth/`. Der Engine-Ordner wird **nicht gelöscht**,
  sondern nach `audio-engine/mixcoach-audio-engine/_archiv_2026-08-13/`
  verschoben, mit einer `LIESMICH.md`, die sagt, warum er da liegt.

**Analyse-Reports:**

- Die 93 JSON im Engine-Stamm gegen die 50 im Datenstamm abgleichen. Für jede
  `id`, die nur dort liegt: prüfen, ob eine Ground Truth darauf zeigt. Wenn ja,
  gehört sie in den Datenstamm; wenn nein, ins Archiv.
- Bei gleicher `id` in beiden: der Stand mit dem höheren
  `scoringVersion`/`mapperVersion` gewinnt; bei Gleichstand der neuere
  `createdAt`. Die Regel als Kommentar dokumentieren.
- Die 63 `.wav` im Engine-Stamm (628 MB) nicht kopieren — nur den Verweis
  (`audioPath`) korrigieren, falls einer ins Leere zeigt.

**Danach** `git rm --cached` für den archivierten Stamm und einen
`.gitignore`-Eintrag, damit er nicht zurückkommt.

**Akzeptanz:** `MixCoach-Selbsttest.command` meldet für „Ground Truth" **einen
Stamm**, nicht zwei. `analyze_timing_bias --check` läuft, und die Veränderung
gegenüber vorher (28 Aufnahmen, 286 Übergänge, Recall 71 %, Precision 74 %,
σ 54,58 s) ist beziffert und erklärt.

**Checkpoint:** Zahlen vorher/nachher in den Chat, dann warten.

## F1.2 · Der Korrekturweg

Das eigentliche Stück Architektur. Ziel:

> Eine Änderung an der Engine-Datei erreicht den Browser — nachweisbar, ohne
> dass jemand seinen Cache löscht.

**Der Mechanismus, kurz gehalten:** Der Report trägt bereits `scoringVersion`
(neu: 3) bzw. keinen Stempel (= `UNSTAMPED = 0`). Das reicht als Ordnung.

- `analysis-engine.ts:mergeRemoteAnalysisIntoStore` — statt bei bekannter `id`
  auszusteigen: **ersetzen, wenn die eingehende Fassung eine höhere
  `scoringVersion` hat.** Bei gleicher Version bleibt es beim frühen Ausstieg.
- `store.ts:addAnalysis` — dieselbe Regel.
- `sync.ts:syncAnalysesWithDb` — „DB gewinnt" wird zu **„höhere Version
  gewinnt"**, bei Gleichstand weiter DB.

**Zwei Dinge, die dabei nicht kaputtgehen dürfen — prüf sie, verlass dich nicht
auf meine Einschätzung:**

1. **Nutzereigener Zustand darf nicht verloren gehen.** Nach meiner Durchsicht
   liegt alles Nutzereigene außerhalb des Report-Objekts (`archivedIds` im
   Store, Bewertungen in `daten/ground_truth/` auf der Engine). Wenn du etwas
   findest, das nur im Report-Objekt steht, muss es beim Ersetzen erhalten
   bleiben — dann sag es und schlag den Weg vor.
2. **Der Hash-Cache darf nicht zur Falle werden.** `findCachedResult` liefert
   bei erneutem Upload derselben Datei die alte `id` zurück. Das ist gewollt.
   Prüf, dass eine Version-Erhöhung trotzdem durchschlägt und nicht am Cache
   hängen bleibt.

**Akzeptanz — ein Test, kein Augenschein:**
`Frontend/src/lib/__tests__/korrekturweg.test.ts`

- ungestempelt (0) im Store + gestempelt (3) von der Engine → **wird ersetzt**
- gestempelt (3) im Store + gestempelt (3) von der Engine → **bleibt**
- gestempelt (3) im Store + ungestempelt (0) von der Engine → **bleibt**
- `archivedIds` überlebt in allen drei Fällen

## F1.3 · Den Backfill fahren und den Weg vorführen

Erst jetzt wirkt B1 aus dem Projekt-Review.

`tools/backfill_reports.py` (ohne Audio, ohne Demucs — alles Nötige steht in den
JSON), `--dry-run` als Vorgabe. Über alle Reports im nun einzigen Datenstamm:

- `scores.beatmatching` → `None`, `scores.timing` → `None`
  (der Mapper tut das seit dem 31.07.; die gespeicherten Reports tragen weiter
  100 bzw. 61)
- `notMeasured` → die Fünferliste aus `analysis_mapper.py:39`
- `scoringVersion` → 3 setzen, **aber nur wo die Werte tatsächlich der
  Rechenvorschrift 3 entsprechen.** Wo das nicht sicher ist, `UNSTAMPED`
  stehen lassen und in der Ausgabe zählen. Einen Stempel zu setzen, der nicht
  stimmt, wäre genau der Fehler, gegen den `scoring_version.py` geschrieben
  wurde.

**Vorführung — das ist die Abnahme, nicht der Test:**

1. Engine starten, einen bestehenden Report im Browser öffnen, `beatmatching`
   notieren.
2. Backfill fahren.
3. Seite neu laden **ohne Cache zu löschen**.
4. `beatmatching` steht auf „nicht gemessen".

Wenn Schritt 4 nicht eintritt, ist F1.2 nicht fertig — egal was die Tests sagen.

**Ergebnis von F1:** `beatmatching = None` in **allen** Reports des einen
Datenstamms, und ein Weg, auf dem jede künftige Korrektur denselben Weg nimmt.

---

# F2 · Die Engine kennt einen Nutzer

**Erst nach dem Checkpoint aus F1.**

## Was F2 ist — und was ausdrücklich nicht

**Ist Teil dieses Auftrags:** ein Nutzerbegriff im Datenmodell der Engine, das
Durchreichen und Prüfen der bestehenden Supabase-Anmeldung, Trennung der
Ablage, CORS.

**Ist NICHT Teil dieses Auftrags:** Hosting, Server, Domain, Stripe,
Datenschutzerklärung, Löschkonzept, Registrierungs-Flow. Das ist Teil 3 der
Roadmap und kommt später.

**Die harte Randbedingung:** Der lokale Betrieb per Doppelklick muss danach
**genauso** funktionieren wie heute. Sebastian ist kein Entwickler; wenn
`MixCoach-Start.command` nach dieser Änderung eine Anmeldung im Terminal
verlangt, ist die Änderung falsch gebaut.

## F2.1 · `user_id` ins Datenmodell

- Jeder Report und jede Ground-Truth-Datei bekommt ein Feld `userId`.
- **Migration der bestehenden Daten** auf einen Standard-Besitzer. Sebastians
  Supabase-`auth.uid()` ist der richtige Wert — er muss ihn dir nennen, das ist
  keine Rateaufgabe. Solange er fehlt: ein sprechender Platzhalter
  (`local-single-user`), der bei der Anmeldung einmalig umgeschrieben wird.
- `tools/migriere_besitzer.py`, `--dry-run` als Vorgabe, umkehrbar.

## F2.2 · Anmeldung durchreichen und prüfen

**Kein zweites Nutzersystem bauen.** Das Frontend hat seit dem 13.08. eine
funktionierende Supabase-Anmeldung (`DEV_BYPASS_AUTH = false`). Das JWT wird an
die Engine mitgeschickt und dort geprüft — mehr nicht.

- FastAPI-Abhängigkeit (`Depends`), die den `Authorization`-Header liest, das
  JWT gegen den Supabase-JWKS prüft und `user_id` liefert.
- **Ein Schalter `MIXCOACH_REQUIRE_AUTH`, Vorgabe `0`.** Bei `0` läuft alles
  wie heute mit dem Standard-Besitzer — das ist der lokale Doppelklick-Betrieb.
  Bei `1` wird geprüft und abgelehnt.
- **Der Fehler darf nicht verschluckt werden.** Schlägt die Prüfung fehl, sagt
  die Antwort warum. Ein `except Exception: pass` an dieser Stelle wäre exakt
  der Fehler, wegen dem `tools/selbsttest.py` überhaupt existiert.
- Der Selbsttest bekommt eine Zeile: *Auth-Prüfung an / aus, und wenn an: greift
  sie?*

## F2.3 · Ablage trennen

- Ergebnisse, Ground Truth und Audio je Nutzer getrennt ablegen
  (`daten/<userId>/analysis_results/` o. ä.) — **eine** Umstellung, in
  `app/paths.py`, nicht verstreut.
- **Achtung, das ist die riskanteste Stelle des ganzen Auftrags:** 46 Werkzeuge
  in `tools/` und die gesamte Trainingskette lesen aus diesen Ordnern. Such
  jeden Aufrufer, bevor du etwas verschiebst. Wenn du beim Suchen unsicher
  bist, ist ein Kompatibilitätspfad (alter Ort wird weiter gelesen, neu wird nur
  geschrieben) die richtige Zwischenstufe — kein Mut zur Lücke.
- `analyze_timing_bias --check` vor und nach der Verschiebung, Zahlen
  gegenüberstellen.

## F2.4 · CORS

`allow_origins=["*"]` mit `allow_credentials=True` durch eine Liste ersetzen,
die aus einer Umgebungsvariablen kommt. Vorgabe für den lokalen Betrieb:
`http://localhost:8080` und `http://127.0.0.1:8080`.

## Akzeptanz F2

1. `MixCoach-Start.command` doppelklicken → alles läuft wie vorher, **ohne
   Anmeldung, ohne Terminal**.
2. Mit `MIXCOACH_REQUIRE_AUTH=1`: ein Aufruf ohne Token wird abgelehnt, mit
   gültigem Token angenommen — beides belegt.
3. 226 Tests grün, plus neue für die Auth-Abhängigkeit.
4. Referenzmetrik unverändert, oder Abweichung erklärt.

---

## Was am Ende dastehen muss

1. **Ein** Ergebnis-Stamm, **ein** Ground-Truth-Stamm — und die 6 abweichenden
   Dateien zusammengeführt, nicht überschrieben.
2. Ein nachgewiesener Korrekturweg: Änderung auf der Platte → im Browser
   sichtbar, ohne Cache-Löschen.
3. `beatmatching = None` in allen Reports.
4. Ein Nutzerbegriff in der Engine, abschaltbar, lokal reibungsfrei.
5. 226 Tests grün, plus die neuen. Referenzmetrik gemessen und erklärt.
6. Ein Bericht `SITZUNG_<datum>.md` nach dem Muster von `SITZUNG_2026-08-10.md`
   — inklusive der Stellen, an denen du dich selbst korrigiert hast.
7. **Alles committet und gepusht.** Beim Schreiben dieses Auftrags lagen
   7 Commits ungepusht.

## Wo du anhalten musst

- Nach **F1.0** (Befunde) — immer.
- Nach **F1.1** (Zusammenführung), mit den Metrik-Zahlen vorher/nachher.
- Bei jedem **Verdict-Konflikt** aus F1.1 — das ist Sebastians Bewertung, nicht
  deine.
- Nach **F1** insgesamt, vor dem Beginn von F2.
- Sobald eine Migration mehr Dateien anfassen würde als angekündigt.

## Was ausdrücklich nicht Teil dieses Auftrags ist

- Kein Anfassen von `app/audio/scoring/*`.
- Keine Änderung an Erkennung, Modell oder Bewertung. Dieser Auftrag verschiebt
  Zahlen nicht, er sorgt dafür, dass sie ankommen.
- Kein Entfernen des Browser-Notpfads und kein Umhängen des LLM-Coaches — das
  steht in `PROMPT_PUNKT3_COACH_2026-08-13.md` und gehört dort hin.
- Kein Hosting, keine Bezahlschranke, keine DSGVO-Arbeit.
- Keine Track-Identität über Inhalts-Hash — nötig, aber erst vor dem ersten
  fremden Nutzer (`ARCHITEKTUR_BEWERTUNG` S5).
