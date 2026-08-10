"""Tests fuer die Uebergangs-Bewertung (Phase 2 - Kernversprechen)."""

from app.audio.beats import tempo_for_window
from app.audio.phrase_grid import build_phrase_grid, phrase_distance_beats
from app.audio.segment_keys import camelot_compatibility_score
from app.audio.transition_quality import (
    _phrase_alignment_score,
    _tempo_match_score,
    aggregate_transition_scores,
    evaluate_transitions,
)


# ---------- Tempo ----------


def test_tempo_from_regular_beats():
    """Beats alle 0,5s = 120 BPM."""
    beats = [i * 0.5 for i in range(80)]
    assert tempo_for_window(beats, 0.0, 40.0) == 120.0


def test_tempo_needs_enough_beats():
    """Zu wenige Beats -> None statt geratener Zahl."""
    beats = [i * 0.5 for i in range(5)]
    assert tempo_for_window(beats, 0.0, 40.0) is None


def test_tempo_match_thresholds():
    assert _tempo_match_score(0.5) == 100
    assert _tempo_match_score(3.0) == 85
    assert _tempo_match_score(9.0) == 40
    assert _tempo_match_score(15.0) == 20
    assert _tempo_match_score(None) is None


# ---------- Phrasen ----------


def test_phrase_grid_every_32_beats():
    beats = [i * 0.5 for i in range(200)]  # 120 BPM, 100s
    segments = [{"index": 1, "start": 0.0, "end": 100.0}]

    grid = build_phrase_grid(beats, segments)

    times = [b["time"] for b in grid]
    # 32 Beats à 0,5s = alle 16 Sekunden eine Phrasengrenze.
    assert times[:4] == [0.0, 16.0, 32.0, 48.0]


def test_phrase_distance_in_beats_not_seconds():
    boundaries = [{"time": 100.0}]

    # 2 Sekunden daneben: bei 120 BPM sind das 4 Beats...
    assert phrase_distance_beats(boundaries, 102.0, 120.0) == 4.0
    # ...bei 60 BPM nur 2 Beats. Gleiche Sekunden, anderes Urteil.
    assert phrase_distance_beats(boundaries, 102.0, 60.0) == 2.0


def test_phrase_alignment_thresholds():
    assert _phrase_alignment_score(0.5) == 100
    assert _phrase_alignment_score(3.0) == 75
    assert _phrase_alignment_score(10.0) == 30
    assert _phrase_alignment_score(None) is None


# ---------- Harmonie ----------


def test_camelot_compatibility():
    assert camelot_compatibility_score("8B", "8B") == 100   # gleich
    assert camelot_compatibility_score("8B", "9B") == 95    # Nachbar
    assert camelot_compatibility_score("8B", "8A") == 90    # relative Moll
    assert camelot_compatibility_score("8B", "3B") == 40    # weit weg
    assert camelot_compatibility_score(None, "8B") is None  # unbekannt


# ---------- Integration ----------


def _one_transition_setup():
    zones = [{
        "time": 50.0, "type": "blend_transition", "confidence": 0.8,
        "energy_before": 0.8, "energy_current": 0.45, "energy_after": 0.8,
    }]
    segments = [
        {"index": 1, "start": 0.0, "end": 50.0},
        {"index": 2, "start": 50.0, "end": 100.0},
    ]
    tempos = [
        {"segment_index": 1, "start": 0.0, "end": 50.0, "bpm": 128.0},
        {"segment_index": 2, "start": 50.0, "end": 100.0, "bpm": 126.0},
    ]
    keys = [
        {"segment_index": 1, "start": 0.0, "end": 50.0, "key": "C Major", "camelot": "8B", "confidence": 0.8},
        {"segment_index": 2, "start": 50.0, "end": 100.0, "key": "G Major", "camelot": "9B", "confidence": 0.8},
    ]
    boundaries = [{"time": 48.0, "segment_index": 1, "phrase_number": 4}]
    return zones, segments, tempos, keys, boundaries


def test_evaluate_transitions_full():
    zones, segments, tempos, keys, boundaries = _one_transition_setup()

    result = evaluate_transitions(zones, segments, tempos, keys, boundaries, 100.0)

    assert len(result) == 1
    t = result[0]

    assert t["bpm_before"] == 128.0
    assert t["bpm_after"] == 126.0
    assert t["bpm_drift"] == 2.0
    assert t["scores"]["tempo"] == 95
    assert t["scores"]["harmonic"] == 95  # 8B -> 9B Nachbar

    # 2s neben der Phrasengrenze bei 128 BPM = ~4,3 Beats -> Score 55.
    assert 4.0 <= t["phrase_beats_off"] <= 4.5
    assert t["scores"]["phrase"] == 55

    assert t["quality_score"] is not None
    assert 0 <= t["quality_score"] <= 100
    assert t["label"] in {"smooth", "neutral", "rough"}
    assert "Uebergang bei 00:50" in t["feedback"]


def test_unmeasurable_parts_stay_none():
    """Kein Tempo, keine Keys, keine Phrasen -> None, nie geraten."""
    zones = [{"time": 50.0, "energy_before": 0.8, "energy_current": 0.4}]
    segments = [
        {"index": 1, "start": 0.0, "end": 50.0},
        {"index": 2, "start": 50.0, "end": 100.0},
    ]
    tempos = [
        {"segment_index": 1, "start": 0.0, "end": 50.0, "bpm": None},
        {"segment_index": 2, "start": 50.0, "end": 100.0, "bpm": None},
    ]
    keys = [
        {"segment_index": 1, "key": None, "camelot": None, "confidence": 0.0, "start": 0.0, "end": 50.0},
        {"segment_index": 2, "key": None, "camelot": None, "confidence": 0.0, "start": 50.0, "end": 100.0},
    ]

    result = evaluate_transitions(zones, segments, tempos, keys, [], 100.0)
    t = result[0]

    assert t["bpm_drift"] is None
    assert t["scores"]["tempo"] is None
    assert t["scores"]["harmonic"] is None
    assert t["scores"]["phrase"] is None
    # Energie ist messbar -> Score existiert trotzdem (nur aus Energie).
    assert t["scores"]["energy"] is not None
    assert t["quality_score"] is not None


def test_aggregate_skips_none():
    transitions = [
        {"scores": {"phrase": 80, "tempo": None, "harmonic": 90, "energy": 70}},
        {"scores": {"phrase": 60, "tempo": 100, "harmonic": None, "energy": 50}},
    ]
    agg = aggregate_transition_scores(transitions)

    assert agg["phrase_timing"] == 70.0
    assert agg["beatmatching"] == 100.0
    assert agg["harmonic"] == 90.0
    assert agg["energy_shape"] == 60.0


def test_phrase_measured_against_outgoing_track_only():
    """Regressionstest gegen den Zirkelschluss: Das Raster des NEUEN
    Segments (ankert am Uebergang selbst) darf nicht zur Messung dienen."""
    zones = [{"time": 50.0, "energy_before": 0.8, "energy_current": 0.4}]
    segments = [
        {"index": 1, "start": 0.0, "end": 50.0},
        {"index": 2, "start": 50.0, "end": 100.0},
    ]
    tempos = [
        {"segment_index": 1, "start": 0.0, "end": 50.0, "bpm": 120.0},
        {"segment_index": 2, "start": 50.0, "end": 100.0, "bpm": 120.0},
    ]
    keys = [
        {"segment_index": 1, "key": None, "camelot": None, "confidence": 0, "start": 0.0, "end": 50.0},
        {"segment_index": 2, "key": None, "camelot": None, "confidence": 0, "start": 50.0, "end": 100.0},
    ]
    boundaries = [
        # Raster des auslaufenden Tracks: 3s vor dem Uebergang (= 6 Beats bei 120).
        {"time": 47.0, "segment_index": 1, "phrase_number": 3},
        # Raster des NEUEN Tracks: exakt auf dem Uebergang - MUSS ignoriert werden.
        {"time": 50.0, "segment_index": 2, "phrase_number": 1},
    ]

    t = evaluate_transitions(zones, segments, tempos, keys, boundaries, 100.0)[0]

    # Mit Zirkelschluss waere das 0.0 - korrekt sind 6 Beats (3s bei 120 BPM).
    assert t["phrase_beats_off"] == 6.0


def test_phrase_grid_extends_beyond_last_full_phrase():
    """Ein Uebergang kurz VOR der naechsten Phrasengrenze muss einen
    kleinen Abstand bekommen, nicht ~30 Beats."""
    # 190 Beats a 0,5s: letzte volle Grenze bei Beat 160 (=80s).
    beats = [i * 0.5 for i in range(190)]
    segments = [{"index": 1, "start": 0.0, "end": 95.0}]

    grid = build_phrase_grid(beats, segments)
    times = [b["time"] for b in grid]

    # Extrapolierte Grenze bei 96s (Beat 192) muss existieren.
    assert any(abs(t - 96.0) < 0.6 for t in times), times

    # Uebergang bei 95s (Segmentende): korrekt ~2 Beats vor der 96s-Grenze.
    off = phrase_distance_beats(grid, 95.0, 120.0)
    assert off is not None and off <= 3.0, off


# --- Set-Gesamtnote: nur noch aus Gemessenem (Regression 31.07.2026) -------

def _transition(phrase, tempo, harmonic, energy):
    return {"scores": {"phrase": phrase, "tempo": tempo,
                       "harmonic": harmonic, "energy": energy}}


def test_overall_ignoriert_phrase_und_beatmatching():
    """phrase_timing und beatmatching sind am 31.07.2026 aus der
    Gesamtnote genommen worden.

    Grund, gemessen: bpm_drift ist in 89 % der Uebergaenge exakt 0 - der
    daraus gemittelte beatmatching-Score lag bei 12 von 19 Aufnahmen auf
    exakt 100 und hat mit 30 % Gewicht die Kopfzahl zusammengedrueckt.
    scores.overall spannte ueber 19 Aufnahmen nur 12 Punkte.

    Der Test setzt beide auf Extremwerte. Aendert sich overall dadurch,
    fliessen sie wieder ein.
    """
    from app.audio.pipeline.pipeline import score_set_quality_v2

    energie = {"points": [{"time": float(t), "rms": 0.5} for t in range(60)]}
    dram = {"energy_trend": "rising"}

    hoch = score_set_quality_v2(energie, dram,
                                [_transition(100, 100, 60, 60)])
    tief = score_set_quality_v2(energie, dram,
                                [_transition(0, 0, 60, 60)])

    assert hoch["overall"] == tief["overall"], (
        "phrase/beatmatching bewegen die Gesamtnote wieder")
    # Die Teilwerte bleiben erhalten - sie werden nur nicht mehr benotet.
    assert hoch["phrase_timing"] == 100.0
    assert hoch["beatmatching"] == 100.0


def test_overall_ignoriert_den_dramaturgie_geschmack():
    """rising 90 / stable 75 / falling 60 war eine Geschmacksentscheidung im
    Gewand eines Messwerts: ein Set, das ruhig ausklingt, wurde bestraft,
    ohne dass belegt ist, dass Aufbauen besser waere."""
    from app.audio.pipeline.pipeline import score_set_quality_v2

    energie = {"points": [{"time": float(t), "rms": 0.5} for t in range(60)]}
    t = [_transition(80, 80, 60, 60)]

    steigend = score_set_quality_v2(energie, {"energy_trend": "rising"}, t)
    fallend = score_set_quality_v2(energie, {"energy_trend": "falling"}, t)

    assert steigend["overall"] == fallend["overall"]
    # Der Wert wird weiter berechnet und ausgewiesen, nur nicht gewichtet.
    assert steigend["dramaturgy"] == 90.0
    assert fallend["dramaturgy"] == 60.0


def test_overall_folgt_den_gemessenen_teilen():
    """Gegenprobe: harmonic und energy_shape muessen die Note bewegen -
    sonst haette die Aenderung sie ganz entwertet."""
    from app.audio.pipeline.pipeline import score_set_quality_v2

    energie = {"points": [{"time": float(t), "rms": 0.5} for t in range(60)]}
    dram = {"energy_trend": "stable"}

    gut = score_set_quality_v2(energie, dram, [_transition(50, 50, 100, 100)])
    schlecht = score_set_quality_v2(energie, dram, [_transition(50, 50, 10, 10)])

    assert gut["overall"] > schlecht["overall"]
