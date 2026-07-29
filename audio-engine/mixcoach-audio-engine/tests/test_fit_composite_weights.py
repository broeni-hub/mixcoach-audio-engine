"""Tests fuer das Gewichte-Fit-Script (Matching-Logik + Kernrechnung, kein
echter Fit-Lauf - der ist ein Integrationstest mit echten Daten)."""

import json

from app.calibration.fit_composite_weights import (
    DIMENSIONS,
    _closest_transition,
    _composite,
    _find_result_json,
    _spearman_for_weights,
    load_training_examples,
)


def test_composite_skips_none_and_renormalizes():
    scores = {"harmonic_clash": 80, "vocal_overlap": None, "exit_quality": 80,
              "beat_alignment": 80, "phrase_timing": 80}
    weights = {d: 0.2 for d in DIMENSIONS}
    assert _composite(scores, weights) == 80.0


def test_composite_all_none_returns_none():
    scores = {d: None for d in DIMENSIONS}
    weights = {d: 0.2 for d in DIMENSIONS}
    assert _composite(scores, weights) is None


def test_closest_transition_picks_nearest_within_tolerance():
    transitions = [{"mid_sec": 100.0}, {"mid_sec": 140.0}]
    match = _closest_transition(transitions, 105.0)
    assert match == {"mid_sec": 100.0}


def test_closest_transition_none_outside_tolerance():
    transitions = [{"mid_sec": 100.0}]
    assert _closest_transition(transitions, 200.0) is None


def test_find_result_json_falls_back_to_archived(tmp_path):
    results_dir = tmp_path
    archived_dir = results_dir / "archived"
    archived_dir.mkdir()
    (archived_dir / "abc123.json").write_text("{}", encoding="utf-8")

    found = _find_result_json(results_dir, "abc123")
    assert found == archived_dir / "abc123.json"


def test_find_result_json_prefers_direct_over_archived(tmp_path):
    (tmp_path / "abc123.json").write_text("{}", encoding="utf-8")
    (tmp_path / "archived").mkdir()
    (tmp_path / "archived" / "abc123.json").write_text("{}", encoding="utf-8")

    found = _find_result_json(tmp_path, "abc123")
    assert found == tmp_path / "abc123.json"


def test_find_result_json_missing_returns_none(tmp_path):
    assert _find_result_json(tmp_path, "does-not-exist") is None


def test_spearman_for_weights_perfect_correlation():
    examples = [
        ({d: 100 for d in DIMENSIONS}, 5.0, 50),
        ({d: 0 for d in DIMENSIONS}, 1.0, 50),
        ({d: 50 for d in DIMENSIONS}, 3.0, 50),
        ({d: 75 for d in DIMENSIONS}, 4.0, 50),
        ({d: 25 for d in DIMENSIONS}, 2.0, 50),
    ]
    weights = {d: 0.2 for d in DIMENSIONS}
    corr = _spearman_for_weights(examples, weights)
    assert corr is not None
    assert corr > 0.99


def test_load_training_examples_matches_csv_to_json(tmp_path):
    results_dir = tmp_path / "analysis_results"
    results_dir.mkdir()
    (results_dir / "set1.json").write_text(json.dumps({
        "setTransitions": [
            {"mid_sec": 50.0, "composite_breakdown": {d: 70 for d in DIMENSIONS}, "quality_score": 40},
        ]
    }), encoding="utf-8")

    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "set_id;file_name;transition_center_time;human_rating;rater;verdict_info;"
        "engine_quality_score;phrase_beats_off;engine_label;comment;time_mmss;quelle\n"
        "set1;test.wav;51.0;4;sebro;correct;40;;neutral;;00:51;erkannt\n"
        "set1;test.wav;51.0;;sebro;correct;40;;neutral;;00:51;erkannt\n"  # kein human_rating -> uebersprungen
        "set2;missing.wav;10.0;3;sebro;correct;;;;;00:10;erkannt\n",  # kein JSON -> uebersprungen
        encoding="utf-8",
    )

    examples = load_training_examples(csv_path, results_dir)

    assert len(examples) == 1
    scores, rating, old_score = examples[0]
    assert rating == 4.0
    assert old_score == 40
    assert scores["harmonic_clash"] == 70
