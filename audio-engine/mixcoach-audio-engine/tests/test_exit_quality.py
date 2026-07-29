"""Tests fuer die Track-1-Exit-Qualitaet via RMS-Verlauf (Composite-Score, Dim. 3)."""

from app.audio.scoring.exit_quality import annotate_exit_quality, exit_quality_score


def _points(times_rms):
    return [{"time": t, "rms": r} for t, r in times_rms]


def test_smooth_fade_scores_high():
    rms = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    assert exit_quality_score(rms) >= 80


def test_jagged_return_scores_lower_than_smooth_fade():
    jagged = [1.0, 0.5, 0.9, 0.4, 0.8, 0.3, 0.7, 0.2]
    smooth = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    assert exit_quality_score(jagged) < exit_quality_score(smooth)


def test_no_decline_scores_low():
    flat_ish = [0.5, 0.51, 0.49, 0.5, 0.52, 0.5]
    score = exit_quality_score(flat_ish)
    assert score is not None
    assert score < 60


def test_too_few_points_returns_none():
    assert exit_quality_score([0.5, 0.4]) is None


def test_silent_start_returns_none():
    assert exit_quality_score([0.0, 0.0, 0.0, 0.0, 0.0]) is None


def test_annotate_uses_window_between_start_and_mid():
    transitions = [{"start_sec": 10.0, "mid_sec": 18.0}]
    points = _points([
        (9.0, 1.0),   # vor dem Fenster - muss ignoriert werden
        (10.0, 1.0), (12.0, 0.8), (14.0, 0.6), (16.0, 0.4), (18.0, 0.2),
        (20.0, 0.1),  # nach dem Fenster - muss ignoriert werden
    ])

    annotate_exit_quality(transitions, points)

    assert transitions[0]["exit_quality_score"] is not None
    assert transitions[0]["scores"]["exit_quality"] == transitions[0]["exit_quality_score"]


def test_annotate_missing_bounds_returns_none():
    transitions = [{"start_sec": None, "mid_sec": None}]
    annotate_exit_quality(transitions, [])
    assert transitions[0]["exit_quality_score"] is None
