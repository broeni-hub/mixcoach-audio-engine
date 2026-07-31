"""Tests fuer das Frontend-Mapping (honest-v2, Scoring v2).

Wichtigster Grundsatz: Der Mapper darf KEINE erfundenen Werte liefern.
Was nicht gemessen wurde, muss null sein - niemals eine plausible Zahl.
"""

from app.api.analysis_mapper import map_set_analysis_to_frontend_result


def _fake_analysis():
    """Minimales, aber vollstaendiges Analyse-Ergebnis wie aus der v2-Pipeline."""
    return {
        "filename": "test.mp3",
        "duration": 600.0,
        "tempo": {"tempo": 126.0, "confidence": 0.9, "stability": 0.9},
        "energy": {
            "points": [
                {"time": float(t), "rms": 0.5, "peak": 0.6} for t in range(100)
            ],
            "average_rms": 0.5,
            "max_peak": 0.6,
        },
        "quality": {
            "overall": 72.5,
            "phrase_timing": 80.0,
            "beatmatching": 65.0,
            "harmonic": 90.0,
            "energy_shape": 70.0,
            "energy_flow": 80.0,
            "dramaturgy": 75.0,
            "rating": "okay",
            "scoring_version": "v2-transition-quality",
        },
        "coach_summary": {
            "positives": ["Stabiler Flow."],
            "improvements": ["Mehr Energiebewegung."],
        },
        "transition_zones": [
            {"time": 120.0, "confidence": 0.8, "type": "blend_transition"}
        ],
        "transitions_detailed": [
            {
                "index": 1,
                "start_sec": 104.0,
                "mid_sec": 120.0,
                "end_sec": 136.0,
                "type": "blend_transition",
                "detection_confidence": 0.8,
                "bpm_before": 128.0,
                "bpm_after": 126.0,
                "bpm_drift": 2.0,
                "key_before": "C Major",
                "key_after": "G Major",
                "camelot_before": "8B",
                "camelot_after": "9B",
                "phrase_beats_off": 1.5,
                "scores": {"phrase": 90, "tempo": 95, "harmonic": 95, "energy": 80},
                "energy_dip_pct": 42,
                "quality_score": 90,
                "composite_quality_score": 78,
                "composite_breakdown": {"harmonic_clash": 80, "vocal_overlap": 100,
                                        "exit_quality": 70, "beat_alignment": 85,
                                        "phrase_timing": 90},
                "harmonic_clash_score": 80,
                "vocal_overlap_score": 100,
                "exit_quality_score": 70,
                "beat_alignment_score": 85,
                "label": "smooth",
                "feedback": "Uebergang bei 02:00 sitzt.",
            }
        ],
        "dominant_key": {"key": "C Major", "camelot": "8B"},
        "beat_grid": {"tempo_global": 126.0, "beat_count": 1200},
        "segment_tempos": [],
        "segment_keys": [],
        "timeline": [],
        "rule_findings": [],
    }


def test_unmeasured_scores_are_null_not_fake():
    """EQ und Creativity werden weiterhin nicht gemessen -> null."""
    result = map_set_analysis_to_frontend_result("test.mp3", _fake_analysis())

    assert result["scores"]["eq"] is None
    assert result["scores"]["creativity"] is None
    assert result["frequency"] is None
    assert "eq" in result["notMeasured"]
    assert "creativity" in result["notMeasured"]


def test_v2_measured_scores_come_from_analysis():
    """Musicality, Flow und Overall sind echte Messwerte."""
    result = map_set_analysis_to_frontend_result("test.mp3", _fake_analysis())

    assert result["bpm"] == 126
    assert result["key"] == "C Major"
    assert result["camelot"] == "8B"
    assert result["scores"]["musicality"] == 90
    assert result["scores"]["flow"] == 80
    assert result["scores"]["overall"] == 72


def test_beatmatching_und_timing_werden_nicht_mehr_als_note_ausgegeben():
    """Regression zur Ehrlichkeitslinie (31.07.2026).

    Beide Noten waren befuellt, trugen aber nicht: beatmatching ist das
    Mittel des Tempo-Scores, und bpm_drift ist in 89 % der Uebergaenge
    exakt 0 (nur 14 verschiedene Tempowerte ueber 19 Aufnahmen) - die Note
    lag bei 12 von 19 Aufnahmen auf exakt 100. timing ist das Mittel des
    Phrasen-Scores, dessen Raster am erkannten Segmentanfang haengt, und
    der streut um sigma = 52,87 s = rund 3,4 Phrasen.

    Die Analyse liefert die Werte weiter (hier 65 bzw. 80, siehe
    _fake_analysis) - der Mapper darf sie nur nicht mehr als Note
    durchreichen. Genau das prueft dieser Test.
    """
    analyse = _fake_analysis()
    assert analyse["quality"]["beatmatching"] == 65.0
    assert analyse["quality"]["phrase_timing"] == 80.0

    result = map_set_analysis_to_frontend_result("test.mp3", analyse)

    assert result["scores"]["beatmatching"] is None
    assert result["scores"]["timing"] is None
    assert "beatmatching" in result["notMeasured"]
    assert "timing" in result["notMeasured"]


def test_set_transitions_use_frontend_contract():
    """snake_case-Felder, die report-view.ts wirklich liest."""
    result = map_set_analysis_to_frontend_result("test.mp3", _fake_analysis())

    assert len(result["setTransitions"]) == 1
    t = result["setTransitions"][0]

    for field in (
        "index", "start_sec", "mid_sec", "end_sec",
        "bpm_before", "bpm_after", "bpm_drift",
        "phrase_alignment_score", "quality_score", "label", "feedback",
        "composite_quality_score", "composite_breakdown",
        "harmonic_clash_score", "vocal_overlap_score",
        "exit_quality_score", "beat_alignment_score",
    ):
        assert field in t, f"Feld {field} fehlt in setTransitions"

    assert t["mid_sec"] == 120.0
    assert t["bpm_before"] == 128.0
    assert t["phrase_alignment_score"] == 90
    assert t["composite_quality_score"] == 78
    assert t["composite_breakdown"]["harmonic_clash"] == 80
    assert t["label"] == "smooth"
    assert t["bass_overlap_score"] is None  # nicht gemessen -> null


def test_missing_tempo_gives_null_and_warning():
    analysis = _fake_analysis()
    analysis["tempo"] = {}

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert result["bpm"] is None
    assert any("Tempo" in w for w in result["analysisWarnings"])


def test_low_tempo_confidence_produces_warning():
    analysis = _fake_analysis()
    analysis["tempo"]["confidence"] = 0.2

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert any("unsicher" in w for w in result["analysisWarnings"])


def test_no_transitions_produces_warning():
    analysis = _fake_analysis()
    analysis["transition_zones"] = []
    analysis["transitions_detailed"] = []

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert any("Uebergangszonen" in w for w in result["analysisWarnings"])
    assert result["setTransitions"] == []


def test_unknown_key_stays_null():
    analysis = _fake_analysis()
    analysis["dominant_key"] = {"key": None, "camelot": None}

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert result["key"] is None


def test_sparse_beat_grid_produces_warning():
    """Zu wenige erkannte Beats -> Phrase-Werte mit Warnung versehen."""
    analysis = _fake_analysis()
    analysis["beat_grid"] = {"tempo_global": 126.0, "beat_count": 100}  # 10/min bei 10min

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert any("Beat-Erkennung" in w for w in result["analysisWarnings"])


def test_empty_energy_gives_empty_curve_not_fake_line():
    analysis = _fake_analysis()
    analysis["energy"] = {"points": []}

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert result["energyCurve"] == []


def test_energy_curve_is_downsampled_to_240_points():
    analysis = _fake_analysis()
    analysis["energy"]["points"] = [
        {"time": float(t), "rms": 0.5, "peak": 0.6} for t in range(1000)
    ]

    result = map_set_analysis_to_frontend_result("test.mp3", analysis)

    assert len(result["energyCurve"]) <= 240
    for point in result["energyCurve"]:
        assert 0 <= point["value"] <= 100


def test_result_has_stable_top_level_shape():
    result = map_set_analysis_to_frontend_result("test.mp3", _fake_analysis())

    for field in (
        "id", "fileName", "createdAt", "bpm", "key", "energyCurve",
        "scores", "notMeasured", "analysisWarnings", "timeline",
        "strengths", "weaknesses", "feedback", "setTransitions",
        "totalDurationSec", "findings",
    ):
        assert field in result, f"Feld {field} fehlt im Frontend-Result"
