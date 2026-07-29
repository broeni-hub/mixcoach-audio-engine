from typing import Dict, List

from app.audio.events import MixEvent, events_to_dicts


def build_mix_events(set_analysis: Dict) -> List[Dict]:
    events: List[MixEvent] = []

    duration = float(set_analysis.get("duration", 0.0))

    events.append(
        MixEvent(
            time=0.0,
            event_type="set_start",
            confidence=1.0,
            description="Set beginnt.",
            metadata={},
        )
    )

    for boundary in set_analysis.get("track_boundaries", []):
        events.append(
            MixEvent(
                time=float(boundary["time"]),
                event_type="track_change",
                confidence=boundary.get("confidence"),
                description="Möglicher Trackwechsel erkannt.",
                metadata=boundary,
            )
        )

    for transition in set_analysis.get("transition_zones", []):
        events.append(
            MixEvent(
                time=float(transition["time"]),
                event_type="transition",
                confidence=transition.get("confidence"),
                description="Mögliche Übergangszone erkannt.",
                metadata=transition,
            )
        )

    for segment in set_analysis.get("detected_tracks", []):
        events.append(
            MixEvent(
                time=float(segment["start"]),
                event_type="track_start",
                confidence=segment.get("boundary_confidence"),
                description=f"Track-Segment {segment['index']} beginnt.",
                metadata=segment,
            )
        )

    if duration > 0:
        events.append(
            MixEvent(
                time=duration,
                event_type="set_end",
                confidence=1.0,
                description="Set endet.",
                metadata={},
            )
        )

    events.sort(key=lambda event: event.time)

    return events_to_dicts(events)