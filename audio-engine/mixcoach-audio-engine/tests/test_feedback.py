"""Tests fuer den Ground-Truth-Feedback-Kreislauf."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.jobs import feedback_store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_ground_truth(tmp_path, monkeypatch):
    """Tests duerfen das echte ground_truth/ nicht mit UUIDs fluten."""
    monkeypatch.setattr(feedback_store, "GROUND_TRUTH_DIR", tmp_path / "gt")


def _new_id() -> str:
    return str(uuid.uuid4())


def test_feedback_starts_empty():
    aid = _new_id()
    r = client.get(f"/analysis/{aid}/feedback")
    assert r.status_code == 200
    data = r.json()
    assert data["verdicts"] == {}
    assert data["missed"] == []


def test_verdict_roundtrip_and_override():
    aid = _new_id()

    r = client.post(f"/analysis/{aid}/feedback/verdict",
                    json={"index": 1, "midSec": 294.0, "verdict": "correct"})
    assert r.status_code == 200
    assert r.json()["verdicts"]["1"]["verdict"] == "correct"

    # Meinung geaendert -> Ueberschreiben statt Duplikat.
    r = client.post(f"/analysis/{aid}/feedback/verdict",
                    json={"index": 1, "midSec": 294.0, "verdict": "not_a_transition"})
    assert r.json()["verdicts"]["1"]["verdict"] == "not_a_transition"
    assert len(r.json()["verdicts"]) == 1

    # Persistiert (GET liefert denselben Stand).
    assert client.get(f"/analysis/{aid}/feedback").json()["verdicts"]["1"]["verdict"] == "not_a_transition"


def test_missed_transitions_dedupe():
    aid = _new_id()

    client.post(f"/analysis/{aid}/feedback/missed", json={"sec": 480.0})
    client.post(f"/analysis/{aid}/feedback/missed", json={"sec": 485.0})   # <15s -> Duplikat
    r = client.post(f"/analysis/{aid}/feedback/missed", json={"sec": 900.0})

    assert r.json()["missed"] == [480.0, 900.0]


def test_invalid_verdict_rejected():
    aid = _new_id()
    r = client.post(f"/analysis/{aid}/feedback/verdict",
                    json={"index": 1, "midSec": 100.0, "verdict": "vielleicht"})
    assert r.status_code == 422


def test_unsafe_id_rejected():
    assert client.get("/analysis/nicht%20sicher!/feedback").status_code == 404


def test_timing_off_verdict_stores_corrected_time():
    """"Stimmt, startet aber woanders" - bestaetigt den Uebergang UND
    liefert den praezisen Zeitpunkt fuers Training."""
    aid = _new_id()

    r = client.post(f"/analysis/{aid}/feedback/verdict",
                    json={"index": 2, "midSec": 300.0,
                          "verdict": "timing_off", "correctedSec": 271.5})
    assert r.status_code == 200
    v = r.json()["verdicts"]["2"]
    assert v["verdict"] == "timing_off"
    assert v["correctedSec"] == 271.5
