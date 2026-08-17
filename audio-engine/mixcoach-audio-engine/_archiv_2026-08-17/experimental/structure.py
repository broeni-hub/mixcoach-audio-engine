from typing import Any, Dict, List, Optional


def detect_track_structure(
    duration: float,
    tempo: float,
    energy: Optional[Any] = None,
) -> List[Dict]:
    return detect_structure(duration=duration, tempo=tempo, energy=energy)


def detect_structure(
    duration: float,
    tempo: float,
    energy: Optional[Any] = None,
) -> List[Dict]:
    if duration <= 0 or tempo <= 0:
        return []

    beat_duration = 60.0 / float(tempo)
    section_duration = beat_duration * 32

    sections: List[Dict] = []
    current = 0.0
    index = 0

    while current < duration:
        end = min(current + section_duration, duration)
        average_energy = _average_energy_between(energy, current, end)

        sections.append(
            {
                "start": round(current, 2),
                "end": round(end, 2),
                "section": _section_name(index, end, duration, average_energy),
                "average_energy": average_energy,
            }
        )

        current += section_duration
        index += 1

    return sections


def _section_name(index: int, end: float, duration: float, average_energy: float) -> str:
    if index == 0:
        return "intro"

    if end >= duration:
        return "outro"

    if average_energy >= 0.075:
        return "drop"

    if average_energy <= 0.035:
        return "break"

    return "main"


def _average_energy_between(energy: Optional[Any], start: float, end: float) -> float:
    points = _get_energy_points(energy)

    if not points:
        return 0.0

    values = [
        float(point["rms"])
        for point in points
        if start <= float(point["time"]) < end
    ]

    if not values:
        return 0.0

    return round(sum(values) / len(values), 5)


def _get_energy_points(energy: Optional[Any]) -> List[Dict]:
    if energy is None:
        return []

    if isinstance(energy, dict):
        return energy.get("points", [])

    if hasattr(energy, "points"):
        return [
            point.model_dump() if hasattr(point, "model_dump") else point
            for point in energy.points
        ]

    return []