"""Tests fuer die Bass-Overlap-Messung (Fingerprint-Alignment)."""

import numpy as np
import pytest
import soundfile as sf

from app.audio.bass_overlap import (
    annotate_bass_overlap,
    lowband_envelope,
    measure_transition_overlap,
)

SR = 22050


def _bass(seconds, freq=60.0, amp=0.5):
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float64)


def _hats(seconds, amp=0.2, seed=0):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, amp, int(seconds * SR))
    # Hochpass-artig: Tiefton entfernen, damit nur "Haette" bleiben
    from scipy.signal import butter, sosfilt
    sos = butter(4, 500.0, btype="high", fs=SR, output="sos")
    return sosfilt(sos, noise)


@pytest.fixture(scope="module")
def tracks(tmp_path_factory):
    """Zwei 'Library-Tracks': durchgehender Bass + Rauschen obendrauf."""
    d = tmp_path_factory.mktemp("lib")
    a = _bass(120, 55.0, 0.5) + _hats(120, seed=1)
    b = _bass(120, 65.0, 0.5) + _hats(120, seed=2)
    pa, pb = d / "a.wav", d / "b.wav"
    sf.write(pa, a, SR)
    sf.write(pb, b, SR)
    return str(pa), str(pb), a, b


def _build_set(a, b, overlap: bool):
    """Set: A 0-60s, Blend 60-75s, B ab 60s. overlap=True: beide Baesse im Blend."""
    total = int(135 * SR)
    out = np.zeros(total)
    from scipy.signal import butter, sosfilt
    hp = butter(4, 500.0, btype="high", fs=SR, output="sos")

    a_seg = a[: int(75 * SR)].copy()
    if not overlap:
        # Sauberer Swap: A verliert seinen Bass ab 60s (EQ-Kill)
        a_low_cut = sosfilt(hp, a[int(60 * SR): int(75 * SR)])
        a_seg[int(60 * SR):] = a_low_cut
    out[: int(75 * SR)] += a_seg
    out[int(60 * SR): int(60 * SR) + int(75 * SR)] += b[: int(75 * SR)]
    return out


def _matches(pa, pb):
    return [
        {"path": pa, "start": 0.0, "end": 75.0, "stretch": 1.0, "track_offset": 0.0},
        {"path": pb, "start": 60.0, "end": 135.0, "stretch": 1.0, "track_offset": 0.0},
    ]


def test_overlap_wird_hoch_bewertet(tracks):
    pa, pb, a, b = tracks
    wave = _build_set(a, b, overlap=True)
    st, se = lowband_envelope(wave, SR)
    score = measure_transition_overlap(st, se, *_matches(pa, pb), 60.0, 75.0)
    assert score is not None and score >= 60, score


def test_sauberer_swap_wird_niedrig_bewertet(tracks):
    pa, pb, a, b = tracks
    wave = _build_set(a, b, overlap=False)
    st, se = lowband_envelope(wave, SR)
    score = measure_transition_overlap(st, se, *_matches(pa, pb), 60.0, 75.0)
    assert score is not None and score <= 35, score


def test_fehlende_datei_gibt_ehrlich_none(tracks):
    pa, pb, a, b = tracks
    wave = _build_set(a, b, overlap=True)
    st, se = lowband_envelope(wave, SR)
    bad = [dict(_matches(pa, pb)[0], path="C:/gibt/es/nicht.wav"), _matches(pa, pb)[1]]
    assert measure_transition_overlap(st, se, bad[0], bad[1], 60.0, 75.0) is None


def test_annotate_setzt_score_und_feedback(tracks):
    pa, pb, a, b = tracks
    wave = _build_set(a, b, overlap=True)
    transitions = [{"mid_sec": 67.0, "start_sec": 60.0, "end_sec": 75.0,
                    "feedback": "Basis.", "feedback_en": "Base."}]
    annotate_bass_overlap(transitions, _matches(pa, pb), wave, SR)
    t = transitions[0]
    assert t.get("bass_overlap_score") is not None and t["bass_overlap_score"] >= 60
    assert "Overlap" in t["feedback"] and "overlap" in t["feedback_en"]
