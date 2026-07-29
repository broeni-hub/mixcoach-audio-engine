"""Tests fuer die Rule Engine (Feedback-Regeln)."""

from app.audio.rule_engine import evaluate_set_rules


def _base_analysis(**overrides):
    # 9 Uebergaenge in 30 Minuten = 3 pro 10 Minuten -> gesunde Dichte.
    healthy_events = [
        {"event_type": "transition", "time": float(i * 200)} for i in range(9)
    ]

    analysis = {
        "duration": 1800.0,  # 30 Minuten
        "quality": {"overall": 80.0},
        "dramaturgy": {"energy_trend": "rising"},
        "events": healthy_events,
    }
    analysis.update(overrides)
    return analysis


def test_good_set_has_no_findings():
    findings = evaluate_set_rules(_base_analysis())
    assert findings == []


def test_low_quality_triggers_finding():
    findings = evaluate_set_rules(
        _base_analysis(quality={"overall": 50.0})
    )
    assert any(f["type"] == "low_set_quality" for f in findings)


def test_falling_energy_triggers_finding():
    findings = evaluate_set_rules(
        _base_analysis(dramaturgy={"energy_trend": "falling"})
    )
    assert any(f["type"] == "falling_energy" for f in findings)


def test_too_many_transitions_triggers_finding():
    # 30 Uebergaenge in 30 Minuten = 10 pro 10 Minuten -> zu viele.
    events = [
        {"event_type": "transition", "time": float(i * 60)} for i in range(30)
    ]
    findings = evaluate_set_rules(_base_analysis(events=events))
    assert any(f["type"] == "too_many_transitions" for f in findings)


def test_uncertain_track_change_triggers_finding():
    events = [
        {"event_type": "transition", "time": float(i * 200)} for i in range(9)
    ] + [
        {"event_type": "track_change", "time": 100.0, "confidence": 0.2}
    ]
    findings = evaluate_set_rules(_base_analysis(events=events))
    assert any(f["type"] == "uncertain_track_change" for f in findings)
