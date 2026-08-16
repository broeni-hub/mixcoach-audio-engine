# MixCoach — Bewertung der technischen Architektur

**Stand: 13.08.2026** · Frage: *Ist die Architektur schlüssig, oder braucht es
fundamentalere Änderungen?* · Grundlage: Code-Durchsicht, nicht Doku

---

## Das Urteil in drei Sätzen

**Die Bausteine sind gut. Die Nahtstellen sind es nicht.**

Jede einzelne Schicht — Analyse-Engine, Bewertung, Frontend, Cloud — ist sauberer
gebaut, als man es bei einem Ein-Personen-Projekt erwarten würde: klare
Trennung, echte Tests, ehrliche Kommentare, ein eigenes Messwerkzeug-Arsenal.
**Die Probleme liegen ausnahmslos dort, wo zwei Schichten sich berühren** — und
zwei davon sind so grundlegend, dass sie nicht durch Konfiguration lösbar sind.

**Ein Neubau ist nicht nötig und wäre ein Fehler.** Zwei gezielte Eingriffe
reichen — aber sie sind fällig, bevor der erste fremde Nutzer das Produkt
anfasst, nicht danach.

---

## 1 · Was gut ist und nicht angefasst gehört

Das gehört an den Anfang, weil der Rest kritisch ist.

**Die Engine-Schichtung trägt.** `loader → pipeline → annotate_* → mapper → API`.
Jeder Bewertungsschritt ist ein eigenes Modul mit eigenem Test, alle hängen an
derselben `transitions_detailed`-Liste und schreiben ihre Zahl hinein. Man kann
einen Schritt austauschen, ohne die anderen zu berühren — genau das ist beim
Composite auch passiert. Das ist die richtige Bauform für ein Messsystem.

**Der asynchrone Job-Fluss ist richtig gewählt.** Upload → `jobId` → Polling →
Ergebnis, mit `ThreadPoolExecutor(max_workers=1)` und Ablage der Ergebnisse auf
Platte. Bei 2–10 Minuten Analysedauer ist alles andere falsch. Dass der
Job-Speicher im Arbeitsspeicher liegt, ist bei einem Nutzer korrekt und nicht
naiv — der Kommentar sagt das auch.

**`paths.py` ist ein Lehrstück.** Ein Datenstamm, ein Override, die Herkunft des
Problems im Docstring. Genau so gehört eine Entscheidung dokumentiert.

**Das Messwerkzeug ist ein echtes Kapital.** `tools/eval/` mit
`nms2.py`, `zeit_regression.py`, `lernkurve.py`, dazu `analyze_timing_bias.py`
mit drei Zählweisen und `--check`, und `predictions_from_analyses.py`, das
Vorhersagen austauschbar macht, ohne die Erkennung anzufassen. Projekte dieser
Größe haben so etwas normalerweise überhaupt nicht.

**Die Ehrlichkeit ist Code geworden, nicht nur Vorsatz.** `notMeasured`,
`scoring_version.py` mit `vergleichbar()`, das bei ungestempelten Reports
bewusst `False` liefert, der Selbsttest, `conftest.py` gegen Test-Müll im
Datenstamm. Das sind Mechanismen, keine Absichtserklärungen.

**Die Versionierungsdisziplin stimmt.** Reports im Repo (3,7 MB), Audio draußen
(13 GB), `.env` draußen mit begründetem `.gitignore`-Kommentar. Das ganze
Repository wiegt 11 MB und enthält die vollständige Messhistorie.

---

## 2 · Wie die Daten wirklich fließen

```
   Audio-Datei
       │
       ▼
┌──────────────────────────────────────────────┐
│  FastAPI-Engine (Python)                     │
│  set_analyzer_helpers.detect_set_transition_ │
│  zones()  →  ml_classifier.select_track_     │
│  changes_ml()  →  annotate_*  →  mapper      │
└──────────────────┬───────────────────────────┘
                   │ 1
                   ▼
      daten/analysis_results/{id}.json      ← MISST. Nicht Quelle der Wahrheit.
                   │
                   │  einmalig, beim ersten Ansehen
                   ▼
┌──────────────────────────────────────────────┐
│  localStorage["mixcoach.state.v1"].analyses  │  ← 2 · was die UI rendert
└──────────────────┬───────────────────────────┘
                   │  bei Anmeldung, "DB gewinnt"
                   ▼
      Supabase  public.analyses.payload (JSONB) │  ← 3 · was den Gerätewechsel
                                                   überlebt

   Parallel und unbenutzt:
   audio-analysis.ts + set-analysis.ts (Browser-Notpfad, ~750 Zeilen)
   app/experimental/ (1796 Zeilen, von nichts importiert)
```

Dieselbe Analyse existiert **dreimal**, in drei verschiedenen Systemen, und
**keine der drei Kopien ist als Quelle der Wahrheit definiert.**

---

## 3 · Sechs strukturelle Befunde

### S1 · Ein korrigierter Report erreicht den Nutzer nicht — **schwer**

`analysis-engine.ts:151`:
```ts
if (list.some((a) => a.id === remote.id)) return;   // mergeRemoteAnalysisIntoStore
```
`store.ts:111`:
```ts
if (s.analyses.some((a) => a.id === result.id)) return;   // addAnalysis
```

Beide sind idempotent über die `id`. Sobald eine Analyse einmal im
`localStorage` liegt, wird die Datei auf der Engine-Platte **nie wieder
gelesen**. Und `sync.ts` merged mit „DB gewinnt" — die Cloud-Kopie überschreibt
die lokale, nicht umgekehrt.

**Folge:** Jede Korrektur am Mapper wirkt ausschließlich auf *künftige*
Analysen. Es gibt keinen Weg, einen bereits angesehenen Report zu berichtigen.

Das ist die strukturelle Ursache von Befund 5a im Projekt-Review: Die
Ehrlichkeitslinie steht seit dem 31.07. im Code, aber die 50 Reports tragen
weiter `beatmatching: 100`. Ein Backfill auf der Platte allein ändert daran
**nichts** — er muss von einem Re-Import begleitet werden, sonst korrigiert er
eine Datei, die niemand mehr liest.

Für ein Produkt, dessen Markenkern „nichts anzeigen, was nicht gemessen wurde"
lautet und dessen Wert eine wachsende Historie ist, ist ein System **ohne
Korrekturweg** ein Konstruktionsfehler, kein Detail.

*Kosten der Behebung: klein.* Der Report braucht eine Version (`scoringVersion`
gibt es seit dem 13.08. bereits), und der Merge muss bei höherer Version
ersetzen statt zu überspringen. Ein halber Tag.

### S2 · Das Backend kennt keinen Nutzer — **schwer, sobald gehostet**

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
```

Kein `Depends`, kein Token, kein `user_id` — an keinem der 19 Endpoints.
`daten/analysis_results/` ist ein flacher Ordner ohne Mandantentrennung.
Gleichzeitig ist das Frontend **voll mandantenfähig**: Supabase mit `user_id`
und der Policy `auth.uid() = user_id`.

Lokal ist das folgerichtig und harmlos. Gehostet bedeutet es: Jeder kann
`GET /analysis` aufrufen und alle Analysen aller Nutzer auflisten,
`GET /analysis/{id}/audio` streamt fremde Set-Aufnahmen, und
`DELETE /analysis/{id}` löscht sie.

**Das ist der Punkt, an dem die Roadmap sich verschätzt.** Teil 3 („Online
gehen, 3–4 Wochen") liest sich wie Hosting plus Stripe. Tatsächlich ist es eine
**Datenmodell-Änderung in der Engine**: `user_id` an jeder Analyse, Auth an
jedem Endpoint, Speicher pro Nutzer getrennt, CORS auf die eigene Domain. Das
sind eher 2–3 Wochen zusätzlich, und sie kommen *vor* dem ersten fremden Nutzer,
nicht danach.

*Kosten: mittel, aber unvermeidbar.* Der billigste Weg ist, das Supabase-JWT an
die Engine durchzureichen und dort zu prüfen — kein zweites Nutzersystem.

### S3 · Zwei Analysatoren mit demselben Ausgabetyp — **mittel**

Es gibt zwei vollständige Analysewege, die beide `AnalysisResult` erzeugen:
die Python-Engine und `audio-analysis.ts` + `set-analysis.ts` im Browser
(~750 Zeilen). Der Browser-Weg ist eine schwache Heuristik, und der
Upload-Preflight (`app.upload.tsx:97`) verhindert bewusst, dass er je läuft.

Die Kennzeichnung (`engine: "local"`, roter Banner, kein Hash-Cache für
Fallback-Reports) ist eine gute Absicherung. Die Frage ist trotzdem, **ob dieser
Weg überhaupt existieren sollte.** Er kostet nicht nur Pflege, sondern hat
bereits einen konkreten Schaden angerichtet:

> **Der gesamte LLM-Coach und das Supabase-Regelwerk sind ausschließlich in
> `runPipeline()` verdrahtet — also im Notpfad.** 396 Zeilen fertiger,
> K1-bereinigter Coach hängen hinter einer Tür, die ein anderer Fix zugemauert
> hat.

Zwei Wege, die dasselbe erzeugen sollen, driften auseinander. Genau das ist
passiert. Das ist derselbe Bauplan wie beim doppelten Ground-Truth-Ordner, nur
im Code statt in den Daten.

*Empfehlung: entfernen.* Der Preflight ist die bessere Lösung für dasselbe
Problem — er sagt dem Nutzer klar, dass die Engine nicht läuft, statt ein
schlechteres Ergebnis zu liefern.

### S4 · Der Datenstamm ist vier Dinge gleichzeitig — **mittel**

`daten/analysis_results/` enthält:
Laufzeit-Reports (50 JSON) · Set-Aufnahmen (13 GB, 40 wav + 6 mp3) ·
die Trainingsgrundlage des Modells · und daneben `ground_truth/`, `relabel/`.

Jeder Zwischenfall der letzten Wochen kam hierher: 62 Test-JSONs im Datenstamm
(behoben), der doppelte Ground-Truth-Ordner (offen, 24 Sets doppelt), drei
Streudateien nach dem Merge, ein Auswertungsskript, das den veralteten Ordner
las und „zu wenig Daten" meldete.

Der tiefere Punkt: **Reports sind gleichzeitig Produktausgabe und
Trainingseingang.** Wird ein Set neu analysiert, ändert sich beides — was der DJ
sieht *und* was das Modell lernt — ohne Grenze dazwischen. `scoringVersion` ist
der richtige erste Schritt; er löst aber nur die Vergleichbarkeit, nicht die
Vermischung.

*Kosten: klein.* Getrennte Ordner (`reports/`, `audio/`, `training/`) und ein
eingefrorener, schreibgeschützter Trainings-Schnappschuss. Ein Tag.

### S5 · Track-IDs hängen am Pfad-String — **mittel, wird schwer**

`manager.py:56`: `md5(path)[:16]`. Bekannt, dokumentiert, mit
`repath_library_index.py` als Werkzeug — das ist ordentlich gehandhabt.

Aber es heißt: Der Fingerprint-Index ist an **eine Ordnerstruktur auf einem
Rechner** gebunden, und über NFC/NFD zusätzlich an **ein Betriebssystem**. Beim
Umzug auf den Mac war genau das der Blocker.

Für ein Produkt, bei dem jeder Nutzer seine eigene Sammlung mitbringt, ist eine
pfadbasierte Identität nicht auslieferbar. Die Alternativen liegen bereit:
Inhalts-Hash oder die rekordbox-Track-ID. Letztere hätte einen Zusatznutzen —
`collection.xml` liefert 6673 Beatgrids und 432 Cue-Punkte, die heute brachliegen.

*Kosten: mittel.* Kein Neu-Fingerprinting nötig, wenn die Umstellung als
Zuordnungstabelle gebaut wird.

### S6 · Ein toter Vorfahr der wichtigsten Funktion — und eine falsche Karte

`CLAUDE.md` beschreibt den Aufbau so:

```
app/experimental/detection/    Kandidatensuche für Übergänge
```

**Das stimmt nicht.** `app/experimental/` wird von keiner Datei importiert —
nachgeprüft über `app/`, `tools/` und `tests/`. Die tatsächliche Kandidatensuche
liegt in `app/audio/set_analyzer_helpers.py:detect_set_transition_zones()`
(351 Zeilen, drei Bewertungsfunktionen für Blend, Drop und Bass-Swap).

Daneben liegt in `app/experimental/detection/transition_detector.py` eine
46-zeilige **frühere Fassung** derselben Idee — dieselbe RMS-Delle, nur ohne
Glättung und ohne Typunterscheidung.

Zwei Folgen, beide real:

1. **Wer der Karte in `CLAUDE.md` folgt, optimiert an toter Datei.** Das ist
   keine Vermutung: Die Diagnose zur 30-Sekunden-Verspätung („`app/experimental/
   detection/transition_detector.py` sucht eine lokale RMS-Delle") zitiert genau
   diesen toten Vorfahren. **Der Befund selbst bleibt richtig** — die
   Live-Fassung sucht dieselbe Delle. Aber die Begründung hängt an der falschen
   Datei, und die Live-Fassung ist deutlich differenzierter, als das Zitat
   nahelegt.
2. Der Ordner ist keine Architekturfrage, sondern Ballast: 1796 Zeilen, die bei
   jeder Suche mitkommen und bei jedem Leser Zeit kosten.

*Kosten: eine Stunde.* Ordner archivieren, `CLAUDE.md` korrigieren, die
Diagnose auf die Live-Funktion umschreiben.

---

## 4 · Was ausdrücklich **kein** Problem ist

Damit die Bewertung nicht in eine Richtung kippt:

- **Der Stack ist richtig gewählt.** FastAPI + React/TanStack + Supabase passt
  zur Aufgabe. Kein Grund zu wechseln, und ein Wechsel wäre reine
  Beschäftigung.
- **`max_workers=1` und der In-Memory-Job-Speicher sind korrekt**, solange ein
  Nutzer analysiert. Sie werden erst bei Gleichzeitigkeit falsch, und dann ist
  eine Warteschlange eine kleine, bekannte Änderung — kein Umbau.
- **Der 76-KB-Report als JSONB** ist bei 50 Reports völlig unproblematisch. Die
  20 flachen Spalten daneben werden geschrieben und (bis auf `insights`) nicht
  gelesen — unschön, aber harmlos.
- **Die verstreuten Importe mitten in `main.py`** (Zeilen 150, 348, 382) sind
  Kosmetik.
- **Die Analysedauer** (~3 min ohne Stems) ist für den lokalen Betrieb in
  Ordnung. Erst online wird sie ein Kostenposten.

---

## 5 · Die Antwort auf die gestellte Frage

**Braucht es fundamentalere Änderungen? Ja — genau zwei. Einen Neubau: nein.**

> **Fundamental 1 · Der Report braucht einen Korrekturweg.**
> Solange ein einmal angesehener Report unveränderlich im Browser einfriert,
> kann die Ehrlichkeitslinie nie rückwirkend gelten. Jede künftige Verbesserung
> der Messung erreicht nur neue Sets. Das widerspricht dem Markenkern und
> blockiert Bedingung 1 der Live-Schwelle.

> **Fundamental 2 · Die Engine braucht ein Nutzerkonzept.**
> Backend einmandantig, Frontend mehrmandantig — das lässt sich nicht hosten.
> Es ist kein Hosting-Thema, sondern ein Datenmodell-Thema, und es gehört vor
> den ersten fremden Nutzer.

Alles Weitere (S3–S6) ist Aufräumen: nützlich, billig, aber nicht fundamental.

---

## 6 · Reihenfolge und Aufwand

| | Eingriff | Aufwand | Wann |
|---|---|---|---|
| **A1** | **Korrekturweg für Reports** — `scoringVersion` im Merge auswerten, bei höherer Version ersetzen statt überspringen. Danach B1 aus dem Review erneut fahren | ½ Tag | **sofort** — B1 wirkt sonst nicht |
| **A2** | **`app/experimental/` archivieren, `CLAUDE.md` korrigieren**, Diagnose auf `set_analyzer_helpers.py` umschreiben | 1 h | sofort |
| **A3** | **Browser-Notpfad entfernen**, LLM-Coach und Regelwerk in den Engine-Pfad heben | 1–2 Tage | mit Punkt-3-Auftrag |
| **A4** | **Datenstamm trennen** — `reports/`, `audio/`, `training/`; Doppelstamm auflösen | 1 Tag | vor dem nächsten Retrain |
| **B1** | **Nutzerkonzept in der Engine** — Supabase-JWT durchreichen und prüfen, `user_id` an jeder Analyse, Speicher getrennt, CORS auf die Domain | 1–2 Wochen | **vor Teil 3** |
| **B2** | **Track-Identität vom Pfad lösen** — Inhalts-Hash oder rekordbox-ID, als Zuordnungstabelle | 3–5 Tage | vor dem ersten fremden Nutzer |
| **C1** | Warteschlange statt In-Memory-Jobs | 2 Tage | erst bei Gleichzeitigkeit |

**Summe der fundamentalen Eingriffe: rund drei Wochen** — und sie liegen fast
vollständig in der Phase, die die Roadmap ohnehin für „Online gehen" vorsieht.
Sie kommen nicht obendrauf, sie waren dort nur nicht eingeplant.

---

## 7 · Was das für die laufenden Aufträge heißt

**Der Punkt-3-Auftrag (`PROMPT_PUNKT3_COACH_2026-08-13.md`) braucht eine
Ergänzung.** Job 2b beschreibt einen Backfill über die 50 Report-Dateien. Nach
Befund S1 ändert dieser Backfill **nichts an dem, was der DJ sieht** — die
Reports kommen aus `localStorage` bzw. Supabase, nicht von der Platte. Eingriff
A1 ist damit **Voraussetzung für Job 2b**, nicht eine spätere Aufräumarbeit.

**Der Befund zum LLM-Coach ist zugleich ein Architekturbefund.** Job 4 des
Punkt-3-Auftrags legt drei Wege vor; Eingriff A3 sagt, welcher davon
architektonisch der saubere ist: Weg B oder C, und der Notpfad verschwindet.

**Die Reihenfolge im Projekt-Review bleibt gültig.** Nichts hier verschiebt die
Live-Schwelle oder die Wochenplanung — A1 und A2 sind zusammen ein Tag, A3 fällt
mit Punkt 3 zusammen, und B1/B2 gehören in die Online-Phase, die ohnehin zuletzt
kommt.

---

## 8 · Der ehrliche Schlusssatz

Die Architektur ist nicht das Problem dieses Projekts. Sie ist besser als der
Ruf, den ihr die vielen Korrekturen der letzten Wochen geben — und diese
Korrekturen kamen fast alle aus **doppelt gehaltenem Zustand** (zwei
Ground-Truth-Ordner, zwei Analysewege, drei Kopien jeder Analyse, ein toter
Zwilling der wichtigsten Funktion), nicht aus schlechtem Entwurf.

Das ist die gemeinsame Ursache, und sie hat eine gemeinsame Gegenregel:

> **Jede Information hat genau einen Ort, an dem sie wahr ist. Alles andere ist
> Kopie und muss sagen, woher sie kommt und wie alt sie ist.**

Wer diese Regel auf S1 bis S6 anwendet, bekommt jede der sechs Antworten von
selbst.
