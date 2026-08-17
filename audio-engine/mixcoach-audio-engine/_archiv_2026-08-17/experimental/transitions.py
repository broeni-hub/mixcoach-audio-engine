from typing import Dict, List

import numpy as np


def detect_energy_transitions(
    audio,
    window_seconds: float = 2.0,
    pre_seconds: float = 16.0,
    post_seconds: float = 16.0,
) -> List[Dict]:
    waveform = audio.waveform
    sr = audio.sample_rate

    window_size = int(sr * window_seconds)
    transitions = []

    if len(waveform) < window_size * 3:
        return transitions

    energies = []
    times = []

    for start in range(0, len(waveform) - window_size, window_size):
        chunk = waveform[start:start + window_size]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        energies.append(rms)
        times.append(start / sr)

    energies = np.array(energies)

    if energies.max() == 0:
        return transitions

    normalized = energies / energies.max()
    duration = audio.duration_seconds

    for i in range(1, len(normalized) - 1):
        before = normalized[i - 1]
        current = normalized[i]
        after = normalized[i + 1]

        drop = before - current
        rise = after - current

        if drop > 0.08 and rise > 0.06:
            center_time = times[i]
            start_time = max(0.0, center_time - pre_seconds)
            end_time = min(duration, center_time + post_seconds)

            transitions.append(
                {
                    "start_time": round(start_time, 2),
                    "center_time": round(center_time, 2),
                    "end_time": round(end_time, 2),
                    "duration": round(end_time - start_time, 2),
                    "type": "energy_transition_zone",
                    "confidence": round(float((drop + rise) / 2), 2),
                    "reason": "Energy dips and recovers, suggesting a possible transition zone.",
                    "energy_before": round(float(before), 3),
                    "energy_current": round(float(current), 3),
                    "energy_after": round(float(after), 3),
                }
            )

    return transitions