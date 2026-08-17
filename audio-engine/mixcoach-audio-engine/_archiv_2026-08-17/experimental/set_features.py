from typing import Dict

from app.audio.energy import calculate_energy_curve
from app.audio.tempo import detect_tempo


def extract_set_features(audio) -> Dict:
    energy = calculate_energy_curve(audio, window_seconds=5.0)
    tempo = detect_tempo(audio)

    return {
        "energy": energy,
        "tempo": tempo,
    }