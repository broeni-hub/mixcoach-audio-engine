# Befund: Blend-Onset aus dem Mix-Audio allein

Stand: 29.07.2026 · Job B, Schritt 2 · **Ergebnis überwiegend negativ**

Dieses Dokument hält fest, was versucht wurde und warum es nicht getragen
hat — damit es niemand ein zweites Mal versucht.

## Ausgangspunkt: die Verfeinerung existiert bereits

Die Spec zeigt auf `app/experimental/transitions.py:47-49` als Ort, an dem
ein Intervall nur vorgetäuscht wird. Der Produktivpfad ist ein anderer:

- `app/audio/ml_classifier.py:342` ruft `foote.refine_boundary()` und legt `blend_start` ab
- `app/audio/transition_quality.py:86` macht daraus `setTransitions.start_sec`

Eine Rückwärtssuche nach dem Blend-Onset ist also vorhanden. Gemessen
(mode dedup, n=124, `correctedSec` als Referenz):

| | vs. `mid_sec` | vs. `start_sec` |
|---|---|---|
| Median | −29,08 s | −10,16 s |
| σ | 51,12 s | 48,14 s |
| innerhalb 8 s | 4 % | 17 % |

Sie holt zwei Drittel des Bias, aber σ sinkt kaum. Der Regressionswächter
auf der Gruppe `correct` zeigt Median **+15,29 s**: wo der Mensch `mid_sec`
akzeptiert hat, liegt `start_sec` zu früh.

Ursache, im Code sichtbar: `refine_boundary()` läuft **immer** zurück, bis
die Novelty unter 25 % des Peaks fällt, gekappt bei 256 Beats. Bei einem
harten Schnitt gibt es aber gar keinen Blend — dort erfindet die Suche eine
Länge. Die Blendlängen zeigen das: Häufung bei exakt 2,0 s (Suche lief ins
Leere) und Maximum 126,8 s (= die Kappung). Teils Artefakte der
Kernelbreite, keine Messung.

## Was versucht wurde

Idee: erst entscheiden **ob** geblendet wurde, dann **wo**. Als Beleg für
„eine zweite Schicht ist dazugekommen" eine Kurve aus drei gegen den ruhigen
Fensteranfang normierten z-Werten — Chroma-Entropie, Höhenenergie,
spektrale Dichte — und darauf die erste *anhaltende* Niveauüberschreitung.

Aufbau: `tools/blend_onset_cache.py` (Merkmale je Kandidat, 261 Fenster à
180 s) und `tools/blend_onset_eval.py` (Varianten, Split auf Set-Ebene).

## Ergebnis (Testhälfte, 9 Sets, n=31)

| Variante | Median | σ | in 8 s | `correct` in 8 s |
|---|---|---|---|---|
| `mid_sec` (alt gemessen) | −24,62 s | 38,30 | 6 % | 100 % |
| `start_sec` (heute) | −10,76 s | 38,65 | 10 % | 21 % |
| `foote w=60` | **+6,83 s** | 47,05 | **19 %** | 0 % |
| Evidenz z>3 / 8 s | −22,28 s | 54,62 | 3 % | 79 % |
| Evidenz z>2,5 / 6 s | −21,89 s | 57,13 | 6 % | 68 % |
| Evidenz z>4 / 10 s | −22,28 s | 54,88 | 3 % | 95 % |

Keine Evidenz-Variante schlägt die Basislinie. σ steigt bei allen auf 54–57
gegenüber 38–39. `foote w=60` erreicht als einzige Variante das
Median-Ziel (|Median| < 8 s), zerstört dafür aber die `correct`-Gruppe.

**Kein Kandidat kommt in die Nähe von „innerhalb 8 s ≥ 50 %".** Bestwert 19 %.

## Warum es scheitert

Entropie, Höhenanteil und spektrale Dichte steigen nicht nur, wenn ein
zweiter Track einsetzt — sie steigen auch bei Breakdown → Build → Drop
*innerhalb eines Tracks*. Genau diese Struktur ist in Clubmusik allgegenwärtig.
Ohne zu wissen, welcher Track gerade läuft, ist „eine zweite Schicht kam
dazu" nicht von „derselbe Track hat sich verändert" trennbar.

Das ist kein Parameterproblem. Feineres Tuning der Schwellen verschiebt nur,
welche der vielen Anstiege erwischt wird.

## Konsequenz: Job A ist Voraussetzung, nicht Parallelspur

Die Spec ordnet ein: „Job B braucht kein Audio und kann parallel laufen."
Nach diesem Befund gilt das für Schritt 1 (Referenzmetrik), aber nicht für
Schritt 2.

`app/audio/landmark_match.py:127` liefert bereits, was fehlt:

```
match() -> offset_frames   # geschaetzter Versatz (Track-Anfang im Mix)
```

Ist bekannt, welcher Track wann im Mix liegt, ist der Blend-Onset der
Moment, an dem Track B erstmals nachweisbar ist — **gemessen statt
geschlossen**. Genau das verspricht auch die Produktvision („Tools ohne
diese Verbindung raten; MixCoach weiß").

Dafür muss die Library auf dem Rechner liegen und der Index repathed sein
(`tools/repath_library_index.py`). Solange die 6113 Pfade ins Leere zeigen,
ist der einzige verfügbare Weg der, der hier gerade gescheitert ist.

## Empfehlung

1. Job A abschließen (Musik kopieren, Index repathen)
2. Blend-Onset aus Landmark-Treffern ableiten, gegen dieselbe Metrik messen
3. `refine_boundary()` erst dann anfassen — heute ist unklar, ob sie danach
   überhaupt noch gebraucht wird

Bis dahin bleibt `start_sec` wie es ist. Es ist messbar besser als `mid_sec`
und schlechter als alles, was hier versucht wurde, wäre eine Verschlechterung.

## Reproduzieren

```bash
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m tools.blend_onset_cache    # ~5 min, 211 MB
../../.venv/bin/python -m tools.blend_onset_eval
```
