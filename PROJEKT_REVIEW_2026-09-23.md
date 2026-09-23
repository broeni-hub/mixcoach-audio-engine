# MixCoach — Projekt-Review 23.09.2026

Anlass: Zwei fremde DJs haben MixCoach benutzt und geantwortet. Sebastian
will auf dieser Grundlage den Status Quo bewerten und entscheiden, wie das
Tool weitergebaut wird.

---

## 0 · Wie es entstand

Alle Zahlen in diesem Dokument sind am 23.09.2026 am Repo nachgemessen, nicht
aus `CLAUDE.md`, `PRODUKTVISION.md` oder einem Sitzungsbericht übernommen.
Gelaufen sind: `analyze_timing_bias --check`, `predictions_from_analyses` für
`mid_sec` und `start_sec`, `tools.eval.uebergangsfenster`,
`tools.eval.beat_jitter`, `tools.eval.relabel_agreement`,
`tools.uebungen_bewertung_auswerten`, `build_profile()`, die Testsuiten und
eine eigene Auszählung über alle 60 gespeicherten Reports.

**Zwei Messungen sind für dieses Review neu geschrieben worden.** Sie liegen
als `tools/eval/harmonik.py` im Projekt, damit sie jederzeit nachvollziehbar
sind:

```
.venv/bin/python -m tools.eval.harmonik                # Harmonik gegen das Urteil
.venv/bin/python -m tools.eval.harmonik --stabilitaet  # bleibt die Tonart gleich?
```

Die Verknüpfung von Bewertung und Übergang ist aus `tools/eval/beat_jitter.py`
übernommen. Das Werkzeug rechnet deren dokumentierte Zahl als **Kontrolle**
mit und sagt selbst, wenn sie nicht herauskommt — dann gilt kein Wert aus dem
Lauf. Am 23.09. kommt sie heraus (ρ = −0,336, soll −0,336).

**Übernommen, nicht nachgemessen:** die Aussagen zum Inhalt des DJ-Feedbacks
(Quelle: Commit-Meldungen `b3dbbe6`, `0d02818`, `96a208d` und die
Projekt-Memory `fabis-sets-als-fremdreferenz`, 13.09.–23.09.2026); die
Zeilenstatistik des Vorgänger-Befunds vom 30.08.

**Eine Lücke, die dieses Review nicht schließt:** Seit dem 30.08.2026 gibt es
kein Projektdokument mehr. Die gesamte September-Arbeit — 14 Commits —
existiert nur als Commit-Meldung. `CLAUDE.md` beschreibt den Stand vom 30.08.
und nennt 405 Tests; es sind 455.

---

## 1 · Die kurze Fassung

Der September hat zum ersten Mal etwas gebracht, das keine Messung im Projekt
je liefern konnte: **zwei fremde DJs haben das Produkt benutzt und geantwortet**
— und beide haben mit ihrer Kritik sachlich recht gehabt, beide Male ging es
um eine Zahl, die der Report anzeigte, ohne sie gemessen zu haben.

**Das Produkt, das sie benutzt haben, ist aber nicht die App.** Es ist
`tools/set_report.py`, ein Kommandozeilen-Werkzeug (1.062 der 2.400
September-Zeilen), aus dem Sebastian von Hand eine HTML-Seite baut und
verschickt. **Am Frontend wurde im September keine einzige Zeile geändert.**

**Und in der App steht der Fehler, den die DJs im Report gerade beanstandet
haben, noch drin — 311 mal.** 99 % aller Feedback-Sätze in den gespeicherten
Reports urteilen über Harmonik. Neu gemessen: der Camelot-Abstand, auf dem
diese Sätze beruhen, hat **keinen** Zusammenhang mit dem menschlichen Urteil
(ρ = +0,063, p = 0,28; kompatibel und inkompatibel liegen beide bei Median
4,0, Mann-Whitney p = 0,355).

Die Erkennung selbst ist seit dem 31.07. unverändert — Recall 70 %, Precision
74 %, σ = 54,58 s, jetzt acht Wochen. **Gesamtstand rund 54 %** (25.08.: 53 %).

---

## 2 · Der Maßstab

Maßgeblich ist `PRODUKTVISION.md`. Sie trägt zwei Dinge:

**Fernziel:** >90 % Übergangserkennung, sekundengenau. Bleibt Ziel, ist kein Tor.

**Live-Schwelle** (das Tor):

> Live-reif ist MixCoach, wenn **jeder angezeigte Wert gemessen ist**, die
> **Historie einen Gerätewechsel überlebt**, und **drei Sets desselben DJs eine
> Entwicklung sichtbar machen**.

Stand der drei Bedingungen heute:

| | Stand 25.08. | **Stand 23.09.** | gemessen an |
|---|---|---|---|
| **1 · Jeder Wert gemessen** | fast | **verletzt** | 311 von 313 Feedback-Sätzen urteilen über eine Größe ohne Beleg (5.1) |
| **2 · Historie überlebt Gerätewechsel** | erfüllt | **erfüllt** | vorgeführt 18.08., `store.ts:addAnalysis()`, Test hält die Stelle |
| **3 · Drei Sets zeigen Entwicklung** | halb | **halb** | Pegel: ρ = −0,732, `developmentVisible: true` · Jitter: ρ = −0,004, `false` |

Bedingung 1 war am 25.08. die am weitesten fortgeschrittene der drei. Sie ist
heute die verletzte — nicht, weil etwas kaputtgegangen wäre, sondern weil zum
ersten Mal nachgemessen wurde, worüber die Sätze im Report eigentlich urteilen.

---

## 3 · Stand gegen die Vision

### Die fünf Erlebnis-Punkte

| | 17.08. | 25.08. | **23.09.** | Begründung |
|---|---|---|---|---|
| 1 · Erkennung | 58 % | 58 % | **60 %** | Referenzmetrik unverändert (achte Woche). Der Zuwachs kommt von der **Ankerregel** (`f500439`): bei fremden Sets setzte ein Fingerprint-Treffer ohne Anker erfundene Übergänge. Fabis drei Sets gingen von 3/9/7 auf 15/15/16 Übergänge. Die Referenzmetrik kann das nicht sehen — sie misst nur Sebastians eigene Sets, wo die Library passt. |
| 2 · Report | 80 % | 80 % | **72 %** | **Zurückgestuft.** Die Ehrlichkeitslinie ist für die Noten-Kacheln eingelöst (`notMeasured` in 60 von 60 Reports), aber nicht für die **Sätze**: 311 von 313 Feedback-Sätzen geben eine harmonische Empfehlung ohne Beleg. Harmonik steht in `nicht_gemessen.py` gar nicht erst als Dimension. |
| 3 · Coach | 50 % | 56 % | **58 %** | 235 Übungen, alle mit `metric`. Übungstexte: 24 Formulierungen statt 4, keine behauptet Wahrnehmung, zweisprachig. „Stärken" enthielt seit dem 14.08. nur Kritik — repariert (`2e85e4e`). Dagegen: das **einzige** Muster des Profils ist harmonisch, also unbelegt. J7 unverändert (13/20, p = 0,263). |
| 4 · Fortschritt | 55 % | 55 % | **57 %** | Die Kurve trägt: Pegel ρ = −0,732 über 14 eigene Aufnahmen, `developmentVisible: true`. Die zweite Achse ist weiter flach (ρ = −0,004) und sagt das jetzt selbst. Fremde Aufnahmen sauber ausgeschlossen (10 von 28), auch die als `.wav` gelieferte. Dagegen: „Dein bester Übergang" zeigt Qualität 61, der schwächste 66 (5.3). |
| 5 · Teilen | 10 % | 10 % | **25 %** | **Der größte Sprung.** `tools/set_report.py` erzeugt eine eigenständige, zweisprachige Seite ohne Audio — und sie ist tatsächlich an zwei fremde DJs gegangen, die geantwortet haben. Nicht 50 %, weil Sebastian sie von Hand baut und verschickt; in der App gibt es das nicht. |

### Die drei Burggräben

| | 17.08. | 25.08. | **23.09.** | Begründung |
|---|---|---|---|---|
| 1 · Daten-Schleife | 40 % | 42 % | **45 %** | Zum ersten Mal haben **fremde DJs** auf Reports reagiert — das erste Signal von außen in der Projektgeschichte. Der Kreis ist trotzdem nicht geschlossen: sie haben per Nachricht geantwortet, nicht per Klick in der App. Weiterhin **null fremde Korrekturen** im Trainingsdatensatz. |
| 2 · Library-Verbindung | 72 % | 72 % | **72 %** | 6113 Tracks, 0 Windows-Pfade. Tracknamen an **19,3 %** der Übergänge (25.08.: 21,8 %) — der Rückgang ist ehrlich, nicht schlecht: es sind fremde Sets dazugekommen, für die keine Library existiert. `collection.xml` liegt weiter **nicht auf diesem Mac**. |
| 3 · Ehrlichkeit | 95 % | 90 % | **80 %** | **Zurückgestuft, und der Stand ist gespalten.** Die verschickte Seite ist strenger als je zuvor: Dichte-Kachel sagt selbst, dass kein Zusammenhang besteht; Referenzband ist die Spanne, nicht der Median; Korrekturvermerk; keine Set-Tonart im Kopf. Die **App** hat nichts davon und urteilt 311 mal harmonisch. |

### Die drei Teile der Roadmap

| | 17.08. | 25.08. | **23.09.** |
|---|---|---|---|
| Teil 1 · Audio-Engine | 72 % | 74 % | **76 %** |
| Teil 2 · Frontend | 68 % | 68 % | **68 %** |
| Teil 3 · Online gehen | 15 % | 15 % | **15 %** |

**Gesamt rund 54 %** (25.08.: 53 %). Der Zuwachs bei Punkt 5 und der Rückgang
bei Punkt 2 heben sich fast auf. Teil 2 steht still, weil im September
**keine einzige Frontend-Zeile** geändert wurde.

---

## 4 · Kennzahlen-Tafel

| | Stand 23.09.2026 |
|---|---|
| **Erkennung** (dedup) | Recall 70 % · Precision 74 % · strikt korrekt 29 % |
| **Timing** | σ 54,58 s · Median −29,43 s · 85 % zu spät · innerhalb 8 s: 5 % |
| Selbsttest der Referenzmetrik | reproduziert (6 von 6 Sollwerten) |
| **Modell** | `min_p` 0,60 · `min_gap` 150 s · LOSO: Recall 0,924 / Precision 0,628 / F1 0,748 · 25 Sets, 3537 Kandidaten |
| **Anker, fairer Vergleich** (n = 97) | `mid_sec` Median −32,95 s, σ 46,15, in 8 s 4 % · `start_sec` Median −10,40 s, σ 47,00, in 8 s **21 %** |
| Regressionswächter `correct` (n = 71) | `mid_sec` 100 % in 8 s · `start_sec` nur **18 %**, Median +16,47 s |
| **Übergangsfenster** | Anker `start_sec` · −60 s…+50 s = 110 s · 73 % Abdeckung (132 Korrekturen) |
| **Reports** | 60 Dateien (+19 archiviert) · 509 Übergänge · 28 eindeutige Aufnahmen |
| `mapperVersion` | `honest-v2` in 60/60 |
| `reportRevision` | 10 in 32 Reports · **28 Reports auf 1–7** |
| `userId` gesetzt | 51 von 60 |
| **Befüllung** | `quality`/`phrase_alignment` 100 % · `composite`/`beat_alignment`/`loudness_jump`/`beat_jitter` 88,2 % · `exit_quality` 79,2 % · `harmonic_clash`/`vocal_overlap` 68,4 % · `energy_dip` 50,1 % · `track_in`/`track_out` **19,3 %** · `bass_overlap` **14,9 %** |
| `notMeasured` | `creativity`/`eq`/`frequency`/`timing` in 60/60 · `beatmatching` in 7 |
| **Übungen** | 235, davon **235 mit `metric`** (100 %) · 278 Beobachtungen |
| **Coach-Profil** | 18 eigene Aufnahmen · 106 Übergänge · 10 fremde ausgeschlossen |
| Pegel-Trend | 1,5 dB · ρ = **−0,732** · `developmentVisible: true` · 14 Aufnahmen |
| Jitter-Trend | 9,8 ms · ρ = **−0,004** · `developmentVisible: false` |
| Muster erkannt | **1** (harmonisch — unbelegt, siehe 5.1) |
| **Nützlichkeitsnachweis (J7)** | 13 von 20 · p = 0,263 · **unverändert seit 17.08.** |
| **K1** (menschliche Untergrenze) | **weiter offen** — dritter Durchgang ebenfalls verankert (r = +0,996 Startversatz/Antwort, 0 von 16 haben den Marker angefahren) |
| **Tests** | Engine **455 grün** (`CLAUDE.md` sagt 405) · Frontend 79 grün · `tsc --noEmit` 0 Fehler |
| **Datenhygiene** | ein Ground-Truth-Stamm (45 Dateien) · `KONFLIKTE.md` abgearbeitet · `app/experimental/` von nichts importiert · 0 Windows-Pfade |
| **Betrieb** | `MIXCOACH_AUTH` nicht gesetzt (= aus) · CORS auf localhost, **nicht** `*` · `PAYWALL_DISABLED = true` · `DEV_BYPASS_AUTH = false` · `.env` ohne Service-Key |
| **Auslieferungsrisiko** | **14 Commits ungepusht** · `origin/HEAD` zeigt auf einen Branch vom **31.07.** · 3 von 5 Worktrees stehen auf diesem alten Stand |

---

## 5 · Befunde, die in keinem Projektdokument stehen

### 5.1 · Der Report urteilt 311 mal über Harmonik — und Harmonik trägt nicht

**Die Auszählung.** Über alle 509 gespeicherten Übergänge tragen 313 einen
Feedback-Satz. **311 davon (99 %) urteilen über Harmonik**, fast immer in
dieser Form:

> „Übergang bei 11:28 wechselt harmonisch weit (F Minor → A Minor, Camelot
> 4A → 8A) — wähle einen Track im Nachbarfeld des Camelot-Rads."

**Die Messung** (neu, 23.09.2026; gleiche Verknüpfung wie
`tools/eval/beat_jitter.py`, deren dokumentierte Zahl als Kontrolle
mitreproduziert wurde):

| Größe | n | Spearman ρ | p |
|---|---|---|---|
| **Camelot-Abstand** (worauf der Satz beruht) | 297 | **+0,063** | **0,28** |
| `harmonic_clash_score` | 237 | −0,138 | 0,034 |
| `loudness_jump_db` (Kontrolle) | 237 | −0,092 | 0,157 |
| `beat_jitter_ms` (Kontrolle) | 237 | **−0,336** | **<0,0001** |

Kompatible Wechsel (Camelot-Abstand ≤ 1, n = 121) gegen inkompatible
(n = 176): **Median 4,0 gegen 4,0, Mann-Whitney p = 0,355.** Es ist kein
Unterschied da.

Das Vorzeichen des Camelot-Abstands ist sogar **positiv** — wenn überhaupt
etwas, dann wurden weite Tonartwechsel minimal *besser* bewertet.

**Und die Tonart selbst ist nicht das Problem.** Gegenprobe über
Wiederholungsanalysen derselben Aufnahme: **89 von 96 wiederholt gemessenen
Übergängen behalten ihre Tonart (93 %)**. Die Erkennung ist stabil. Sie misst
zuverlässig etwas, das mit der Qualität des Übergangs nichts zu tun hat —
exakt der Fall, den `nicht_gemessen.py` selbst beschreibt: *„Befüllt ist nicht
gemessen."*

**Warum es durchgerutscht ist.** `nicht_gemessen.py` ist die eine Stelle, an
der steht, was ein Report nicht trägt — aber es führt nur die fünf Dimensionen
der **Noten-Kacheln** (`creativity`, `eq`, `frequency`, `timing`,
`beatmatching`) plus `flow`/`musicality` als offen. **Harmonik ist dort keine
Dimension**, weil sie nie als Note im Kopf stand. Die Ehrlichkeitslinie deckt
die Kacheln ab und die **Sätze nicht**. In `PRODUKTVISION.md` steht seit dem
17.08. die Zahl −0,14 für harmonische Kompatibilität mit dem Zusatz, sie sage
über die Qualität nichts — und direkt darunter, die Ehrlichkeitslinie sei
eingelöst. Beides stand nebeneinander, fünf Wochen lang.

**Der Report für die fremden DJs macht es seit dem 23.09. richtig.** Dort steht
Harmonik unter „Aufgefallen, aber nicht bewertet", mit dem ausdrücklichen
Hinweis, dass kein Zusammenhang belegt ist. Die App hat diesen Abschnitt nicht.

### 5.2 · Das Produkt, das die DJs benutzt haben, ist nicht die App

`tools/set_report.py` wird von `app/` und `Frontend/` **von keiner Stelle
importiert**. Es ist ein Kommandozeilen-Werkzeug. Sebastian ruft es auf, es
schreibt eine HTML-Datei, er verschickt sie.

Von den ~2.400 im September geänderten Zeilen entfallen **1.062 auf diese eine
Datei** — mit Abstand der größte Posten. Am Frontend wurde **nichts** geändert.

Damit gibt es die Sache, vor der `CLAUDE.md` unter „Jede Information hat genau
einen Ort, an dem sie wahr ist" ausdrücklich warnt: **zwei Report-Erzeuger**.
Sie sind bereits auseinandergelaufen:

| | verschickte Seite | App |
|---|---|---|
| Referenzband | **Spanne** (0,50–2,00 dB / 5,8–11,9 ms) | gibt es nicht |
| Dichte | „kein Zusammenhang belegt" | gibt es nicht |
| Harmonik | „aufgefallen, **nicht bewertet**" | 311 Urteile |
| Set-Tonart im Kopf | entfernt (kippt mit den Grenzen) | — |
| Korrekturvermerk | ja | `reportRevision` |
| „Was schon sitzt" | ja | nein |
| Sprache | DE/EN | DE/EN (Übungen) |

Das ist derselbe Bauplan wie bei den zwei Ground-Truth-Stämmen und den zwei
`notMeasured`-Listen. Beide Male ist einer der Stände davongelaufen, und beide
Male hat es Tage gekostet.

### 5.3 · „Dein bester Übergang" zeigt eine schlechtere Zahl als der schwächste

Aus `build_profile()`, heute gemessen:

- **best:** MixCoach4.WAV, Übergang 4 — Pegelsprung 0,0 dB, Jitter 9,74 ms,
  angezeigte **Qualität 61**
- **worst:** MixCoach5.WAV, Übergang 6 — Pegelsprung 9,3 dB, Jitter 12,35 ms,
  angezeigte **Qualität 66**

Die **Auswahl** ist richtig: sie läuft über die beiden belegten Größen. Die
**Anzeige** nimmt `quality_score` — eine Zahl ohne belegten Zusammenhang — und
widerspricht damit der eigenen Auswahl. `CoachProfilePanel.tsx:197` zeigt sie.
Beide Feedback-Sätze dazu sind zudem harmonisch, also aus 5.1.

### 5.4 · Beide DJs haben denselben Fehlertyp gefunden, unabhängig voneinander

- **Fabi (13.09.):** „Was genau ist der Vergleichswert der Dichte? Ist es
  empfohlen, schneller Tracks zu wechseln?" — Die Dichte-Kachel stand
  gleichrangig neben zwei belegten Größen und nannte einen Bereich. Gemessen:
  ρ = −0,094, p = 0,67. Kein Zusammenhang.
- **Zweiter DJ (23.09.):** „maybe I'm not a machine but I believe 10ms is
  fucking amazing haha" — Das Referenzband lief von 0 bis zum **Median** der
  sechs Profi-Sets. Sein Wert 11,2 ms lag innerhalb der tatsächlichen Spanne
  (5,8–11,9) und besser als Dixon bei Tomorrowland. Standardfehler des
  Set-Medians ±1,8 ms bei angezeigtem Rückstand 1,2 ms; gegen kein einziges
  Referenz-Set nachweisbar (alle p > 0,09).

**Zwei Fremde, zwei Wochen auseinander, derselbe Fehlertyp: eine angezeigte
Größe ohne Messung dahinter.** Das ist die aussagekräftigste Rückmeldung, die
das Projekt je bekommen hat — nicht weil die Kritik hart war, sondern weil sie
**genau die Linie trifft, die das Produkt als Markenkern führt**. Ein DJ merkt
Pseudo-Präzision sofort. Und beide haben sie in der ersten Stunde gefunden.

Der Befund 5.1 ist die dritte Instanz desselben Fehlers — nur hat sie noch
niemand von außen gesehen, weil die verschickte Seite Harmonik gar nicht
bewertet. **In der App würde der nächste DJ sie finden.**

### 5.5 · 28 von 60 Reports stehen auf einer alten `reportRevision`

32 Reports stehen auf `reportRevision: 10`, die übrigen 28 auf 1 bis 7. Der
Korrekturweg vom 16.08. wirkt nur bei erhöhter Revision. Die Backfills vom
16.09. haben also einen Teil des Bestands erreicht und einen Teil nicht. Für
die Messungen ist das ohne Belang — für das, was ein Browser zeigt, nicht.

### 5.6 · Die Falle mit dem Default-Branch ist weiter offen

`git ls-remote --symref origin HEAD` zeigt auf `claude/amazing-chatelet-50ec0a`,
Stand **31.07.2026**. Drei der fünf Worktrees stehen dort. Jede von der
Desktop-App im Hintergrund abgezweigte Aufgabe startet auf einem Stand, dem
die gesamte August- und September-Arbeit fehlt. Der Befund steht seit dem
14.09. in der Projekt-Memory und ist nicht behoben.

Dazu: **14 Commits sind ungepusht.** Die komplette September-Arbeit — beide
fremden DJs, `set_report.py`, die Ankerregel — existiert genau einmal, auf
diesem Mac, auf einem Branch.

---

## 6 · Die Korrektur-Schleife

14 Commits im September. Eingeordnet nach dem, was sie bewirken:

| Art | Anzahl | Commits |
|---|---|---|
| **Nimmt einen eigenen früheren Fehler zurück** | **10** | `f500439` erfundene Übergänge · `2e85e4e` „Stärken" enthielt nur Kritik · `62935c8`, `c99c033`, `4a53d21` dreimal dieselben Übungstexte · `06e0fc4` Backfill dazu · `0d02818` Set-Tonart · `87a17cf` Datenstand reparieren · `da5c4c8` fremde `.wav` · `b3dbbe6` Rückstand ohne Messung |
| Neue Reichweite | 3 | `96a208d` zwei Werkzeuge · `b67ed71`, `817d9bc` Englisch |
| Daten | 1 | `b44a2e6` zweites fremdes Set |

**10 von 14.** Das ist keine Anklage — drei dieser zehn sind erst durch die
fremden DJs sichtbar geworden, und genau dafür holt man sich fremde Nutzer.
Aber der Anteil hat eine Ursache, die sich benennen lässt:

**Drei der Korrekturen betreffen Übungstexte** (`62935c8`, `c99c033`,
`4a53d21`, zusammen 391 + 238 Zeilen). Dreimal hintereinander wurde dieselbe
Sache angefasst, weil beim ersten Mal nicht gemessen wurde, wie ein Mensch
„gleich" liest. Der dritte Commit heißt wörtlich: *„Ähnlichkeit so gemessen,
wie man liest."*

**Die Gegenmaßnahme steht schon da** und hat funktioniert:
`tests/test_uebungen_wortlaut.py` (238 Zeilen) hält die Regel jetzt fest.
Dasselbe Muster wie bei `nicht_gemessen.py` im August — erst dreimal
korrigieren, dann die Regel an eine Stelle schreiben.

**Was für den nächsten Monat daraus folgt:** Die Regel vorher schreiben. Bei
Harmonik (5.1) heißt das konkret: nicht die 311 Sätze einzeln ändern, sondern
Harmonik in `nicht_gemessen.py` eintragen und die Sätze von dort erzeugen
lassen.

---

## 7 · Offene Posten, sortiert nach der Live-Schwelle

### Bedingung 1 — jeder angezeigte Wert ist gemessen (**verletzt**)

| | Posten | Aufwand |
|---|---|---|
| **A** | **Harmonik in `nicht_gemessen.py` eintragen** mit der Zahl aus 5.1, und die 311 Feedback-Sätze von dort steuern: beschreiben statt empfehlen, so wie es die verschickte Seite seit dem 23.09. macht. Betrifft auch das einzige Muster des Profils. | 1 Tag |
| **B** | **`quality_score` aus „bester/schwächster Übergang" nehmen** (5.3) und die Zahl zeigen, nach der ausgewählt wurde — Pegelsprung und Jitter. | 1 Std. |
| **C** | Die Entscheidung zu `quality_score` insgesamt. Steht seit dem 13.08. offen, **dritte Verschiebung**. 5.3 ist ihr erster sichtbarer Schaden. | Entscheidung |

### Bedingung 3 — drei Sets zeigen eine Entwicklung (**halb**)

| | Posten | Aufwand |
|---|---|---|
| **D** | Die Jitter-Achse ist flach (ρ = −0,004) und sagt das ehrlich. Eine **dritte belegte Größe** wäre der einzige Weg zu mehr — dafür gibt es heute keinen Kandidaten. **Nicht anfangen, bis einer da ist.** | — |
| **E** | `ownRecording` steht in 1 von 60 Reports. Bei jedem neuen fremden Set `tools/aufnahme_markieren.py` aufrufen, sonst verschiebt es die Kurve. | Routine |

### Nicht an der Schwelle, aber teuer wenn es schiefgeht

| | Posten | Aufwand |
|---|---|---|
| **F** | **14 Commits pushen.** Die September-Arbeit existiert einmal. | 5 Min. |
| **G** | `origin/HEAD` auf `main` stellen (5.6). Solange das nicht steht, ist jede delegierte Hintergrund-Aufgabe wirkungslos. | 5 Min. |
| **H** | `CLAUDE.md` nachziehen — sie beschreibt den 30.08. und nennt 405 statt 455 Tests. | 1 Std. |

### Weiter offen, unverändert

- **K1** — die menschliche Untergrenze. **Dreimal gescheitert**, jedes Mal am
  Instrument. Solange sie offen ist, weiß niemand, wie viel Luft σ = 54,58 s
  nach unten hat.
- **K2** — `collection.xml` liegt nicht auf diesem Mac. Der einzige Weg zu
  „sekundengenau" ohne offene Forschung. **Nur Sebastian kann das.**
- **J7** — p = 0,263, unverändert. Die Übungen sind von einem Münzwurf nicht
  zu unterscheiden.
- Passwort-Zurücksetzen fehlt; die Bestätigungsmail nach der Registrierung
  wird versprochen und kommt bei `mailer_autoconfirm: true` nie. (Gefunden
  18.08., **zweite Verschiebung**.)
- Die Entscheidungen zur Übungsbibliothek und zum LLM-Coach.

---

## 8 · Ausblick — die nächsten drei Wochen

Ausgerichtet an der Schwelle, nicht an der Schwierigkeit. Der Satz, der alles
ordnet: **Der nächste fremde DJ darf nicht denselben Fehlertyp finden wie die
ersten beiden.**

### Woche 1 — die App auf den Stand der verschickten Seite bringen

Ziel: Bedingung 1 wieder erfüllt.

1. **F + G** (10 Minuten, zuerst): pushen, `origin/HEAD` umstellen.
2. **A**: Harmonik in `nicht_gemessen.py`, Sätze von dort. Das ist der Posten,
   der Bedingung 1 schließt.
3. **B**: `quality_score` aus der Highlight-Kachel.
4. **Vorführung in der laufenden App** — nicht nur grüne Tests. Die
   Arbeitsregel dazu steht in `CLAUDE.md` und ist im August zweimal an einem
   Tag verletzt worden.

### Woche 2 — ein Report-Erzeuger statt zwei

Ziel: 5.2 auflösen, bevor die Stände weiter auseinanderlaufen.

Die Regeln, die heute nur in `set_report.py` stehen — Referenzband als Spanne,
„Was schon sitzt", „aufgefallen, nicht bewertet", Schwellen — gehören nach
`app/`, und `set_report.py` liest sie von dort. So wie `profile.py` seit dem
27.08. die Übungsregel aus `uebungen.py` liest, statt sie zu kopieren.

**Danach ist die verschickte Seite eine Darstellung der App, kein zweites
Produkt.** Das ist die Voraussetzung dafür, dass die nächste Runde
DJ-Feedback überhaupt etwas über die App aussagt.

### Woche 3 — die nächste Runde DJ-Feedback

Ziel: das Signal von außen vergrößern, das der September geliefert hat.

Erst jetzt, weil ein Report, den die App nicht zeigt, kein Produkttest ist.
Wenn Sebastian weitere Sets einsammelt, geht die Seite aus **einem** Erzeuger
raus, und was die DJs dazu sagen, gilt für das Produkt.

**Eine Frage, die dabei beantwortet werden sollte** und die bisher niemand
gestellt hat: Beide DJs haben auf *Zahlen* reagiert. Keiner hat bisher gesagt,
ob er eine **Übung** gemacht hat. J7 sagt mit p = 0,263, dass die Übungen von
einem Münzwurf nicht zu unterscheiden sind — die einzige Stichprobe dazu ist
Sebastian selbst. Zwei fremde DJs, die je fünf Übungspaare beurteilen, wären
20 zusätzliche Urteile und der erste Nützlichkeitsnachweis von außen.

### Was in diesen drei Wochen **nicht** angefasst wird

- Die Erkennung. Sie ist seit acht Wochen unverändert, und die gemessen
  abgeschlossenen Fragen (mehr Sets, die 17 Merkmale, die Markerzahl, der
  Betriebspunkt) sagen alle dasselbe: ohne neuen Eingang bewegt sie sich
  nicht. Der neue Eingang heißt K2 und hängt an Sebastian.
- Eine dritte belegte Größe suchen. Es gibt keinen Kandidaten (Posten D).
- Den Anker auf `start_sec` umstellen. Die Zahlen sehen verlockend aus
  (21 % statt 4 % innerhalb 8 s), aber der Regressionswächter sagt Nein:
  die 71 heute korrekten Übergänge fielen von 100 % auf **18 %** innerhalb
  8 s. Das Fenster ist die richtige Antwort darauf, und es steht schon.

---

## 9 · Was nur Sebastian tun kann

1. **`collection.xml` finden.** Der rekordbox-Export liegt nicht auf diesem
   Mac (gesucht am 19.08. in `/Users`, `/Volumes`, Projektstamm). Er ist der
   einzige Weg zu „sekundengenau" ohne offene Forschung — 6673 Beatgrids und
   432 Cue-Punkte, von Hand kuratierte Wahrheit über Downbeats. Wahrscheinlich
   auf dem alten Windows-Rechner oder einer Sicherung.
2. **K1 ein viertes Mal ansetzen — oder streichen.** Dreimal ist das
   Instrument gescheitert. Die ehrliche Alternative ist, in
   `PRODUKTVISION.md` „sekundengenau" durch das Fenster zu ersetzen und die
   Frage zu schließen. Das ist eine Produktentscheidung, keine Messung.
3. **`quality_score`** — behalten, umbauen oder entfernen. Dritte
   Verschiebung.
4. **Die nächsten Sets einsammeln** und dabei fragen, ob jemand eine Übung
   gemacht hat.
5. **Entscheiden, ob die App oder die verschickte Seite das Produkt ist.**
   Woche 2 oben nimmt an: die App. Wenn die Antwort für die nächsten drei
   Monate „die Seite" lautet, ist der Plan ein anderer — dann gehört die
   Arbeit in einen Weg, der die Seite ohne Sebastians Terminal erzeugt.

---

## 10 · Was über die Beta hinaus trägt

- **Die Ehrlichkeitslinie ist der Markenkern, und sie funktioniert.** Zwei
  fremde DJs haben unabhängig voneinander genau die zwei Stellen gefunden, an
  denen sie verletzt war. Das ist kein Rückschlag, das ist der Beweis, dass
  die Linie die richtige ist: Die Zielgruppe merkt es. Ein Produkt, das ihr
  standhält, hat ein Argument, das kein Konkurrent kopieren kann, ohne
  dieselbe Arbeit zu machen.
- **Der Datensatz.** 45 Ground-Truth-Dateien, 6113 Tracks, 509 bewertete
  Übergänge, ein Stamm. Der Burggraben ist die Seltenheit, nicht der
  Qualitätssprung — das ist gemessen und bleibt wahr.
- **Die Werkzeuge, mit denen dieses Review entstanden ist.** `eval/`,
  Referenzmetrik mit Selbsttest, `nicht_gemessen.py`. Ein Projekt, das seine
  eigenen Behauptungen in Minuten widerlegen kann, macht Fehler einmal und
  nicht ein Jahr lang. Befund 5.1 ist heute in 20 Minuten entstanden.
- **`set_report.py` als Form.** Eine Seite, die ein fremder DJ ohne Erklärung
  lesen kann, ist Erlebnis-Punkt 5. Sie existiert und ist erprobt.

---

## 11 · Das größte Risiko

**Dass die nächste Runde DJ-Feedback auf eine Seite trifft, die das Produkt
nicht ist — und dass die Antworten deshalb nichts über das Produkt sagen.**

Der Beleg steht in den Zahlen dieses Reviews:

- Die beiden DJs haben `tools/set_report.py` gesehen, das von `app/` und
  `Frontend/` **von keiner Stelle** importiert wird.
- Im September wurden **1.062 Zeilen** in diese eine Datei geschrieben und
  **0 Zeilen** ins Frontend.
- Die Seite ist inzwischen **strenger** als die App: Harmonik steht dort unter
  „nicht bewertet", in der App unter 311 Empfehlungen.

Wenn Sebastian jetzt fünf weitere Sets einsammelt und fünf Seiten verschickt,
bekommt er fünf Rückmeldungen zu einem Werkzeug, das kein Nutzer je selbst
bedienen wird — und die App, die live gehen soll, bleibt ungetestet und trägt
weiter den Fehlertyp, den die ersten beiden DJs schon gefunden haben.

**Die Reihenfolge ist deshalb: erst A (Harmonik), dann ein Report-Erzeuger
statt zwei, dann die nächste Runde.** Nicht umgekehrt. Das ist derselbe
Fehler wie beim Backfill ohne Korrekturweg am 13.08. — die Aufgabe war
richtig, die Reihenfolge nicht.

---

*Gemessen am 23.09.2026 am Stand `b3dbbe6` (`setup/macos-umzug`).
Alle Zahlen reproduzierbar mit `MIXCOACH_DATA_DIR=daten/` und den in
Abschnitt 0 genannten Werkzeugen.*
