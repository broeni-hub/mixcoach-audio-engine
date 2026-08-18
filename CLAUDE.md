# MixCoach — Projektkontext

DJ-Set-Analyse: Aufnahme rein, Report mit bewerteten Übergängen raus.
Der USP ist die Transition, nicht der Track.

**Maßgeblich für Ziel und Tor ist `PRODUKTVISION.md`** — dort stehen seit der
Zusammenführung am 17.08.2026 beide: das Fernziel und die Live-Schwelle.
`ROADMAP.md` sagt, in welcher Reihenfolge.

**Stand 18.08.2026:** Der Korrekturweg steht — eine Änderung auf der Platte
erreicht den Browser, ohne dass jemand seinen Cache löscht (`reportRevision`,
vorgeführt am 16.08.). Punkt 3 hat zum ersten Mal Übungen, die eine gemessene
Zahl aus dem eigenen Set nennen; die Vorlage „Transition Review" steht in
keinem Report mehr. Ein Ergebnis-Stamm, ein Ground-Truth-Stamm.

**Bedingung 2 ist vorgeführt** (18.08.). Eine bei angemeldetem Nutzer über die
Engine entstandene Analyse steht ohne Neuladen in `public.analyses`; danach
wurde jeder `mixcoach.*`-Schlüssel aus `localStorage` entfernt, und nach dem
Neuladen war sie wieder da — sie kann nur aus der Datenbank gekommen sein.
Hergang und Messwerte: `SITZUNG_2026-08-14.md`, Abschnitt N5.

Bis dahin hing die Persistenz an genau einer Stelle: `runPipeline()`, dem
Browser-Notpfad, den der Preflight gar nicht erst laufen lässt. Der
Engine-Pfad schrieb nur in `localStorage`. Es fehlte kein Feature — die Kette
riss eine Stelle vor dem Ziel. Sie hängt jetzt in `store.ts:addAnalysis()`,
dem gemeinsamen Punkt aller Wege, und ein Test hält fest, dass keine zweite
Stelle entsteht.

Offen und wartend auf Sebastian:

- **J7 ist gelaufen, und das Ergebnis ist unentschieden.** 20 Paare, blind:
  **13 zu 7** für die belegte Übung (65 %), zweiseitiger Binomialtest
  **p = 0,263**. Nötig für 5 % wären 15 von 20 gewesen. Von einem Münzwurf ist
  das nicht zu unterscheiden (`tools/uebungen_bewertung_auswerten.py`,
  Lauf `abend1`).

  **Punkt 3 bleibt damit bei 50 %, aber aus einem anderen Grund als bisher:**
  nicht mehr, weil die Messung fehlt, sondern weil sie stattgefunden hat und
  nichts belegt. Wer die Übungen für besser hält, braucht eine größere
  Stichprobe — nicht dieselbe Behauptung nochmal.
- Die Entscheidungen zu `quality_score`, zur Übungsbibliothek
  (`ENTSCHEIDUNG_UEBUNGSBIBLIOTHEK.md`) und zum LLM-Coach.
- Neu gefunden am 18.08., beides klein und außerhalb jedes Auftrags: die App
  hat **keinen Weg, ein Passwort zurückzusetzen**, und verspricht nach der
  Registrierung eine Bestätigungsmail, die bei `mailer_autoconfirm: true`
  nie kommt.

## Die Live-Schwelle — Maßstab für jede Priorisierung

> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.**

Gilt seit 30.07.2026 und ersetzt „Precision 75–80 %". Grund: 20 zusätzliche
gelabelte Sets bringen +0,1 pp Precision, die vorhandenen Merkmale erklären 8 %
der Zeitvarianz. Präzision und Timing bleiben Ziele, sind aber **kein Tor** mehr.

Praktisch heißt das bei jeder Aufgabe: Sie zahlt auf eine der drei Bedingungen
ein, oder sie hat einen anderen genannten Grund. Herleitung und ausgezählter
Stand: `STANDORTBESTIMMUNG_2026-07-30.md`, Befund: `ZUKUNFTSWEGE_2026-07-30.md`.

## Widerspruch ist Teil des Auftrags

**Sebastians Anweisung vom 17.08.2026, gilt für jede Sitzung — hier und in
Cowork:**

> Wenn eine Anweisung, eine Frage oder ein Prompt das Projekt in eine falsche
> Richtung rückt oder in der falschen Reihenfolge kommt, sag das **sehr klar
> und deutlich** — bevor du anfängst. Nenn die Aufgabe, die stattdessen dran
> wäre, und warum.

Das ist keine Höflichkeitsformel, sondern eine Arbeitsanweisung. Konkret:

- **Vor jedem Auftrag prüfen:** Zahlt er auf eine der drei Bedingungen der
  Live-Schwelle ein? Gibt es eine Aufgabe, die vorher fällig ist, weil dieser
  Auftrag sonst wirkungslos bleibt?
- **Wenn ja: zuerst widersprechen, dann liefern.** Nicht anfangen und
  unterwegs einen Nebensatz einbauen.
- **Beispiele aus der Projektgeschichte, an denen es teuer war:** Ein Backfill
  ohne Korrekturweg (13.08.) korrigiert Dateien, die niemand mehr liest — die
  Reihenfolge war falsch, nicht die Aufgabe. Eine Vorführung ohne die
  Persistenz im Engine-Pfad (17.08.) hätte einen Abend gekostet und wie ein
  Produktfehler ausgesehen.
- **Auch gegen den Auftraggeber.** „Sebastian hat es so gesagt" ist kein Grund,
  eine falsche Reihenfolge auszuführen. Der Widerspruch gehört in den Chat,
  bevor der erste Commit entsteht.
- **Und gegen sich selbst:** Wenn eine frühere eigene Empfehlung durch eine
  Messung widerlegt ist, wird das ausgesprochen und die alte Zahl daneben
  gestellt — nicht still korrigiert.

## Aufbau

```
audio-engine/mixcoach-audio-engine/   FastAPI-Backend + Analyse
  app/audio/scoring/                  Composite-Bewertung — NICHT ANFASSEN
  app/audio/set_analyzer_helpers.py   Kandidatensuche für Übergänge
  app/library/manager.py              Fingerprint-/Index-Verwaltung
  app/paths.py                        Datenstamm, siehe unten
  tools/                              Auswertungs- und Wartungsskripte
daten/                                Datenstamm (MIXCOACH_DATA_DIR)
  library/index.json                  6113 Tracks
  library/fp/<tid>.npy                Chroma, Hop 372 ms
  library/lm/<tid>.npz                Landmark-Hashes
Frontend/                             TanStack Start + React 19 + Supabase
```

## Umgebung

Python **3.12** in `.venv/` im Projektstamm (System-Python 3.9 reicht nicht:
`app/main.py:240` nutzt `str | None` in einer Signatur, die FastAPI zur
Laufzeit auswertet). Node 24 und Python 3.12 liegen unter `~/.local`,
per `~/.zshrc` im PATH.

`MIXCOACH_DATA_DIR` **muss gesetzt sein** und auf `daten/` zeigen. Ohne die
Variable fällt `app/paths.py` auf den Engine-Ordner zurück, und die App sucht
Library, Ergebnisse und Ground Truth am falschen Ort. Genau so ist die Ground
Truth einmal auf zwei Stämme auseinandergelaufen.

**Seit dem 13.08.2026 gibt es wieder einen Stamm:** `daten/ground_truth/`,
45 Dateien. Der zweite liegt unter `_archiv_2026-08-13/` und wird nicht mehr
gelesen; seine abweichenden Bewertungen sind eingearbeitet
(`tools/staemme_zusammenfuehren.py`). Die neun widersprechenden Urteile, die
dabei herauskamen, sind am 17.08. entschieden — `daten/ground_truth/
KONFLIKTE.md` führt „Offen: 0". Die Variable bleibt trotzdem Pflicht: ohne sie
entsteht derselbe Doppelstamm von vorn.

Details und offene Blocker: `SETUP_MACOS.md`.

## Zwei Eigenheiten, die man kennen muss

**Track-IDs hängen am Pfad-String.** `manager.py:56` bildet die ID als
`md5(path)[:16]`. Ein geänderter Pfad heißt neue ID heißt verwaiste
Fingerprints. Deshalb nie „einfach neu scannen", sondern
`tools/repath_library_index.py` benutzen.

**NFC/NFD.** Windows schreibt Dateinamen als NFC, macOS liefert oft NFD.
Beide Formen finden dieselbe Datei über `exists()`, ergeben aber
verschiedene md5-Summen und damit verschiedene Track-IDs. Pfade, die in
Track-IDs eingehen, immer auf die Schreibweise bringen, die `os.scandir`
zurückgibt.

## Selbsttest — zuerst laufen lassen

```bash
.venv/bin/python -m tools.selbsttest       # oder MixCoach-Selbsttest.command
```

Prüft nicht, ob der Code läuft, sondern ob die **Voraussetzungen für jede
Messung** da sind: Datenstamm, Modell, Library-Pfade, Stem-Trennung,
Befüllungsgrade, Cloud-Anbindung. `FEHLT` heißt: an dieser Stelle wird nicht
gemessen, auch wenn alles normal aussieht.

Anlass waren drei Vorfälle an einem Tag (11.08.2026), die alle denselben
Bauplan hatten — ein **stiller Ausfall, der sich als Datenproblem tarnt**:
ein Schalter ohne Werkzeug dahinter, ein Skript das den veralteten Ordner las
und „zu wenig Daten" meldete, und eine Cloud-Anbindung, die bei jedem Aufruf
scheiterte, während die App normal aussah. Der verschluckte Fehler ist in
diesem Projekt die teuerste Codezeile.

## Referenzmetrik

`tools/analyze_timing_bias.py` ist die Messlatte für die Erkennung. Läuft
ohne Audio und ohne numpy.

```bash
.venv/bin/python -m tools.analyze_timing_bias --check     # muss grün sein
```

Seit dem 31.07.2026 ist `--mode dedup` die **Vorgabe**: gezählt werden
Aufnahmen (`fileName`), nicht Ground-Truth-Dateien — sonst zählt REC001 elfmal.
`--check` sagt an, gegen welchen Stand es prüft.

Stand 17.08.2026, Sicht `dedup`: 28 Aufnahmen, 286 bewertete Übergänge,
91 zusätzlich als `missed` erfasst, Recall 70 %, Precision 74 %, strikt
korrekt 29 %, **σ = 54,58 s**, Median −29,43 s, 85 % zu spät. Die alte Sicht
`spec` (69 „Sets", σ = 52,87 s) bleibt über `--mode spec` abrufbar — **das
Entdoppeln hat σ erhöht**, die Doppelzählung hatte die Streuung geschönt.

Nur die 19 verwertbaren Aufnahmen (`dedup --nur-verwertbar`): Recall 73 %,
Precision 80 %, σ = 45,85 s.

Gegenüber dem 31.07. haben sich **nur Recall und `missed`** bewegt (71 → 70 %,
88 → 91; verwertbar 74 → 73 %). Ursache ist die Stamm-Zusammenführung vom
13.08.: aus dem archivierten Ordner kamen drei zusätzliche `missed`-Angaben
dazu, also mehr Wahrheit bei gleicher Erkennung. Precision, σ und Median sind
unverändert — die Erkennung selbst wurde nicht angefasst.

Die Diagnose dazu: `detect_set_transition_zones()` in
`app/audio/set_analyzer_helpers.py` sucht eine RMS-Delle — das ist im DJ-Mix
der Breakdown vor dem Drop, also das *Ende* des Blends. Der Mensch labelt den
*Anfang*. Die Differenz ist die Transitionslänge (8–64 Takte), daher die große
Streuung. Ein globaler Offset behebt das nicht und lässt σ unverändert.
**σ ist die Zahl, an der sich jede Änderung messen lassen muss.**

Bis zum 17.08.2026 stand hier `detect_transition_zones()` — ein 46-Zeiler in
`app/experimental/`, der von nichts importiert wurde und inzwischen unter
`_archiv_2026-08-17/` liegt. Der Befund gilt unverändert für die lebende
Fassung; sie ist nur differenzierter (geglättete Kurve, drei Fenster im
Vergleich, eigene Bewertung für Blend, Drop und Bass-Swap).

## Arbeitsregeln

- `app/audio/scoring/*` nicht anfassen (Composite-Rebuild).
- Bestehende API-Endpoints und Frontend-Seiten nicht verändern.
- Keine Grid-Search über die Schwellwerte in `detect_set_transition_zones()` —
  belegt falscher Hebel, siehe oben.
- Ehrlichkeitslinie: nichts anzeigen, was nicht gemessen wurde. Das ist
  Markenkern, kein Stilmittel.
- **Ein Test belegt die Regel, nicht den Weg durch die Anwendung.** Zu jeder
  Abnahme gehört eine Vorführung in der laufenden App. Zweimal an einem Tag
  gelernt: bei F1.2 waren die Tests grün, während die Report-Seite den
  korrigierten Stand gar nicht erst holte — und beim Coach zeigte das
  Fazit weiter einen Satz, den der Backfill entfernt hatte, weil er in einem
  zweiten Feld nochmal stand. Beide Male hat erst das Öffnen der Seite es
  gezeigt.
- **Jede Information hat genau einen Ort, an dem sie wahr ist.** Zwei
  Ergebnis-Stämme, zwei Ground-Truth-Stämme, zwei Kopien derselben
  Coach-Sätze, eine Schwelle an zwei Stellen — jedes Mal lief einer der
  beiden Stände davon, und jedes Mal hat es Tage gekostet. Wer eine zweite
  Kopie anlegt, muss sagen, welche gilt.
- Kommentare und Doku auf Deutsch, wie im Bestand.

## Was gemessen erledigt ist — nicht nochmal aufmachen

- **Mehr gelabelte Sets kaufen Recall, keine Precision.** Von 4 auf 24 Sets:
  Recall +17,4 pp, Precision +1,6 pp bei ±6,0 pp Ziehungsstreuung
  (`tools/eval/lernkurve.py`).
- **Die 17 Merkmale tragen die Zeit nicht.** R² = 0,011 auf 1303
  Kandidatenpaaren, ein konstanter Offset schafft dasselbe
  (`tools/eval/zeit_regression.py`). Zweifach belegt, 30.07. und 10.08.
- **Die Auswahl rankt nicht schlecht, sie setzt zu viele Marker.** 317 auf 170
  echte Übergänge, Ausschöpfung der Orakel-Schranke 93–95 %
  (`tools/eval/nms2.py`). Precision ist durch die Markerzahl gedeckelt.
- **Kein fünfter Blend-Onset-Schätzer.** Vier sind gemessen gescheitert.
- **Keine Synthetik im Training, kein Landmark-Vorfilter.** Beide gemessen
  verworfen, siehe `PROJEKTSTAND-CLAUDE.md` Abschnitt 4.

Wer eine dieser Fragen neu stellt, braucht einen neuen Eingang — nicht mehr
Daten und keine andere Zielgröße.

## Tests

```bash
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m pytest tests/ -q      # 294 Tests, alle grün
```

Dazu 54 Frontend-Tests (`cd Frontend && npx vitest run`) und `npx tsc
--noEmit`, das seit dem 15.08. bei **0 Fehlern** steht.

`tests/conftest.py` verhindert, dass Testläufe Analyse-JSONs im Datenstamm
hinterlassen. Vor dem 31.07. taten sie das — 62 Stück waren aufgelaufen und
haben eine Messung verschoben.

Der Schutz hatte bis zum 16.08. ein Loch, das nur unter Last aufging: der
Job-Executor lebt prozessweit, und `_run_job` las das Zielverzeichnis erst
beim Schreiben. Lief ein Test in seinen Timeout, war der Patch da schon
zurückgenommen und die Analyse landete im echten Datenstamm. Der Zielordner
wird jetzt beim Absenden festgehalten (`job_manager._run_job`).
