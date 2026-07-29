"""Tests fuer den Composite-Quality-Score (5-Dimensionen-Zusammenfuehrung)."""

from app.audio.scoring.composite import annotate_composite_scores, composite_score


def test_equal_weights_average_when_all_present():
    score = composite_score(
        harmonic_clash=100, vocal_overlap=100, exit_quality=100,
        beat_alignment=100, phrase_timing=0,
        weights={"harmonic_clash": 0.25, "vocal_overlap": 0.25,
                 "exit_quality": 0.25, "beat_alignment": 0.25, "phrase_timing": 0.0},
    )
    assert score == 100


def test_missing_dimension_renormalizes_not_zero():
    """Eine fehlende Dimension darf den Score nicht wie eine 0 behandeln."""
    with_all = composite_score(80, 80, 80, 80, 80)
    with_one_missing = composite_score(80, 80, 80, 80, None)
    assert with_all == 80
    assert with_one_missing == 80  # nicht abgesenkt, nur neu normiert


def test_all_missing_returns_none():
    assert composite_score(None, None, None, None, None) is None


def test_zero_weight_dimension_is_excluded_even_if_present():
    score = composite_score(
        harmonic_clash=0, vocal_overlap=100, exit_quality=100,
        beat_alignment=100, phrase_timing=100,
        weights={"harmonic_clash": 0.0, "vocal_overlap": 0.25,
                 "exit_quality": 0.25, "beat_alignment": 0.25, "phrase_timing": 0.25},
    )
    assert score == 100


def test_annotate_composite_scores_reads_phrase_from_existing_scores_dict():
    transitions = [{
        "harmonic_clash_score": 90,
        "vocal_overlap_score": 90,
        "exit_quality_score": 90,
        "beat_alignment_score": 90,
        "scores": {"phrase": 90, "tempo": 50, "harmonic": 50, "energy": 50},
    }]

    annotate_composite_scores(transitions)

    assert transitions[0]["composite_quality_score"] == 90
    assert transitions[0]["composite_breakdown"]["phrase_timing"] == 90
    # bestehende Felder duerfen nicht angefasst werden.
    assert transitions[0]["scores"]["tempo"] == 50
