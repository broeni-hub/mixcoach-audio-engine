# MixCoach Engine: Kalibrierungs-Status (2026-07-02, v2 Fusion)

## Datensatz (Ground Truth von Basti)

| Set | Dauer | Echte Übergänge | Besonderheit |
| --- | --- | --- | --- |
| REC001 | 29,5 min | 8 | Doppel-Übergang mit 82s Abstand |
| REC002 | 32,0 min | 5 | erstes Kalibrierungs-Set |
| REC007 | 34,5 min | 8 | ungesehen validiert: R 7/8, P 7/15 |
| REC013 | 31,1 min | 6 | Validierungs-Set |

Gesamt: 27 annotierte Übergänge. Dateien: REC00x_groundtruth.json

## Gesamtbilanz über 4 Sets (Fusion-Detektor, Stand jetzt)

Recall 31/34 = **91%** | Precision 31/58 = **53%** (5 Sets, inkl. REC009: R 6/7, P 6/12)

Verpasst: REC001 15:50 (Doppel-Übergang, harmonisch zu ähnlich) und
REC007 8:00 (kein Energie- UND kein Harmonie-Signal — sehr glatter Blend).
Beide Misses zeigen dieselbe Grenze: Übergänge ohne messbares Energie-
oder Harmonie-Ereignis brauchen ein drittes Signal (z.B. Bassline-/
Rhythmus-Textur) — Kandidat für die nächste Detektor-Generation.

## Entwicklung der Erkennungsqualität

| Stand | Recall | Precision |
| --- | --- | --- |
| Roh-Detektor (nur Energie) | 100% | 16% |
| Zonen-Klassifikator (Greedy + 150s-Abstand) | 79% | 60% |
| **Boundary-Detection v2 (Fusion, aktuell)** | **95%** | **58%** |

Zeitfenster: −45s/+60s um Bastis "ab ca."-Angaben (Annotation = Blend-Start,
Engine = Blend-Zentrum).

## Wie v2 funktioniert (app/audio/track_change_classifier.py)

Zwei unabhängige Detektoren, vereinigt:

1. **Harmonie-Novelty-Kurve**: Für jeden Zeitpunkt wird das harmonische
   Material 45s davor mit 45s danach verglichen. Peaks = Kandidaten.
   Findet auch Übergänge ohne Energie-Einbruch, Mindestabstand nur 60s
   (löst Doppel-Übergänge und Verdrängung).
2. **Energie-Zonen-Klassifikator**: findet Übergänge ohne Harmonie-Wechsel
   (gleiche Tonart). Ergänzt, wo kein Novelty-Peak in der Nähe liegt.

Jedes Boundary trägt `detected_by` (novelty/energy/both) — die UI kann
später eine konservative Ansicht (nur "both") anbieten.

## Einzelergebnisse v2

| Set | Recall | Precision |
| --- | --- | --- |
| REC002 | 5/5 | 5/11 |
| REC013 | 6/6 | 6/11 |
| REC001 | 7/8 | 7/9 |

Einziger verpasster Übergang: REC001 15:50 (zweite Hälfte des 82s-Paars —
harmonisch zu ähnlich zum Nachbartrack für die Novelty-Kurve, und der
Energie-Detektor hatte dort keine ausgewählte Zone).

## Bekannte Grenzen

1. Precision 58%: ~4 von 10 Meldungen sind Energie-Events, keine
   Trackwechsel. Kein sauberer Schwellenwert trennbar bei n=3 —
   mehr annotierte Sets nötig, bevor weiter geschraubt wird.
2. Phrase-Anker weiterhin ohne Downbeat-Validierung.
3. Tempo pro Segment aus globalem Beat-Grid.
4. Analyse-Laufzeit ~2-3 min pro 30-min-Set → Async-Backend vor Nutzertests.

## Nächste Schritte

1. Async-Verarbeitung im Backend (Upload → Job → Polling)
2. Weitere annotierte Sets sammeln (Ziel: 10) — dann Precision-Tuning
3. Downbeat-Detektor

## Neu: Ground-Truth-Feedback direkt im Produkt (2026-07-02)

Der Annotations-Prozess ist jetzt in die App eingebaut — Nutzer trainieren
die Engine beim normalen Nachhören:

- **Pro Übergang** im Transitions-Explorer: "Stimmt" / "Kein Übergang"
- **In der Waveform**: "Übergang fehlt hier" (an der Playhead-Position)
- Speicherung: Backend-Ordner `ground_truth/{analysis_id}.json`
- Endpunkte: GET/POST /analysis/{id}/feedback[/verdict|/missed]

Damit skaliert die Datensammlung von "Basti schreibt Zeiten in den Chat"
auf "jeder Testnutzer annotiert nebenbei". Sobald ~10 Sets mit Feedback
vorliegen: ML-Klassifikator statt Hand-Schwellen (siehe Nächste Schritte).

## Neu: Der Trainings-Kreislauf ist geschlossen (2026-07-02)

**Boundary-Detection v3 (aktiv):** ML-Klassifikator (Gradient Boosting,
60 Bäume), trainiert auf 5 Sets / 34 Übergängen. LOSO-validiert:
**Recall 88-97%, Precision 81-83%** — gegenüber 53% Precision der
Hand-Kalibrierung. Läuft ohne sklearn im Backend (JSON-Export, Paritäts-
geprüft). Fallback auf Fusion v2, falls Modell fehlt oder nichts findet.

**Neue Werkzeuge in app/calibration/:**
- `training_features_v1.json` — die Basis-Trainingsdaten (gesichert, reproduzierbar)
- `build_features.py` — WAV + Wahrheit → Trainingszeilen (nutzt exakt die
  Inferenz-Extraktion, kein Train/Serve-Drift möglich)
- `retrain_model.py` — sammelt App-Feedback aus ground_truth/, trainiert
  neu, validiert (LOSO), exportiert NUR bei Verbesserung (Backup automatisch)

**Retraining ausführen** (wenn Feedback zu einigen Sets gesammelt ist):
```
cd mixcoach-audio-engine
pip install scikit-learn        (einmalig)
python -m app.calibration.retrain_model
```
Danach Backend neu starten. Das Skript verweigert den Export, wenn das
neue Modell schlechter wäre — Feedback kann das Modell nie verschlechtern.

**Feedback-Vokabular im Report:** Stimmt / Kein Übergang / Startet
woanders (mit präziser Zeit) / Übergang fehlt hier (Flagge in Waveform).

## Boundary-Detection v4: Dichte Kandidaten (nach Nutzerfeedback)

**Anlass:** Basti meldete nach mehreren Sets: viele Übergänge gar nicht
erkannt (trotz klar unterschiedlicher Tracks), Startzeitpunkte ungenau.

**Diagnose — drei Strukturfehler behoben:**
1. Kandidaten-Engpass: Das ML konnte nur Energie-Zonen bewerten. Übergang
   ohne Energie-Delle = unsichtbar. → Jetzt: dichtes 20s-Raster übers
   ganze Set + Zonen (generate_candidates, geteilt zwischen Training und
   Inferenz — kein Train/Serve-Drift möglich).
2. Mindestabstand 150s unterdrückte jeden zweiten Übergang bei zügigem
   Mixing. → Jetzt 90s, per LOSO-Gridsearch bestimmt.
3. (Offen für nächsten Block:) Start- vs. Zentrum-Meldung.

**LOSO-Validierung v4:** Recall **94%** / Precision 65% (F1 0.77).
Bewusster Trade-off: Recall-Priorität — verpasste Übergänge sind fürs
Coaching schlimmer als Fehlalarme, die per Feedback-Button wegtrainiert
werden. REC009: 7/7 (vorher 4/7).

**Retrain-Skript** sucht jetzt selbst die beste Schwelle/Abstand-Kombi
(Kriterium: bester F1 unter allen Configs mit Recall >= 90%).

**Nächste Blöcke:** Foote-Novelty (beat-synchron, Start-genau) →
rekordbox/Library-Fingerprinting (der Weg zu ~100% bei Techno ohne Drops).

## Boundary-Detection v5: Foote-Novelty (beat-synchron)

**Neu (app/audio/foote.py):** Selbstaehnlichkeits-Segmentierung nach Foote —
das Set wird beat-synchron mit sich selbst verglichen; Trackwechsel
erscheinen als "Schachbrett-Ecken", unabhängig von Energie. Zeitauflösung
~1 Beat statt ~20s.

**Zwei Wirkungen:**
1. 15. Modell-Feature (Foote-z-Score am Kandidaten)
2. **Start-Verfeinerung:** Jede gewählte Boundary wird auf den nächsten
   Novelty-Peak gesnappt (beat-genau); der Beginn des Novelty-Anstiegs
   wird als `blend_start` gemeldet → adressiert "Starts nicht erkannt".
   start_sec im Frontend-Vertrag nutzt jetzt den echten Blend-Start.

**LOSO Modell v3:** Recall 91% / Precision 74% / F1 0.82
(v2 ohne Foote: 94/65/0.77 — bewusster Tausch: +9pp Precision,
beat-genaue Zeiten, −3pp Recall). Auswahl: p>=0.6, Abstand>=90s.

**Naechster Block:** rekordbox-/Library-Fingerprinting — der Weg zu ~100%
bei drop-losem Techno (Matching statt blinder Analyse).
