from app.experimental.models import TrackAnalysis


def phrase_score(track_a: TrackAnalysis, track_b: TrackAnalysis) -> int:
    if not track_a.phrases or not track_b.phrases:
        return 50

    start_a = track_a.phrases[0].start
    start_b = track_b.phrases[0].start

    diff = abs(start_a - start_b)

    if diff < 0.25:
        return 100

    if diff < 0.5:
        return 90

    if diff < 1:
        return 80

    if diff < 2:
        return 60

    return 30