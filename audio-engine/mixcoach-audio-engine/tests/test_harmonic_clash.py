"""Tests fuer den Chroma-basierten Harmonic-Clash (Composite-Score, Dim. 1)."""

import numpy as np

from app.audio.scoring.harmonic_clash import harmonic_clash_score

SR = 22050


def _sine(freq: float, seconds: float = 3.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_identical_pitch_scores_high():
    a = _sine(440.0)
    b = _sine(440.0)
    score = harmonic_clash_score(a, b, SR)
    assert score is not None
    assert score >= 85


def test_octave_apart_still_scores_high():
    """Chroma ist oktav-invariant - eine Oktave hoeher gilt als dieselbe Tonhoehenklasse."""
    a = _sine(220.0)
    b = _sine(440.0)
    score = harmonic_clash_score(a, b, SR)
    assert score is not None
    assert score >= 75


def test_tritone_scores_lower_than_unison():
    a = _sine(440.0)
    tritone = _sine(440.0 * 2 ** (6 / 12))
    unison_score = harmonic_clash_score(a, _sine(440.0), SR)
    tritone_score = harmonic_clash_score(a, tritone, SR)
    assert tritone_score is not None and unison_score is not None
    assert tritone_score < unison_score


def test_silence_returns_none():
    silence = np.zeros(int(SR * 3), dtype=np.float32)
    tone = _sine(440.0)
    assert harmonic_clash_score(silence, tone, SR) is None


def test_too_short_returns_none():
    a = _sine(440.0, seconds=0.5)
    b = _sine(440.0, seconds=0.5)
    assert harmonic_clash_score(a, b, SR) is None
