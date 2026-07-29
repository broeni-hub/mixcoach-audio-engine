"""Tests fuer die K-gewichtete Lautheits-Analyse."""

import numpy as np

from app.audio.loudness import (
    annotate_transitions,
    loudness_curve,
    set_loudness_summary,
)

SR = 22050


def _noise(seconds, gain, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.normal(0, 0.1, int(seconds * SR)) * gain).astype(np.float64)


def test_gain_sprung_wird_in_db_gemessen():
    """Halbe Amplitude = -6.02 dB - muss als Sprung ankommen."""
    wave = np.concatenate([_noise(120, 1.0), _noise(120, 0.5, seed=1)])
    times, values = loudness_curve(wave, SR)

    transitions = [{"start_sec": 118.0, "end_sec": 122.0, "feedback": "Basis."}]
    annotate_transitions(transitions, times, values, duration=240.0)

    jump = transitions[0]["loudness_jump_db"]
    assert jump is not None
    assert -7.5 < jump < -4.5, jump
    assert "dB" in transitions[0]["feedback"]  # hoerbarer Sprung -> Hinweis


def test_gleicher_pegel_kein_alarm():
    wave = np.concatenate([_noise(120, 1.0), _noise(120, 1.0, seed=1)])
    times, values = loudness_curve(wave, SR)
    transitions = [{"start_sec": 118.0, "end_sec": 122.0, "feedback": "Basis."}]
    annotate_transitions(transitions, times, values, duration=240.0)

    assert abs(transitions[0]["loudness_jump_db"]) < 1.0
    assert transitions[0]["feedback"] == "Basis."  # kein unnoetiger Hinweis


def test_randnaehe_gibt_ehrlich_none():
    wave = _noise(60, 1.0)
    times, values = loudness_curve(wave, SR)
    transitions = [{"start_sec": 5.0, "end_sec": 55.0, "feedback": ""}]
    annotate_transitions(transitions, times, values, duration=60.0)
    assert transitions[0]["loudness_jump_db"] is None


def test_summary_liefert_range_und_drift():
    wave = np.concatenate([_noise(100, 0.5), _noise(100, 1.0, seed=1)])
    times, values = loudness_curve(wave, SR)
    summary = set_loudness_summary(times, values)
    assert summary is not None
    assert summary["range_db"] > 4
    assert summary["drift_db"] > 4  # zweite Haelfte lauter
