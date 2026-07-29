"""Phrasen-Raster fuer DJ-Sets.

Elektronische Musik ist ueberwiegend in 8-Bar-Phrasen (32 Beats)
organisiert. Ein Uebergang, der auf einem Phrasenstart landet, klingt
musikalisch; einer mitten in der Phrase wirkt versetzt.

Bekannte Vereinfachung (dokumentiert, bewusst): Das Raster wird am ersten
Beat jedes erkannten Segments verankert. Wenn die Segment-Erkennung den
Trackanfang verfehlt, verschiebt sich das Raster. Ein echter
Downbeat-Detektor ist der naechste Ausbauschritt.
"""

from typing import Dict, List, Optional

BEATS_PER_PHRASE = 32  # 8 Takte à 4 Beats


def build_phrase_grid(beats: List[float], segments: List[Dict]) -> List[Dict]:
    """Phrasengrenzen pro Segment, verankert am ersten Beat des Segments."""
    boundaries: List[Dict] = []

    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])

        segment_beats = [b for b in beats if start <= b < end]

        if len(segment_beats) < BEATS_PER_PHRASE:
            continue

        last_i = 0
        for i in range(0, len(segment_beats), BEATS_PER_PHRASE):
            boundaries.append(
                {
                    "time": round(segment_beats[i], 3),
                    "segment_index": segment["index"],
                    "phrase_number": i // BEATS_PER_PHRASE + 1,
                }
            )
            last_i = i

        # Raster ueber das Segmentende hinaus verlaengern (extrapoliert).
        # Sonst wird ein Uebergang, der 2 Beats VOR der naechsten
        # Phrasengrenze liegt, mit "30 Beats daneben" bestraft statt mit 2.
        beat_interval = (segment_beats[-1] - segment_beats[0]) / max(1, len(segment_beats) - 1)
        phrase_seconds = BEATS_PER_PHRASE * beat_interval
        next_time = segment_beats[last_i] + phrase_seconds
        phrase_number = last_i // BEATS_PER_PHRASE + 2

        while next_time <= end + phrase_seconds and beat_interval > 0:
            boundaries.append(
                {
                    "time": round(next_time, 3),
                    "segment_index": segment["index"],
                    "phrase_number": phrase_number,
                }
            )
            next_time += phrase_seconds
            phrase_number += 1

    return boundaries


def phrase_distance_beats(
    phrase_boundaries: List[Dict],
    center_time: float,
    local_bpm: Optional[float],
) -> Optional[float]:
    """Abstand eines Zeitpunkts zur naechsten Phrasengrenze - in Beats.

    In Beats statt Sekunden, damit schnelle Genres (DnB, 174 BPM) nicht
    systematisch schlechter bewertet werden als langsame (House, 120 BPM).
    """
    if not phrase_boundaries or not local_bpm or local_bpm <= 0:
        return None

    nearest = min(
        (float(b["time"]) for b in phrase_boundaries),
        key=lambda t: abs(t - center_time),
    )

    seconds_off = abs(center_time - nearest)
    beat_duration = 60.0 / local_bpm

    return round(seconds_off / beat_duration, 2)
