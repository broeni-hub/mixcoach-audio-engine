from typing import Dict, List

import numpy as np


def detect_transition_zones(energy: Dict) -> List[Dict]:
    points = energy.get("points", [])

    if len(points) < 3:
        return []

    rms_values = np.array([point["rms"] for point in points])

    max_rms = float(np.max(rms_values))

    if max_rms <= 0:
        return []

    normalized = rms_values / max_rms
    zones = []

    for index in range(1, len(normalized) - 1):

        before = normalized[index - 1]
        current = normalized[index]
        after = normalized[index + 1]

        local_drop = before - current
        local_rise = after - current

        if local_drop > 0.08 and local_rise > 0.06:

            zones.append(
                {
                    "time": points[index]["time"],
                    "confidence": round(
                        float((local_drop + local_rise) / 2),
                        3,
                    ),
                    "energy_before": round(float(before), 3),
                    "energy_current": round(float(current), 3),
                    "energy_after": round(float(after), 3),
                    "type": "possible_transition",
                }
            )

    return zones