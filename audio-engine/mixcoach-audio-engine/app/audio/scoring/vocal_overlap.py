"""Vocal-Overlap-Risiko - laufen im Blend beide Gesangsspuren gleichzeitig?

Gibt es bisher nicht in MixCoach. Funktioniert nach demselben Prinzip wie
app/audio/bass_overlap.py (dort fuer den Tieftonbereich, hier fuer die
Demucs-Vocals-Stem): erst pruefen, ob BEIDE Tracks in ihren Solo-Fenstern
ueberhaupt hoerbaren Gesang haben, dann vergleichen, ob die Vocal-Energie
im gemeinsamen Blend-Fenster deutlich ueber der eines einzelnen Sologesangs
liegt (= beide singen gleichzeitig, klingt matschig/unausgewogen).

KALIBRIERUNGS-STAND: die Schwellwerte unten (SILENCE_RMS, ACTIVE_RATIO, die
Rampe in der Risiko-Berechnung) sind ein Startwert ohne Ground-Truth-
Abgleich. Ueber app/calibration/fit_composite_weights.py spaeter gegen
labels_prefilled.csv nachschaerfen. Riskanteste der 5 neuen Dimensionen -
keine echte Quellentrennungs-Ground-Truth, nur ein Naeherungswert.

Score-Polaritaet WIE UEBERALL SONST im Composite: 100 = unproblematisch
(sauber, kein Ueberlapp), 0 = starker Verdacht auf gleichzeitigen Gesang.
Achtung, Gegenteil von bass_overlap_score (dort ist hoch = schlecht)!
"""

from typing import Optional

import numpy as np

MIN_SAMPLES_SECONDS = 1.5
SILENCE_RMS = 0.002
ACTIVE_RATIO = 0.35


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0


def vocal_overlap_score(
    tail_vocals: np.ndarray,
    head_vocals: np.ndarray,
    blend_vocals: np.ndarray,
    sample_rate: int,
) -> Optional[int]:
    min_samples = int(MIN_SAMPLES_SECONDS * sample_rate)
    windows = (tail_vocals, head_vocals, blend_vocals)
    if any(w is None or w.size < min_samples for w in windows):
        return None

    tail_e, head_e, blend_e = (_rms(w) for w in windows)
    loudest = max(tail_e, head_e, blend_e)

    if loudest < SILENCE_RMS:
        return 100  # in keinem Fenster hoerbarer Gesang - kein Risiko

    tail_active = tail_e >= loudest * ACTIVE_RATIO
    head_active = head_e >= loudest * ACTIVE_RATIO

    if not (tail_active and head_active):
        return 100  # hoechstens ein Track singt hier - kein Ueberlapp moeglich

    solo_reference = max(tail_e, head_e)
    ratio = blend_e / solo_reference if solo_reference > 0 else 0.0

    # ratio ~1.0 = etwa ein Solist kommt durch, ratio ~1.6+ = deutlich mehr
    # Vocal-Energie als ein einzelner Gesang -> beide laufen gleichzeitig.
    risk = max(0.0, min(1.0, (ratio - 1.0) / 0.6))
    return int(round((1.0 - risk) * 100))
