"""Tests fuer die Foote-Novelty-Segmentierung."""

import numpy as np

from app.audio.foote import (
    beat_sync_features,
    foote_novelty,
    foote_peaks,
    novelty_zscore_at,
    refine_boundary,
)


def _synthetic_beat_features(n_beats=400, change_at=200):
    """Beat-Features: Textur A bis change_at, dann Textur B."""
    rng = np.random.default_rng(3)
    D = 31
    a = rng.normal(0, 0.05, (D, n_beats)) + 0.05
    a[2, :change_at] += 1.0    # Textur A
    a[17, change_at:] += 1.0   # Textur B
    norms = np.linalg.norm(a, axis=0, keepdims=True)
    return a / norms


def test_novelty_peaks_at_texture_change():
    feats = _synthetic_beat_features()
    novelty = foote_novelty(feats)

    peak = int(np.argmax(novelty))
    assert abs(peak - 200) <= 4, f"Peak bei Beat {peak}, erwartet ~200"


def test_flat_features_produce_no_peaks():
    rng = np.random.default_rng(1)
    feats = rng.normal(0.5, 0.01, (31, 400))
    feats /= np.linalg.norm(feats, axis=0, keepdims=True)

    beats = [i * 0.5 for i in range(400)]
    peaks = foote_peaks(foote_novelty(feats), beats)

    assert len(peaks) <= 2  # Rauschen darf keine Peak-Flut erzeugen


def test_peaks_respect_min_distance():
    feats = _synthetic_beat_features()
    beats = [i * 0.5 for i in range(400)]
    peaks = foote_peaks(foote_novelty(feats), beats)

    times = [p["beat_index"] for p in peaks]
    for a, b in zip(times, times[1:]):
        assert b - a >= 32


def test_refine_boundary_finds_start_before_peak():
    feats = _synthetic_beat_features()
    novelty = foote_novelty(feats)
    beats = [i * 0.5 for i in range(400)]

    # Grobe Boundary 5s (10 Beats) neben dem echten Wechsel bei Beat 200 (=100s)
    refined = refine_boundary(105.0, beats, novelty)

    assert refined is not None
    assert abs(refined["peak_time"] - 100.0) <= 3.0
    assert refined["start_time"] <= refined["peak_time"]
    # Der Anstieg beginnt vor dem Peak, aber nicht absurd weit davor.
    assert refined["peak_time"] - refined["start_time"] <= 40.0


def test_zscore_sampling():
    feats = _synthetic_beat_features()
    novelty = foote_novelty(feats)
    beats = [i * 0.5 for i in range(400)]

    at_change, far_away = novelty_zscore_at([100.0, 30.0], beats, novelty)
    assert at_change > far_away
    assert at_change > 2.0  # klarer Ausreisser am Wechsel


def test_beat_sync_shapes():
    chroma = np.random.default_rng(0).random((12, 5000))
    mfcc = np.random.default_rng(1).random((20, 5000))
    beats = [i * 0.5 for i in range(100)]

    feats = beat_sync_features(chroma, mfcc, beats, 22050)

    assert feats.shape[0] == 12 + 19  # Chroma + MFCC ohne c0
    assert feats.shape[1] == 99       # ein Vektor pro Beat-Intervall
