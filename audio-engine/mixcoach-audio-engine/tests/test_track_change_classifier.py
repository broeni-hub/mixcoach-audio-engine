"""Tests fuer den Trackwechsel-Klassifikator (kalibriert an REC002)."""

import numpy as np

from app.audio.track_change_classifier import (
    MIN_TRACK_GAP_SECONDS,
    classify_transition_zones,
    compute_chroma_matrix,
)

SR, HOP = 22050, 512
FPS = SR / HOP


def _synthetic_chroma(total_seconds: float, change_at: float) -> np.ndarray:
    """Chroma-Matrix: vor change_at Energie auf C, danach auf G#."""
    frames = int(total_seconds * FPS)
    change_frame = int(change_at * FPS)

    chroma = np.full((12, frames), 0.05)
    chroma[0, :change_frame] = 1.0   # C dominiert vorher
    chroma[8, change_frame:] = 1.0   # G# dominiert nachher
    return chroma


def test_zone_at_harmonic_change_wins():
    """Die Zone am echten Harmonie-Wechsel muss als Trackwechsel gewaehlt werden."""
    chroma = _synthetic_chroma(600.0, change_at=300.0)
    zones = [
        {"time": 300.0, "score": 50.0},   # am Wechsel
        {"time": 120.0, "score": 90.0},   # hoher Detektor-Score, aber kein Wechsel
    ]

    result = classify_transition_zones(zones, chroma, SR, HOP)
    by_time = {z["time"]: z for z in result}

    assert by_time[300.0]["chroma_change"] > by_time[120.0]["chroma_change"]
    assert by_time[300.0]["is_likely_track_change"] is True


def test_min_gap_blocks_nearby_zones():
    """Zwei Zonen 60s auseinander: nur die staerkere wird Trackwechsel."""
    chroma = _synthetic_chroma(600.0, change_at=300.0)
    zones = [
        {"time": 300.0, "score": 50.0},
        {"time": 360.0, "score": 40.0},  # 60s < MIN_TRACK_GAP_SECONDS
    ]
    assert 60.0 < MIN_TRACK_GAP_SECONDS

    result = classify_transition_zones(zones, chroma, SR, HOP)
    selected = [z for z in result if z["is_likely_track_change"]]

    assert len(selected) == 1
    assert selected[0]["time"] == 300.0


def test_all_zones_keep_their_data():
    """Klassifikation verwirft nichts - Events bleiben mit allen Feldern erhalten."""
    chroma = _synthetic_chroma(600.0, change_at=300.0)
    zones = [{"time": 300.0, "score": 50.0, "type": "blend_transition"}]

    result = classify_transition_zones(zones, chroma, SR, HOP)

    assert len(result) == 1
    assert result[0]["type"] == "blend_transition"
    assert "chroma_change" in result[0]
    assert "track_change_score" in result[0]


def test_compute_chroma_matrix_shape():
    rng = np.random.default_rng(1)
    wave = rng.normal(0, 0.1, SR * 10).astype(np.float32)

    chroma = compute_chroma_matrix(wave, SR, HOP)

    assert chroma.shape[0] == 12
    assert chroma.shape[1] > 100


def test_empty_zones_no_crash():
    chroma = _synthetic_chroma(60.0, change_at=30.0)
    assert classify_transition_zones([], chroma, SR, HOP) == []


def test_edge_zones_are_never_track_changes():
    """Beide annotierten Sets hatten einen Fehlalarm kurz nach Set-Start.
    Zonen im Intro/Outro duerfen keine Trackwechsel sein."""
    chroma = _synthetic_chroma(600.0, change_at=30.0)
    zones = [
        {"time": 30.0, "score": 99.0},    # 30s nach Start -> Intro, kein Wechsel
        {"time": 570.0, "score": 99.0},   # 30s vor Ende -> Outro, kein Wechsel
        {"time": 300.0, "score": 40.0},   # mittendrin -> erlaubt
    ]

    result = classify_transition_zones(zones, chroma, SR, HOP, duration=600.0)
    selected = [z["time"] for z in result if z["is_likely_track_change"]]

    assert selected == [300.0]


def test_novelty_peak_at_harmonic_change():
    """Die Novelty-Kurve muss am harmonischen Wechsel einen Peak melden."""
    from app.audio.track_change_classifier import harmonic_novelty_peaks

    chroma = _synthetic_chroma(600.0, change_at=300.0)
    peaks = harmonic_novelty_peaks(chroma, SR, 600.0, HOP)

    assert peaks, "kein Peak gefunden"
    assert any(abs(p["time"] - 300.0) <= 15 for p in peaks), peaks


def test_fusion_finds_novelty_only_boundary():
    """Harmonie-Wechsel OHNE Energie-Zone muss trotzdem gefunden werden
    (das war die Schwaeche des reinen Zonen-Ansatzes)."""
    from app.audio.track_change_classifier import detect_track_changes

    chroma = _synthetic_chroma(600.0, change_at=300.0)
    boundaries, _ = detect_track_changes([], chroma, SR, 600.0, HOP)

    assert any(abs(b["time"] - 300.0) <= 15 for b in boundaries), boundaries
    b = [b for b in boundaries if abs(b["time"] - 300.0) <= 15][0]
    assert b["detected_by"] == "novelty"
    # Keine Energie-Zone in der Naehe -> ehrliche None-Werte, nichts erfunden.
    assert b["energy_before"] is None


def test_fusion_keeps_energy_only_boundary():
    """Eine starke Energie-Zone ohne Harmonie-Wechsel bleibt erhalten
    (z.B. Wechsel zwischen zwei Tracks in derselben Tonart)."""
    from app.audio.track_change_classifier import detect_track_changes

    # Chroma ohne jeden Wechsel:
    chroma = _synthetic_chroma(600.0, change_at=9999.0)
    zones = [{
        "time": 300.0, "score": 80.0, "type": "drop_transition",
        "confidence": 0.8, "energy_before": 0.8, "energy_current": 0.3,
        "energy_after": 0.8,
    }]

    boundaries, _ = detect_track_changes(zones, chroma, SR, 600.0, HOP)

    assert any(abs(b["time"] - 300.0) <= 5 for b in boundaries), boundaries


def test_fusion_merges_duplicates():
    """Novelty-Peak und Zone am selben Uebergang -> EIN Boundary, nicht zwei."""
    from app.audio.track_change_classifier import detect_track_changes

    chroma = _synthetic_chroma(600.0, change_at=300.0)
    zones = [{
        "time": 305.0, "score": 80.0, "type": "blend_transition",
        "confidence": 0.8, "energy_before": 0.8, "energy_current": 0.4,
        "energy_after": 0.8,
    }]

    boundaries, _ = detect_track_changes(zones, chroma, SR, 600.0, HOP)
    near = [b for b in boundaries if 250 <= b["time"] <= 350]

    assert len(near) == 1, boundaries
    assert near[0]["detected_by"] == "both"
    assert near[0]["energy_before"] == 0.8  # Energie-Infos der Zone uebernommen
