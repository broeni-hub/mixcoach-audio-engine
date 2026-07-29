from app.experimental.models import TrackAnalysis


def transition_timing_score(track_a: TrackAnalysis, track_b: TrackAnalysis) -> int:
    if not track_a.transitions or not track_a.phrases:
        return 50

    transition = track_a.transitions[0]
    center = transition.center_time

    phrase_starts = [phrase.start for phrase in track_a.phrases]

    nearest_phrase_start = min(
        phrase_starts,
        key=lambda start: abs(start - center),
    )

    diff = abs(center - nearest_phrase_start)

    if diff < 0.5:
        return 100

    if diff < 1:
        return 90

    if diff < 2:
        return 75

    if diff < 4:
        return 55

    return 30