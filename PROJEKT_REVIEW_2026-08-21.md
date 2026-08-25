# MixCoach — Projekt-Review, 21.08.2026

## 0 · Wie es entstand

Alle Zahlen unten sind heute am Repo nachgemessen: Git, Modell-Datei,
Referenzmetrik (`--check` plus der faire Vergleich über `--predictions`),
Befüllung über alle 450 Übergänge in `daten/analysis_results/`,
Frontend-Schalter, `.env`-Schlüsselnamen, Datenhygiene. Kein Wert stammt aus
`PROJEKTSTAND-CLAUDE.md`, `ROADMAP.md` oder einem Sitzungsbericht.

**Übernommen, nicht nachgemessen** (mit Datum der Ursprungsmessung):
Lernkurve +1,6 pp Precision (10.08.), R² = 0,011 der Zeitregression (30.07./
10.08.), Orakel-Ausschöpfung 93–95 % (10.08.), J7-Ergebnis 13:7 bei p = 0,263
(17.08.), Stem-Gewichte 0,000 (11.08.). Alle fünf brauchen Audio oder einen
Trainingslauf.

**Ein Vorbehalt zum Stand selbst:** Zwei Änderungen von heute liegen
**uncommittet** im Arbeitsbaum (`app/coach/profile.py`,
`tests/test_pegel_zeitreihe.py`). Die Zahlen zu Bedingung 3 unten beschreiben
den Stand **mit** dieser Reparatur; ohne sie steht dort das, was in Abschnitt 5
als erster Befund steht.

---

## 1 · Die kurze Fassung

Die App hat zwischen dem 18. und dem 21.08. eine Verschlechterung angezeigt,
die nicht stattgefunden hat — zwei Probedateien aus dem Cloud-Nachweis mit je
einem Übergang kippten die Fortschrittskurve, also genau die Messung, die
Bedingung 3 der Live-Schwelle trägt. Zugleich ist der Coach zum ersten Mal
seit dem 14.08. auf **zwei** belegten Größen statt einer, und die zweite lag
die ganze Zeit da, begraben unter einer Skala, deren Nullpunkt sechsmal so
hoch liegt wie der größte je gemessene Wert. Die Erkennung ist unberührt und
Ziffer für Ziffer reproduziert. Gegenüber der Vision stehen rund **53 %**
(17.08.: 52 %, 13.08.: 48 %). Das größte Risiko ist nicht mehr eine fehlende
Funktion, sondern dass die drei Bedingungen als „erfüllt" gelten, während zwei
von ihnen zuletzt nur durch Zufall nicht gekippt sind.

---

## 2 · Der Maßstab

`PRODUKTVISION.md`, seit 17.08.2026 das einzige maßgebliche Vision-Dokument.

> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die
> Historie einen Gerätewechsel überlebt, und drei Sets desselben DJs eine
> Entwicklung sichtbar machen.**

| Bedingung | 17.08. | **21.08.** |
|---|---|---|
| 1 · Jeder angezeigte Wert ist gemessen | erfüllt, bis auf B5 | **verletzt** — der Report sagt „beatmatching: nicht gemessen" und zeigt daneben eine Beatmatching-Übung mit Zahl (Abschnitt 5b) |
| 2 · Historie überlebt Gerätewechsel | gebaut, nie vorgeführt | **erfüllt** — vorgeführt am 18.08. |
| 3 · Drei Sets zeigen eine Entwicklung | erfüllt und sichtbar | **erfüllt, aber war es drei Tage lang nicht** (Abschnitt 5a) |

Das Fernziel (>90 % Erkennung, sekundengenau) bleibt Ziel und ist kein Tor.

---

## 3 · Stand gegen die Vision

### Die fünf Erlebnis-Punkte

| | 13.08. | 17.08. | **21.08.** | Begründung |
|---|---|---|---|---|
| 1 · Erkennung | 58 % | 58 % | **58 %** | Unberührt, Referenzmetrik identisch. Neu ist kein Fortschritt, sondern ein Verlust an Sicherheit: die Messung, die die menschliche Untergrenze klären sollte, ist mit einem Instrument entstanden, das die Antwort vorbelegt hat (19.08.). |
| 2 · Report | 78 % | 80 % | **80 %** | `beat_jitter_ms` an 86,7 % der Übergänge dazugekommen — aufgewogen vom Widerspruch in `notMeasured`. |
| 3 · Coach | 32 % | 50 % | **56 %** | Zwei belegte Größen statt einer. 202 Übungen statt 110, alle mit `metric`. 21 von 24 Aufnahmen mit Coach. Weiter kein Nützlichkeitsnachweis (J7: p = 0,263). |
| 4 · Fortschritt | 50 % | 55 % | **55 %** | Die Kurve ist nach der Reparatur besser als je dokumentiert (r = −0,740 gegen −0,622). Dagegen: die zweite Achse ist **flach**, und „bestes Set" zeigt ein fremdes Set. |
| 5 · Teilen | 10 % | 10 % | **10 %** | Unverändert, nicht begonnen. |

### Die drei Burggräben

| | 13.08. | 17.08. | **21.08.** | Begründung |
|---|---|---|---|---|
| 1 · Daten-Schleife | 40 % | 40 % | **42 %** | Korrektur am letzten Review: dort stand „die 9 Bewertungskonflikte sind weiter offen". `daten/ground_truth/KONFLIKTE.md` führt heute **Offen: 0**. Weiterhin null fremde Nutzer. |
| 2 · Library-Verbindung | 72 % | 72 % | **72 %** | Tracknamen an 21,8 % der Übergänge (17.08.: 20,4 %). Neu und schlecht: `collection.xml` liegt **nicht auf diesem Mac** — der einzige Weg zu „sekundengenau" ohne offene Forschung ist damit nicht begehbar. |
| 3 · Ehrlichkeit | 90 % | 95 % | **90 %** | Zurückgestuft. `notMeasured` ist weiter eine feste Fünferliste und widerspricht seit dem 20.08. nachweisbar dem, was im selben Report steht. |

### Die drei Teile der Roadmap

| | 13.08. | 17.08. | **21.08.** |
|---|---|---|---|
| Teil 1 · Audio-Engine | 70 % | 72 % | **74 %** |
| Teil 2 · Frontend | 62 % | 68 % | **68 %** |
| Teil 3 · Online gehen | 15 % | 15 % | **15 %** |

**Gesamt rund 53 %.** Der Zuwachs kommt aus Punkt 3; Punkt 4 hat einen
Fortschritt und einen gleich großen Fund gegeneinander.

---

## 4 · Kennzahlen-Tafel

| | Stand 21.08.2026 |
|---|---|
| Betriebspunkt | `min_probability 0,6` · `min_gap 150 s` |
| LOSO-Validierung | R 92,4 % · P 62,8 % · F1 0,748 (25 Sets / 3537 Kandidaten) |
| Referenzmetrik `dedup` | 28 Aufnahmen · 286 bewertete Übergänge · 91 `missed` |
| | Recall **70 %** · Precision **74 %** · strikt korrekt **29 %** |
| Timing | σ **54,58 s** · Median −29,43 s · 85 % zu spät |
| innerhalb 8 s / 16 s | **5 % / 22 %** |
| Tests | **319** Backend · 66 Frontend · `tsc` 0 Fehler |
| Reports / Aufnahmen / Übergänge | 56 / 24 / 450 |
| Übungen / Beobachtungen | **202** (alle mit `metric`) / 237 |
| Belegte Coach-Größen | **2** (17.08.: 1) |
| Ground-Truth-Stämme | 1 (45 Dateien) · KONFLIKTE offen: **0** |
| Library | 6113 Tracks · **1** Windows-Pfad übrig |
| `PAYWALL_DISABLED` | `true` |
| `DEV_BYPASS_AUTH` | `false` |
| Engine-Auth | **keine** — 0 `Depends` in `app/main.py`, CORS `allow_origins=["*"]` |
| Nicht gepusht | **2 Commits** · 1 verwaister Worktree |

### Befüllung je Übergang (450)

| Feld | 17.08. | **21.08.** |
|---|---|---|
| `quality_score`, `phrase_alignment_score` | 100 % | **100 %** (beide messen nichts, ρ ≈ 0) |
| `composite_quality_score` | 86,4 % | **86,7 %** |
| `loudness_jump_db` | 86,4 % | **86,7 %** ← tragende Größe 1 |
| `beat_alignment_score` | 86,4 % | **86,7 %** |
| **`beat_jitter_ms`** | — | **86,7 %** ← tragende Größe 2, neu |
| `harmonic_clash_score` / `vocal_overlap_score` | 78,7 % | **77,3 %** |
| `exit_quality_score` | — | **76,4 %** |
| `energy_dip_pct` | — | **49,3 %** |
| `bass_overlap_score` | — | **16,9 %** |
| Tracknamen | 20,4 % | **21,8 %** |

`reportRevision` verteilt sich auf 3 (5×), 4 (1×), 5 (18×), 7 (32×) — der
Korrekturweg greift, aber 24 Reports stehen auf einem älteren Stand.

---

## 5 · Befunde, die in keinem Projektdokument stehen

### a) Die Fortschrittskurve zeigte drei Tage lang das Gegenteil der Wahrheit

Am 18.08. entstanden beim Cloud-Nachweis zwei Probedateien,
`PROBE-J1-2026-08-18.wav` und `J1-NACHWEIS-2026-08-18.wav`, mit **je einem
Übergang bei 3,4 dB**. Sie standen nicht auf der Ausschlussliste
(`TESTDATEIEN = {"mix.wav", "synthetic_mix.wav"}`), landeten als zwei der drei
jüngsten Punkte auf der Kurve und drehten den Trend:

| | angezeigt | tatsächlich |
|---|---|---|
| aktueller Pegelsprung | 2,6 dB | 1,5 dB |
| delta (`lowerIsBetter`) | **+0,9** → „schlechter geworden" | 0,0 |
| Anteil über 3 dB | 66,7 % | **16,7 %** |
| delta Anteil | **+41,7 pp** | −2,4 pp |
| Trend über eigene Aufnahmen | r = −0,320 (p = 0,227) | **r = −0,740 (p = 0,002)** |

Die Sitzungsnotiz vom 18.08. hält ausdrücklich fest, die Probedateien
„stören keine Messung". Geprüft war das an der **Referenzmetrik** — die zählt
gelabelte Aufnahmen, und dort stimmt es. Die Fortschrittskurve zählt
**Aufnahmen**. Der Satz war für die eine Messung richtig und für die andere
falsch, und niemand hat den Unterschied bemerkt.

Heute repariert durch eine Regel, die ohne Pflege trägt: ein Kurvenpunkt
braucht mindestens drei Übergänge, weil ein Median über einen Wert keiner ist.
Im Bestand trennt die Grenze sauber — **jede** Test- und Probedatei hat genau
einen Übergang, **jede** echte Aufnahme mindestens drei.

### b) Der Report widerspricht sich selbst — zugunsten der Bescheidenheit

`MixCoach5.WAV` trägt gleichzeitig:

```
notMeasured        : ['beatmatching', 'creativity', 'eq', 'frequency', 'timing']
scores.beatmatching: None
beat_jitter_ms     : 9 von 9 Übergängen befüllt
Übung              : "Beats zusammenhalten bei 5:48 — schwankte um 26,0 ms"
```

Das gilt für **alle 56 Reports**. Seit dem 20.08. ist Beatmatching gemessen,
belegt (Spearman −0,336 über 237 Bewertungen) und Grundlage von 90 Übungen —
und derselbe Report sagt darüber „nicht gemessen". Das ist ein Verstoß gegen
die Ehrlichkeitslinie in der selteneren Richtung: nicht zu viel behauptet,
sondern eine echte Messung verleugnet. Ursache ist B5, seit dem 18.08.
beiseitegelegt: `notMeasured` ist eine feste Liste statt eines Blicks auf den
Befüllungsstand.

### c) Welcher Marker angezeigt wird, entscheidet, welche Zahl gut aussieht

Auf derselben Teilmenge (97 korrigierte Übergänge):

| Marker | Median | σ | innerhalb 8 s | Wächter `correct` (n=71) |
|---|---|---|---|---|
| `mid_sec` | −32,95 s | 46,15 s | **4 %** | **100 %** innerhalb 8 s |
| `start_sec` | −10,40 s | 47,00 s | **21 %** | **18 %** |

`start_sec` trifft die menschliche Korrektur fünfmal so oft — und die
bestätigten Übergänge fünfmal so selten. Der Grund ist kein Messfehler,
sondern der Anker: bestätigt wurde bei `mid_sec`, korrigiert wurde weg davon.
Das ist derselbe Mechanismus, der am 19.08. die K1-Messung wertlos gemacht
hat, nur an einer zweiten Stelle. **Die Ground Truth ist nicht unabhängig von
dem, was die Oberfläche angezeigt hat** — und das begrenzt, was σ überhaupt
aussagen kann.

### d) Die zweite Achse gibt es, und sie ist flach

Der Beat-Jitter über 14 eigene Aufnahmen: Pearson **−0,053** (p = 0,845),
erste drei 10,08 ms → letzte drei 10,08 ms. Er trägt eine Übung, aber keine
Entwicklung. Das gehört so angezeigt und nicht als Kurve, die nach Fortschritt
aussieht.

### e) Der „beste Übergang" stammt aus einem fremden Set

Das Profil zeigt als besten Übergang `Dixon WE2 Tomorrowland 2025.mp3`
(−0,0 dB). Der Trend schließt fremde Sets ausdrücklich aus
(`excludedForeign: 6`), `best`/`worst` nicht. Dem DJ seinen besten Übergang
aus einem Set zu zeigen, das er nicht gemixt hat, ist derselbe Fehler wie in
(a), eine Funktion weiter. **Nicht behoben.**

### f) Übungen entstehen an zwei Stellen

`app/coach/uebungen.py` (je Report) und `app/coach/profile.py` (über alle
Sets, mit eigenem DE/EN-Text). Am 20.08. wäre die zweite Größe fast nur im
Report gelandet und im Coach-Panel — dem, was der Nutzer sieht — unsichtbar
geblieben. Beide sind nachgezogen, **die doppelte Stelle bleibt.**

### g) Excel hat eine Spalte zerstört

In `labels_prefilled.csv` steht `phrase_beats_off` als **„10. Nov"** — aus
10.11 gemacht. Die Datei liegt als cp1252 vor, ist also mehrfach durch Excel
gegangen. Wer diese Spalte auswertet, rechnet mit Datteln.

### h) Die Engine ist offen

`app/main.py`: **0** `Depends`, CORS `allow_origins=["*"]`. Jeder, der den Port
erreicht, kann jede Analyse lesen und löschen. Lokal folgenlos — beim ersten
Hosting-Schritt ist es der erste Blocker, und in Teil 3 steht es nicht.

---

## 6 · Korrektur-Schleife

Von den letzten 40 Commits reparieren **4** eigenes Werk („Ein gescheiterter
Link schlägt die alte Sitzung", „Die Meldung nennt jetzt RLS beim Namen", „Das
Coach-Fazit zeigte weiter den Satz, den J4 entfernt hat", „Zwischenstand").
Das ist **10 %** — niedriger als der Eindruck aus den Sitzungsberichten, weil
die teuren Fälle keine Commits sind, sondern Funde: der stille Ausfall, der
wie ein Ergebnis aussieht.

Davon sind seit dem 11.08. **elf** gezählt (drei am 11.08., fünf am 18.08.,
K1 am 19.08., die Kurve und der `notMeasured`-Widerspruch heute). Der
gemeinsame Bauplan: eine Messung liefert eine Zahl, die Zahl ist plausibel,
und niemand prüft das Instrument.

**Was dagegen schon greift:** der Selbsttest (fängt fehlende Voraussetzungen),
`reportRevision` (bringt Korrekturen in den Browser), `conftest.py` (hält
Testläufe aus dem Datenstamm). **Was fehlt:** eine Regel, die vor dem Zitieren
einer Zahl das Instrument prüft. Die drei jüngsten Fälle wären alle daran
gescheitert.

---

## 7 · Offene Posten, sortiert nach der Live-Schwelle

**Bedingung 1 — jeder angezeigte Wert ist gemessen**

1. **B5: `notMeasured` dynamisch machen.** Bricht den Widerspruch aus 5b.
   Seit dem 18.08. beiseitegelegt, **3× verschoben**.
2. Die zwei Übungs-Stellen zusammenlegen (5f).

**Bedingung 3 — drei Sets zeigen eine Entwicklung**

3. **`best`/`worst` auf eigene Aufnahmen begrenzen** (5e). Angefangen, nicht
   fertig.
4. Die Jitter-Zeitreihe als zweite Achse — mit dem ehrlichen Befund, dass sie
   flach ist (5d).

**Ohne Bedingungsbezug, mit genanntem Grund**

5. **K1-Durchgang mit Werkzeug-Fassung 2** — 19 min. **3× verschoben**
   (19., 20., 21.08.). Solange er fehlt, ist unbekannt, wie viel Luft σ hat.
6. **`collection.xml` auf den Mac holen** — **3× verschoben**. Blockiert K2.
7. Entscheidungen zu `quality_score`, Übungsbibliothek, LLM-Coach — offen seit
   dem 14./15.08., **6 Tage**.
8. J7 mit größerer Stichprobe, oder Punkt 3 bleibt ohne Nützlichkeitsnachweis.
9. Passwort-Reset end-to-end prüfen (braucht ein echtes Postfach).
10. `SUPABASE_SERVICE_ROLE_KEY` fehlt — Warteliste und Einladungscodes sind
    lokal tot.

---

## 8 · Ausblick — die nächste Woche, an der Schwelle ausgerichtet

| Tag | Was | Bedingung |
|---|---|---|
| 1 | B5 fertig: `notMeasured` aus dem Befüllungsstand. Bricht den Widerspruch in allen 56 Reports. | 1 |
| 1 | `best`/`worst` auf eigene Aufnahmen. Halber Tag. | 3 |
| 2 | Jitter-Zeitreihe als zweite Achse, flach angezeigt. | 3 |
| 2–3 | Die zwei Übungs-Stellen zusammenlegen. | 1 |
| 3 | K1-Durchgang (Sebastian, 19 min) → danach σ-Untergrenze bekannt. | — |
| 4–5 | Engine-Auth und CORS, bevor irgendetwas gehostet wird. | Teil 3 |

Nicht auf dem Plan und mit Grund: mehr Sets labeln, ein fünfter
Blend-Onset-Schätzer, Grid-Search über die Schwellwerte, Stem-Trennung
einschalten. Alle vier sind gemessen erledigt.

---

## 9 · Was nur Sebastian tun kann

1. **`MixCoach-Zweitrunde.command` doppelklicken**, 19 min. Danach ist
   beantwortet, ob σ = 54,58 s noch Luft hat.
2. **`collection.xml` von der Windows-Maschine** nach `daten/` kopieren.
3. **`/app/coach` öffnen** und nachsehen, ob „Halte die Beats zusammen"
   dasteht — ich gebe keine Passwörter ein.
4. **Die zwei Probedateien löschen** (in der App, Delete-Button). Die
   Reparatur aus 5a fängt sie ab, aber sie liegen weiter im Stamm.
5. **Entscheiden:** `quality_score`, Übungsbibliothek, LLM-Coach.
6. **Push** — 2 Commits liegen nur lokal, dazu ein verwaister Worktree.

---

## 10 · Was über die Beta hinaus trägt

Der Datensatz (45 Ground-Truth-Dateien, ein Stamm, 0 Konflikte) und die
Library (6113 Tracks, Recall 0,90 bei Precision 1,0) sind nicht nachbaubar.
Die Ehrlichkeitslinie ist vom Anzeigeprinzip zum Betriebsprinzip geworden:
237 Beobachtungen stehen ausdrücklich **ohne** Handlungsaufforderung da. Und
die Methode selbst trägt — der Killer-Test vor dem Bau hat am 20.08. eine
Größe freigelegt, die zwei Wochen lang als tot galt.

## 11 · Das größte Risiko

**Nicht eine fehlende Funktion, sondern der Abstand zwischen „erfüllt" und
„nachgewiesen erfüllt".**

Der Beleg steht in diesem Review dreimal. Bedingung 3 galt seit dem 15.08. als
erfüllt und war es vom 18. bis zum 21.08. nicht — bemerkt durch Zufall, beim
Vorbereiten einer anderen Aufgabe. Bedingung 1 gilt als erfüllt und ist es in
allen 56 Reports nicht. Die K1-Zahl galt neun Tage als erhoben und war ein
Artefakt des Instruments.

Dreimal derselbe Mechanismus: eine Messung liefert eine plausible Zahl, die
Zahl wandert in ein Dokument, und das Dokument wird zitiert statt nachgemessen.
Die Live-Schwelle ist als Tor zur geschlossenen Beta gedacht — sie trifft also
zum ersten Mal Menschen, die nicht Sebastian sind. Wer sie auf Papierstand
aufmacht, führt einem Fremden eine Verschlechterung vor, die nicht stattgefunden
hat.

**Die Gegenmaßnahme ist billig:** jede der drei Bedingungen bekommt eine Prüfung
im Selbsttest, die bei jedem Lauf mitläuft — Bedingung 3 hätte am 19.08. rot
gezeigt statt am 21.08. durch Zufall aufzufallen.
