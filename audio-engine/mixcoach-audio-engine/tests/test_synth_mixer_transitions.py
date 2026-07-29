"""Tests fuer tools/synth_mixer/transitions.py."""

import numpy as np

from tools.synth_mixer.transitions import (
    crossfade_curve,
    estimate_phase_offset_samples,
    expected_quality_label,
    pick_transition_start,
    render_transition,
    sample_profile_params,
)


# ---------- Crossfade-Kurven ----------


def test_equal_power_conserves_energy():
    """fade_out**2 + fade_in**2 == 1 an jedem Punkt (konstante Lautstaerke)."""
    fade_out, fade_in = crossfade_curve("equal_power", 1000)
    energy = fade_out**2 + fade_in**2
    assert np.allclose(energy, 1.0, atol=1e-9)


def test_linear_curve_endpoints():
    fade_out, fade_in = crossfade_curve("linear", 100)
    assert fade_out[0] == 1.0
    assert fade_in[0] == 0.0
    assert abs(fade_out[-1]) < 0.02   # letzter Sample vor t=1 (endpoint=False)
    assert abs(fade_in[-1] - 1.0) < 0.02


def test_exponential_and_s_curve_endpoints_and_monotonic():
    for name in ("exponential", "s_curve"):
        fade_out, fade_in = crossfade_curve(name, 200)
        assert fade_out[0] > 0.95, name
        assert fade_in[0] < 0.05, name
        assert np.all(np.diff(fade_out) <= 1e-9), f"{name} fade_out nicht monoton fallend"
        assert np.all(np.diff(fade_in) >= -1e-9), f"{name} fade_in nicht monoton steigend"


def test_unknown_curve_raises():
    try:
        crossfade_curve("does-not-exist", 10)
        assert False, "haette ValueError werfen muessen"
    except ValueError:
        pass


# ---------- render_transition ----------


def test_render_transition_linear_matches_input_at_boundaries():
    """Gleicher Pegel auf beiden Seiten (Gain-Staging ist hier ein No-Op),
    damit der Boundary-Check unabhaengig vom Gain-Matching bleibt."""
    sr = 22050
    n = sr  # 1s Overlap
    tail_a = np.ones(n * 2, dtype=np.float32)
    head_b = np.ones(n * 2, dtype=np.float32)

    mixed = render_transition(tail_a, head_b, sr, "crossfade", "linear", n)

    assert len(mixed) == n
    assert abs(mixed[0] - 1.0) < 0.01
    assert abs(mixed[-1] - 1.0) < 0.02


def test_render_transition_matches_gain_before_blending():
    """Kern des Gain-Staging-Fixes (2026-07-13): B ist im Rohsignal deutlich
    leiser als A - ohne Gain-Matching wuerde der Uebergang nach einem
    Fade-out-ins-Leere klingen. Mit Matching landet das Ende des Blends auf
    A's Pegel, nicht auf B's leiserem Rohpegel."""
    sr = 22050
    n = sr
    tail_a = np.ones(n * 2, dtype=np.float32)
    # Ratio 2.5x - deutlich leiser, aber unter der 4x-Gain-Deckelung, damit
    # der Test das Matching zeigt statt die Sicherheits-Kappung.
    head_b = np.full(n * 2, 0.4, dtype=np.float32)

    mixed = render_transition(tail_a, head_b, sr, "crossfade", "linear", n)

    assert abs(mixed[-1] - 1.0) < 0.05, (
        f"Ende des Blends sollte nach Gain-Matching bei A's Pegel (1.0) liegen, "
        f"nicht bei B's unangeglichenem Rohpegel (0.4) - war {mixed[-1]:.3f}"
    )


def test_render_transition_cut_is_hard_switch():
    sr = 22050
    n = 2000
    tail_a = np.ones(n * 2, dtype=np.float32)
    head_b = np.full(n * 2, -1.0, dtype=np.float32)

    mixed = render_transition(tail_a, head_b, sr, "cut", "linear", n)

    # Weit vor dem Mikro-Ramp: noch A. Weit danach: schon B.
    assert mixed[0] == 1.0
    assert mixed[-1] == -1.0


def test_render_transition_beat_offset_shifts_b_content():
    sr = 22050
    n = 2000
    tail_a = np.zeros(n * 2, dtype=np.float32)
    head_b = np.arange(n * 3, dtype=np.float32)  # eindeutig identifizierbarer Inhalt

    mixed_no_offset = render_transition(tail_a, head_b, sr, "crossfade", "linear", n, beat_offset_samples=0)
    mixed_with_offset = render_transition(tail_a, head_b, sr, "crossfade", "linear", n, beat_offset_samples=500)

    assert not np.allclose(mixed_no_offset, mixed_with_offset)


# ---------- Quality-Profile-Parameter ----------


def test_sample_profile_params_clean_has_no_offsets():
    import random
    rng = random.Random(0)
    for _ in range(20):
        params = sample_profile_params("clean", rng)
        assert params["phrase_offset_beats"] == 0.0
        assert params["beat_offset_ms"] == 0.0


def test_sample_profile_params_off_phrase_within_range():
    import random
    from tools.synth_mixer.config import OFF_PHRASE_BEATS_RANGE
    rng = random.Random(1)
    lo, hi = OFF_PHRASE_BEATS_RANGE
    for _ in range(30):
        params = sample_profile_params("off_phrase", rng)
        assert lo <= params["phrase_offset_beats"] <= hi


def test_sample_profile_params_unknown_profile_raises():
    import random
    try:
        sample_profile_params("not-a-real-profile", random.Random(0))
        assert False
    except ValueError:
        pass


# ---------- expected_quality_label ----------


def test_expected_quality_label_mapping_table():
    assert expected_quality_label("clean") == 5
    assert expected_quality_label("off_phrase", phrase_offset_beats=2) == 3
    assert expected_quality_label("off_phrase", phrase_offset_beats=8) == 2
    assert expected_quality_label("off_beat", beat_offset_ms=50) == 3
    assert expected_quality_label("off_beat", beat_offset_ms=250) == 2
    assert expected_quality_label("key_clash", camelot_distance_value=2) == 2
    assert expected_quality_label("key_clash", camelot_distance_value=6) == 1
    assert expected_quality_label("abrupt") == 2
    assert expected_quality_label("train_wreck") == 1
    for label in (
        expected_quality_label("clean"),
        expected_quality_label("off_phrase", phrase_offset_beats=2),
        expected_quality_label("train_wreck"),
    ):
        assert 1 <= label <= 5


# ---------- pick_transition_start ----------


def test_pick_transition_start_snaps_to_phrase_boundary_when_no_offset():
    # 74.0 + 8s Overlap waere > 80s Tail -> die naechst-fruehere Grenze (42.0)
    # ist die letzte, die noch Platz fuer den Overlap laesst.
    boundaries = [10.0, 42.0, 74.0]
    start = pick_transition_start(boundaries, tail_duration=80.0, overlap_seconds=8.0,
                                  bpm=120.0, phrase_offset_beats=0.0)
    assert start == 42.0

    # Mit mehr Platz im Tail ist 74.0 gueltig und wird gewaehlt (spaeteste Grenze).
    start2 = pick_transition_start(boundaries, tail_duration=90.0, overlap_seconds=8.0,
                                   bpm=120.0, phrase_offset_beats=0.0)
    assert start2 == 74.0


def test_pick_transition_start_applies_beat_offset():
    boundaries = [74.0]
    start_clean = pick_transition_start(boundaries, tail_duration=80.0, overlap_seconds=4.0,
                                        bpm=120.0, phrase_offset_beats=0.0)
    start_off = pick_transition_start(boundaries, tail_duration=80.0, overlap_seconds=4.0,
                                      bpm=120.0, phrase_offset_beats=4.0)
    beat_len = 60.0 / 120.0
    assert abs((start_off - start_clean) - 4 * beat_len) < 1e-6


def test_pick_transition_start_stays_within_bounds():
    start = pick_transition_start([], tail_duration=10.0, overlap_seconds=8.0,
                                  bpm=120.0, phrase_offset_beats=-50.0)
    assert 0.0 <= start <= 2.0


# ---------- Beat-Phasen-Ausrichtung ----------


def _click_track(sr: int, beat_len_samples: int, n_beats: int, shift_samples: int = 0) -> np.ndarray:
    n = beat_len_samples * (n_beats + 1) + abs(shift_samples) + 1000
    y = np.zeros(n, dtype=np.float32)
    click_len = 300
    for i in range(n_beats):
        pos = i * beat_len_samples + shift_samples
        if 0 <= pos < n - click_len:
            t = np.arange(click_len) / sr
            y[pos:pos + click_len] += (np.sin(2 * np.pi * 200 * t) * np.exp(-t * 60)).astype(np.float32)
    return y


def test_estimate_phase_offset_recovers_known_shift():
    sr = 22050
    beat_len = sr  # 1 Beat = 1s, einfache Zahlen
    shift = int(0.15 * sr)  # B kommt 150ms "zu spaet"

    a = _click_track(sr, beat_len, n_beats=6)
    b = _click_track(sr, beat_len, n_beats=6, shift_samples=shift)

    lag = estimate_phase_offset_samples(a, b, sr, beat_len)

    # Aufloesung ist auf Onset-Frames (hop=512) begrenzt - Toleranz entsprechend.
    assert abs(abs(lag) - shift) < 1024, f"erwartete Verschiebung ~{shift}, gefunden {lag}"


def test_estimate_phase_offset_near_zero_when_already_aligned():
    sr = 22050
    beat_len = sr
    a = _click_track(sr, beat_len, n_beats=6)
    b = _click_track(sr, beat_len, n_beats=6, shift_samples=0)

    lag = estimate_phase_offset_samples(a, b, sr, beat_len)

    assert abs(lag) < 1024


def test_estimate_phase_offset_too_short_returns_zero():
    sr = 22050
    tiny = np.zeros(100, dtype=np.float32)
    assert estimate_phase_offset_samples(tiny, tiny, sr, sr) == 0
