"""Orchestriert die Demucs-Trennung pro Uebergang fuer die stem-basierten
Scoring-Dimensionen (Harmonic-Clash, Vocal-Overlap).

Ein Demucs-Aufruf pro Uebergang, nicht drei: das gesamte
[start_sec, end_sec]-Fenster wird EINMAL getrennt, Tail/Head/Blend-Teil-
fenster werden danach nur noch aus dem bereits getrennten Ergebnis
herausgeschnitten (kein wiederholtes Trennen ueberlappender Bereiche).
"""

from typing import Dict, List

import numpy as np

from app.audio.scoring import stems as stem_lib
from app.audio.scoring.harmonic_clash import harmonic_clash_score
from app.audio.scoring.vocal_overlap import vocal_overlap_score

BLEND_HALF_WINDOW_SECONDS = 6.0


def _slice(array: np.ndarray, sr: int, window_start: float, a: float, b: float) -> np.ndarray:
    """Schneidet [a, b] (absolute Set-Zeit in Sekunden) aus einem Array aus,
    das bei window_start beginnt."""
    start_idx = max(0, int(round((a - window_start) * sr)))
    end_idx = min(array.size, int(round((b - window_start) * sr)))
    if end_idx <= start_idx:
        return np.array([], dtype=array.dtype)
    return array[start_idx:end_idx]


def annotate_stem_based_scores(
    transitions_detailed: List[Dict], waveform: np.ndarray, sample_rate: int,
) -> None:
    """Haengt harmonic_clash_score + vocal_overlap_score an jeden Uebergang.

    Beide bleiben None, wenn Demucs fuer dieses Fenster fehlschlaegt oder das
    Fenster zu kurz ist - nie ein geratener Wert (siehe stems.py)."""
    for t in transitions_detailed:
        start = t.get("start_sec")
        mid = t.get("mid_sec")
        end = t.get("end_sec")

        if start is None or mid is None or end is None or float(end) <= float(start):
            t["harmonic_clash_score"] = None
            t["vocal_overlap_score"] = None
            continue

        start_f, mid_f, end_f = float(start), float(mid), float(end)
        start_idx = max(0, int(round(start_f * sample_rate)))
        end_idx = min(waveform.size, int(round(end_f * sample_rate)))
        window = waveform[start_idx:end_idx]

        separated = stem_lib.separate_window(window, sample_rate)
        if separated is None:
            t["harmonic_clash_score"] = None
            t["vocal_overlap_score"] = None
            continue

        stem_sr = stem_lib.stems_samplerate()
        vocals = separated["vocals"]
        harmonic = separated["other"] + separated["vocals"]

        tail_harmonic = _slice(harmonic, stem_sr, start_f, start_f, mid_f)
        head_harmonic = _slice(harmonic, stem_sr, start_f, mid_f, end_f)
        tail_vocals = _slice(vocals, stem_sr, start_f, start_f, mid_f)
        head_vocals = _slice(vocals, stem_sr, start_f, mid_f, end_f)
        blend_vocals = _slice(
            vocals, stem_sr, start_f,
            max(start_f, mid_f - BLEND_HALF_WINDOW_SECONDS),
            min(end_f, mid_f + BLEND_HALF_WINDOW_SECONDS),
        )

        harmonic_score = harmonic_clash_score(tail_harmonic, head_harmonic, stem_sr)
        vocal_score = vocal_overlap_score(tail_vocals, head_vocals, blend_vocals, stem_sr)

        t["harmonic_clash_score"] = harmonic_score
        t["vocal_overlap_score"] = vocal_score
        scores = t.setdefault("scores", {})
        scores["harmonic_clash"] = harmonic_score
        scores["vocal_overlap"] = vocal_score
