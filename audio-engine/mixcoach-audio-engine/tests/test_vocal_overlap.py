"""Tests fuer das Vocal-Overlap-Risiko (Composite-Score, Dim. 2)."""

import numpy as np

from app.audio.scoring.vocal_overlap import vocal_overlap_score

SR = 22050


def _noise(level: float, seconds: float = 2.0, sr: int = SR) -> np.ndarray:
    rng = np.random.default_rng(0)
    return (rng.standard_normal(int(sr * seconds)) * level).astype(np.float32)


def test_only_one_track_singing_no_risk():
    tail = _noise(0.05)
    head = _noise(0.0003)  # praktisch still
    blend = _noise(0.05)
    assert vocal_overlap_score(tail, head, blend, SR) == 100


def test_both_silent_no_risk():
    tail = _noise(0.0001)
    head = _noise(0.0001)
    blend = _noise(0.0001)
    assert vocal_overlap_score(tail, head, blend, SR) == 100


def test_both_singing_blend_not_louder_low_risk():
    tail = _noise(0.05)
    head = _noise(0.05)
    blend = _noise(0.05)  # blend ~ wie ein Solist -> kein zusaetzliches Risiko
    score = vocal_overlap_score(tail, head, blend, SR)
    assert score is not None
    assert score >= 90


def test_both_singing_blend_much_louder_high_risk():
    tail = _noise(0.05)
    head = _noise(0.05)
    blend = _noise(0.09)  # deutlich mehr Energie als ein einzelner Gesang
    score = vocal_overlap_score(tail, head, blend, SR)
    assert score is not None
    assert score <= 40


def test_too_short_returns_none():
    tail = _noise(0.05, seconds=0.5)
    head = _noise(0.05, seconds=0.5)
    blend = _noise(0.05, seconds=0.5)
    assert vocal_overlap_score(tail, head, blend, SR) is None
