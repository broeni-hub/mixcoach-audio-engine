from typing import Dict, List


def build_timeline(set_analysis: Dict) -> List[Dict]:
    events: List[Dict] = []

    for boundary in set_analysis.get("track_boundaries", []):
        events.append(
            {
                "time": float(boundary["time"]),
                "type": "track_change",
                "confidence": boundary.get("confidence"),
                "description": "Möglicher Trackwechsel erkannt.",
            }
        )

    for transition in set_analysis.get("transition_zones", []):
        events.append(
            {
                "time": float(transition["time"]),
                "type": "transition",
                "confidence": transition.get("confidence"),
                "description": "Mögliche Übergangszone erkannt.",
            }
        )

    for segment in set_analysis.get("detected_tracks", []):
        events.append(
            {
                "time": float(segment["start"]),
                "type": "track_segment_start",
                "track_index": segment["index"],
                "description": f"Track-Segment {segment['index']} beginnt.",
            }
        )

    events.sort(key=lambda event: event["time"])

    return events