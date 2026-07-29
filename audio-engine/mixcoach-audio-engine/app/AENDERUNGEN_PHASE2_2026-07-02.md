# MixCoach Audio-Engine Phase 2: Die Engine misst jetzt Musik (2026-07-02)

Für: Basti | Von: Claude | Alle 43 Tests bestehen.

## Was die Engine jetzt kann (vorher: nur Energie-Kurven)

**Vorher** bewertete die Engine ein Set nur über Lautstärke-Verläufe:
Wie glatt ist die Energie, wie viele Übergänge gibt es. Kein Beat, keine
Phrase, keine Tonart — das Kernversprechen "dein Übergang liegt neben dem
Phrasenstart" war nicht einlösbar.

**Jetzt** läuft pro Set:

1. **Beat-Grid**: Alle Beats des Sets werden erkannt (librosa).
2. **Tempo pro Segment**: Jeder erkannte Track-Abschnitt bekommt sein
   eigenes BPM (Median der Beat-Abstände, Ränder ausgespart). Ein Set
   hat einen Tempo-Verlauf, kein globales BPM.
3. **Phrasen-Raster**: 32-Beat-Phrasen (8 Takte), pro Segment verankert.
4. **Tonart pro Segment**: Krumhansl-Profile + Camelot-Code, mit
   Konfidenz. Unsichere Erkennung → ehrlich null.
5. **Bewertung pro Übergang**: Phrase-Timing (in Beats!), Tempo-Match,
   harmonische Kompatibilität (Camelot-Rad), Energie-Form. Plus ein
   konkreter Feedback-Satz mit echten Zahlen, z.B.:
   *"Übergang bei 01:08 springt von 129 auf 144 BPM — gleiche die Tempi
   vor dem Blend an oder nutze einen Cut statt eines Blends."*

## Neuer Overall-Score (v2)

Der alte Score belohnte glatte Lautstärke und zählte Übergänge (das maß
den Detektor, nicht den DJ). Der neue Score mittelt die **Qualität der
Übergänge**: 30% Phrase-Timing, 30% Tempo-Match, 10% Harmonie,
10% Energie-Form, 10% Energie-Fluss, 10% Dramaturgie. Nicht messbare
Teile werden übersprungen, nie geraten.

## Frontend-Vertrag

- `key` + `camelot`: jetzt echte Messwerte (dominante Tonart des Sets)
- `scores.beatmatching` = Tempo-Match, `scores.timing` = Phrase-Timing,
  `scores.musicality` = Harmonie — alles echt gemessen
- Weiterhin ehrlich null: `eq`, `creativity`, `frequency`
- `setTransitions`: jetzt im snake_case-Format, das das Frontend wirklich
  liest (`mid_sec`, `bpm_before`, `phrase_alignment_score`, …) — das alte
  Format konnte die UI nicht auswerten. Neu pro Übergang: `feedback`
  (deutscher Coaching-Satz), `key_before/after`, `phrase_beats_off`.

## Neue Dateien

- `app/audio/beats.py` — Beat-Grid + Tempo pro Segment
- `app/audio/phrase_grid.py` — Phrasen-Raster + Abstand in Beats
- `app/audio/segment_keys.py` — Tonart pro Segment + Camelot-Kompatibilität
- `app/audio/transition_quality.py` — Bewertung + Feedback pro Übergang
- `tests/test_transition_quality.py` — 10 neue Unit-Tests

## Verifiziert

Sichtprüfung mit einem synthetischen Mix mit absichtlichem Tempo-Sprung
(128→140 BPM): Die Engine misst 129→144 BPM, erkennt den Sprung, misst
das Phrase-Timing in Beats und benennt beides im Feedback. 43/43 Tests grün.

## Ehrliche Grenzen (für die Roadmap)

1. **Phrasen-Anker**: Das Raster startet am ersten Beat jedes Segments.
   Verfehlt die Segment-Erkennung den Trackanfang, verschiebt sich das
   Raster. Nächster Schritt: echter Downbeat-Detektor.
2. **Beat-Tracker-Toleranz**: ~2-3% BPM-Abweichung möglich (144 statt 140).
3. **Key auf synthetischem Material**: Rauschen+Kicks ergeben eine
   "Tonart" mit mittlerer Konfidenz. Auf echter Musik aussagekräftiger —
   genau dafür braucht es die annotierten Test-Mixes (Ground Truth).
4. **Laufzeit**: 2,5-Minuten-Set ≈ 15s Analyse. Ein 60-Minuten-Set wird
   mehrere Minuten brauchen → Async-Verarbeitung vor echten Nutzertests.
