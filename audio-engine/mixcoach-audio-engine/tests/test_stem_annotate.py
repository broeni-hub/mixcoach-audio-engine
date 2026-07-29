"""Tests fuer die Demucs-Orchestrierung pro Uebergang.

Demucs selbst wird gemockt (separate_window/stems_samplerate) - hier wird
nur getestet, dass die richtigen Fenster ausgeschnitten und die Scores
korrekt an den Uebergang gehaengt werden, nicht die Modellqualitaet.
"""

import numpy as np

from app.audio.scoring import stem_annotate


def test_missing_window_returns_none(monkeypatch):
    calls = []
    monkeypatch.setattr(
        stem_annotate.stem_lib, "separate_window",
        lambda w, sr: calls.append(1) or None,
    )
    transitions = [{"start_sec": None, "mid_sec": None, "end_sec": None}]
    stem_annotate.annotate_stem_based_scores(transitions, np.zeros(1000), 22050)

    assert transitions[0]["harmonic_clash_score"] is None
    assert transitions[0]["vocal_overlap_score"] is None
    assert calls == []  # Demucs darf gar nicht erst aufgerufen werden


def test_separation_failure_sets_none(monkeypatch):
    monkeypatch.setattr(stem_annotate.stem_lib, "separate_window", lambda w, sr: None)
    transitions = [{"start_sec": 0.0, "mid_sec": 10.0, "end_sec": 20.0}]
    waveform = np.zeros(20 * 22050, dtype=np.float32)

    stem_annotate.annotate_stem_based_scores(transitions, waveform, 22050)

    assert transitions[0]["harmonic_clash_score"] is None
    assert transitions[0]["vocal_overlap_score"] is None


def test_calls_demucs_once_per_transition(monkeypatch):
    """Ein Demucs-Aufruf pro Uebergang, nicht drei (Tail/Head/Blend werden
    aus einem einzigen getrennten Fenster geschnitten)."""
    sr = 22050
    call_count = {"n": 0}

    def fake_separate(window, sample_rate):
        call_count["n"] += 1
        n = window.size
        rng = np.random.default_rng(0)
        return {
            "drums": np.zeros(n, dtype=np.float32),
            "bass": np.zeros(n, dtype=np.float32),
            "other": (rng.standard_normal(n) * 0.05).astype(np.float32),
            "vocals": (rng.standard_normal(n) * 0.05).astype(np.float32),
        }

    monkeypatch.setattr(stem_annotate.stem_lib, "separate_window", fake_separate)
    monkeypatch.setattr(stem_annotate.stem_lib, "stems_samplerate", lambda: sr)

    transitions = [{"start_sec": 0.0, "mid_sec": 15.0, "end_sec": 30.0}]
    waveform = np.zeros(30 * sr, dtype=np.float32)

    stem_annotate.annotate_stem_based_scores(transitions, waveform, sr)

    assert call_count["n"] == 1
    assert transitions[0]["harmonic_clash_score"] is not None
    assert transitions[0]["vocal_overlap_score"] is not None
    assert transitions[0]["scores"]["harmonic_clash"] == transitions[0]["harmonic_clash_score"]
    assert transitions[0]["scores"]["vocal_overlap"] == transitions[0]["vocal_overlap_score"]


def test_slice_helper_cuts_correct_range():
    sr = 10
    array = np.arange(100, dtype=np.float32)  # 10s @ sr=10
    window_start = 5.0  # Array-Index 0 entspricht Set-Zeit 5.0s

    sliced = stem_annotate._slice(array, sr, window_start, a=6.0, b=8.0)

    assert np.array_equal(sliced, array[10:30])
