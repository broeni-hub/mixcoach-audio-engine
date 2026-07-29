"""Tests fuer den ML-Trackwechsel-Klassifikator (JSON-Inferenz)."""

import numpy as np

from app.audio.ml_classifier import (
    MODEL_PATH,
    extract_zone_features,
    load_model,
    predict_probability,
    select_track_changes_ml,
)


def test_model_file_exists_and_loads():
    assert MODEL_PATH.exists(), "Modell-Datei fehlt im Repo (app/models/)"
    model = load_model()
    assert model is not None
    assert len(model["trees"]) == 60
    assert len(model["features"]) == 17  # inkl. beat_cv/exit_rough seit 2026-07-12
    # Recall-Untergrenze bewusst von 0.90 auf 0.80 gesenkt (siehe MIN_RECALL
    # in retrain_model.py) - harte Negativbeispiele machten am 2026-07-12
    # einen Precision-Gewinn moeglich, der nur mit etwas weniger Recall zu
    # haben war (LOSO: R=85%, P=53% statt R=94%-96%, P=48-49%).
    assert model["loso_validation"]["recall"] >= 0.8


def test_probabilities_are_valid():
    model = load_model()
    n = len(model["features"])
    # Extremwerte duerfen nie ausserhalb [0,1] landen.
    for x in (np.zeros(n).tolist(), (np.ones(n) * 100).tolist()):
        p = predict_probability(model, x)
        assert 0.0 <= p <= 1.0


def test_feature_vector_matches_training_order():
    """17 Features, exakt in der Reihenfolge des Trainings (inkl. Foote,
    beat_cv, exit_rough - die beiden letzten append-only, siehe
    EDGE_FEATURE_INDEX-Kommentar in select_track_changes_ml)."""
    zones = [{
        "time": 300.0, "score": 80.0,
        "signals": {"blend_score": 40, "drop_score": 30, "bass_swap_score": 20},
        "energy_before": 0.8, "energy_current": 0.4, "energy_after": 0.8,
    }]
    chroma = np.full((12, 30000), 0.1)
    mfcc = np.random.default_rng(0).normal(size=(20, 30000))
    env = np.abs(np.random.default_rng(1).normal(size=30000))

    vectors = extract_zone_features(zones, chroma, mfcc, env, 600.0, 22050)

    assert len(vectors) == 1
    assert len(vectors[0]) == 17
    assert vectors[0][0] == 80.0          # score
    assert vectors[0][13] == 0.0          # edge (300s ist mittig)
    assert vectors[0][14] == 0.0          # foote (keine Beats uebergeben)
    assert vectors[0][15] == 0.0          # beat_cv (keine Beats uebergeben)
    assert vectors[0][16] == 0.0          # exit_rough (keine Energiekurve uebergeben)


def test_beat_cv_and_exit_rough_are_measurable_when_data_present():
    zones = [{
        "time": 300.0, "score": 0.0,
        "signals": {}, "energy_before": 0.0, "energy_current": 0.0, "energy_after": 0.0,
    }]
    chroma = np.full((12, 30000), 0.1)
    mfcc = np.zeros((20, 30000))
    env = np.zeros(30000)

    # Unregelmaessige Beats um t=300 -> beat_cv > 0.
    beats = [290.0, 291.5, 292.7, 294.9, 296.0, 298.5, 300.4, 302.1, 305.0, 307.9]
    # Zackige Energiekurve unmittelbar vor t=300 -> exit_rough > 0.
    energy_points = [
        {"time": 285.0, "rms": 0.8}, {"time": 288.0, "rms": 0.2},
        {"time": 291.0, "rms": 0.7}, {"time": 294.0, "rms": 0.1},
        {"time": 297.0, "rms": 0.6}, {"time": 299.0, "rms": 0.15},
    ]

    vectors = extract_zone_features(
        zones, chroma, mfcc, env, 600.0, 22050,
        beats=beats, energy_points=energy_points,
    )

    assert vectors[0][15] > 0.0   # beat_cv
    assert vectors[0][16] > 0.0   # exit_rough


def test_edge_zones_never_selected():
    zones = [{
        "time": 30.0, "score": 99.0,  # 30s nach Start -> Rand
        "signals": {"blend_score": 90, "drop_score": 90, "bass_swap_score": 90},
        "energy_before": 0.9, "energy_current": 0.2, "energy_after": 0.9,
    }]
    chroma = np.full((12, 30000), 0.1)
    mfcc = np.zeros((20, 30000))
    env = np.zeros(30000)

    selected = select_track_changes_ml(zones, chroma, mfcc, env, 600.0, 22050)

    assert selected == []


def test_grid_works_without_energy_zones():
    """v2: Auch OHNE Energie-Zonen prueft das dichte Raster das ganze Set.
    Flaches Chroma -> keine Auswahl (leere Liste), aber kein None-Fallback."""
    chroma = np.full((12, 30000), 0.1)
    result = select_track_changes_ml([], chroma, np.zeros((20, 30000)), np.zeros(30000), 600.0, 22050)

    assert result is not None       # Grid liefert Kandidaten
    assert isinstance(result, list)


def test_grid_finds_harmonic_change_without_zone():
    """Kern von v2+v3: Ein Uebergang ohne jede Energie-Signatur wird ueber
    das Raster gefunden - und mit Beats snappt die Foote-Verfeinerung den
    Zeitpunkt beat-genau auf den Wechsel.

    Chroma, MFCC UND Rhythmus-Textur wechseln (nicht nur Chroma) -
    realistischer fuer einen echten Trackwechsel (der meist mehrere
    gleichzeitige Signale traegt) und noetig, um die seit 2026-07-12
    hoehere Entscheidungsschwelle zu erreichen (min_probability 0.5 -> 0.6,
    bewusst gesenkter Recall gegen bessere Precision, siehe MIN_RECALL in
    retrain_model.py; mit jedem weiteren Retrain auf mehr Daten kann sich
    die Modell-Grenze nochmal leicht verschieben). Ein Signal, das NUR in
    einem einzelnen Feature steckt, reicht beim aktuellen Modell nicht mehr
    - das ist beabsichtigt."""
    frames = int(600 * 22050 / 512)
    change = int(300 * 22050 / 512)
    chroma = np.full((12, frames), 0.05)
    chroma[0, :change] = 1.0
    chroma[7, change:] = 1.0
    mfcc = np.zeros((20, frames))
    mfcc[3, :change] = 5.0
    mfcc[3, change:] = -5.0
    rng = np.random.default_rng(0)
    env = np.zeros(frames)
    env[:change] = np.abs(rng.normal(0, 1.0, change))
    env[change:] = np.abs(rng.normal(0, 0.1, frames - change))
    beats = [i * 0.5 for i in range(1200)]  # 120 BPM

    result = select_track_changes_ml(
        [], chroma, mfcc, env, 600.0, 22050,
        beats=beats,
    )

    assert result, "Harmonie-Wechsel ohne Energie-Zone wurde nicht gefunden"
    assert any(abs(b["time"] - 300) <= 10 for b in result), [b["time"] for b in result]
    # Die Foote-Verfeinerung liefert zusaetzlich den Blend-Start.
    hit = [b for b in result if abs(b["time"] - 300) <= 10][0]
    assert hit.get("blend_start") is not None
    assert hit["blend_start"] <= hit["time"]
