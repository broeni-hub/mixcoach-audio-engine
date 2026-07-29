from typing import Dict, List


def evaluate_set_rules(set_analysis: Dict) -> List[Dict]:
    events = set_analysis.get("events", [])
    quality = set_analysis.get("quality", {})
    dramaturgy = set_analysis.get("dramaturgy", {})

    findings: List[Dict] = []

    findings.extend(_check_low_quality(quality))
    findings.extend(_check_dramaturgy(dramaturgy))
    findings.extend(_check_event_density(events, set_analysis.get("duration", 0.0)))
    findings.extend(_check_low_confidence_track_changes(events))

    return findings


def _check_low_quality(quality: Dict) -> List[Dict]:
    raw = quality.get("overall")

    if raw is None:
        # Nicht messbar ist nicht dasselbe wie schlecht - kein Finding.
        return []

    overall = float(raw)

    if overall >= 70:
        return []

    return [
        {
            "severity": "high",
            "type": "low_set_quality",
            "time": 0.0,
            "message": "Die Gesamtqualität des Sets ist niedrig. Flow, Übergänge oder Dramaturgie sollten geprüft werden.",
        }
    ]


def _check_dramaturgy(dramaturgy: Dict) -> List[Dict]:
    trend = dramaturgy.get("energy_trend")

    if trend != "falling":
        return []

    return [
        {
            "severity": "medium",
            "type": "falling_energy",
            "time": 0.0,
            "message": "Die Energie fällt über das Set hinweg ab. Das kann gegen Ende schwächer wirken.",
        }
    ]


def _check_event_density(events: List[Dict], duration: float) -> List[Dict]:
    if duration <= 0:
        return []

    transitions = [
        event for event in events
        if event.get("event_type") == "transition"
    ]

    minutes = duration / 60.0
    transitions_per_10_min = len(transitions) / max(minutes / 10.0, 1)

    if transitions_per_10_min > 6:
        return [
            {
                "severity": "medium",
                "type": "too_many_transitions",
                "time": 0.0,
                "message": "Sehr viele Übergangszonen erkannt. Das Set könnte hektisch wirken oder die Erkennung ist zu empfindlich.",
            }
        ]

    if transitions_per_10_min < 1:
        return [
            {
                "severity": "low",
                "type": "few_transitions",
                "time": 0.0,
                "message": "Wenige Übergangszonen erkannt. Das Set wirkt eventuell sehr statisch oder die Übergänge sind sehr glatt.",
            }
        ]

    return []


def _check_low_confidence_track_changes(events: List[Dict]) -> List[Dict]:
    findings = []

    for event in events:
        if event.get("event_type") != "track_change":
            continue

        confidence = event.get("confidence")

        if confidence is None:
            continue

        if float(confidence) < 0.35:
            findings.append(
                {
                    "severity": "medium",
                    "type": "uncertain_track_change",
                    "time": float(event.get("time", 0.0)),
                    "message": "Unsicherer Trackwechsel erkannt. Hier sollte später Fingerprinting oder BPM-/Key-Abgleich helfen.",
                }
            )

    return findings