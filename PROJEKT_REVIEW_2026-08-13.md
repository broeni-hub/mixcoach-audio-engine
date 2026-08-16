# MixCoach — Produktprojekt-Review

**Stand: 13.08.2026** · Auftraggeber: Sebastian · Anlass: „Wo stehen wir wirklich,
und warum musste zuletzt so viel korrigiert werden?"

---

> ## Fortgeschrieben am 13.08.2026, abends — nach dem F1-Lauf
>
> Zwischen der ersten und dieser Fassung liegen neun Commits
> (`fdb1780` … `4b2ced8`), abgearbeitet nach
> `PROMPT_ARCHITEKTUR_F1_F2_2026-08-13.md`. **Abschnitt 3, 4, 5, 7, 8 und 11
> sind neu gerechnet**, alle Zahlen heute Abend am Repo nachgemessen.
> Abschnitt 0, 2, 6, 9 und 10 stehen unverändert.
>
> Drei Dinge, die man beim Lesen wissen muss:
>
> 1. **Es ist mehr passiert als beauftragt, und es ist gut.** Neben der
>    Stamm-Zusammenführung wurde die Ehrlichkeitslinie in die Daten gezogen
>    (B1), der Pegelsprung nachgetragen (B4) — und dabei ist zum ersten Mal
>    eine belegte Entwicklung über Sets herausgekommen.
> 2. **F1 ist vollständig gelöst** — einschließlich des Korrekturwegs
>    (`819ee71`, nachgereicht am Abend, und `3002c11` am Morgen des 14.08.).
>    **F2 ist nicht begonnen**, wie vorgesehen. Siehe **Abschnitt 5f**.
> 3. **Eine Aussage aus `ARCHITEKTUR_BEWERTUNG_2026-08-13.md` ist widerlegt.**
>    Dort steht, `beat_alignment_score` sei „die einzige Dimension mit Signal".
>    Das stimmt nicht: `|loudness_jump_db|` trägt stärker (ρ −0,377 gegen
>    +0,315, gleiches n). Heute unabhängig nachgerechnet, Abschnitt 4.
>
> **Namenskollision aufgelöst:** Die Fortschritts-Aufgaben heißen ab jetzt
> `E1`/`E2` (vorher `F1`/`F2`). `F1`/`F2` bezeichnen ausschließlich die beiden
> fundamentalen Architektur-Änderungen.

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

**Der 13.08. ist der erste Tag, an dem das Produkt einen belegten Fortschritt
zeigen kann.**

`|loudness_jump_db|` ist über 13 eigene Aufnahmen vom 06.07. bis 28.07.
gefallen: Median 2,80 dB in den ersten drei Sets, **1,85 dB in den letzten
drei**, Anteil über 3 dB von ~50 % auf ~22 %, Trend r = −0,622. Damit ist
**Bedingung 3 der Live-Schwelle** — „drei Sets desselben DJs machen eine
Entwicklung sichtbar" — zum ersten Mal nicht behauptet, sondern gemessen.

Dass ausgerechnet der Pegelsprung es ist, war nicht der Plan: Er ist mit
ρ = **−0,377** gegen die eigenen Bewertungen der stärkste Zusammenhang im ganzen
Bestand — stärker als `beat_alignment` (+0,315), das bis heute als die einzige
tragende Größe galt. Nachgerechnet und bestätigt.

Weiter gewonnen: Ein Ergebnis- und ein Ground-Truth-Stamm statt je zwei, drei
verschollene Labels eingesammelt, neun Bewertungskonflikte dokumentiert statt
geraten. Die Ehrlichkeitslinie ist in den Daten angekommen — 50 von 51 Reports
tragen `beatmatching: null` und `scoringVersion 3`. Und die Kopfzahl
unterscheidet endlich: σ von 2,6 auf **12,5**.

**Und der Korrekturweg steht** (`819ee71`, `3002c11`). Damit ist **F1
vollständig gelöst** — die fundamentale Änderung, die heute blockierte. F2
(Nutzerbegriff in der Engine) ist nicht begonnen; das war so vorgesehen.

**Gegenüber der Vision stehen rund 50 %** (13.08. mittags: 45 %, 30.07.: 40 %).

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

| Punkt | 30.07. | 13.08. früh | **13.08. abends** | Was sich bewegt hat |
|---|---|---|---|---|
| 1 · Erkennung | 55 % | 58 % | **58 %** | Unverändert. Die Zusammenführung hat Recall 71 → 70 % geschoben (drei zusätzliche `missed`), σ und Precision blieben. |
| 2 · Report | 65 % | 72 % | **78 %** | `loudness_jump_db` 50 → 86 %, Kopfzahl streut endlich (σ 2,6 → 12,5), `notMeasured` benennt fünf statt drei Lücken. Bass-Overlap weiter 16 %. |
| 3 · Coach | 30 % | 30 % | **32 %** | Der LLM-Prompt bekommt keine erfundenen Zahlen mehr. Die Übungen sind weiter Vorlagen. |
| 4 · Fortschritt | 25 % | 40 % | **50 %** | **Bedingung 3 ist erstmals belegt** (r = −0,622 über 13 Aufnahmen). Die Historie überlebt den Gerätewechsel weiterhin nicht vorgeführt. |
| 5 · Teilen | 10 % | 10 % | **10 %** | Unverändert. |

### Die drei Burggräben

| Burggraben | 30.07. | 13.08. früh | **13.08. abends** | Begründung |
|---|---|---|---|---|
| 1 · Daten-Schleife | 30 % | 35 % | **40 %** | Drei von Hand gesetzte Labels aus dem zweiten Stamm eingesammelt, neun Konflikte in `KONFLIKTE.md` dokumentiert statt geraten. Die Schleife verliert keine Arbeit mehr. |
| 2 · Library-Verbindung | 70 % | 72 % | **72 %** | Unverändert. Weiter brach: 6673 rekordbox-Beatgrids, 432 Cue-Punkte. |
| 3 · Ehrlichkeit | 60 % | 70 % | **90 %** | In den Daten angekommen (51/51 `beatmatching: null`, auch die 16 archivierten), und ab jetzt korrigierbar (5f). Kein „belegt", weil die Vorführung durch die laufende App aussteht. |

### Die Roadmap-Teile

| | 30.07. | 13.08. früh | **13.08. abends** |
|---|---|---|---|
| Teil 1 · Audio-Engine | 60 % | 65 % | **70 %** |
| Teil 2 · Frontend | 55 % | 60 % | **62 %** |
| Teil 3 · Online gehen | 10 % | 15 % | **15 %** |

**Gesamt: rund 48 % der Vision** (13.08. früh: 45 %, 30.07.: 40 %). Der
Forschungsteil (sekundengenaue Erkennung) ist unverändert ein Bruchteil des
Rests — und hat sich heute kein Stück bewegt, ohne dass es geschadet hätte.

---

## 4 · Kennzahlen-Tafel

### Erkennung

| Größe | Wert | Quelle |
|---|---|---|
| Aktiver Betriebspunkt | `min_p = 0,6`, `gap = 150 s` | `track_change_gbm.json` |
| LOSO-Validierung | **R 92,4 % · P 62,8 % · F1 0,748** | ebd., 25 Sets / 3537 Kandidaten |
| Vorheriger Punkt (`gap=90`) | R 94,1 % · P 50,5 % · F1 0,657 | `SITZUNG_2026-08-10.md` |
| Referenzmetrik in der Praxis | Recall **70 %** · Precision 74 % · strikt korrekt 29 % | `analyze_timing_bias --check`, 28 Aufnahmen, 286 Übergänge, **91 `missed`** (vorher 88) |
| Timing-Streuung | **σ = 54,58 s**, Median −29,43 s, 85 % zu spät | ebd., unverändert nach der Zusammenführung |
| Innerhalb 8 s | **5 %** | ebd. |
| Markerzahl vs. echte Übergänge | 317 auf 170 | `tools/eval/nms2.py` |
| Ausschöpfung der Orakel-Schranke | 93–95 % | ebd. |
| Zeitvorhersage aus 17 Merkmalen | R² = 0,011 | `tools/eval/zeit_regression.py` |

> **Wichtig:** Die Praxiszahlen (71/74/29, σ 54,58) stammen aus Ground Truth zu
> Analysen, die mit `gap=90` gefahren wurden. Der neue Betriebspunkt ist darin
> **nicht enthalten**. Was der Retrain praktisch gebracht hat, ist ungemessen.

### Report — Befüllung über alle 432 Übergänge in 51 Reports

| Messwert | 30.07. | 13.08. früh | **13.08. abends** |
|---|---|---|---|
| BPM, Tonart, Camelot | 100 % | 100 % | **100 %** |
| `quality_score` | 100 % | 100 % | **100 %** (ρ +0,018) |
| `phrase_alignment_score` | 100 % | 100 % | **100 %** (misst nichts) |
| `composite_quality_score` | 30 % | 86,3 % | **86,1 %** |
| `loudness_jump_db` | 50 % | 49,7 % | **86,1 %** ⬆⬆ |
| `beat_alignment_score` | — | 86,3 % | **86,1 %** |
| `harmonic_clash_score` | — | 80,7 % | **80,6 %** |
| `vocal_overlap_score` | — | 80,7 % | **80,6 %** |
| `exit_quality_score` | — | 76,6 % | **76,4 %** |
| `energy_dip_pct` | 50 % | 50,3 % | **50,5 %** |
| `bass_overlap_score` | **15 %** | 15,5 % | **15,5 %** ← unverändert |
| `track_in` / `track_out` | — | 19,0 % | **19,0 %** ← unverändert |
| `scoringVersion 3` gestempelt | — | 0 von 50 | **50 von 51** ⬆⬆ |
| `scores.beatmatching = null` | — | 0 von 50 | **50 von 51** ⬆⬆ |

### Welcher Messwert trägt — heute unabhängig nachgerechnet

Zuordnung Report-Übergang zu Bewertung über `mid_sec`, Fenster < 5 s, gegen
`labels_prefilled.csv`:

| Messwert | Spearman gegen `human_rating` | n |
|---|---|---|
| **`\|loudness_jump_db\|`** | **−0,377** | 146 |
| `beat_alignment_score` | +0,315 | 146 |
| `composite_quality_score` | +0,146 | 146 |
| `quality_score` (die Kopfzahl) | +0,018 | 206 |

**Das kippt eine Aussage aus `ARCHITEKTUR_BEWERTUNG_2026-08-13.md`**, die
`beat_alignment_score` als „die einzige Dimension mit Signal" führt. Der
Pegelsprung trägt stärker, hat das physikalisch richtige Vorzeichen, eine echte
Einheit und eine Spannweite von −9,0 bis +9,3 dB. `beat_alignment` streut auf
einer 0–100-Skala mit σ = 2,59 — es unterscheidet kaum. `bass_overlap` ist zu
90 % exakt 0 oder 100, also ein Schalter, keine Abstufung.

**Für den Coach heißt das:** Der Pegelsprung, nicht `beat_alignment`, ist die
erste Regel. Die Übungstabelle in `PROMPT_PUNKT3_COACH_2026-08-13.md` Job 1
listet ihn als Regel 2 — die Reihenfolge dreht sich.

### Die Kopfzahl unterscheidet endlich

`scores.overall` wurde beim Backfill aus den Teilen neu gebildet, die im Report
stehen (`musicality`, `flow`) — kein neuer Rechenweg, nur ohne die zwei
gestrichenen Größen:

```
alt   Median 71   Spanne 65–77   sigma  2,6
neu   Median 62   Spanne 53–90   sigma 12,5
```

Die alte Note spannte über 51 Sets zwölf Punkte. `pipeline.py` nennt sie selbst
„eine Kopfzahl, die keinen DJ von einem anderen unterscheiden kann". Die neue
streut fünfmal so weit. Welche Eingänge je Report zur Verfügung standen, steht
jetzt in `overallInputs` — geraten wird nichts.

### Betrieb und Technik

| Größe | Wert |
|---|---|
| Library-Index | 6113 Tracks · 6112 macOS-Pfade · 1 Rest-Windows-Pfad · fp/ + lm/ je 6113 · 1,7 GB |
| Datenstamm | **51 Reports · 45 Ground-Truth-Dateien · ein Stamm** |
| Zweiter Stamm | **archiviert** in `_archiv_2026-08-13/` (93 Reports, 24 Bewertungen, 67 wav), mit `LIESMICH.md`; bewusst weiter in git — die JSON wiegen 2,2 MB und git hat alles als Umbenennung erkannt |
| Bewertungskonflikte | **9 offen**, dokumentiert in `daten/ground_truth/KONFLIKTE.md` |
| Backend | 19 Endpoints · 10.732 LOC in `app/` · 39 Dateien toter Code in `app/experimental/` |
| Tests | **235** (vorher 226) |
| Frontend | 29 Routen · TanStack Start + React 19 + Supabase |
| Login | `DEV_BYPASS_AUTH = false` ✅ |
| Bezahlschranke | `PAYWALL_DISABLED = true` (bewusst) |
| `.env` | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `VITE_*` ✅ · **`SUPABASE_SERVICE_ROLE_KEY` fehlt** |
| Engine-Auth | **keine** — 0 `Depends`, `allow_origins=["*"]`, kein `user_id` (F2 nicht begonnen) |
| Korrekturweg | **gebaut** — `lib/scoring-version.ts`, vier Stellen, 15 Frontend-Tests (vorher 7) |
| Toter Code | `app/experimental/` unverändert 39 Dateien, von außen 0 Importe |
| Push-Stand | **`main` 10 Commits hinterher** — nichts gepusht, drei Dokumente uncommittet |

---

## 5 · Fünf Befunde, die heute in keinem Projektdokument stehen

### 5a · Die Ehrlichkeitslinie ist im Code, nicht in den Daten — **erledigt**

> **Nachtrag abends:** Behoben in `177ce79`. Nachgezählt: `beatmatching = null`
> und `scoringVersion 3` in **50 von 51** Reports, `notMeasured` mit fünf
> Einträgen. Der eine ungestempelte Report ist `11da05af…` (`mix.wav`, eine
> Testaufnahme mit einem Übergang, deren Audio nur im Archiv liegt) — er blieb
> bewusst stehen statt einen unsicheren Stempel zu bekommen. Das ist die
> richtige Entscheidung.
>
> **Die Ursache unten war zu eng formuliert.** „Seit dem 31.07. wurde nichts neu
> gerechnet" ist die halbe Wahrheit; der strukturelle Grund ist das Fehlen eines
> Korrekturwegs — und der fehlt weiter (**5f**). Der Backfill ist auf der Platte
> angekommen, im Browser nicht.



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

### 5d · Die Arbeit vom 11.–13.08. liegt nur auf dieser Platte — **unverändert**

```
main hinterher:                    8 Commits   (vormittags: 13)
setup/macos-umzug hinterher:       5 Commits
letzter Fetch:                     10.08.2026, 19:10
```

Betroffen sind jetzt zusätzlich die Stamm-Zusammenführung, der
Ehrlichkeits-Backfill und der Pegelsprung-Nachtrag — also **genau die Arbeit,
die heute den ersten belegten Fortschritt erzeugt hat**. Das GitHub-Repo wurde
am 10.08. gegen dieses Risiko eingerichtet und ist seither nicht benutzt worden.

Dazu kommt: Die drei Dokumente dieses Tages (`ARCHITEKTUR_BEWERTUNG`,
`PROMPT_ARCHITEKTUR_F1_F2`, `PROMPT_PUNKT3_COACH`) sind noch nicht einmal
committet.

### 5f · Der Korrekturweg — **gebaut**, und er hat einen tieferen Fund freigelegt

Nachgeprüft am Code, nicht an der Commit-Meldung:

- `Frontend/src/lib/scoring-version.ts` (neu) — `versionVon()`, `loestAb()`,
  `mitNutzerstand()`. Gegenstück zu `scoring_version.py`. Höhere Version löst
  ab, Gleichstand bleibt, ungestempelt löst nie ab.
- Angewendet an **allen vier** Stellen: `store.ts:117`,
  `analysis-engine.ts:156`, die zweite Sperre bei Zeile 187 entfernt,
  `sync.ts:119–123` („DB gewinnt" nur noch bei Gleichstand).
- `__tests__/korrekturweg.test.ts` deckt alle vier Fälle aus dem Auftrag ab
  plus `archived`. Frontend-Tests **7 → 15**.

**Der eigentliche Fund lag tiefer, als ich ihn beschrieben hatte.** Die
Merge-Regeln allein hätten nichts bewirkt: Es gab **überhaupt keinen Pfad**, der
einen Report je neu von der Engine geholt hätte. Selbst der Knopf „Mit meinen
Korrekturen neu erkennen" rief `mergeRemoteAnalysisIntoStore` auf und lief dort
ins blanke `return` — er hat seit jeher nichts aktualisiert. Die Report-Seite
fragt jetzt beim Öffnen einmal nach (`app.analyses.$id.tsx:88–96`); ist die
Engine aus, bleibt der gespeicherte Stand stehen.

**Stand der Daten nach dem Backfill** (`177ce79`, `3002c11`), heute nachgezählt:

```
51 Reports:  beatmatching = null   51 / 51
             scoringVersion 3      44 / 51
16 archivierte Reports: ebenfalls nachgezogen
```

Die sieben ohne Stempel sind **kein Rückstand, sondern die richtige
Entscheidung**: Es sind genau die Reports ohne `loudness_jump_db` — sechs ohne
Audio (`REC001`, `REC010`) und die Testaufnahme `mix.wav`. Ein Wert der
Rechenvorschrift 3 fehlt ihnen, also tragen sie deren Stempel nicht. Genau
dafür ist `UNSTAMPED` gebaut.

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

> **Umbenannt:** Die Fortschritts-Aufgaben heißen jetzt `E1`/`E2`. `F1`/`F2` sind
> ausschließlich die fundamentalen Architektur-Änderungen.

### Zuerst — die Architektur-Schuld aus dem heutigen Lauf

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| ~~**F1**~~ | ~~Korrekturweg / eine Wahrheit je Analyse~~ | — | **gelöst** (`a814117`, `4b2ced8`, `819ee71`, `3002c11`) |
| **F1-Rest** | **Einmal vorführen:** Report öffnen → Backfill fahren → neu laden ohne Cache zu löschen. Die Tests belegen die Regel, nicht den Weg durch die laufende App | ½ h | offen |
| **F2** | **Nutzerbegriff in der Engine** — JWT durchreichen, `user_id`, Ablage trennen, CORS. Heute: 0 `Depends`, `allow_origins=["*"]`, kein `user_id` | 1–2 Wochen | nicht begonnen, **vor Teil 3** |
| **A2** | **`app/experimental/` archivieren + `CLAUDE.md` korrigieren** — 39 Dateien, von außen 0 Importe; die Karte in `CLAUDE.md:33` nennt sie weiter als Kandidatensuche | 1 h | offen |

### Bedingung 1 — jeder angezeigte Wert ist gemessen

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| ~~**B1**~~ | ~~Ehrlichkeits-Backfill~~ | — | **erledigt** (`177ce79`), 50 von 51 — Wirkung wartet auf F1.2 |
| **B2** | **`quality_score` entscheiden** — die Grundlage hat sich geändert: nicht mehr `composite` gegen `quality_score`, sondern **der Pegelsprung als tragende Größe**. Vorlage gehört neu geschrieben | **deine Entscheidung** | wartet, neu zu fassen |
| **B3** | **`bass_overlap_score`** — nicht mehr „von 16 % auf 100 %". Der Wert ist zu 90 % exakt 0 oder 100: **ein Schalter, keine Abstufung.** Erst klären, ob er überhaupt abstuft, dann füllen | 1 Tag Klärung | offen, neu gefasst |
| ~~**B4**~~ | ~~`loudness_jump_db` hochziehen~~ | — | **erledigt** (`fdb1780`), 50 % → 86 %, 158 von 158 in 36 s |
| **B5** | **`notMeasured` dynamisch machen** statt fester Liste | 1 Tag | offen (die Fünferliste steht, der Mechanismus fehlt) |
| **B6** | **`energy_dip_pct` von 50,5 % hoch** — dieselbe blockweise Lücke wie beim Pegelsprung, vermutlich derselbe Grund | 1 Tag | **neu** |

### Bedingung 2 — die Historie überlebt einen Gerätewechsel

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **H1** | **Vorführen:** Analyse hochladen → Browser-Profil wechseln → anmelden → nachsehen | ½ Tag | Blocker gefallen, nicht vorgeführt |
| **H2** | **`SUPABASE_SERVICE_ROLE_KEY` in `Frontend/.env`** | 10 min | **nur du** |

### Bedingung 3 — drei Sets zeigen eine Entwicklung

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **E1** | ~~Drei Sets neu analysieren~~ | — | **entfällt in dieser Form.** Der Nachweis ist über 13 vorhandene Aufnahmen gelungen, ohne Neuanalyse — und Neuanalyse hätte die Ground Truth entwertet |
| **E2** | **Fortschritts-Radar auf den Pegelsprung stellen** — die Kurve existiert in den Daten, nicht in der Oberfläche. `beat_alignment` (σ 2,59) und `bass_overlap` (Schalter) tragen sie nicht | 2–3 Tage | offen, **jetzt belegt machbar** |
| **E3** | **Die Vorbehalte prüfen** — 13 Aufnahmen über 22 Tage, r = −0,622 bei n = 13 ist ein Hinweis, keine Gewissheit. Ob sich frühe und späte Sets nur im Können unterscheiden, sagen die Daten nicht | ½ Tag | **neu** |

### Parallel, nicht blockierend

| | Aufgabe | Aufwand |
|---|---|---|
| **P1** | **`start_sec` vs. `mid_sec` zu Ende messen** (Abschnitt 5c) — gemeinsame Metrik über `correct` **und** `timing_off` | 1 Tag |
| **P2** | **Referenzmetrik gegen `gap=150` neu erheben** (Abschnitt 5e) — braucht neu analysierte Sets und damit neue Labels | ½ Tag + Labelarbeit |
| **P3** | **Zweite, blinde Labelrunde** — `MixCoach-Zweitrunde.command` | **dein Abend** |
| ~~**P4**~~ | ~~Doppelstamm, Streudateien~~ | **erledigt** (`a814117`, `4b2ced8`) |
| **P5** | **Neun Bewertungskonflikte entscheiden** — `daten/ground_truth/KONFLIKTE.md`. Auffällig: in `04804f27` setzt der neuere Stand 5 von 6 auf `not_a_transition`, wo der ältere `correct` sagte | **eine halbe Stunde, nur du** |
| **P6** | **Pushen** — 8 Commits und drei uncommittete Dokumente | 5 min |

---

## 8 · Ausblick — die nächsten acht Wochen

Die Reihenfolge folgt der Live-Schwelle, nicht der Schwierigkeit. Gegenüber der
Vormittagsfassung hat sich der Plan **verkürzt**, nicht verlängert: Woche 1 und
3 sind zum großen Teil schon abgearbeitet.

**Woche 1 — abschließen, was steht.** Vorführung des Korrekturwegs, A2, B5, P5,
P6. Der Weg ist gebaut und getestet; was fehlt, ist der eine Durchlauf durch die
laufende App. Dazu `app/experimental/` archivieren und `CLAUDE.md` berichtigen,
die neun Bewertungskonflikte entscheiden und pushen. Danach ist Burggraben 3
belegt.

**Woche 2 — die Entwicklung sichtbar machen.** E2, E3, H1, H2. Die Kurve, die
seit heute in den Daten steckt, gehört in die Oberfläche — und zwar mit ihren
Vorbehalten, nicht als Werbeversprechen. Danach Bedingung 2 einmal vorführen.
Am Ende dieser Woche sind **alle drei Bedingungen der Live-Schwelle erfüllt
oder vorgeführt**.

**Woche 3 — den Coach auf messbaren Boden stellen.** Der Auftrag liegt fertig in
`PROMPT_PUNKT3_COACH_2026-08-13.md`, mit **einer Korrektur**: Der Pegelsprung
ist Regel 1, nicht Regel 2 — er ist mit 86 % befüllt und trägt am stärksten.
Damit hat der Coach zum ersten Mal einen Satz, der stimmt: *„Bei 32:14 kam der
neue Track 4,2 dB lauter rein. Mix ihn nochmal, Ziel unter 1 dB."* Punkt 3
steht seit sechs Wochen bei ~30 % und ist die größte Einzellücke.

**Woche 4 — die zwei offenen Messfragen.** B3 (stuft Bass-Overlap überhaupt ab?),
B6 (`energy_dip_pct`), P1 (`start_sec` vs. `mid_sec`). Alles eintägige
Messungen mit vorhandenen Werkzeugen, keine Forschungsprojekte.

**Woche 5 — Demo-Report, Onboarding, Teilen.** Ab hier kann jemand anderes als du
das Produkt verstehen, ohne dass du daneben sitzt.

**Woche 6–8 — online gehen.** Und hier liegt die eine Verlängerung: **F2 gehört
an den Anfang dieser Phase**, nicht ans Ende. Erst Nutzerbegriff in der Engine,
dann Hosting, DSGVO, Stripe.

**Ziel: geschlossene Beta in rund 8 Wochen** — unverändert, obwohl F2 dazukommt.
Woche 1 und 3 des alten Plans sind heute in großen Teilen abgearbeitet worden.

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

Die Vormittagsfassung nannte hier die **Aufmerksamkeitsverteilung**: dass die
Übergangserkennung die interessanteste Frage bleibt und die Zeit anzieht, die
Punkt 3, 4 und 5 bräuchten. Und sie schloss mit der Behauptung, ein halber Tag
Backfill würde mehr für das Produkt tun als zwei Wochen Messarbeit.

**Der heutige Nachmittag hat das bestätigt** — deutlicher, als mir lieb ist. In
einem Lauf ohne eine einzige Zeile an der Erkennung sind entstanden: die
Ehrlichkeit in den Daten, ein Messwert von 50 auf 86 % befüllt, eine Kopfzahl
die unterscheidet, und der erste belegte Fortschrittsnachweis des Projekts. σ
steht unverändert bei 54,58 s, und es hat nichts gekostet.

**Das Risiko hat sich damit verschoben, nicht aufgelöst.** Die neue Fassung
lautet:

> Der Fortschrittsnachweis ruht auf **einer** Größe, in **einer** Stichprobe von
> 13 Aufnahmen über 22 Tage, von **einem** Rater bewertet. r = −0,622 bei n = 13
> ist ein deutlicher Hinweis und keine Gewissheit.

Die Versuchung ist jetzt, diese Zahl als Beweis zu behandeln, weil sie die erste
gute Nachricht seit Wochen ist. Der Markenkern verlangt das Gegenteil: E3 steht
nicht ohne Grund in der Liste, und die Vorbehalte gehören in die Oberfläche,
nicht nur in den Sitzungsbericht.

Das zweite Risiko ist unscheinbarer und heute größer geworden: **Der Fortschritt
dieses Tages existiert auf genau einer Festplatte.** Acht ungepushte Commits,
drei uncommittete Dokumente — darunter der Nachweis, auf den seit dem 30.07.
hingearbeitet wurde.
