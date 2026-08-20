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
        "totalDurationSec": 900.0,
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


RUNDE1_WERTE = (70.0, 185.0, 250.0)


def _alle_zahlen(knoten) -> list[float]:
    """Jede Zahl in der Antwort, egal wie tief sie liegt."""
    if isinstance(knoten, bool):
        return []
    if isinstance(knoten, (int, float)):
        return [float(knoten)]
    if isinstance(knoten, dict):
        return [z for v in knoten.values() for z in _alle_zahlen(v)]
    if isinstance(knoten, list):
        return [z for v in knoten for z in _alle_zahlen(v)]
    return []


def test_aufgaben_enthalten_die_erste_angabe_nirgends():
    """Blindheit. correctedSec darf in der Antwort an keiner Stelle stehen -
    auch nicht in einem Feld, das die Seite zufaellig nicht rendert.

    Geprueft wird strukturell auf der geparsten Antwort, nicht als
    Textsuche: '70.0' steckt als Teilkette auch in einem voellig
    harmlosen startSec von 270.0, und ein Test, der daran scheitert,
    verliert seine Aussage. Der Schluesselname wird weiter im Rohtext
    gesucht - er darf ueberhaupt nicht vorkommen.
    """
    antwort = client.get(f"/relabel/{AID}/aufgaben")
    assert antwort.status_code == 200
    assert "correctedSec" not in antwort.text

    zahlen = _alle_zahlen(antwort.json())
    for wert in RUNDE1_WERTE:
        assert wert not in zahlen, (
            f"{wert} steht in der Antwort - Blindheit gebrochen")


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


# ---------------------------------------------------------------------------
# Werkzeug-Fassung 2 (19.08.2026): die Antwort darf nicht vorbelegt sein.
#
# Fassung 1 setzte den Abspielkopf auf den Engine-Marker und schickte die
# Abspielposition ab. Ergebnis auf den 16 echten Antworten: Runde 2 lag im
# Median 4,7 s neben dem Marker (Runde 1: -50,1 s), 15 von 16 naeher als
# Runde 1. Diese Tests halten fest, dass das nicht zurueckkommt.
# ---------------------------------------------------------------------------

def test_startpunkt_ist_nicht_der_engine_marker():
    """Der Kern des Fehlers von Fassung 1. Faellt dieser Test, misst die
    zweite Runde wieder das Werkzeug statt den Menschen."""
    d = client.get(f"/relabel/{AID}/aufgaben").json()
    versaetze = [a["startSec"] - a["engineSec"] for a in d["aufgaben"]]
    assert all(relabel_store.VERSATZ_MIN_S <= abs(v) <= relabel_store.VERSATZ_MAX_S
               for v in versaetze), f"Startpunkt zu nah am Marker: {versaetze}"

    # Und ueber viele Uebergaenge hinweg faellt nie einer in die Sperrzone.
    # Eine Gleichverteilung ohne Sperrzone tut genau das - am 19.08.2026
    # gleich beim ersten Lauf mit 16 echten Uebergaengen.
    viele = [relabel_store.startversatz(4711, i) for i in range(500)]
    assert all(abs(v) >= relabel_store.VERSATZ_MIN_S for v in viele)
    assert any(v > 0 for v in viele) and any(v < 0 for v in viele)


def test_startpunkt_bleibt_ueber_aufrufe_gleich():
    """Aus dem Sitzungs-Seed abgeleitet, nicht je Aufruf gewuerfelt - sonst
    saehe ein Neuladen des Browsers eine andere Aufgabe."""
    erst = {a["index"]: a["startSec"]
            for a in client.get(f"/relabel/{AID}/aufgaben").json()["aufgaben"]}
    zweit = {a["index"]: a["startSec"]
             for a in client.get(f"/relabel/{AID}/aufgaben").json()["aufgaben"]}
    assert erst == zweit


def test_startpunkt_bleibt_in_der_aufnahme():
    """Marker minus Versatz kann vor 0 liegen - dann wird geklemmt."""
    d = client.get(f"/relabel/{AID}/aufgaben").json()
    assert all(a["startSec"] >= 0 for a in d["aufgaben"])


def test_antwort_haelt_startpunkt_und_markersprung_fest():
    """Ohne diese beiden Felder laesst sich Ankern hinterher nicht pruefen."""
    client.post(f"/relabel/{AID}/antwort",
                json={"index": 1, "sec": 75.0, "was": "b_rein",
                      "startSec": 143.0, "zumMarker": True})
    antwort = relabel_store.laden(AID)["antworten"]["1"]
    assert antwort["startSec"] == 143.0
    assert antwort["zumMarker"] is True
    assert antwort["werkzeug"] == relabel_store.WERKZEUG


def test_antwort_aus_alter_fassung_gilt_nicht_als_erledigt():
    """Wer den Durchgang wiederholt, bekommt die mit Fassung 1 erhobenen
    Uebergaenge erneut vorgelegt - sie sind eine widerlegte Messung."""
    relabel_store.speichern_antwort(AID, 2, 190.0, "b_rein")
    daten = relabel_store.laden(AID)
    daten["antworten"]["2"]["werkzeug"] = 1
    relabel_store._schreiben(daten)

    assert relabel_store.erledigt_mit_werkzeug(AID) == []
    assert client.get(f"/relabel/{AID}/aufgaben").json()["erledigt"] == []


def test_ueberschriebene_antwort_geht_nicht_verloren():
    """Eine Messung wird abgeloest, nicht geloescht."""
    relabel_store.speichern_antwort(AID, 3, 250.0, "a_raus")
    relabel_store.speichern_antwort(AID, 3, 261.5, "b_rein")
    daten = relabel_store.laden(AID)
    assert daten["antworten"]["3"]["sec"] == 261.5
    assert [e["sec"] for e in daten["ersetzt"]] == [250.0]
    assert daten["ersetzt"][0]["index"] == 3


def test_seite_belegt_die_antwort_nicht_mit_dem_marker_vor():
    """Textprobe auf der Seite - grob, aber genau dieser Zweizeiler war der
    Fehler: currentTime = engineSec beim Laden, und sec = currentTime beim
    Absenden."""
    seite = client.get(f"/relabel/{AID}").text
    # Fassung 1 hatte woertlich: loadedmetadata -> zumMarker.
    assert 'addEventListener("loadedmetadata", zumMarker' not in seite
    assert "audio.currentTime = a.startSec" in seite
    # Abgeschickt wird der ausdrueckliche Griff, nicht die Abspielposition.
    assert "sec:gewaehlt" in seite
    assert "gewaehlt = audio.currentTime" in seite
