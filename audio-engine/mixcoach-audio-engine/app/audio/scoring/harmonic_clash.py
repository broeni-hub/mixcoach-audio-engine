"""Harmonic-Clash im Overlap-Fenster - Chroma-Vergleich auf isolierten Stems.

Unterschied zum bestehenden Harmonic-Score (transition_quality.py, ueber
segment_keys.camelot_compatibility_score): der bestehende Score vergleicht
nur die JE EINE dominante Tonart pro Segment (grob, diskret: gleich/
Nachbar/relativ/weit - 4 Stufen). Diese Dimension vergleicht den TATSAECH-
LICHEN Chroma-Fingerabdruck (12-dimensionaler Tonhoehenklassen-Vektor) der
beiden Tracks direkt vor/nach dem Uebergang - stufenlos statt diskret, und
misst echte Ueberschneidung statt nur den Wechsel des dominanten Grundtons.

"Harmonisch" heisst hier: Schlagzeug/Bass rausgerechnet (Demucs-Stems
'other' + 'vocals'), damit Perkussion die Chroma-Schaetzung nicht verzerrt -
das ist der Hauptgrund, staerker aufgeloeste Stems statt der Roh-Aufnahme zu
nehmen.
"""

from typing import Optional

import librosa
import numpy as np

MIN_SAMPLES_SECONDS = 2.0


def _mean_chroma(audio: np.ndarray, sample_rate: int) -> Optional[np.ndarray]:
    if audio is None or audio.size < int(MIN_SAMPLES_SECONDS * sample_rate):
        return None
    if float(np.sqrt(np.mean(np.square(audio)))) < 1e-5:
        return None  # praktisch stumm (Instrumental-Stelle) - nicht messbar

    chroma = librosa.feature.chroma_cqt(y=audio.astype(np.float32), sr=sample_rate)
    mean = np.mean(chroma, axis=1)
    norm = np.linalg.norm(mean)
    if norm <= 1e-9:
        return None
    return mean / norm


def harmonic_clash_score(
    tail_harmonic: np.ndarray, head_harmonic: np.ndarray, sample_rate: int,
) -> Optional[int]:
    """0 (dissonant/clash) .. 100 (harmonisch passend) oder None (nicht messbar).

    Kosinus-Aehnlichkeit zweier normierter Chroma-Vektoren - beide Vektoren
    sind nicht-negativ, das Ergebnis liegt also automatisch in [0, 1].
    """
    chroma_a = _mean_chroma(tail_harmonic, sample_rate)
    chroma_b = _mean_chroma(head_harmonic, sample_rate)
    if chroma_a is None or chroma_b is None:
        return None

    similarity = float(np.dot(chroma_a, chroma_b))
    return int(round(max(0.0, min(1.0, similarity)) * 100))
