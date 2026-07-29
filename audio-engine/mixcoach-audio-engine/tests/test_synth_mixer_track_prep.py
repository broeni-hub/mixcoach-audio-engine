"""Tests fuer tools/synth_mixer/track_prep.py (Camelot-Distanz, Phrasen-Raster)."""

from tools.synth_mixer.track_prep import _phrase_grid_for_bars, camelot_distance


def test_camelot_distance_same_key():
    assert camelot_distance("8A", "8A") == 0


def test_camelot_distance_neighbor():
    assert camelot_distance("8A", "9A") == 1


def test_camelot_distance_relative_major_minor():
    assert camelot_distance("8A", "8B") == 1


def test_camelot_distance_wraps_around_wheel():
    # 1 und 12 sind Nachbarn auf dem Rad (Ring geschlossen).
    assert camelot_distance("1A", "12A") == 1


def test_camelot_distance_far_apart():
    assert camelot_distance("1A", "7A") == 6


def test_camelot_distance_unknown_key_is_none():
    assert camelot_distance(None, "8A") is None
    assert camelot_distance("8A", None) is None
    assert camelot_distance("garbage", "8A") is None


def test_phrase_grid_for_bars_basic():
    # 120 BPM -> 0.5s/Beat -> 2s/Bar. 8-Bar-Phrase = 16s.
    downbeats = [i * 2.0 for i in range(20)]  # 0, 2, 4, ..., 38
    grid = _phrase_grid_for_bars(downbeats, duration=40.0, bars_per_phrase=8)
    assert grid[0] == 0.0
    assert grid[1] == 16.0
    assert grid[2] == 32.0


def test_phrase_grid_for_bars_too_few_downbeats_returns_empty():
    assert _phrase_grid_for_bars([1.0, 2.0], duration=40.0, bars_per_phrase=32) == []
