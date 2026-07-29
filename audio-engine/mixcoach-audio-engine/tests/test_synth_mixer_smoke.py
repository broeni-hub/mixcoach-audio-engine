"""Smoke-Test: aus 3 synthetischen Sinus/Click-Tracks (keine echten
Audiodateien noetig) einen Mini-Mix bauen und pruefen, dass die
Uebergangs-Zeitstempel im Label wirklich zum tatsaechlichen RMS-Sprung im
Audio passen - nicht nur, dass der Code durchlaeuft."""

import random
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from tools.synth_mixer.config import SAMPLE_RATE
from tools.synth_mixer.generator import build_mix

SR = SAMPLE_RATE


def _make_click_track(bpm: float, seconds: float, level: float, tone_hz: float) -> np.ndarray:
    """Sinus-Pad + percussive Clicks auf jedem Beat - genug Perkussion,
    damit librosas Beat-Tracker ein sauberes Tempo erkennt."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    pad = np.sin(2 * np.pi * tone_hz * t) * (level * 0.3)

    signal = pad.copy()
    beat_interval = int(SR * 60.0 / bpm)
    click_len = 1200
    for start in range(0, n - click_len, beat_interval):
        ct = np.arange(click_len) / SR
        click = np.sin(2 * np.pi * 90 * ct) * np.exp(-ct * 40)
        signal[start:start + click_len] += click * level

    return signal.astype(np.float32)


@pytest.fixture
def synthetic_tracks(tmp_path: Path) -> list[Path]:
    bpm = 120.0
    # Deutlich unterschiedliche Pegel je Track, damit ein RMS-Vorher/Nachher-
    # Vergleich den Uebergang eindeutig zeigt (unabhaengig vom Click-Rauschen).
    specs = [
        ("track_a.wav", 0.9, 220.0),
        ("track_b.wav", 0.2, 330.0),
        ("track_c.wav", 0.9, 440.0),
    ]
    paths = []
    for name, level, tone in specs:
        y = _make_click_track(bpm, seconds=40.0, level=level, tone_hz=tone)
        path = tmp_path / name
        sf.write(str(path), y, SR, format="WAV")
        paths.append(path)
    return paths


def _rms(waveform: np.ndarray, sr: int, t0: float, t1: float) -> float:
    a, b = int(t0 * sr), int(t1 * sr)
    a, b = max(0, a), min(len(waveform), b)
    if b <= a:
        return 0.0
    seg = waveform[a:b]
    return float(np.sqrt(np.mean(seg**2)))


def test_smoke_mini_mix_transition_timestamps_match_audio(synthetic_tracks):
    rng = random.Random(0)
    # "abrupt" -> harter Cut: die Uebergangsstelle ist im Audio ein
    # eindeutiger Pegelsprung, nicht ueber einen Blend verschmiert.
    profile_sequence = ["abrupt", "abrupt"]

    waveform, label = build_mix(synthetic_tracks, profile_sequence, rng, mix_id="smoke_test_001")

    assert len(label.tracks) == 3
    assert len(label.transitions) == 2
    assert label.duration_seconds == pytest.approx(len(waveform) / SR, abs=0.01)
    assert label.sample_rate == SR

    for transition in label.transitions:
        center = transition.center_time
        before = _rms(waveform, SR, center - 1.0, center - 0.3)
        after = _rms(waveform, SR, center + 0.3, center + 1.0)

        assert before > 0.0 and after > 0.0, "RMS vor/nach dem Uebergang nicht messbar (Fenster leer?)"
        ratio = max(before, after) / min(before, after)
        assert ratio > 1.5, (
            f"Kein klarer Pegelsprung um den gemeldeten Uebergang bei {center:.2f}s "
            f"(RMS davor={before:.3f}, danach={after:.3f}) - Timestamp im Label "
            f"stimmt vermutlich nicht mit dem tatsaechlichen Audio ueberein."
        )
