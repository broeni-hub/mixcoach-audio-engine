from math import sqrt

from app.experimental.models import TrackAnalysis


def calculate_similarity(
    track_a: TrackAnalysis,
    track_b: TrackAnalysis,
) -> float:
    tempo = abs(track_a.tempo - track_b.tempo)

    energy = abs(
        track_a.energy.average_rms -
        track_b.energy.average_rms
    )

    similarity = 100 - (
        tempo * 3 +
        energy * 150
    )

    similarity = max(0.0, min(100.0, similarity))

    return round(similarity, 2)