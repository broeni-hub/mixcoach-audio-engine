from app.experimental.models import TrackAnalysis


def harmonic_score(track_a: TrackAnalysis, track_b: TrackAnalysis) -> int:
    camelot_a = track_a.key.camelot
    camelot_b = track_b.key.camelot

    if not camelot_a or not camelot_b:
        return 50

    if camelot_a == camelot_b:
        return 100

    try:
        number_a = int(camelot_a[:-1])
        mode_a = camelot_a[-1]

        number_b = int(camelot_b[:-1])
        mode_b = camelot_b[-1]

    except ValueError:
        return 50

    if mode_a == mode_b and abs(number_a - number_b) in {1, 11}:
        return 95

    if number_a == number_b and mode_a != mode_b:
        return 90

    return 40