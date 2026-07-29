"""Tests fuer das Coach-Profil (Aggregation ueber alle Sets)."""

import json

import pytest

import app.coach.profile as profile


def _result(id_, created, overall, transitions):
    return {
        "id": id_,
        "fileName": f"{id_}.wav",
        "createdAt": created,
        "scores": {"timing": overall, "beatmatching": overall,
                   "musicality": overall, "flow": overall, "overall": overall},
        "setTransitions": transitions,
    }


def _t(index, quality, beats_off=2.0, bpm=(126, 128), camelot=("8A", "9A")):
    return {
        "index": index, "mid_sec": 100.0 * index, "start_sec": 100.0 * index - 10,
        "quality_score": quality, "phrase_beats_off": beats_off,
        "bpm_before": bpm[0], "bpm_after": bpm[1], "bpm_drift": abs(bpm[1] - bpm[0]),
        "camelot_before": camelot[0], "camelot_after": camelot[1],
        "feedback": "Test.",
    }


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "RESULTS_DIR", tmp_path)
    from app.jobs import feedback_store
    monkeypatch.setattr(feedback_store, "GROUND_TRUTH_DIR", tmp_path / "gt")
    return tmp_path


def test_leeres_profil_ist_ehrlich(results_dir):
    p = profile.build_profile()
    assert p["setsAnalyzed"] == 0
    assert p["enoughData"] is False
    assert p["patterns"] == [] and p["exercises"] == []


def test_trends_und_uebungen_aus_echten_reports(results_dir):
    for i, score in enumerate([50, 55, 60, 70, 75, 80]):
        transitions = [_t(1, score), _t(2, score + 5)]
        (results_dir / f"set{i}.json").write_text(
            json.dumps(_result(f"id{i}", f"2026-07-0{i+1}T10:00:00Z", score, transitions)))

    p = profile.build_profile()
    assert p["setsAnalyzed"] == 6
    assert p["trends"]["overall"]["delta"] > 0  # klar steigender Trend
    assert p["best"]["quality"] == 85
    assert 1 <= len(p["exercises"]) <= 3
    assert p["exercises"][0]["analysisId"]  # anspringbar


def test_fehlalarm_verdicts_werden_ausgeschlossen(results_dir):
    (results_dir / "s.json").write_text(
        json.dumps(_result("abcd1234", "2026-07-01T10:00:00Z", 70,
                           [_t(1, 20), _t(2, 90)])))
    gt = results_dir / "gt"
    gt.mkdir()
    (gt / "abcd1234.json").write_text(json.dumps(
        {"analysisId": "abcd1234",
         "verdicts": {"1": {"midSec": 100.0, "verdict": "not_a_transition"}}}))

    p = profile.build_profile()
    assert p["transitionsMeasured"] == 1
    assert p["worst"]["quality"] == 90  # der Fehlalarm (20) zaehlt nicht


def test_muster_nur_mit_genug_belegen(results_dir):
    # 3 harmonisch schiefe Uebergaenge: unter MIN_PATTERN_SAMPLES -> kein Muster.
    transitions = [_t(i, 70, camelot=("8A", "2B")) for i in range(1, 4)]
    (results_dir / "s.json").write_text(
        json.dumps(_result("x", "2026-07-01T10:00:00Z", 70, transitions)))
    assert profile.build_profile()["patterns"] == []


def test_phrase_tempo_muster_wird_erkannt(results_dir):
    transitions = (
        [_t(i, 70, beats_off=12.0, bpm=(120, 128)) for i in range(1, 6)]  # hoch: schlecht
        + [_t(i, 70, beats_off=1.0, bpm=(128, 120)) for i in range(6, 11)]  # runter: gut
    )
    (results_dir / "s.json").write_text(
        json.dumps(_result("x", "2026-07-01T10:00:00Z", 70, transitions)))
    patterns = profile.build_profile()["patterns"]
    assert any(p["id"] == "phrase_tempo_direction" for p in patterns)


def test_endpoint_liefert_profil():
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app

    res = TestClient(fastapi_app).get("/coach/profile")
    assert res.status_code == 200
    body = res.json()
    for key in ("setsAnalyzed", "trends", "patterns", "exercises", "enoughData"):
        assert key in body
