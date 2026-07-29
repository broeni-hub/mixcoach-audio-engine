from typing import Dict, List


def detect_track_boundaries(set_analysis: Dict) -> List[Dict]:
    transition_zones = set_analysis.get("transition_zones", [])
    duration = float(set_analysis.get("duration", 0.0))

    boundaries: List[Dict] = []

    for index, zone in enumerate(transition_zones, start=1):
        time = float(zone.get("time", 0.0))
        confidence = float(zone.get("confidence", 0.0))

        if time <= 0 or time >= duration:
            continue

        boundary_score = min(1.0, confidence * 2.5)

        if boundary_score < 0.15:
            continue

        boundaries.append(
            {
                "index": index,
                "time": round(time, 2),
                "confidence": round(boundary_score, 3),
                "reason": "Energy dip/rise pattern suggests a possible track change.",
            }
        )

    return boundaries


def build_track_segments_from_boundaries(
    duration: float,
    boundaries: List[Dict],
) -> List[Dict]:
    segments: List[Dict] = []
    start = 0.0

    sorted_boundaries = sorted(
        boundaries,
        key=lambda item: item["time"],
    )

    for index, boundary in enumerate(sorted_boundaries, start=1):
        end = float(boundary["time"])

        if end <= start:
            continue

        segments.append(
            {
                "index": index,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "type": "detected_track",
                "boundary_confidence": boundary["confidence"],
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
                "type": "detected_track",
                "boundary_confidence": None,
            }
        )

    return segments