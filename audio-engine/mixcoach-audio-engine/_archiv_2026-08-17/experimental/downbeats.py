from typing import List


def detect_downbeats(beat_times: List[float]) -> List[float]:
    """
    Simple MVP:
    Every 4th beat is treated as a downbeat.

    This will later be replaced by a real downbeat detector.
    """

    return beat_times[::4]

