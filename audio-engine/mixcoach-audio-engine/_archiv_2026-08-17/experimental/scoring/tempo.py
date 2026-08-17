from typing import Dict

from app.experimental.models import TrackAnalysis


def tempo_score(track_a: TrackAnalysis, track_b: TrackAnalysis) -> Dict:
    tempo_a = float(track_a.tempo)
    tempo_b = float(track_b.tempo)

    tempo_diff = abs(tempo_a - tempo_b)

    if tempo_diff <= 1:
        score = 100
    elif tempo_diff <= 2:
        score = 95
    elif tempo_diff <= 4:
        score = 85
    elif tempo_diff <= 6:
        score = 70
    elif tempo_diff <= 8:
        score = 55
    elif tempo_diff <= 10:
        score = 40
    else:
        score = 20

    return {
        "score": score,
        "tempo_diff": round(tempo_diff, 2),
    }