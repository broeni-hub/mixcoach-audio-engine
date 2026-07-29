from typing import Dict, List

import numpy as np


def calculate_energy_curve(audio, window_seconds: float = 2.0) -> Dict:
    waveform = audio.waveform
    sr = audio.sample_rate

    window_size = int(sr * window_seconds)

    if window_size <= 0:
        raise ValueError("window_seconds must be greater than 0")

    points: List[Dict] = []

    for start in range(0, len(waveform) - window_size, window_size):
        chunk = waveform[start:start + window_size]

        rms = float(np.sqrt(np.mean(chunk ** 2)))
        peak = float(np.max(np.abs(chunk)))

        points.append({
            "time": round(start / sr, 2),
            "rms": round(rms, 5),
            "peak": round(peak, 5),
        })

    if not points:
        return {
            "points": [],
            "average_rms": 0.0,
            "max_peak": 0.0,
        }

    average_rms = float(np.mean([p["rms"] for p in points]))
    max_peak = float(max(p["peak"] for p in points))

    return {
        "points": points,
        "average_rms": round(average_rms, 5),
        "max_peak": round(max_peak, 5),
    }