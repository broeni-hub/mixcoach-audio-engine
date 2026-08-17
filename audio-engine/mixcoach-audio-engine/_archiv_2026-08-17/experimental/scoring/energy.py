from app.experimental.models import TrackAnalysis


def energy_score(track_a: TrackAnalysis, track_b: TrackAnalysis) -> int:
    energy_a = track_a.energy.average_rms
    energy_b = track_b.energy.average_rms

    if energy_a <= 0 or energy_b <= 0:
        return 50

    diff_ratio = abs(energy_a - energy_b) / max(energy_a, energy_b)

    if diff_ratio < 0.10:
        return 100

    if diff_ratio < 0.20:
        return 85

    if diff_ratio < 0.35:
        return 65

    if diff_ratio < 0.50:
        return 45

    return 25