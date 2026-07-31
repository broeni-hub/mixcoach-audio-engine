"""Tests fuer die zweite, blinde Labelrunde (K1, app/api/relabel.py).

Der wichtigste Test ist test_aufgaben_enthalten_die_erste_angabe_nirgends:
faellt er, ist die Messung wertlos, weil der Mensch seine alte Antwort
sehen kann.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.jobs import feedback_store, job_manager, relabel_store
from app.main import app

client = TestClient(app)

AID = "relabel-test-set"


@pytest.fixture(autouse=True)
def _isolierte_ablage(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback_store, "GROUND_TRUTH_DIR", tmp_path / "gt")
    monkeypatch.setattr(relabel_store, "RELABEL_DIR", tmp_path / "relabel")

    ergebnis = {
        "id": AID,
        "fileName": "test-set.mp3",
        "setTransitions": [
            {"index": i, "mid_sec": 100.0 * i, "start_sec": 100.0 * i - 16,
             "end_sec": 100.0 * i + 16}
            for i in range(1, 7)
        ],
    }
    monkeypatch.setattr(job_manager, "get_result",
                        lambda aid: ergebnis if aid == AID else None)

    # Runde 1: drei timing_off mit correctedSec, ein correct, ein
    # timing_off OHNE correctedSec.
    feedback_store.save_verdict(AID, 1, 100.0, "timing_off", corrected_sec=70.0)
    feedback_store.save_verdict(AID, 2, 200.0, "timing_off", corrected_sec=185.0)
    feedback_store.save_verdict(AID, 3, 300.0, "timing_off", corrected_sec=250.0)
    feedback_store.save_verdict(AID, 4, 400.0, "correct")
    feedback_store.save_verdict(AID, 5, 500.0, "timing_off")
    return tmp_path


def test_aufgaben_enthalten_die_erste_angabe_nirgends():
    """Blindheit. correctedSec darf in der Antwort an keiner Stelle stehen -
    auch nicht in einem Feld, das die Seite zufaellig nicht rendert."""
    antwort = client.get(f"/relabel/{AID}/aufgaben")
    assert antwort.status_code == 200
    roh = antwort.text

    for wert in ("70.0", "185.0", "250.0", "correctedSec"):
        assert wert not in roh, f"{wert!r} steht in der Antwort - Blindheit gebrochen"


def test_nur_timing_off_mit_correctedsec_wird_gefragt():
    """correct-Verdicts duerfen NICHT vorkommen: dort ist midSec der vom
    Menschen angenommene Wert, der gezeigte Engine-Marker waere also seine
    Antwort. timing_off ohne correctedSec hat keinen Vergleichswert."""
    d = client.get(f"/relabel/{AID}/aufgaben").json()
    assert sorted(a["index"] for a in d["aufgaben"]) == [1, 2, 3]
    assert d["gesamt"] == 3


def test_engine_marker_wird_mitgeschickt():
    """Der Engine-Vorschlag ist derselbe Reiz wie in Runde 1 und gehoert
    dazu - ohne ihn waere es eine andere Aufgabe."""
    d = client.get(f"/relabel/{AID}/aufgaben").json()
    assert {a["index"]: a["engineSec"] for a in d["aufgaben"]} == {
        1: 100.0, 2: 200.0, 3: 300.0}


def test_reihenfolge_ist_gewuerfelt_aber_ueber_sitzungen_stabil():
    erste = [a["index"] for a in client.get(f"/relabel/{AID}/aufgaben").json()["aufgaben"]]
    zweite = [a["index"] for a in client.get(f"/relabel/{AID}/aufgaben").json()["aufgaben"]]
    assert erste == zweite, "Reihenfolge darf sich zwischen Aufrufen nicht aendern"

    # Ueber viele Seeds kommt nicht immer dieselbe Reihenfolge heraus.
    varianten = {tuple(relabel_store.reihenfolge([1, 2, 3, 4, 5], s)) for s in range(40)}
    assert len(varianten) > 1


def test_antwort_landet_in_relabel_und_nicht_in_ground_truth(_isolierte_ablage):
    antwort = client.post(f"/relabel/{AID}/antwort",
                          json={"index": 2, "sec": 190.5, "was": "b_rein"})
    assert antwort.status_code == 200

    ziel = relabel_store.RELABEL_DIR / f"{AID}.json"
    assert ziel.exists()
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["antworten"]["2"]["sec"] == 190.5
    assert daten["antworten"]["2"]["was"] == "b_rein"
    assert daten["antworten"]["2"]["at"] > 0

    # Die Ground Truth der ersten Runde bleibt unveraendert.
    gt = feedback_store.load_feedback(AID)
    assert gt["verdicts"]["2"]["correctedSec"] == 185.0
    assert "was" not in gt["verdicts"]["2"]


def test_unbekannte_option_wird_abgelehnt():
    antwort = client.post(f"/relabel/{AID}/antwort",
                          json={"index": 1, "sec": 10.0, "was": "vielleicht"})
    assert antwort.status_code == 422


def test_seite_zeigt_keine_zeitangabe_aus_runde_eins():
    seite = client.get(f"/relabel/{AID}").text
    assert seite.startswith("<!doctype html>")
    for wert in ("70.0", "185.0", "250.0", "correctedSec"):
        assert wert not in seite


def test_unbekanntes_set_gibt_404():
    assert client.get("/relabel/gibt-es-nicht/aufgaben").status_code == 404
    assert client.get("/relabel/gibt-es-nicht").status_code == 404
