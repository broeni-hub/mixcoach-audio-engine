"""Tests fuer die Duplikat-Erkennung im Fingerprint-Benchmark-Tool.

Die Benchmark-Genauigkeit haengt daran, dass akustische Duplikate (derselbe
Song zweimal in der Library, andere Datei) NICHT als Fehlalarm gezaehlt
werden - sonst sieht die Precision faelschlich schlechter aus als sie ist
(gefunden 2026-07-14: 2 von ~30 Matches waren Duplikate).
"""

import numpy as np

from tools.benchmark_fingerprint import _acoustic_duplicate


def _fake_chroma(n_frames: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((12, n_frames))


def test_identical_fingerprints_are_duplicates():
    chroma = _fake_chroma(300, seed=1)
    assert _acoustic_duplicate(chroma, chroma.copy())


def test_same_recording_slightly_different_length_is_duplicate():
    # Duplikat = dieselbe Aufnahme, evtl. minimal andere Laenge (Trim/Encode).
    chroma = _fake_chroma(400, seed=2)
    trimmed = chroma[:, :360].copy()
    assert _acoustic_duplicate(chroma, trimmed)


def test_different_songs_are_not_duplicates():
    a = _fake_chroma(300, seed=3)
    b = _fake_chroma(300, seed=99)
    assert not _acoustic_duplicate(a, b)


def test_too_short_is_not_duplicate():
    a = _fake_chroma(40, seed=4)
    assert not _acoustic_duplicate(a, a.copy())


def test_noisy_copy_still_duplicate():
    # Leichtes Rauschen (anderes Encoding) darf die Erkennung nicht kippen.
    rng = np.random.default_rng(5)
    a = _fake_chroma(300, seed=5)
    b = a + rng.normal(0, 0.02, a.shape)
    assert _acoustic_duplicate(a, b)


def test_shifted_copy_is_duplicate():
    # Verschiedene Rips desselben Songs starten oft leicht versetzt
    # (Encoder-Padding) - genau der real beobachtete Fall (daphni/bodzin).
    a = _fake_chroma(300, seed=6)
    shifted = a[:, 12:]  # ~2s Versatz bei ~5.4fps
    assert _acoustic_duplicate(a, shifted)


def test_shifted_different_songs_still_not_duplicates():
    a = _fake_chroma(300, seed=7)
    b = _fake_chroma(300, seed=77)
    assert not _acoustic_duplicate(a, b[:, 12:])
