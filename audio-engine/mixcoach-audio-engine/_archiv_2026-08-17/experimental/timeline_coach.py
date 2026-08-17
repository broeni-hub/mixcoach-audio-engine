from typing import Dict, List


def generate_timeline_feedback(set_analysis: Dict) -> List[Dict]:
    timeline = set_analysis.get("timeline", [])
    feedback: List[Dict] = []

    if not timeline:
        return [
            {
                "time": 0.0,
                "severity": "medium",
                "message": "Keine Timeline-Events erkannt. Das Set ist entweder sehr glatt oder die Erkennung ist noch zu grob.",
            }
        ]

    track_changes = [
        event for event in timeline
        if event.get("type") == "track_change"
    ]

    transitions = [
        event for event in timeline
        if event.get("type") == "transition"
    ]

    if len(track_changes) == 0:
        feedback.append(
            {
                "time": 0.0,
                "severity": "medium",
                "message": "Keine klaren Trackwechsel erkannt. Für lange Sets sollten Übergänge deutlicher modelliert werden.",
            }
        )

    if len(transitions) > len(track_changes) * 3 and track_changes:
        feedback.append(
            {
                "time": 0.0,
                "severity": "low",
                "message": "Viele Übergangszonen, aber wenige Trackwechsel. Die Erkennung ist möglicherweise zu empfindlich.",
            }
        )

    for event in track_changes:
        confidence = event.get("confidence") or 0.0

        if confidence >= 0.75:
            feedback.append(
                {
                    "time": event["time"],
                    "severity": "low",
                    "message": "Starker Kandidat für einen Trackwechsel.",
                }
            )
        elif confidence < 0.35:
            feedback.append(
                {
                    "time": event["time"],
                    "severity": "medium",
                    "message": "Unsicherer Trackwechsel. Hier sollte später zusätzlich BPM, Key oder Fingerprint geprüft werden.",
                }
            )

    return feedback