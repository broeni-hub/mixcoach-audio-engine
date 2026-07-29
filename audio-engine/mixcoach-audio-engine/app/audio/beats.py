"""Beat-Grid und Tempo-Analyse fuer komplette Sets.

Liefert die Grundlage fuer Phrasen-Raster und Tempo-pro-Segment.
Ein globales BPM ist fuer ein DJ-Set zu grob - Sets haben Tempo-Verlaeufe.
"""

from typing import Dict, List, Optional

import librosa
import numpy as np


def detect_beat_grid(audio) -> Dict:
    """Beat-Zeitpunkte ueber das gesamte Set (librosa beat tracker)."""
    y = audio.waveform
    sr = audio.sample_rate

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
    )

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    tempo_value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)

    return {
        "beats": [round(float(t), 3) for t in beat_times],
        "tempo_global": round(tempo_value, 2),
        "beat_count": int(len(beat_times)),
    }


def tempo_for_window(
    beats: List[float],
    start: float,
    end: float,
    min_beats: int = 12,
) -> Optional[float]:
    """Lokales Tempo aus den Beat-Abstaenden innerhalb eines Zeitfensters.

    Median statt Mittelwert, damit einzelne Fehl-Beats nicht durchschlagen.
    Gibt None zurueck, wenn zu wenige Beats im Fenster liegen - dann wird
    ehrlich 'nicht messbar' gemeldet statt einer erfundenen Zahl.
    """
    window = [b for b in beats if start <= b < end]

    if len(window) < min_beats:
        return None

    intervals = np.diff(np.array(window))
    intervals = intervals[(intervals > 0.2) & (intervals < 2.0)]  # 30-300 BPM

    if len(intervals) < min_beats - 1:
        return None

    median_interval = float(np.median(intervals))

    if median_interval <= 0:
        return None

    return round(60.0 / median_interval, 2)


def segment_tempos(beats: List[float], segments: List[Dict]) -> List[Dict]:
    """Tempo pro erkanntem Track-Segment.

    Die Randbereiche (je 10%) werden abgeschnitten, damit der Uebergang
    selbst die Messung nicht verfaelscht.
    """
    results = []

    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        margin = (end - start) * 0.1

        bpm = tempo_for_window(beats, start + margin, end - margin)

        results.append(
            {
                "segment_index": segment["index"],
                "start": start,
                "end": end,
                "bpm": bpm,
            }
        )

    return results
