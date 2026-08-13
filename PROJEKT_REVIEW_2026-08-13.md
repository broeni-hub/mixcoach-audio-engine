# MixCoach — Produktprojekt-Review

**Stand: 13.08.2026** · Auftraggeber: Sebastian · Anlass: „Wo stehen wir wirklich,
und warum musste zuletzt so viel korrigiert werden?"

---

## 0 · Wie dieses Dokument entstanden ist

Jede Zahl unten ist **heute am Repo nachgemessen**, nicht aus `PROJEKTSTAND`,
`ROADMAP` oder `memory.md` übernommen. Das ist kein Formalismus: In diesem
Projekt sind mehrfach Aussagen aus Projektnotizen weitergetragen worden, die
sich beim Nachsehen als falsch erwiesen (Abschnitt 6). Übernommene Zahlen sind
als solche gekennzeichnet.

**Nachgemessen wurde:** Git-Historie und Push-Stand · aktiver Modell-Betriebspunkt
(`app/models/track_change_gbm.json`) · Befüllungsgrad aller 431 Übergänge in den
50 Reports · `scores`-Block und `notMeasured` in allen 50 Reports ·
Library-Index (6113 Einträge, Pfadauflösung) · Frontend-Schalter
(`DEV_BYPASS_AUTH`, `PAYWALL_DISABLED`, `.env`-Schlüssel) · Referenzmetrik
`tools/analyze_timing_bias.py` in drei Varianten.

**Nicht nachgemessen (übernommen):** die 226 Tests (das venv ist aus meiner
Umgebung nicht startbar — Stand laut `CLAUDE.md`: alle grün) · Fingerprint-Recall
0,90 / Precision 1,0 (Stand 15.07., seither nicht neu erhoben) · das physische
Vorhandensein der 6112 Musikdateien (der Composite-Backfill vom 11.08. hat 239
Übergänge aus echtem Audio gerechnet — sie waren also da).

---

## 1 · Die kurze Fassung

Das Projekt ist **weiter, als es sich anfühlt**, und **an einer Stelle ehrlicher
im Code als im Produkt**.

Was seit der Standortbestimmung vom 30.07. echt gewonnen wurde: Der
Betriebspunkt des Modells steht auf `gap=150` (LOSO-Precision **62,8 %** statt
50,5 %). Der Composite ist von 30 % auf **86 %** der Übergänge befüllt. Die
Historie in Supabase ist **nicht ungebaut, sondern war abgeschaltet** — der
letzte Blocker (`DEV_BYPASS_AUTH`) ist heute gefallen. Und es gibt seit dem
11.08. einen Selbsttest, der stille Ausfälle sichtbar macht.

Was dagegen unbemerkt geblieben ist — und der wichtigste Befund dieses Reviews:
**Die Ehrlichkeitslinie ist im Code gezogen, aber nicht in den Daten
angekommen.** Alle 50 gespeicherten Reports tragen weiter `beatmatching: 100`
und `timing: 61` — die zwei Zahlen, die K1 als nicht messend belegt hat. Der
Mapper setzt sie auf `None`, aber seit dem 31.07. wurde **keine einzige Analyse
neu gerechnet**. Was der DJ in seiner Historie sieht, ist unverändert der alte,
unehrliche Stand. Ein halber Tag Backfill behebt das.

**Gegenüber der Vision stehen rund 45 %** (30.07.: 40 %). Der Zuwachs kommt fast
vollständig aus Punkt 2 (Report) und Burggraben 3 (Ehrlichkeit) — nicht aus
Punkt 1 (Erkennung).

---

## 2 · Der Maßstab

Zwei Dokumente definieren, woran gemessen wird. Beide gelten unverändert.

**Die Vision** (`PRODUKTVISION.md`, Projekt-Anweisungen): „Andere Tools
analysieren deine Musik. MixCoach analysiert dein DJing." Fünf Erlebnis-Punkte
(Erkennung → Report → Coach → Fortschritt → Teilen), drei Burggräben
(Daten-Schleife, Library-Verbindung, radikale Ehrlichkeit).

**Die Live-Schwelle** (seit 30.07., in `CLAUDE.md` verankert):

> Live-reif ist MixCoach, wenn **jeder angezeigte Wert gemessen ist**, die
> **Historie einen Gerätewechsel überlebt**, und **drei Sets desselben DJs eine
> Entwicklung sichtbar machen**.

Sie ersetzt „Precision 75–80 %". Der Grund ist gemessen: 20 zusätzliche Sets
bringen +0,1 pp Precision, die 17 Merkmale erklären 1,1 % der Zeitvarianz
(R² = 0,011, zweifach belegt). Präzision bleibt Ziel, ist aber **kein Tor** mehr.

Diese Schwelle ist der richtige Maßstab, und sie ist der Grund, warum dieses
Review anders sortiert als eine klassische Roadmap: Nicht „was ist schwer",
sondern „was steht zwischen dir und einer geschlossenen Beta".

---

## 3 · Stand gegen die Vision

### Die fünf Erlebnis-Punkte

| Punkt | 30.07. | **13.08.** | Was sich bewegt hat |
|---|---|---|---|
| 1 · Erkennung | 55 % | **58 %** | Betriebspunkt `gap=150`: LOSO-Precision 50,5 → 62,8 %. In der Praxis noch nicht nachgewiesen (Abschnitt 5e). |
| 2 · Report | 65 % | **72 %** | Composite 30 → 86 %, `beat_alignment` 86 %, Set-Dramaturgie neu. Bass-Overlap unverändert 15 %. |
| 3 · Coach | 30 % | **30 %** | Unverändert. Alle 50 Reports tragen dieselbe eine Vorlage-Übung. |
| 4 · Fortschritt | 25 % | **40 %** | Supabase-Historie ist gebaut und der Login ist seit heute an. Fehlt: einmal vorführen. |
| 5 · Teilen | 10 % | **10 %** | Unverändert. Keine Export-Bibliothek im Projekt. |

### Die drei Burggräben

| Burggraben | 30.07. | **13.08.** | Begründung |
|---|---|---|---|
| 1 · Daten-Schleife | 30 % | **35 %** | Halb belegt: mehr Labels kaufen Recall (+17,4 pp von 4→24 Sets), keine Precision (+1,6 pp bei ±6,0 pp Streuung). Die Mechanik greift, das Wachstumsargument trägt nur zur Hälfte. |
| 2 · Library-Verbindung | 70 % | **72 %** | 6112 von 6113 Pfaden auf macOS aufgelöst, `uint16`-Überlauf im Landmark-Pfad behoben. Weiter brach: 6673 rekordbox-Beatgrids und 432 Cue-Punkte. |
| 3 · Ehrlichkeit | 60 % | **70 %** | Im Code belegt (Job 1, Selbsttest, `scoringVersion`). In den Daten **nicht angekommen** — siehe Abschnitt 5a. Deshalb kein „belegt". |

### Die Roadmap-Teile

| | 30.07. | **13.08.** |
|---|---|---|
| Teil 1 · Audio-Engine | 60 % | **65 %** |
| Teil 2 · Frontend | 55 % | **60 %** |
| Teil 3 · Online gehen | 10 % | **15 %** |

**Gesamt: rund 45 % der Vision** (30.07.: 40 %). Wie zuvor gilt: Die
verbleibenden 55 % sind nicht gleich schwer. Der Forschungsteil (sekundengenaue
Erkennung) ist ein Bruchteil davon — der Rest ist absehbare Handwerksarbeit.

---

## 4 · Kennzahlen-Tafel

### Erkennung

| Größe | Wert | Quelle |
|---|---|---|
| Aktiver Betriebspunkt | `min_p = 0,6`, `gap = 150 s` | `track_change_gbm.json` |
| LOSO-Validierung | **R 92,4 % · P 62,8 % · F1 0,748** | ebd., 25 Sets / 3537 Kandidaten |
| Vorheriger Punkt (`gap=90`) | R 94,1 % · P 50,5 % · F1 0,657 | `SITZUNG_2026-08-10.md` |
| Referenzmetrik in der Praxis | Recall 71 % · Precision 74 % · strikt korrekt 29 % | `analyze_timing_bias --check`, 28 Aufnahmen, 286 Übergänge |
| Timing-Streuung | **σ = 54,58 s**, Median −29,43 s, 85 % zu spät | ebd. |
| Innerhalb 8 s | **5 %** | ebd. |
| Markerzahl vs. echte Übergänge | 317 auf 170 | `tools/eval/nms2.py` |
| Ausschöpfung der Orakel-Schranke | 93–95 % | ebd. |
| Zeitvorhersage aus 17 Merkmalen | R² = 0,011 | `tools/eval/zeit_regression.py` |

> **Wichtig:** Die Praxiszahlen (71/74/29, σ 54,58) stammen aus Ground Truth zu
> Analysen, die mit `gap=90` gefahren wurden. Der neue Betriebspunkt ist darin
> **nicht enthalten**. Was der Retrain praktisch gebracht hat, ist ungemessen.

### Report — Befüllung über alle 431 Übergänge in 50 Reports

| Messwert | 30.07. | **13.08.** |
|---|---|---|
| BPM, Tonart, Camelot | 100 % | **100 %** |
| `quality_score` | 100 % | **100 %** (Spearman +0,014 gegen menschliches Urteil) |
| `phrase_alignment_score` | 100 % | **100 %** (misst nichts, ρ = 0,014) |
| `composite_quality_score` | 30 % | **86,3 %** ⬆ |
| `beat_alignment_score` | — | **86,3 %** |
| `harmonic_clash_score` | — | **80,7 %** |
| `vocal_overlap_score` | — | **80,7 %** (Median 100 — feuert praktisch nie) |
| `exit_quality_score` | — | **76,6 %** |
| `energy_dip_pct` | 50 % | **50,3 %** |
| `loudness_jump_db` | 50 % | **49,7 %** |
| `bass_overlap_score` | **15 %** | **15,5 %** ← unverändert |
| `track_in` / `track_out` (echte Tracknamen) | — | **19,0 %** |
| `scoringVersion` gestempelt | — | **0 von 50** |

Composite-Gewichte nach dem Refit vom 11.08. auf 170 bewerteten Übergängen:

```
beat_alignment  0,980   ← die einzige Dimension mit Signal (Spearman +0,315)
exit_quality    0,020
harmonic_clash  0,000   ← Demucs, Gewicht null
vocal_overlap   0,000   ← Demucs, Gewicht null
phrase_timing   0,000
```

Spearman gegen menschliches Urteil: Training 0,421 / **unabhängiger Test 0,220**.

### Betrieb und Technik

| Größe | Wert |
|---|---|
| Library-Index | 6113 Tracks · 6112 macOS-Pfade · 1 Rest-Windows-Pfad · fp/ + lm/ je 6113 · 1,7 GB |
| Datenstamm | 50 Reports · 45 Ground-Truth-Dateien · 13 GB (40 wav, 6 mp3) |
| Ground Truth doppelt | `daten/ground_truth` 45 · `audio-engine/.../ground_truth` 24 · **24 Sets in beiden** |
| Backend | 19 Endpoints · 10.732 LOC in `app/` · 39 Dateien toter Code in `app/experimental/` |
| Tests | 226 (30 Dateien) — laut `CLAUDE.md` grün, hier nicht nachgefahren |
| Frontend | 29 Routen · TanStack Start + React 19 + Supabase · `node_modules` vorhanden |
| Login | `DEV_BYPASS_AUTH = false` ✅ (seit heute) |
| Bezahlschranke | `PAYWALL_DISABLED = true` (bewusst) |
| `.env` | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `VITE_*` ✅ · **`SUPABASE_SERVICE_ROLE_KEY` fehlt** |
| Git-Remote | `github.com/broeni-hub/mixcoach-audio-engine` |
| Push-Stand | **7 Commits nicht gepusht**, `main` 13 Commits hinterher, letzter Fetch 10.08. |

---

## 5 · Fünf Befunde, die heute in keinem Projektdokument stehen

### 5a · Die Ehrlichkeitslinie ist im Code, nicht in den Daten

`analysis_mapper.py:104/106` setzt `beatmatching` und `timing` auf `None`,
`NOT_YET_MEASURED` listet fünf Einträge. Nachgezählt in den 50 gespeicherten
Reports:

```
beatmatching = None :  0 von 50      notMeasured = ['eq','creativity','frequency'] : 50 von 50
timing       = None :  0 von 50      mapperVersion = 'honest-v2'                   : 50 von 50
```

Der Grund ist banal: Seit dem 31.07. wurde **keine Analyse neu gerechnet**. Der
Code ist ehrlich, die Historie nicht. Solange das so bleibt, sieht der DJ in
jedem seiner Sets weiter eine Beatmatching-Note von 96–100 aus einem
Tempo-Schätzer, der in 89 % der Fälle exakt 0,0 Drift meldet.

Das ist **der größte verbliebene Verstoß gegen den Markenkern** — und er ist
unsichtbar, weil er nicht im Code steht, sondern in Dateien, die niemand mehr
ansieht. Ein Backfill-Skript nach dem Muster von `tools/backfill_composite.py`
behebt ihn in einem halben Tag.

### 5b · Echte Tracknamen stehen an jedem fünften Übergang

Die Vision verspricht: „mit echten Tracknamen, nicht ‚Track 3'". Gemessen:
`track_in` und `track_out` sind in **82 von 431 Übergängen (19,0 %)** gesetzt.
In 34 von 50 Reports gibt es überhaupt eine Trefferliste.

Das ist nicht dasselbe wie der Fingerprint-Recall von 0,90 — der beschreibt, ob
ein Track im Set gefunden wird. Ob an einem konkreten Übergang **beide Seiten**
benannt sind, ist eine andere und strengere Frage, und sie stand bisher nicht
in den Zahlen. Burggraben 2 sieht deshalb von der Produktseite schwächer aus als
von der Messseite.

### 5c · `start_sec` schlägt `mid_sec` — anders als am 30.07. gemessen

`ZUKUNFTSWEGE_2026-07-30.md` 1.6 hält fest: „Kein Schätzer schlägt `mid_sec`",
für `start_sec` σ 79,68 bei n = 56. Heute mit dem projekteigenen Werkzeug
(`predictions_from_analyses.py` → `analyze_timing_bias --predictions`) auf
**derselben Teilmenge n = 97** neu erhoben:

| | `mid_sec` | `start_sec` |
|---|---|---|
| Median | −32,95 s | **−10,40 s** |
| σ | 46,15 s | 47,00 s |
| innerhalb 8 s | 4 % | **21 %** |
| innerhalb 16 s | 20 % | **37 %** |
| Engine zu spät | 90 % | 65 % |

Lesart: `start_sec` nimmt dem Fehler den **systematischen Anteil** (Bias −33 s →
−10 s, Trefferquote 5×), nicht die **Streuung** (σ unverändert). Genau das sagt
die Blend-Definitions-These voraus: `mid_sec` markiert das Ende des Blends,
`start_sec` zielt auf den Anfang — den richtigen Begriff, nur verrauscht.

**Der ehrliche Gegeneinwand steht im Regressionswächter:** Auf den 71
Übergängen, die du als `correct` bestätigt hast, liegt `start_sec` im Median
+16,47 s daneben, nur 18 % innerhalb 8 s. Ein pauschaler Umstieg tauscht also
Gewinn bei `timing_off` gegen Verlust bei `correct`. Ob die Rechnung aufgeht,
sagt erst eine gemeinsame Metrik über beide Gruppen.

**Kosten der Klärung: etwa ein Tag.** Für den mit Abstand größten offenen Hebel
in Punkt 1 ist das billig — und die Werkzeuge dafür liegen bereits im Repo.

### 5d · Die Arbeit vom 11.–13.08. liegt nur auf dieser Platte

```
nicht gepusht (HEAD vs origin/setup/macos-umzug):  7 Commits
main hinterher:                                   13 Commits
letzter Fetch:                                    10.08.2026, 19:10
```

Betroffen sind unter anderem der Composite-Backfill, der Selbsttest, die
Supabase-Korrektur und die Scoring-Version. Das GitHub-Repo wurde am 10.08.
genau gegen dieses Risiko eingerichtet — und ist seither nicht benutzt worden.

### 5e · Die Referenzmetrik misst noch das alte Modell

Der Retrain vom 10.08. hat den Betriebspunkt auf `gap=150` gesetzt
(LOSO-Precision 62,8 %). Die Praxiszahlen (Recall 71 % / Precision 74 %) stammen
aber aus Ground Truth zu Analysen mit `gap=90`. **Der wichtigste Fortschritt der
letzten Wochen ist in der Referenzmetrik nicht sichtbar** — und wird es erst,
wenn Sets mit dem neuen Punkt analysiert und bewertet sind.

---

## 6 · Warum zuletzt so viel korrigiert werden musste

Deine Beobachtung stimmt und lässt sich auszählen. Von 25 Commits seit dem
31.07. sind **acht Korrekturen an vorherigen eigenen Aussagen**:

| Commit | Was korrigiert wurde |
|---|---|
| `fdf2b00` | Ein ganzer Tag K1-Arbeit lag unsichtbar in `.claude/worktrees/` — vorher als „nicht begonnen" berichtet |
| `9a5d5d2` | „drei Zahlen, die nicht mehr stimmten" in der Doku |
| `073b23f` | Zwei verlorene Messskripte rekonstruiert; Retrain-Suchgitter war zu eng |
| `e2f6507` | Vier Streudateien im Datenstamm wieder entfernt |
| `2e4087d` | Der Stem-Schalter bewirkte nichts und meldete nichts (torch/demucs fehlten) |
| `1bec471` | „mein Rat von gestern ist widerlegt" — Weg C → C′ |
| `56ff86c` | „Die Historie ist nicht ungebaut, sie ist abgeschaltet" |
| `2a83684` | Supabase-Schlüssel verwechselt — **du hattest recht, die Diagnose war falsch** |

### Fünf wiederkehrende Ursachen

**1 · Der Zustand liegt an zwei Orten.** Ground Truth in zwei Ordnern (45 vs. 24,
24 Sets doppelt), Code in einem unsichtbaren Worktree, Doku aus dem Juli neben
Code aus dem August. Jede dieser Korrekturen entstand daraus, dass jemand den
falschen Stand gelesen hat — mich eingeschlossen. **Das ist die teuerste
Einzelursache.**

**2 · Verschluckte Fehler.** `except Exception: pass` um den torch-Import,
`fireAndForget` um den Supabase-Sync. Die App sah aus, als arbeite sie. In einem
Projekt, dessen Markenkern Ehrlichkeit ist, ist der verschluckte Fehler die
teuerste Codezeile — der Satz steht inzwischen in `CLAUDE.md`, und er ist richtig.

**3 · Kein Gedächtnis zwischen Sitzungen.** Messskripte lagen im Scratchpad und
sind mit der Sitzung verschwunden. Und `memory.md` führt bis heute
`tools/real_mix_labeler/` und `tools/active_learning/` als implementiert — sie
existieren nicht und haben nie existiert. Eine optimistische Notiz wurde vier
Wochen lang als Tatsache weitergereicht.

**4 · Der Rechnerwechsel.** `requirements.txt` war ein `pip freeze` der
Windows-Engine; von 142 Paketen kamen 99 an, torch und demucs fehlten still.
Dazu Track-IDs am Pfad-String, NFC/NFD, Windows-Pfade im Index. Das ist der
Anteil deiner Vermutung, der zutrifft — aber er erklärt höchstens die Hälfte.

**5 · Diagnose vor Prüfung.** Der Supabase-Fall ist der klarste: eine plausible
Ableitung („Key fehlt → Sync tot") statt eines Blicks darauf, welcher Key
tatsächlich gebraucht wird. Du hast widersprochen, und du hattest recht. Genau
davor warnt die eigene Arbeitsregel — *„immer empirisch messen, nie theoretisch
herleiten"* — und genau dagegen wurde verstoßen.

### Einordnung

Diese Korrekturen sind **kein Zeichen eines kaputten Prozesses**. Sieben der
acht kamen von Claude Code selbst, ohne dass jemand nachgehakt hat; die achte
kam von dir. Ein Projekt, in dem falsche Zahlen wochenlang unwidersprochen
stehen bleiben, wäre schlechter dran — die Belegpflicht in den Prompts wirkt.

Der Preis ist trotzdem real: Aus deiner Sicht ist das Rauschen, und es kostet
Vertrauen in jede neue Zahl.

### Vier Gegenmaßnahmen, konkret

| Maßnahme | Aufwand | Wirkt gegen |
|---|---|---|
| **Selbsttest zur Pflicht am Sitzungsanfang** — `MixCoach-Selbsttest.command` doppelklicken, Ergebnis in die Sitzung geben | 2 min je Sitzung | Ursachen 1, 2, 4 |
| **Doppelstamm auflösen** — `audio-engine/.../ground_truth/` und `analysis_results/` archivieren oder löschen | 1 h einmalig | Ursache 1 |
| **Push nach jeder Sitzung** — `MixCoach-Hochladen.command`, Worktrees nach dem Merge aufräumen | 1 min je Sitzung | Ursachen 1, 3 |
| **`memory.md` gegen das Repo abgleichen** — mindestens die falsche 4-Stufen-Pipeline streichen | 30 min | Ursache 3 |

---

## 7 · Offene Posten, sortiert nach der Live-Schwelle

### Bedingung 1 — jeder angezeigte Wert ist gemessen

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **B1** | **Ehrlichkeits-Backfill über die 50 Reports** — `beatmatching`/`timing` auf `None`, `notMeasured` auf die Fünferliste | ½ Tag | offen, unbemerkt |
| **B2** | **`quality_score` entscheiden** — C′ liegt seit 11.08. vor: `composite` als Kopfzahl, ohne Stems, mit ehrlichem Namen | **deine Entscheidung** | wartet |
| **B3** | **`bass_overlap_score` von 15,5 % auf ~100 %** — der Wert, den sonst niemand anbietet. Ursache klären (laut Refit **nicht** Demucs) | 2–3 Tage | offen |
| **B4** | **`loudness_jump_db` von 49,7 % hoch** | 1–2 Tage | offen |
| **B5** | **`notMeasured` dynamisch machen** statt fester Dreier-/Fünferliste | 1 Tag | offen |

### Bedingung 2 — die Historie überlebt einen Gerätewechsel

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **H1** | **Vorführen:** Analyse hochladen → Browser-Profil wechseln → anmelden → nachsehen | ½ Tag | Blocker gefallen, nicht vorgeführt |
| **H2** | **`SUPABASE_SERVICE_ROLE_KEY` in `Frontend/.env`** — schaltet LLM-Coaching (`coach-feedback.functions.ts`) und Beta-Funktionen frei. Für die Historie **nicht** nötig | 10 min | **nur du** |

### Bedingung 3 — drei Sets zeigen eine Entwicklung

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **F1** | **Drei Sets desselben DJs neu analysieren** — mit `gap=150` und `scoringVersion 3`. Ohne gestempelte Reports gilt jeder Vergleich als unzulässig (`vergleichbar()` gibt `False`) | 1 Tag | offen |
| **F2** | **Fortschritts-Radar auf tragende Größen** stellen — `beat_alignment`, `loudness_jump_db`, `bass_overlap`. Phrasen-Timing bleibt draußen | 2–3 Tage | offen |

### Parallel, nicht blockierend

| | Aufgabe | Aufwand |
|---|---|---|
| **P1** | **`start_sec` vs. `mid_sec` zu Ende messen** (Abschnitt 5c) — gemeinsame Metrik über `correct` **und** `timing_off` | 1 Tag |
| **P2** | **Referenzmetrik gegen `gap=150` neu erheben** (Abschnitt 5e) | ½ Tag, braucht F1 |
| **P3** | **Zweite, blinde Labelrunde** — Instrument steht seit 31.07., `MixCoach-Zweitrunde.command` | **dein Abend** |
| **P4** | **Aufräumen** — 7 Commits pushen, Doppelstamm, Streudateien, `app/experimental/` (39 Dateien tot) | ½ Tag |

---

## 8 · Ausblick — die nächsten acht Wochen

Die Reihenfolge folgt der Live-Schwelle, nicht der Schwierigkeit.

**Woche 1 — Ehrlichkeit fertig machen.** B1, B5, P4. Am Ende zeigt kein Report
mehr eine Zahl, die nicht misst, und die Arbeit liegt auf GitHub. Kein
Forschungsrisiko, hoher Symbolwert: erst danach ist Burggraben 3 wirklich belegt.

**Woche 2 — Historie beweisen.** H1, H2, F1. Am Ende gibt es drei gestempelte
Reports desselben DJs in der Cloud, und Bedingung 2 ist einmal vorgeführt statt
behauptet. **Das ist der höchste Hebel im ganzen Projekt** — ohne Historie kann
Erlebnis-Punkt 4 nicht existieren, und Punkt 4 ist laut eurem eigenen
Geschäftsmodell der Abo-Grund.

**Woche 3 — Messwerte füllen.** B3, B4. Bass-Overlap ist der Wert, den die
Vision namentlich als Alleinstellung nennt und der in fünf von sechs Übergängen
fehlt.

**Woche 4 — die Timing-Frage einmal sauber beantworten.** P1, P2. Nicht als
Forschungsprojekt, sondern als eintägige Messung mit vorhandenen Werkzeugen.
Danach weißt du, ob `start_sec` der Ausweg ist oder ob die Erkennung so bleibt,
wie sie ist. **Beides ist ein Ergebnis.**

**Woche 5–6 — den Coach auf messbaren Boden stellen.** Übungen aus eigenem
Material, aber nur aus Größen, die tragen: „Bei deinem Übergang von X nach Y kam
B 4,2 dB lauter rein. Mix ihn nochmal, Ziel unter 1 dB." Das LLM ist verdrahtet
und braucht nur H2. Punkt 3 steht seit sechs Wochen bei 30 % — das ist die
größte Einzellücke zur Vision.

**Woche 7 — Demo-Report, Onboarding, Teilen.** Ab hier kann jemand anderes als du
das Produkt verstehen, ohne dass du daneben sitzt. Vorher ist jeder Beta-Test
verschenkt.

**Woche 8+ — online gehen.** Hosting, DSGVO-Basics, dann Stripe.

**Ziel: geschlossene Beta in rund 8 Wochen**, in der jeder angezeigte Wert
gemessen ist — ohne dass die Timing-Frage vorher gelöst sein muss.

---

## 9 · Was nur du tun kannst

1. **`SUPABASE_SERVICE_ROLE_KEY` eintragen** (H2, 10 min). Supabase → Project
   Settings → API → `service_role`. Nach `Frontend/.env`, niemals ins Repo.
   Schaltet das LLM-Coaching frei — das ist die Voraussetzung für Punkt 3.
2. **`quality_score` entscheiden** (B2). Die Vorlage liegt seit dem 11.08. in
   `SITZUNG_2026-08-10.md` Abschnitt 4. Empfehlung dort: **C′**.
3. **Die zweite, blinde Labelrunde fahren** (P3, ein Abend). Sie entscheidet, ob
   „sekundengenau" in `PRODUKTVISION.md` stehen bleiben kann.
4. **Drei Sets desselben Abends bereitlegen** (F1). Ohne sie ist Bedingung 3
   nicht prüfbar.

---

## 10 · Was über die Beta hinaus trägt

Vier Dinge unterscheiden „ehrlich und brauchbar" von „Weltklasse". Keines davon
ist heute begonnen.

**Das Intervall statt des Punktes.** Die Engine gibt `mid_sec` aus und meint das
Ende des Blends; der Mensch meint den Anfang. Ein ehrliches `[start, end]` —
`start_sec` misst bereits, `end_sec` ist in 100 % der Fälle ein festes `mid+16 s`
— würde einen großen Teil der 45 % `timing_off` ohne einen einzigen neuen
Datenpunkt zu `correct` machen. Abschnitt 5c beziffert den Hebel erstmals.

**Der rekordbox-Schatz.** 6673 Beatgrids und 432 Cue-Punkte liegen ungenutzt auf
der Platte. Deine eigene, von Hand kuratierte Wahrheit über Downbeats — genau
die Größe, die die Engine mit 22 % Trefferquote schätzt. `pyrekordbox` liest die
ANLZ-Dateien. Das ist der einzige Weg zu „sekundengenau", der nicht durch
Forschung führt.

**Tracknamen an jedem Übergang.** 19 % ist zu wenig für ein Versprechen, das im
Leitsatz steht.

**Ein zweiter Rater.** Alle Labels stammen von `sebro`. Ohne einen zweiten gibt
es keine Obergrenze dafür, was ein Modell überhaupt erreichen kann. Zwanzig
Übergänge mit einem befreundeten DJ sind der billigste wertvolle Datenpunkt, den
das Projekt bekommen kann.

---

## 11 · Das größte Risiko

Unverändert seit dem 30.07., und dieses Review bestätigt es: **Nicht die
Technik, sondern die Aufmerksamkeitsverteilung.** Die Übergangserkennung ist die
interessanteste Frage im Projekt und zieht die Zeit an, die Punkt 3, 4 und 5
bräuchten.

Der Beleg steht in diesem Dokument: Punkt 3 (Coach) steht seit sechs Wochen
unverändert bei 30 %, Punkt 5 (Teilen) bei 10 % — während in derselben Zeit
sieben Sitzungen an der Erkennung gearbeitet haben. Der Composite-Backfill vom
11.08. hat 78 Minuten GPU gekostet und ergeben, dass die Stems Gewicht null
haben. Das war richtig zu messen. Es hat den DJ keinen Schritt weitergebracht.

Ein halber Tag Backfill (B1) würde mehr für das Produkt tun als die letzten
zwei Wochen Messarbeit zusammen.
