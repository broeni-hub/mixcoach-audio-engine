from typing import Dict, List


def build_segments(
    duration: float,
    transition_zones: List[Dict],
) -> List[Dict]:

    segments = []

    start = 0.0

    for index, zone in enumerate(transition_zones, start=1):

        end = float(zone["time"])

        if end <= start:
            continue

        segments.append(
            {
                "index": index,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "type": "track_segment",
            }
        )

        start = end

    if start < duration:

        segments.append(
            {
                "index": len(segments) + 1,
                "start": round(start, 2),
                "end": round(duration, 2),
                "duration": round(duration - start, 2),
                "type": "track_segment",
            }
        )

    return segments