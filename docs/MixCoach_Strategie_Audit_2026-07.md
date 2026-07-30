# MixCoach — Strategie- & Skalierbarkeits-Audit

**Datum:** 30.07.2026
**Auftrag:** Führt der aktuelle Weg zum Ziel? Wenn nein, welche fundamental anderen Wege gibt es?
**Methode:** Repo-Inventur mit Belegen, eigene read-only Messungen, Reproduktion der zitierten Kennzahlen.
Alle Messskripte liegen im Scratchpad-Ordner der Audit-Sitzung, es wurde kein Produktivcode verändert.

---

## 1. Executive Summary

**Der Engpass ist nicht das Labeln — es ist die Beat-Erkennung, und deshalb war die gesamte Label-Arbeit der letzten drei Wochen wirkungslos.** `app/audio/beats.py:20` ruft `librosa.beat.beat_track` ohne Tempo-Parameter auf; gemessen an 40 Tracks der eigenen Library liefert das **6 verschiedene BPM-Werte für 40 Tracks** und trifft nur in 22 % der Fälle auf ±1 BPM. Ein 2-BPM-Fehler lässt die Beat-Positionen über einen 5-Minuten-Track um ~10 Beats driften. Das Phrasenraster (`phrase_grid.py:19`) zählt 32 Beats ab dem *erkannten Segmentanfang* — es erbt damit den Beat-Fehler **und** den Detektor-Fehler (Precision 0.497). Ergebnis: `phrase_beats_off` korreliert mit ρ = 0.014 mit dem menschlichen Urteil; da es 35 % des `quality_score` stellt, ist die berühmte Null-Korrelation (ρ = 0.047 reproduziert, n=305) nicht überraschend, sondern zwangsläufig. Die Features messen den eigenen Detektorfehler, nicht das DJing.

Die Konsequenz ist hart: Seit dem letzten erfolgreichen Modell-Export am 08.07. wurden ~26 Sets gelabelt und 6 Retrains gefahren — **alle 6 endeten mit `ABBRUCH`**. Rund 17 Personenstunden für 0 Prozentpunkte. Eine Extrapolation von 53 % auf 90 % ist nicht teuer, sondern undefiniert: Eine Rate von null lässt sich nicht hochrechnen. Zusätzlich ist die Zielmetrik selbst entwertet — `CLUSTER_GAP = 105.0` erlaubt ±105 Sekunden Toleranz, und bei nur einem Rater ist die Inter-Rater-Reliabilität nicht messbar.

**Empfehlung:** Detection-Genauigkeit aufhören zu jagen. Stattdessen (a) Beat/Downbeat durch ein fertiges Modell ersetzen und (b) auf ein assistiertes Produkt umstellen, bei dem der DJ die Struktur liefert — was zu ~80 % bereits gebaut ist.

---

## 2. Ist-Zustand: verifizierte Fakten

### 2.1 Repo-Struktur und Aufwandsverteilung

Kein Git-Repo (kein Versionsschutz). Zeilenzahlen (`wc -l`, nur `.py`/`.ts`/`.tsx`):

| Bereich | LOC | Anmerkung |
|---|---:|---|
| `app/audio/` (ohne scoring/pipeline) | 3.893 | Detektoren, Matching, Loudness |
| `app/audio/scoring/` | 514 | die 5 Composite-Dimensionen |
| `app/audio/pipeline/` | 374 | Orchestrierung |
| `app/calibration/` | 1.521 | Retrain, Feature-Bau, Gewichts-Fit |
| `app/api` + `jobs` + `library` + `coach` + `core` + `main.py` | 1.701 | API-Schicht |
| `app/experimental/` | 1.796 | **toter Code, siehe 2.8** |
| `tools/` (ohne synth_mixer) | 2.070 | Benchmarks, Diagnose, Experimente |
| `tools/synth_mixer/` | 1.757 | synthetische Mix-Erzeugung |
| `tests/` | 2.835 | 184 Tests |
| Frontend `src/` | 22.042 | inkl. ~1.600 generierte Zeilen |

**Löwenanteil des Backend-Aufwands:** Audio-Analyse + Fingerprinting (~4.800 LOC) und die Trainings-/Kalibrier-Infrastruktur (~5.300 LOC inkl. tools). Die Scoring-Engine, um die es produktseitig geht, ist mit 514 LOC der kleinste Block.

### 2.2 Analyse-Pipeline (Weg einer Audiodatei) — mit gemessenen Zeiten

Einstieg `POST /analysis/jobs` (`main.py:46`) → `job_manager.py:168` `load_audio_file(max_duration_seconds=7200)` → `pipeline.run_set_pipeline` (`pipeline.py:61`).

Gemessen an einem **echten 69,7-Minuten-Set** (100 MB MP3, aus `daten/analysis_results/`):

| Schritt | Funktion | Zeit |
|---|---|---:|
| Laden | `loader.load_audio_file` | 8,0 s |
| Energiekurve | `energy.calculate_energy_curve` | 0,1 s |
| Tempo | `tempo.detect_tempo` | 8,8 s |
| Kandidatenzonen (87) | `set_analyzer_helpers.detect_set_transition_zones` | 0,1 s |
| Chroma-Matrix | `track_change_classifier.compute_chroma_matrix` | 22,2 s |
| MFCC | `ml_classifier.compute_mfcc_matrix` | 5,6 s |
| Hiband-Hüllkurve | `ml_classifier.compute_hiband_envelope` | 1,8 s |
| Beatgrid (8.855 Beats) | `beats.detect_beat_grid` | 13,7 s |
| ML-Auswahl (17 Übergänge) | `ml_classifier.select_track_changes_ml` | 1,3 s |
| Fingerprints laden (6.113) | `library.manager.load_fingerprints` | 4,8 s |
| **Library-Matching** | `library_match.match_library` | **140,6 s** |
| **Demucs-Stems** | `scoring/stems.separate_window` | **25,0 s je Übergang** |

**Hotspots:** Demucs (17 × 25 s = **424 s = 7,1 min**) und Library-Matching (141 s). Summe ohne Demucs 207 s; **mit Demucs ~10,5 Minuten für ein 70-Minuten-Set**. Rund 70 % der Rechenzeit entfallen auf Demucs — für den `composite_quality_score` (siehe 2.4).

`ROADMAP.md:31` nennt "mehrere Minuten pro Set" als zu senkendes Problem — das ist korrekt, die Ursache ist aber konkret benennbar und liegt nicht in der Analyse-Breite.

### 2.3 Transition Detection — und woher "53 %" kommt

Verfahren: Gradient-Boosting-Klassifikator (`ml_classifier.select_track_changes_ml`) über 87 Energie-Kandidatenzonen, 17 Features (`app/models/track_change_gbm.json`):
`score, blend, drop, bass_swap, chroma_75_15, chroma_45_10, mfcc_dist, rhythm_hi, e_before, e_current, e_after, pos_in_set, nearest_zone, edge, foote, beat_cv, exit_rough`.
Auswahlregel: `min_probability = 0.6`, `min_gap_seconds = 90.0`. Fallback auf Heuristik `detect_track_changes` (`pipeline.py:103`), wenn das ML nichts liefert. Fingerprint-Treffer überschreiben die ML-Zeiten (`merge_with_fingerprints`).

**Die Zahl 53 %:** stammt aus `dd/retrain_log.txt` (Lauf 27.07.2026 16:04, `AKTIV: R=87% P=53% F1=0.66`) und ist die **Precision** des aktiven Modells auf 19 ungesehenen Sets. Verifiziert. Das aktive Modell (`app/models/track_change_gbm.json`, geschrieben 28.07. 09:51) trägt die gespeicherte LOSO-Validierung **R = 0.941 / P = 0.497 / F1 = 0.65**.

**Die Metrik selbst (`retrain_model.py:199-228`):**
```python
CLUSTER_GAP = 105.0                                   # Zeile 72
hits = sum(1 for c in clusters
           if any(c[0] - CLUSTER_GAP <= s <= c[-1] + CLUSTER_GAP for s in selected))
recall = hits / len(clusters); precision = hits / len(selected)
```
Ein Marker zählt als Treffer bei **±105 Sekunden** Abstand. Bei Tracks von 4–6 Minuten ist das Trefferfenster bis zu 3,5 Minuten breit. Selbst unter dieser sehr großzügigen Toleranz liegt die Precision bei ~50 %.

**Es gibt keine feste Holdout-Menge.** Validierung ist ausschließlich Leave-One-Set-Out (`retrain_model.py:231`), erzeugt zur Laufzeit. Eine dauerhaft unangetastete Testmenge existiert nicht — im Code nicht und in der Doku nicht.

### 2.4 Scoring-Engine: Stand des Rebuilds

Alle 5 Dimensionen sind **implementiert**, keine Stubs (`harmonic_clash.py`, `vocal_overlap.py`, `exit_quality.py`, `beat_alignment.py`; `phrase_timing` kommt aus dem alten `scores['phrase']`).

Gewichtsbestimmung (`composite.py:32`):
```python
DEFAULT_WEIGHTS = {"harmonic_clash": 0.09, "vocal_overlap": 0.42,
                   "exit_quality": 0.0, "beat_alignment": 0.49, "phrase_timing": 0.0}
```
Ermittelt per **Zufallssuche** (`fit_composite_weights.py:45-48`): 4.000 zufällige Gewichtsvektoren + 300 Verfeinerungsrunden, Auswahl nach maximalem Spearman auf dem Trainings-Split. Der Docstring von `composite.py:20-27` nennt die Datenbasis selbst: **20 gematchte Übergänge, 14 Training / 6 Test**.

Das ist statistisch nicht tragfähig: Aus 4.300 Kandidaten wird der beste auf 14 Punkten gewählt; die zitierten Testwerte (0.47/0.62) beruhen auf **6** Beispielen und sind bei n=6 nicht signifikant. Zwei der fünf Dimensionen haben Gewicht 0.0, fließen also gar nicht ein.

**Eigene Nachmessung der Einzeldimensionen** (21 Übergänge, die sich Labels zuordnen ließen):

| Dimension | n | ρ vs. human_rating | p |
|---|---:|---:|---:|
| `beat_alignment` | 21 | **+0.472** | 0.031 |
| `harmonic_clash` | 21 | +0.153 | 0.507 |
| `exit_quality` | 19 | −0.023 | 0.924 |
| `vocal_overlap` | 21 | **−0.278** | 0.222 |
| `phrase_timing` | 21 | **−0.346** | 0.125 |

Nur `beat_alignment` zeigt ein positives Signal, und auch das hält einer Bonferroni-Korrektur über 5 Tests nicht stand (0.031 × 5 = 0.155). Bemerkenswert: `vocal_overlap` trägt das zweithöchste Gewicht (0.42), korreliert in dieser Stichprobe aber **negativ**. Das ist die Signatur eines Fits auf Rauschen.

**Der Composite-Score erreicht keinen Nutzer.** Er wird berechnet, in `analysis_mapper.py:281` in das Frontend-JSON gemappt — und im gesamten React-Code (`Frontend/src/`) **kein einziges Mal ausgelesen**. Die 7,1 Minuten Demucs pro Set produzieren eine Zahl, die niemand sieht.

### 2.5 Datenbestand (exakt gezählt)

Aus `labels_prefilled.csv` (429 Datenzeilen):

| Kennzahl | Wert |
|---|---:|
| Zeilen mit `human_rating` | **358** |
| davon mit `engine_quality_score` | 305 |
| verschiedene Sets (bewertet) | 31 |
| Labels je Set | min 1 / Median 9 / max 41 |
| **Duplikate** | **0** |
| Rater | **1** (`sebro`) |

Rating-Verteilung: `0 → 31 | 2 → 43 | 3 → 61 | 4 → 60 | 5 → 163`. Keine 1er.
Quelle: `erkannt 310 | missed 80 | nur_ground_truth 39`.

Ground-Truth (`daten/ground_truth/`, 45 Dateien): **356 Positiv-Anker**, **100 Negativ-Anker**.
Analyse-Reports: 38 (inkl. `archived/`), zusammen 419 `setTransitions`, davon **116 mit `composite_quality_score`**.
Audio: 31 Dateien, 9,9 GB. Fingerprint-Index: 6.113 Tracks (1,63 GB).
Label-Geschwindigkeit: 45 Sets vom 05.07. bis 28.07. (KW27: 5, KW28: 14, KW29: 20, KW30: 2, KW31: 4).

**Drei Angaben aus dem Auftrag sind damit widerlegt:**
1. *"239 Labels"* → tatsächlich 358 (die 239 waren vermutlich ein früherer Stand).
2. *"enthält Duplikate durch einen Delete-Bug"* → 358 bewertete Zeilen, 358 eindeutige `(set_id, time)`-Paare, null Duplikate.
3. *"fast nur 4er/5er-Ratings, keine 1er"* → keine 1er stimmt, aber 74 Bewertungen (21 %) liegen bei 0 oder 2. Die Schiefe ist real, aber nicht das Kernproblem.

**Ebenfalls widerlegt — die 4-stufige Trainingsdaten-Pipeline existiert nicht:**
`tools/real_mix_labeler/` und `tools/active_learning/` sind **nicht vorhanden** (geprüft per Glob über das gesamte Projekt). Es existiert nur `tools/synth_mixer/`. Eine separate React-Labeling-UI gibt es nicht; gelabelt wird im Haupt-Frontend über `SetTransitionsExplorer.tsx`. `mixcoach_eval_pipeline.py` existiert nicht.

### 2.6 Evaluation und Zykluszeit

Vorhandene Skripte: `app/calibration/retrain_model.py` (LOSO + Gate + Export), `auto_retrain.py` (Schwelle `RETRAIN_THRESHOLD = 10` neue Sets), `fit_composite_weights.py`, `export_labels_v3.py` (CSV-Export zur Excel-Kontrolle), `tools/benchmark_fingerprint.py`, `tools/benchmark_landmark_gapfill.py`. Bedienung per `.bat` im Projektroot.

Der Zyklus ist **halbautomatisiert**: Labeln (manuell, App) → `MixCoach-Retrain.bat` (automatisch) → Gate entscheidet über Export. Ein Feature-Cache (`feedback_features_cache.json`, 1,5 MB) verhindert erneute Feature-Extraktion für unveränderte Sets.

**Gemessene Zykluszeit (Änderung → Ergebnis):**
- Labeln eines Sets: erfordert Anhören. Sets sind 40–70 min → realistisch 20–40 min/Set. *(geschätzt, siehe Anhang)*
- Feature-Extraktion neuer Sets: entspricht einer vollen Analyse, ~3–10 min/Set (gemessen: 207 s ohne Demucs für 70 min).
- LOSO-Suche: 12 Konfigurationen × ~20 Folds. Aus dem Log ohne Zeitstempel je Lauf nicht exakt ableitbar, Größenordnung Minuten.
- **Ein vollständiger Zyklus mit 10 neuen Sets (die Retrain-Schwelle): grob 5–8 Stunden, davon der weit überwiegende Teil Handarbeit.**

Das ist aber nicht die relevante Zahl. Die relevante Zahl steht im nächsten Punkt.

### 2.7 Der Zyklus liefert seit dem 08.07. nichts mehr

`dd/retrain_log.txt` enthält **11 Trainingsläufe** seit 06.07.2026:

| Datum | Ergebnis |
|---|---|
| 06.07. 15:02 | ABBRUCH (deutlich schlechter) |
| 06.07. 15:14 | **Modell exportiert** |
| 06.07. 16:25 | abgebrochen (Strg-C) |
| 06.07. 21:25 | ABBRUCH (schlechter auf neuen Sets) |
| 08.07. 10:28 | ABBRUCH |
| 08.07. 15:16 | ABBRUCH |
| 08.07. 21:25 | **Modell exportiert** |
| 18.07. / 20.07. | abgebrochen (Strg-C) |
| 27.07. 11:22 | ABBRUCH |
| 27.07. 16:04 | ABBRUCH |
| 28.07. 07:31 (auto) | `"exported": false, "reason": "worse_on_new_sets"` |

Seit dem 08.07.2026 hat **kein einziger Lauf das Modell verbessert**. In diesem Zeitraum wurden ~26 weitere Sets gelabelt (KW29–31). Die Fixed-Eval-Precision auf ungesehenen Sets bewegte sich zwischen den beiden 27.07.-Läufen von 51 % auf 53 % — das ist Rauschen bei n=18 bzw. n=19 Sets, kein Fortschritt.

Der am 28.07. 09:51 exportierte Stand (real-only-Rezept) hat gegenüber seinem Vorgänger eine **niedrigere** gespeicherte Precision (0.497 vs. 0.564) und ein niedrigeres F1 (0.65 vs. 0.685). Das Gate ließ das durch, weil es Regression toleriert: `export_ok = (new_r >= 0.80) and (new_f1 >= old_f1 - 0.05)` (`retrain_model.py:370`).

### 2.8 Tests, Qualität, toter Code

- **184 Tests, 3 schlagen fehl** (`tests/test_feedback.py`: `test_verdict_roundtrip_and_override`, `test_missed_transitions_dedupe`, `test_timing_off_verdict_stores_corrected_time` — alle `FileNotFoundError` auf ein Ground-Truth-Temp-Verzeichnis). Laufzeit 168 s.
- Scoring-Tests existieren für alle 5 Dimensionen, sind aber **Unit-Tests auf synthetischen Eingaben** (46–53 LOC je Datei). Sie prüfen Rechenwege, nicht ob ein Score musikalisch sinnvoll ist. Wer eine Score-Funktion ändert, bekommt **keinen Regressionsschutz gegen Qualitätsverlust** — nur gegen Programmierfehler.
- **`app/experimental/` (1.796 LOC, ~40 Dateien) wird von keiner einzigen Datei außerhalb seiner selbst importiert.** Vollständig toter Code: eigene Datenbankschicht, eigenes Scoring (`energy`, `harmonic`, `phrase`, `tempo`, `transition_timing`, `recommendations`), `mix_advisor`, `smart_playlist`, `similarity`, `timeline_coach`.
- **Halbfertig, bewusst stillgelegt:** `landmark_match.py` (Shazam-artiges Hashing) ist funktionsfähig und getestet, aber absichtlich nicht im Live-Pfad (`pipeline.py:119-133`) — ~2.000 s pro Erkennungslücke. Korrekte Entscheidung, aber gebundene Arbeit ohne Produktwert.
- `labels_alt.csv` (304 Zeilen) enthält **kein einziges `human_rating`** — Karteileiche.

### 2.9 Coach-Feedback-Layer

**Kein LLM im Einsatz** (geprüft: keine Referenz auf `openai`, `anthropic`, `gpt-`, `claude-` in `app/` oder `tools/`).

Backend: `transition_quality._feedback` (`transition_quality.py:234`) baut aus Schwellwerten Sätze zusammen — Beispiel:
```python
if beats_off is not None and beats_off > 4:
    issues.append(f"liegt {beats_off:.0f} Beats neben dem Phrasenstart - ...")
```
Fallback, wenn keine Regel greift: *"Übergang bei {at} ist solide, aber nicht herausragend"*.
`rule_engine.evaluate_set_rules` + `coach_summary.generate_coach_summary` aggregieren auf Set-Ebene.
Frontend: `lib/coach.ts` (586 LOC) enthält eine statische `EXERCISE_LIBRARY` plus Mustererkennung (`detectPatterns`, `weeklyPlan`, `buildCoachInsight`).

**Wie viel Produktwert hängt woran?** Der gesamte Text ist Template-basiert und speist sich aus genau den Zahlen, die laut 2.4 nicht mit menschlichem Urteil korrelieren. Der Satz *"liegt 6 Beats neben dem Phrasenstart"* ist so verlässlich wie `phrase_beats_off` — also ρ = 0.014. **Der Feedback-Text erbt die Detection-Genauigkeit vollständig; er hat aktuell keinen eigenständigen Wert.** Umgekehrt heißt das aber auch: Ein besserer Textlayer über verlässlichen Rohmesswerten wäre sofort wertvoll, ohne dass die Detection perfekt sein muss (siehe 5.4).

---

## 3. Diagnose: der eigentliche Engpass

### 3.1 Die Ursachenkette (gemessen, nicht vermutet)

**Schritt 1 — Die Beat-Erkennung ist ein Raster, kein Schätzer.**
`app/audio/beats.py:20`:
```python
tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
```
Keine Tempo-Parameter, also librosa-Defaults (`start_bpm=120`, sehr enger Prior). Gemessen an 40 zufälligen Library-Tracks mit rekordbox-BPM zwischen 118 und 140 (90 s Ausschnitt ab Sekunde 45):

| Toleranz | Trefferquote produktiv |
|---|---:|
| ±0,5 BPM | 5/40 (**12 %**) |
| ±1,0 BPM | 9/40 (**22 %**) |
| ±2,0 BPM | 24/40 (60 %) |
| ±5,0 BPM | 37/40 (92 %) |

Entscheidend ist nicht der mittlere Fehler (3,12 BPM), sondern die **Quantisierung**: Über 40 verschiedene Tracks liefert der Schätzer nur **6 verschiedene Werte** — `[92.3, 99.4, 117.5, 123.0, 129.2, 136.0]`. Die Referenz streut kontinuierlich (std 5,7). Der Detektor rastet auf ein festes Gitter ein.

Das Projekt weiß das bereits: `tools/synth_mixer/track_prep.py:26-39` dokumentiert den Befund vom 14.07. ("~123 BPM gemessen bei mehreren komplett verschiedenen Songs") und implementiert eine Korrektur — die **bewusst nicht** in `beats.py` übernommen wurde, weil der Klassifikator auf der verzerrten Feature-Verteilung kalibriert ist. *Wichtig: Meine Messung zeigt, dass die synth_mixer-Korrektur im Tanzmusik-Bereich **nicht** besser ist (MAE 5,92 vs. 3,12 BPM; sie produziert Oktavfehler wie 74 statt 148 BPM). Der Ausweg ist also nicht "die Korrektur portieren", sondern "einen richtigen Beat-Tracker verwenden".*

**Schritt 2 — Der Beat-Fehler wird über die Track-Länge integriert.**
2 BPM Fehler bei 128 BPM = 1,6 % Tempoabweichung. Über einen 5-Minuten-Track kumuliert das zu ~4,7 Sekunden Versatz — bei 128 BPM rund **10 Beats**. Beat-Positionen in der zweiten Track-Hälfte sind damit strukturell falsch.

**Schritt 3 — Das Phrasenraster erbt den Fehler doppelt.**
`phrase_grid.py:18-40` verankert das 32-Beat-Raster am ersten Beat des **erkannten Segments** und zählt ab. Der Docstring sagt es selbst (`phrase_grid.py:7-10`):
> *"Bekannte Vereinfachung (dokumentiert, bewusst): Das Raster wird am ersten Beat jedes erkannten Segments verankert. Wenn die Segment-Erkennung den Trackanfang verfehlt, verschiebt sich das Raster. Ein echter Downbeat-Detektor ist der nächste Ausbauschritt."*

Damit hat das Raster zwei unabhängige Fehlerquellen: den driftenden Beat (Schritt 2) und den Segmentanfang, der zu ~50 % falsch ist (Precision 0.497) — bei einer Toleranz von ±105 s, die Fehler von über einer Minute noch als "korrekt" durchgehen lässt.

**Schritt 4 — Deshalb ist `phrase_beats_off` Rauschen.** Gemessen: ρ = 0.014 gegen `human_rating` (n=89, p=0.89).

**Schritt 5 — Deshalb ist `quality_score` Rauschen.** `transition_quality.py:199-203` gewichtet `phrase 0.35`, `tempo 0.35`, `harmonic 0.15`, `energy 0.15`. 70 % des Scores hängen an Beat- und Phrasengrößen aus Schritt 1–3. Reproduziert: **ρ = 0.047** (n=305, p=0.42), Pearson r = 0.043.

Die aussagekräftigste Ansicht ist die Aufschlüsselung nach Rating:

| human_rating | n | ⌀ engine_quality_score |
|---:|---:|---:|
| 0 | 29 | 72,9 |
| 2 | 41 | 75,0 |
| 3 | 56 | 73,0 |
| 4 | 50 | 74,5 |
| 5 | 129 | 74,7 |

Der Score sagt bei einem als katastrophal bewerteten Übergang praktisch dasselbe wie bei einem perfekten. 50 % aller Werte liegen in einem Band von 15 Punkten (66–81). **Der Score hat keine Auflösung.**

### 3.2 Antwort A: Wo genau ist der Flaschenhals?

**Falsche Features — nicht fehlende Daten, nicht fehlende Automatisierung.**

Das lässt sich beweisen, nicht nur behaupten. Wären die Daten das Problem, müsste mehr Labeln helfen. Es hilft messbar nicht:

> Seit 08.07.2026 (letzter erfolgreicher Export): ~26 zusätzlich gelabelte Sets, 6 Retrain-Läufe, **6× `ABBRUCH`**. Fixed-Eval-Precision 51 % → 53 % (Rauschen). Gespeicherte LOSO-Precision 0.564 → 0.497 (schlechter).

**Personenstunden je Prozentpunkt:**
26 Sets × ~30 min Labeln ≈ 13 h, plus 6 Retrain-Läufe à ~30–60 min ≈ 4 h → **≈ 17 Personenstunden für 0 Prozentpunkte.**

**Extrapolation 53 % → 90 %:** Nicht durchführbar. Der gemessene Fortschritt pro Stunde ist null; 37 Prozentpunkte geteilt durch null ist keine große Zahl, sondern eine undefinierte. Selbst wenn man die 2 Punkte Messrauschen großzügig als echten Fortschritt verbucht, ergäbe das 8,5 h/Punkt × 37 = **315 Stunden ≈ 8 Personenwochen Vollzeit** — und diese Rechnung setzt Linearität voraus, die durch 6 aufeinanderfolgende abgelehnte Retrains explizit widerlegt ist.

**Unmissverständlich formuliert: Der aktuelle Weg erreicht 90 % nicht. Nicht in 8 Wochen, nicht in 8 Monaten. Nicht, weil zu wenig gelabelt wird, sondern weil die Merkmale, auf die gelabelt wird, das Zielphänomen nicht enthalten.**

### 3.3 Antwort B: Ist ">90 % Transition Detection" das richtige Ziel?

**Nein — aus drei unabhängigen Gründen.**

**(1) "Korrekt erkannt" ist nicht scharf definiert.** `CLUSTER_GAP = 105.0` (`retrain_model.py:72`) akzeptiert ±105 Sekunden. Bei 4–6-Minuten-Tracks deckt das Trefferfenster einen erheblichen Teil des Tracks ab. Eine Zahl wie "90 %" unter dieser Toleranz sagt fast nichts über das aus, was ein DJ als "der Übergang saß" empfindet. Umgekehrt: Würde man auf DJ-relevante Toleranz verschärfen (±2 Beats ≈ ±1 s), läge die heutige Genauigkeit **weit unter** 50 %. Die Metrik ist nicht nur ungenau, sie ist optimistisch verzerrt.

**(2) Die Inter-Rater-Reliabilität ist unbekannt und strukturell nicht messbar.** Alle 358 Labels stammen von einem Rater (`rater`-Spalte: `sebro` × 358). Ohne einen zweiten Rater gibt es keine Obergrenze dafür, was ein Modell überhaupt erreichen kann. Bei einer Aufgabe wie "wo genau beginnt dieser Übergang?" ist bei erfahrenen DJs eine Übereinstimmung von deutlich unter 90 % zu erwarten — insbesondere bei langen Blends, wo "der Übergang" gar kein Zeitpunkt, sondern ein 30–60-Sekunden-Intervall ist. **Das ist kein Nebenaspekt: Wenn zwei DJs sich nur zu 80 % einig sind, ist 90 % Maschinengenauigkeit definitionsgemäß unerreichbar, und das Problem liegt in der Metrik, nicht im Algorithmus.** *(Nicht verifizierbar mit den vorhandenen Daten — siehe Experiment in Abschnitt 7.)*

**(3) Das Produkt braucht diese Genauigkeit gar nicht.** `PRODUKTVISION.md:20` postuliert: *"Du markierst nichts von Hand."* Das ist eine **Annahme über Bequemlichkeit, kein Nutzerbedürfnis.** Der DJ weiß, wo seine Übergänge liegen — er hat sie selbst gemixt. Er hat oft sogar eine Tracklist. Die autonome Erkennung löst ein Problem, das der Nutzer nicht hat, und erkauft es mit dem einzigen wirklich schweren technischen Problem im gesamten Projekt.

Der Wert des Produkts liegt in `PRODUKTVISION.md:26`: *"Dein Phrase-Timing ist stark — außer wenn du in schnellere Tracks mischst."* Diese Aussage braucht **Bewertung**, nicht **Auffindung**. Auffindung ist die teuerste und am wenigsten differenzierende Komponente.

### 3.4 Antwort C: Was sagt die 0.02-Korrelation wirklich?

Reproduziert: **ρ = 0.047** über alle 305 Paare (p = 0.42); **ρ = 0.021** ohne die 0er-Ratings (n=276) — das ist exakt die im Auftrag genannte Zahl. Die drei konkurrierenden Erklärungen lassen sich mit den vorhandenen Daten trennen:

**(iii) "Kontext-/Genreabhängigkeit" — widerlegt.**
Wenn die Qualität einer Transition nur im Kontext bewertbar wäre, müsste die Korrelation *innerhalb eines Sets* (gleiches Genre, gleicher Abend, gleicher Stil) deutlich höher sein. Gemessen über 14 Sets mit ≥8 Labels und Streuung:
> set-interne ρ: **Mittelwert +0.069**, Median +0.15, Spanne −0.58 bis +0.38. Nur **2 von 14** Sets über ρ = 0.3.

Kontext-Kontrolle bringt keine Verbesserung. Diese Erklärung trägt nicht.

**(ii) "Labels zu verrauscht/zu wenig gestreut" — trägt nur am Rand.**
Die Labels sind besser als angenommen: 358 Ratings, null Duplikate, 21 % im schlechten Bereich (0 oder 2), Median 9 Labels je Set. Es fehlen 1er-Ratings und die Verteilung ist rechtsschief (46 % Fünfen) — das dämpft Korrelationen, kann aber ρ = 0.047 nicht erklären. Eine echte Schwäche bleibt: nur ein Rater, also unbekanntes Label-Rauschen.

**(i) "Das Feature-Set bildet nicht ab, was Menschen hören" — die Daten stützen diese Erklärung, und die Ursachenkette in 3.1 erklärt den Mechanismus.**
Belege in aufsteigender Schärfe:
- Der Score hat kaum Auflösung (IQR 15 Punkte, ⌀ 73–75 bei *jedem* Rating).
- `phrase_beats_off`, das schwerstgewichtete Einzelfeature, korreliert mit ρ = 0.014.
- Die Beat-Erkennung, aus der Phrase und Tempo abgeleitet werden, liefert 6 Werte für 40 Tracks.
- Das Phrasenraster ist per Konstruktion (`phrase_grid.py:19`) an eine Segmentgrenze gekoppelt, die zu 50 % falsch ist.

**Wie man die Hypothesen mit minimalem Aufwand endgültig trennt** (~1 PT):
Nimm 30 Übergänge mit bekannten, *manuell gesetzten* Grenzen (die 356 Positiv-Anker liefern sie). Berechne `phrase_beats_off` einmal mit dem produktiven Beatgrid und einmal mit einem fertigen Downbeat-Tracker. Steigt die Korrelation zum `human_rating` deutlich, ist (i) bestätigt und der Fix benannt. Bleibt sie bei ~0, ist das Konstrukt "Phrasen-Timing erklärt Qualität" selbst falsch — auch das wäre ein wertvolles Ergebnis, und zwar eines, das man in einem Tag statt in sechs Monaten bekommt.

---

## 4. Bewertung der bisherigen Arbeit

| Modul | LOC | Urteil | Begründung |
|---|---:|---|---|
| `app/library/` + `library_match.py` (Fingerprinting) | ~1.200 | **Behalten — das ist das Kronjuwel** | Recall 0.90 / Precision 1.0, gemessen mit Ground Truth. 6.113 Tracks indexiert. Liefert echte Tracknamen *und* exakte Zeitgrenzen. Der einzige Teil, der nachweislich funktioniert und schwer kopierbar ist. |
| `app/audio/loudness.py` (LUFS, BS.1770) | ~150 | **Behalten** | Standardkonform, unabhängig von der Detection, direkt anzeigbar. Echter Messwert. |
| `app/audio/bass_overlap.py` | ~200 | **Behalten** | Messbar zwischen zwei sicher erkannten Tracks; hängt am Fingerprinting, nicht an der ML-Detection. |
| Frontend (Report, Waveform, Feedback-UI) | 22.042 | **Behalten und umwidmen** | Nach eigenem Stand F2/F3 fertig. `SetTransitionsExplorer.tsx` + Endpunkte `verdict`/`missed`/`rematch` sind bereits ~80 % der assistierten Variante (Abschnitt 5.4). |
| `app/audio/beats.py` | ~90 | **Wegwerfen und ersetzen** | 6 BPM-Werte für 40 Tracks, 22 % Trefferquote bei ±1 BPM. Fertige Modelle sind hier seit Jahren besser. Größter Einzelhebel im Projekt. |
| `app/audio/phrase_grid.py` | ~60 | **Wegwerfen und ersetzen** | Zählt 32 Beats ab einer unsicheren Segmentgrenze. Braucht echtes Downbeat-Tracking, nicht Reparatur. |
| `transition_quality.py` Gewichtung (`phrase 0.35 / tempo 0.35`) | ~250 | **Umbauen** | Die Feedback-Textbausteine sind brauchbar; die Score-Gewichtung ist widerlegt (ρ = 0.047) und muss weg, bis die Eingangsgrößen stimmen. |
| `app/audio/scoring/` (Composite, 5 Dimensionen) | 514 | **Umbauen — Gewichte wegwerfen, Dimensionen behalten** | `DEFAULT_WEIGHTS` sind auf 14 Beispielen aus 4.300 Kandidaten gefittet und statistisch wertlos; `vocal_overlap` (Gewicht 0.42) korreliert negativ. Die *Messungen* selbst sind sinnvoll — nur die Aggregation zu einer Zahl ist es nicht. |
| Demucs-Stems im Live-Pfad | — | **Sofort abschalten** | 7,1 min von 10,5 min Analysezeit für einen Score, den das Frontend nie ausliest. `MIXCOACH_ENABLE_STEM_SCORING=0` genügt. |
| `app/audio/ml_classifier.py` + Retrain-Kette | ~1.500 | **Einfrieren, nicht wegwerfen** | Precision 0.497 bei ±105 s. Als *Vorschlagsgenerator* für eine assistierte UI weiterhin nützlich (Recall 0.94 ist gut!), als autonome Wahrheit unbrauchbar. Retrain-Läufe einstellen. |
| `tools/synth_mixer/` | 1.757 | **Wegwerfen (aus dem aktiven Weg)** | Eigene Messung vom 28.07. zeigt: synthetische Daten verschlechtern echte Sets in beiden Metriken. Wurde bereits per `include_synthetic=False` deaktiviert — der Code ist damit ohne Funktion im Produktivpfad. |
| `app/audio/landmark_match.py` + `tools/experiment_*.py` | ~1.500 | **Einfrieren** | Sauber gebaut, korrekt als nicht-live erkannt. Bringt +2,5 Prozentpunkte Recall für ~2.000 s pro Lücke. Nicht anfassen. |
| **`app/experimental/`** | **1.796** | **Wegwerfen** | Von keiner Datei importiert. Toter Code, der bei jeder Suche und jedem Refactoring Zeit kostet. |
| `labels_alt.csv` | 304 Zeilen | **Wegwerfen** | Kein einziges `human_rating`. |
| 3 fehlschlagende Tests | — | **Reparieren** | `test_feedback.py`, `FileNotFoundError`. Ein rotes Testfeld gewöhnt einen daran, Rot zu ignorieren. |

**Summe "Wegwerfen": ~5.400 LOC** (experimental 1.796 + synth_mixer 1.757 + landmark/experimente ~1.500 + beats/phrase_grid ~150). Das ist rund ein Drittel des Backend-Codes.

---

## 5. Alternative Wege

### 5.1 Datenbeschaffung im großen Stil

**1001Tracklists / Mixcloud / SoundCloud / YouTube-Sets.**
Die Kernidee im Auftrag ist richtig und wichtiger, als sie klingt: *Wenn eine Tracklist mit Timestamps existiert, ist das Erkennungsproblem kein Detektionsproblem mehr, sondern ein Alignment-Problem* — und Alignment ist die Disziplin, in der dieses Projekt bereits nachweislich gut ist (Fingerprint-Recall 0.90, Precision 1.0). Der Wert liegt aber **nicht** primär in Trainingsdaten, sondern in der Evaluation: 1001Tracklists-Timestamps sind von Menschen gesetzte, unabhängige Zweitmeinungen — genau das, was für die in 3.3 fehlende Inter-Rater-Reliabilität gebraucht wird.

Einschränkungen, die man kennen muss: 1001Tracklists-Timestamps markieren meist den *Einsatz eines Tracks*, nicht Beginn und Ende des Blends, und ihre Genauigkeit liegt typischerweise im Sekunden- bis Zehnsekundenbereich. *[UNVERIFIZIERT — nicht aus dem Repo belegbar.]* Für ±105 s reicht das locker, für DJ-relevante Präzision (±2 Beats) nicht. Als Ersatz für eigene Labels taugen sie also nur begrenzt; als **Skalen-Referenz und Realitätscheck** sind sie sehr wertvoll.

Rechtlich nüchtern *[UNVERIFIZIERT, keine Rechtsberatung]*: Systematisches Scraping verstößt regelmäßig gegen die ToS solcher Seiten; das Herunterladen der Mix-Audios ist urheberrechtlich nicht tragfähig, YouTube-Downloads sind ToS-widrig. **Tragfähig** ist dagegen: Timestamps manuell oder in kleinem Umfang für die eigene Evaluation heranziehen, ohne Audio zu speichern und ohne Weiterverbreitung. **Nicht tragfähig** ist ein Produkt, das auf einer gescrapten Mix-Bibliothek aufbaut. Aufwand Scraper: 3–5 PT; Aufwand für die tragfähige kleine Variante: 0,5 PT.

**DJ-Software-Exports — das ist die eigentlich interessante Quelle.**
Rekordbox-History (`.xml`/DeviceSQL), Serato-History (`.csv`-Export), Traktor `.nml`: Diese Dateien enthalten **exakt, was gespielt wurde und wann** — vom Gerät protokolliert, ohne Schätzung. Kein Urheberrechtsproblem, keine ToS-Frage, denn es sind die Daten des Nutzers, freiwillig hochgeladen. **Der rekordbox-XML-Parser existiert bereits** (`app/library/manager.py:74`, liest `Location`, `Tempo`, `Tonality`). Der Schritt von der Collection-XML zur History-Datei ist klein. Aufwand: 2–3 PT je Format. Wirkung: **eliminiert das Detektionsproblem für alle Nutzer, die mit diesen Systemen auflegen.**

**DJ-Schule / Community.** Sinnvoll, aber langsam. Der eigentliche Gewinn wäre ein **zweiter Rater** für die IRR-Frage — dafür genügen 1–2 Personen und ein Nachmittag, keine Kooperation. Aufwand: 1 PT plus Terminfindung.

### 5.2 Fremde Modelle statt Eigenbau

Dies ist der **billigste Accuracy-Sprung im gesamten Projekt**, und die Messung in 3.1 belegt es: Der Eigenbau-Beat-Tracker liefert 6 verschiedene Werte für 40 Tracks. Alles, was hier verglichen wird, ist besser als das.

| Werkzeug | Ersetzt | Lizenz *[UNVERIFIZIERT]* | Integrationsaufwand | Wirkung |
|---|---|---|---|---|
| **madmom** (DBNDownBeatTracker) | `beats.py`, `phrase_grid.py` | BSD-artig, akademisch eingeschränkt | 2–3 PT | **Höchste.** Liefert Beats *und* Downbeats — genau die Größe, die `phrase_grid.py` heute rät. |
| **BeatNet** | `beats.py` | MIT-nah | 2 PT | Modernes Beat/Downbeat-Tracking, aktiver gepflegt als madmom. |
| **allin1** (All-In-One Music Structure Analyzer) | `beats.py`, `phrase_grid.py`, Teile von `set_analyzer_helpers.py` | MIT-nah | 3–5 PT | Beat, Downbeat **und** funktionale Segmente (intro/verse/chorus/drop). Deckt die Phrasenstruktur ab, die hier heuristisch gebaut wird. Rechenintensiv (GPU empfohlen). |
| **Essentia** | `tempo.py`, `segment_keys.py` | AGPL (!) | 2 PT | Robuster als librosa-Defaults. **AGPL ist für ein kommerzielles SaaS ein ernstes Problem** — vor Nutzung prüfen. |
| **Demucs** | bereits im Einsatz | MIT | — | Schon integriert; das Problem ist nicht die Qualität, sondern dass 7,1 min für einen unsichtbaren Score verbrannt werden. |
| **CLAP / OpenL3 Embeddings** | die 17 handgebauten Features | MIT-nah | 5–8 PT | Interessant mittelfristig, aber bei 45 gelabelten Sets zu wenig Daten, um darauf zu trainieren. **Jetzt nicht.** |

**Direkte Antwort auf die gestellte Frage:** Ja, die selbstgebaute Beat-/Phrase-Erkennung ist schlechter als frei verfügbare fertige Modelle — belegt durch 22 % Trefferquote bei ±1 BPM und 6 diskrete Ausgabewerte. Und ja, das ist der billigste Accuracy-Sprung im Projekt: 2–3 PT gegen einen Fehler, der sich durch `phrase_timing`, `beat_alignment`, `tempo` und damit durch **70 % des Qualitäts-Scores** zieht.

**Wichtige Einschränkung, damit hier keine falsche Hoffnung entsteht:** Ein besserer Beat-Tracker repariert die *Messgrößen*. Er repariert **nicht** automatisch die Korrelation zum menschlichen Urteil — es ist möglich, dass auch bei perfektem Phrasen-Timing der Zusammenhang zur wahrgenommenen Qualität schwach bleibt. Genau deshalb steht in Abschnitt 7 ein Experiment, das das *vor* der Integration klärt.

### 5.3 Kaufen / Partnern

Ehrliche Einschätzung: **hier liegt am wenigsten.** Kommerzielle Audio-APIs *[UNVERIFIZIERT]* liefern Track-Analyse (BPM, Key, Struktur) — also genau das, was `PRODUKTVISION.md:13` explizit als *nicht* das Differenzierungsmerkmal benennt. Sie lösen die Mix-Analyse nicht.

- **Kommerzielle Analyse-APIs:** ersetzen bestenfalls `tempo.py`/`segment_keys.py`, kosten laufend Geld pro Analyse und schaffen eine Abhängigkeit. Fertige Open-Source-Modelle (5.2) sind hier besser: kostenlos und lokal.
- **Lizenzierung von Analysedaten:** Es gibt keinen Markt für "bewertete DJ-Transitions". Das Gut existiert nicht — das ist ja gerade die Vision-These vom Burggraben.
- **Kooperation mit DJ-Plattform / White-Label:** Strategisch am ehesten interessant (Vertriebszugang, Nutzer = Daten), aber nichts, was ein Solo-Entwickler vor einem funktionierenden Produkt verhandelt. **Vertagen.**

Aufwand: 0 PT jetzt. Empfehlung: nicht verfolgen, bis ein Nutzer freiwillig zahlt.

### 5.4 Produkt-Pivot: das harte Problem umgehen

**(a) User liefert die Struktur (Tracklist / rekordbox-History-Upload).**
Der DJ lädt seine History-Datei mit hoch → Transition-Zeitpunkte sind bekannt → das ML-Problem verschwindet vollständig, übrig bleibt Bewertung + Coaching. Der rekordbox-Parser existiert (`manager.py:74`). Aufwand: **3–5 PT.** Risiko: nicht jeder DJ hat eine History-Datei (Vinyl, fremdes Setup) — braucht einen Fallback. Wirkung: **eliminiert das Kernproblem für die Mehrheit der Zielgruppe.**

**(b) Assistiert statt autonom — und das ist zu ~80 % gebaut.**
Die Engine schlägt vor (Recall 0.94 — sie *findet* fast alles, sie produziert nur zu viele Fehlalarme), der DJ bestätigt/verschiebt/löscht in der Waveform. Vorhanden sind bereits: `SetTransitionsExplorer.tsx` mit den Verdict-Buttons, `POST /analysis/{id}/feedback/verdict` (`main.py:168`), `.../feedback/missed` (`main.py:178`), `.../rematch` (`main.py:185`).

Was fehlt, ist nicht Technik, sondern **Blickrichtung**: Heute ist das ein Korrektur-Werkzeug, mit dem der Nutzer der Maschine hilft. Es muss ein Eingabe-Werkzeug werden, mit dem der Nutzer sein Set beschreibt — und die Maschine bewertet. Aufwand: **5–8 PT.**

Der entscheidende Nebeneffekt: **Der Labeling-Engpass wird zum Produktfeature.** Jede Nutzung erzeugt exakte Labels. Die Datenschleife aus `PRODUKTVISION.md:36` funktioniert damit zum ersten Mal wirklich — heute erzeugt sie Labels, die auf ein Feature-Set einzahlen, das nicht funktioniert.

Und die Precision-Frage entschärft sich strukturell: Bei einem Vorschlagssystem ist ein Fehlalarm ein Klick, kein Vertrauensbruch. **Recall 0.94 ist für einen Vorschlagsmodus ein gutes Ergebnis. Precision 0.50 ist es nur für einen Autonomiemodus nicht.** Dasselbe Modell, das als autonome Wahrheit versagt, ist als Assistent brauchbar.

**(c) Vom Score zum Coaching-Gespräch (LLM über Rohmesswerten).**
Statt einer Zahl, der niemand glaubt (ρ = 0.047), beschreibt ein LLM anhand der Rohmesswerte im Übergangsfenster qualitativ, was passiert ist: *"Bei 14:32 laufen beide Bässe 16 Beats übereinander, und der einsteigende Track ist 2,5 dB lauter."* Das ist überprüfbar, nachhörbar und erfüllt die Ehrlichkeits-Säule besser als jeder aggregierte Score.

Braucht das hohe Detection-Genauigkeit? **Nein** — es braucht *korrekte Grenzen*, und die liefert entweder der Fingerprint (Precision 1.0) oder der Nutzer (Variante a/b). Aufwand: **5–8 PT.** Laufende Kosten: gering, ein Set hat ~10–20 Übergänge. Risiko: LLM-Halluzination — beherrschbar, indem nur gemessene Zahlen in den Prompt gehen und der Text sie nur formuliert, nicht erfindet.

**(d) Realtime/Practice-Tool.** Reizvoll (`PRODUKTVISION.md:44` nennt es als Langfristziel), aber technisch deutlich schwerer als das ungelöste Post-hoc-Problem: Latenz, Live-Beat-Tracking, Audio-Interface-Handling. Aufwand: **20+ PT**, hohes Risiko. **Jetzt nicht.**

**(e) Engere Nische (ein Genre / ein Transition-Typ).** Würde die Varianz senken und Kalibrierung erleichtern. Aber es adressiert den Engpass nicht: Ein kaputter Beat-Tracker ist auch in einem einzigen Genre kaputt — die Messung in 3.1 erfolgte bereits ausschließlich auf 118–140-BPM-Tanzmusik. Aufwand: 0 PT (Entscheidung, kein Code). Wirkung auf den Engpass: **keine.**

### 5.5 Vergleichstabelle

| Option | Aufwand PT | Risiko | Erwartete Wirkung auf das Kernproblem | In 1 Woche testbar? |
|---|---:|---|---|---|
| **Beat/Downbeat durch madmom o. BeatNet ersetzen** | 2–3 | niedrig | **Sehr hoch** — repariert die Wurzel von 70 % des Scores | **Ja**, ohne Integration (Abschnitt 7) |
| **Assistierte Transition-Eingabe** (aufbauend auf vorhandener UI) | 5–8 | niedrig | **Sehr hoch** — umgeht das ML-Problem, erzeugt exakte Labels | Ja, als Klick-Prototyp |
| **rekordbox/Serato-History-Upload** | 3–5 | mittel (nicht jeder hat sie) | **Hoch** — Detektion entfällt vollständig | Ja, mit einer eigenen History-Datei |
| Demucs im Live-Pfad abschalten | 0,1 | keins | Analysezeit 10,5 → 3,5 min, kein Funktionsverlust | Ja, sofort (ENV-Variable) |
| LLM-Coaching über Rohmesswerten | 5–8 | mittel (Halluzination) | Hoch auf *wahrgenommenen* Wert, nicht auf Accuracy | Ja, mit 3 Übergängen von Hand |
| allin1 für Segmentstruktur | 3–5 | mittel (Rechenlast/GPU) | Mittel–hoch | Teilweise |
| Zweiter Rater für IRR | 1 | keins | **Klärt, ob 90 % überhaupt existiert** | Ja |
| `app/experimental/` löschen | 0,5 | keins | Keine auf Accuracy; entlastet jede weitere Arbeit | Ja |
| 1001Tracklists als Evaluations-Referenz | 0,5 | niedrig (klein halten) | Mittel — unabhängige Zweitmeinung | Ja |
| 1001Tracklists-Scraper im großen Stil | 3–5 | **hoch** (ToS/Urheberrecht) | Niedrig — Timestamps zu grob für DJ-Präzision | Nein |
| CLAP/OpenL3-Embeddings statt Handfeatures | 5–8 | hoch (zu wenig Daten) | Unklar bei 45 Sets | Nein |
| Kommerzielle Audio-API | 2–3 | mittel (Kosten, Abhängigkeit) | Niedrig — löst Track-, nicht Mix-Analyse | Ja |
| Realtime-Practice-Tool | 20+ | sehr hoch | Umgeht das Problem nicht, verschärft es | Nein |
| **Weiter labeln + retrainen (Status quo)** | ∞ | — | **Gemessen null** (6× ABBRUCH seit 08.07.) | — |

---

## 6. Empfehlung + 90-Tage-Plan

### 6.1 Die Empfehlung

**Hör auf, autonome Transition-Detection zu bauen. Baue ein assistiertes Bewertungswerkzeug auf einem reparierten Beat-Fundament.**

Konkret, in dieser Reihenfolge:
1. **Beat/Downbeat durch ein fertiges Modell ersetzen** (madmom oder BeatNet). Das repariert `phrase_timing`, `beat_alignment` und `tempo` gleichzeitig — die Größen, die 70 % des Scores stellen und heute Rauschen sind.
2. **Struktur vom Nutzer beziehen statt raten** — per History-Upload (wo vorhanden) oder per Bestätigung in der bestehenden UI. Die ML-Detection bleibt als *Vorschlagsgenerator* (Recall 0.94 ist dafür gut genug), nicht als Wahrheit.
3. **Score durch nachprüfbare Einzelmesswerte ersetzen**, formuliert als Coaching-Text. Kein aggregierter `quality_score`, solange dessen Korrelation zum menschlichen Urteil nicht belegt ist.

**Warum diese und keine andere:** Sie ist die einzige Kombination, die (a) den gemessenen Engpass an der Wurzel trifft, (b) auf dem aufbaut, was nachweislich funktioniert (Fingerprinting, Frontend), (c) das Labeling-Problem strukturell auflöst statt es zu vergrößern, und (d) mit ~15 PT auskommt statt mit den ~315 h, die der Status quo bei optimistischster Rechnung bräuchte, um ein Ziel zu erreichen, das laut 3.3 gar nicht wohldefiniert ist.

Das Wichtigste: **Sie widerspricht der Vision weniger, als es zunächst aussieht.** `PRODUKTVISION.md:13` sagt *"Nicht Track-Analyse, sondern Mix-Analyse. Nicht Werkzeug, sondern Coach."* Genau das bleibt. Was fällt, ist ausschließlich der Satz *"Du markierst nichts von Hand"* (`PRODUKTVISION.md:20`) — eine Bequemlichkeitsannahme, kein Wertversprechen. Der Burggraben "Datenschleife" wird durch die Umstellung **stärker**, nicht schwächer: Heute liefert Nutzerfeedback Korrekturen an einem kaputten Feature-Set; künftig liefert es exakte Grenzen.

### 6.2 Was du sofort einstellen solltest

1. **Labeln zum Zweck des Modelltrainings.** 6 von 6 Retrains seit dem 08.07. abgelehnt, 17 h für 0 Punkte. Labeln nur noch dort, wo es der *Evaluation* dient (kleine, saubere Referenzmenge).
2. **`MixCoach-Retrain.bat` / `MixCoach-Retrain-Jetzt.bat` ausführen.** Das aktive Modell einfrieren. Jeder weitere Lauf kostet Zeit und hat nachweislich keine Chance, das Gate zu passieren.
3. **Demucs im Live-Pfad.** `MIXCOACH_ENABLE_STEM_SCORING=0` setzen. 7,1 von 10,5 Minuten Analysezeit für einen Score, den kein Frontend-Code ausliest.
4. **`fit_composite_weights.py` weiter fitten.** 4.300 Kandidaten auf 14 Beispielen ist kein Fit, sondern eine Zufallsziehung. Das Skript bleibt nützlich — aber erst ab ~150 gematchten Übergängen mit Composite-Score (heute: 21).
5. **Landmark-Hashing / Fingerprint-Tuning.** Sauber abgeschlossen und korrekt als offline eingestuft. Nicht wieder anfangen.
6. **Synth-Mixer-Arbeit.** Eigene Messung vom 28.07. zeigt, dass synthetische Daten echten Sets schaden. Der Code ist bereits per Default deaktiviert.

### 6.3 90-Tage-Plan

**Block 1 (Tag 1–30): Fundament reparieren und Ballast abwerfen**
- Woche 1: Das Experiment aus Abschnitt 7 (Beat-Tracker-Vergleich). Zweiter Rater für IRR.
- Woche 2: Bei positivem Ergebnis madmom/BeatNet in `beats.py` integrieren; echtes Downbeat-Tracking in `phrase_grid.py`.
- Woche 3: Demucs abschalten, `app/experimental/` löschen, `labels_alt.csv` entfernen, 3 rote Tests reparieren.
- Woche 4: `quality_score` aus der Nutzeransicht entfernen; stattdessen Einzelmesswerte mit Nachhör-Sprung.

> **Messbares Ergebnis Block 1:** `phrase_beats_off` korreliert auf derselben Label-Menge messbar besser als heute (ρ = 0.014). **Zielwert: ρ ≥ 0.30 auf n ≥ 100.** Analysezeit unter 4 min für ein 60-Minuten-Set. Wird ρ ≥ 0.30 nicht erreicht, greift Kill-Kriterium 2.

**Block 2 (Tag 31–60): Assistiertes Produkt**
- History-Upload für rekordbox (Parser existiert), Serato-CSV als Zweites.
- `SetTransitionsExplorer` von Korrektur- auf Eingabe-Werkzeug umstellen: Übergang setzen, verschieben, löschen — mit Tastatur und Waveform-Zoom.
- ML-Ausgabe klar als *Vorschlag* kennzeichnen (passt zur Ehrlichkeits-Säule).

> **Messbares Ergebnis Block 2:** Ein DJ kann ein 60-Minuten-Set in **unter 5 Minuten** vollständig und korrekt strukturieren — per History-Upload in unter 1 Minute. Selbst gemessen an 3 eigenen Sets mit Stoppuhr.

**Block 3 (Tag 61–90): Coaching-Wert und erster externer Test**
- LLM-Textlayer über den Rohmesswerten (nur gemessene Zahlen im Prompt).
- 5 externe DJs aus der Zielgruppe, je 2 Sets, strukturiertes Feedback.

> **Messbares Ergebnis Block 3:** Von 5 externen Testern sagen **mindestens 3**, das Feedback habe ihnen etwas gezeigt, das sie selbst nicht bemerkt hatten. Das ist die einzige Zahl, die am Ende über das Produkt entscheidet — und sie ist unabhängig von jeder Accuracy-Metrik.

---

## 7. Das Experiment für nächste Woche

**Riskanteste Annahme der Empfehlung:** *Ein besserer Beat-Tracker repariert die Korrelation zum menschlichen Urteil.* Wenn das falsch ist, ist auch der empfohlene Weg teilweise falsch — dann ist "Phrasen-Timing erklärt Transitionsqualität" als Konstrukt widerlegt, und das Produkt muss ganz auf andere Messgrößen setzen. Diese Annahme lässt sich in **1–2 Tagen ohne jede Integration** prüfen.

**Aufbau (read-only, kein Produktivcode):**

1. `pip install madmom` (bzw. BeatNet) in einer separaten Umgebung.
2. Nimm die **356 Positiv-Anker** aus `daten/ground_truth/` — das sind von Hand bestätigte, exakte Übergangsgrenzen. Behalte nur die, für die es ein `human_rating` in `labels_prefilled.csv` gibt (~300).
3. Berechne für jeden dieser Übergänge `phrase_beats_off` **zweimal**:
   - **A:** mit dem produktiven Beatgrid (`app/audio/beats.detect_beat_grid`) und dem heutigen Raster,
   - **B:** mit madmom-Downbeats, wobei die Phrasengrenze am **nächstgelegenen Downbeat** verankert wird statt am Segmentanfang.
4. Berechne für A und B jeweils Spearman gegen `human_rating`.

**Entscheidungsregel:**
- **ρ(B) ≥ 0.30** → Annahme bestätigt. Integration lohnt sich, weiter nach Plan 6.3.
- **0.15 ≤ ρ(B) < 0.30** → Teilerfolg. Integrieren, aber `quality_score` bleibt aus der Nutzeransicht draußen.
- **ρ(B) < 0.15** → **Annahme widerlegt.** Phrasen-Timing erklärt wahrgenommene Qualität nicht. Dann keine Beat-Integration, sondern direkt auf Variante 5.4(c): messbare Einzelfakten (Bass-Overlap, Lautheitssprung, Tempodifferenz) statt abgeleiteter Timing-Scores.

**Warum genau dieses Experiment:** Es kostet 1–2 PT, braucht keinen Produktivcode-Eingriff, nutzt ausschließlich vorhandene Daten — und es kann die Kernempfehlung dieses Audits **widerlegen**. Ein Experiment, das das nicht kann, ist keines wert.

**Zweiter Test, parallel, 1 PT — Inter-Rater-Reliabilität:**
Setz dich mit einem zweiten DJ zusammen. Nehmt **20 Übergänge** aus bereits gelabelten Sets. Er bewertet unabhängig auf derselben 0–5-Skala und markiert die Grenze auf die Sekunde. Dann rechne: Spearman zwischen beiden Ratern und den Median-Zeitversatz.
Das liefert die Zahl, die diesem Projekt seit Beginn fehlt: **die Obergrenze dessen, was ein Modell überhaupt erreichen kann.** Liegt die menschliche Übereinstimmung bei ρ ≈ 0.5, ist jede Diskussion über 90 % beendet — und das ist eine Befreiung, keine schlechte Nachricht.

---

## 8. Kill-Kriterien

Woran erkennst du, dass MixCoach **in dieser Form** nicht funktioniert?

1. **Das Experiment aus Abschnitt 7 liefert ρ(B) < 0.15 UND die IRR zwischen zwei DJs liegt unter ρ = 0.4.**
   Dann ist "Transitionsqualität" keine Größe, über die zwei Menschen sich einig sind — und ein Produkt, das sie objektiv misst, kann nicht existieren. Ausweg: kein Kill des Projekts, aber ein Kill des *Bewertungs*-Produkts. Übrig bleibt ein ehrliches Analyse-Werkzeug (Tracknamen, Lautheit, Bass-Overlap, Tempo) ohne Qualitätsurteil — verkaufbar, aber ein anderes, kleineres Produkt.

2. **Nach Block 1 liegt die Korrelation weiterhin unter ρ = 0.30**, obwohl Beat und Downbeat nachweislich korrekt sind. Dann liegt der Fehler nicht in der Messkette, sondern in der Grundthese. Spätestens hier aufhören, an Scores zu arbeiten.

3. **Nach Block 2 braucht ein DJ länger als 10 Minuten**, um ein 60-Minuten-Set zu strukturieren. Dann ist der assistierte Weg im Alltag zu teuer, und da der autonome Weg gemessen nicht funktioniert, gibt es keinen dritten.

4. **Von 5 externen Testern sagen weniger als 2**, sie hätten etwas Neues über ihr DJing gelernt. Das ist das härteste Kriterium, weil es das Wertversprechen direkt prüft. Ein Produkt, das ambitionierten DJs nichts zeigt, was sie nicht selbst hören, hat keinen Abo-Grund — unabhängig von jeder technischen Kennzahl.

5. **Nach 90 Tagen kein einziger Nutzer außer dir hat zweimal freiwillig ein Set hochgeladen.** Die Vision (`PRODUKTVISION.md:48`) begründet das Abo mit der Entwicklung über Zeit. Wer nicht zweimal kommt, erzeugt keine Historie — und ohne Historie gibt es kein Abo-Produkt, sondern ein Gimmick.

**Ein Kriterium, das ausdrücklich NICHT taugt:** "Precision erreicht 90 % nicht." Diese Zahl ist bei ±105 s Toleranz und einem einzigen Rater nicht aussagekräftig genug, um darauf ein Projekt zu beenden — oder fortzuführen.

---

## 9. Anhang: offene Fragen und Nicht-Verifiziertes

**Was ich nicht verifizieren konnte:**

- **Inter-Rater-Reliabilität.** Nicht messbar: alle 358 Labels haben `rater = sebro`. Das ist die wichtigste fehlende Zahl des Projekts.
- **Herkunft der "239".** Der Auftrag nennt 239 gelabelte Transitions, `composite.py:3` ebenfalls. Heute sind es 358 mit `human_rating` bzw. 305 mit zusätzlichem `engine_quality_score`. Vermutlich ein früherer Stand; nicht rekonstruierbar.
- **Herkunft der "Duplikate durch Delete-Bug".** In `labels_prefilled.csv` keine Duplikate. Im Retrain-Log tauchen dagegen zusammengeführte Duplikate auf Analyse-Ebene auf (`REC001.WAV: 11 Duplikat(e) zusammengefuehrt`) — der Bug betraf also mehrfach angelegte *Analysen* desselben Audios, nicht die Labels. `retrain_model._merge_truth` behandelt das bereits.
- **Zeitaufwand pro gelabeltem Set.** Geschätzt 20–40 min (Set-Längen 40–70 min, Anhören nötig). Nicht instrumentiert. **Alle Personenstunden-Angaben in 3.2 hängen an dieser Schätzung** — bei 10 min/Set wären es ~8 h statt 17 h, was an der Kernaussage (0 Prozentpunkte Ertrag) nichts ändert.
- **Exakte Retrain-Laufzeit.** `dd/retrain_log.txt` hat Zeitstempel nur je Lauf-Beginn, keine Dauer.
- **Lizenzen und Laufzeiten der externen Bibliotheken** (madmom, BeatNet, allin1, Essentia). Aus meinem Wissen, nicht geprüft — vor Integration verifizieren. Besonders **Essentia (AGPL)** ist für ein kommerzielles SaaS potenziell disqualifizierend.
- **ToS/Rechtslage 1001Tracklists, Mixcloud, YouTube.** Einschätzung ohne Prüfung der aktuellen Bedingungen, keine Rechtsberatung.
- **Genauigkeit von 1001Tracklists-Timestamps.** Vermutlich Sekunden- bis Zehnsekundenbereich, nicht belegt.
- **rekordbox-BPM als Referenz.** Ist selbst algorithmisch ermittelt (von rekordbox), nicht händisch verifizierte Wahrheit. Als praktische Referenz brauchbar, weil DJs damit arbeiten und Beatgrids korrigieren — aber kein absoluter Maßstab. Die Kernaussage der Messung hängt nicht daran: **6 diskrete Ausgabewerte bei 40 verschiedenen Tracks** ist ein Befund über den Schätzer selbst, unabhängig von jeder Referenz.
- **Composite-Dimensionen bei n=21.** Die Korrelationen in 2.4 beruhen auf 21 zuordenbaren Übergängen. Richtungsweisend, nicht beweiskräftig.

**Offene Fragen an dich:**

1. Wie lange brauchst du tatsächlich, um ein Set zu labeln? Miss es einmal mit der Stoppuhr — es macht die Kosten-Rechnung in 3.2 belastbar.
2. Hast du rekordbox-History-Dateien deiner eigenen Sets? Falls ja, ist Variante 5.4(a) sofort an echtem Material testbar.
3. Kennst du einen zweiten DJ, der 20 Übergänge bewerten würde? Das ist der billigste wertvolle Datenpunkt, den dieses Projekt bekommen kann.
4. Würdest du das Produkt selbst nutzen, wenn du die Übergänge per Klick bestätigen müsstest? Wenn nein, ist Variante 5.4(b) tot und Variante (a) die einzige verbleibende — das solltest du wissen, bevor 5–8 PT hineingehen.

---

*Erstellt am 30.07.2026. Alle Messungen read-only, kein Produktivcode verändert. Verwendete Audit-Skripte: `audit_labels.py`, `audit_corr.py`, `audit_deepdive.py`, `audit_timing.py`, `audit_demucs.py`, `audit_bpm.py`, `audit_bpm2.py`.*
