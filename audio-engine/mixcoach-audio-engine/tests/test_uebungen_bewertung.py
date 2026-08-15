"""Blindheit des Uebungs-Vergleichs (J7).

Der wichtigste Test ist test_die_herkunft_steht_nirgends_in_der_antwort:
faellt er, ist die Messung wertlos, weil Sebastian sehen kann, welcher
Text der neue ist - und dann bewertet er seine eigene Entscheidung statt
des Textes.

Dieselbe Anforderung wie bei der zweiten Labelrunde
(tests/test_relabel.py), nur eine Ebene weiter: dort durfte die eigene
Antwort von damals nicht durchscheinen, hier nicht die Herkunft.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api import uebungen_bewertung
from app.main import app

client = TestClient(app)

LAUF = "testlauf"


@pytest.fixture(autouse=True)
def _isolierter_bestand(tmp_path, monkeypatch):
    """Ein kleiner, eigener Bestand - der echte bleibt unberuehrt."""
    ergebnisse = tmp_path / "analysis_results"
    ergebnisse.mkdir()
    monkeypatch.setattr(uebungen_bewertung, "RESULTS_DIR", ergebnisse)
    monkeypatch.setattr(uebungen_bewertung, "BEWERTUNG_DIR", tmp_path / "bewertung")

    # Drei Aufnahmen mit je zwei Uebergaengen ueber der Schwelle.
    for s in range(3):
        uebergaenge = [
            {"index": i, "mid_sec": 100.0 * i, "start_sec": 100.0 * i - 16,
             "loudness_jump_db": 4.0 + i + s}
            for i in (1, 2)
        ]
        (ergebnisse / f"set{s}.json").write_text(json.dumps({
            "id": f"id-{s}", "fileName": f"Set{s}.wav", "setTransitions": uebergaenge,
        }), encoding="utf-8")
    return tmp_path


def _aufgaben():
    antwort = client.get(f"/uebungen-bewertung/{LAUF}/aufgaben")
    assert antwort.status_code == 200
    return antwort.json()["aufgaben"]


# --- Blindheit -------------------------------------------------------------


# Mehr darf eine Aufgabe nicht enthalten. Eine Positivliste statt einer
# Suche nach verdaechtigen Woertern: "neu" und "alt" kommen im Uebungstext
# selbst vor ("kam der neue Track 4,2 dB lauter rein"), eine Substring-Suche
# schluege dort immer an und wuerde nichts belegen. Was zaehlt, ist welche
# FELDER den Browser erreichen.
ERLAUBTE_FELDER = {"index", "fileName", "atSec", "a", "b"}


def test_die_herkunft_steht_nirgends_in_der_antwort():
    """Kein Feld und kein Marker verraet, welcher Text der neue ist."""
    for a in _aufgaben():
        assert set(a) == ERLAUBTE_FELDER, f"unerwartete Felder: {set(a) - ERLAUBTE_FELDER}"

    roh = client.get(f"/uebungen-bewertung/{LAUF}/aufgaben").text
    for marker in ("_vorlage_ist", '"herkunft"', '"vorlage"', '"belegt"'):
        assert marker not in roh, f"{marker!r} steht in der Antwort"


def test_die_seite_verraet_die_herkunft_ebenfalls_nicht():
    roh = client.get(f"/uebungen-bewertung/{LAUF}").text
    assert roh.count("_vorlage_ist") == 0
    # Die Knoepfe heissen nach ihrer Position, nicht nach ihrer Herkunft.
    for verraeter in ("vorlage", "belegt", "template"):
        assert verraeter not in roh.lower()


def test_beide_texte_kommen_vor_und_sind_verschieden():
    for a in _aufgaben():
        assert a["a"] and a["b"]
        assert a["a"] != a["b"]
        # Genau einer der beiden ist die alte Vorlage.
        ist_vorlage = [t == uebungen_bewertung.VORLAGE for t in (a["a"], a["b"])]
        assert sum(ist_vorlage) == 1


def test_die_seite_ist_gewuerfelt_und_nicht_immer_gleich_herum():
    """Staende die Vorlage immer links, waere die Reihenfolge der Verraeter."""
    daten = uebungen_bewertung._lauf_laden(LAUF)
    seiten = {a["_vorlage_ist"] for a in daten["aufgaben"]}
    assert seiten == {"a", "b"}, "die Vorlage steht immer auf derselben Seite"


# --- Zuordnung und Speicherung --------------------------------------------


def test_gleiche_runde_gleiche_zuordnung():
    """Neuladen darf nicht neu wuerfeln - sonst zaehlt eine halb
    beantwortete Runde falsch."""
    erst = [a["_vorlage_ist"] for a in uebungen_bewertung._lauf_laden(LAUF)["aufgaben"]]
    client.get(f"/uebungen-bewertung/{LAUF}")
    dann = [a["_vorlage_ist"] for a in uebungen_bewertung._lauf_laden(LAUF)["aufgaben"]]
    assert erst == dann


def test_antwort_wird_zur_herkunft_aufgeloest():
    daten = uebungen_bewertung._lauf_laden(LAUF)
    aufgabe = daten["aufgaben"][0]
    vorlagen_seite = aufgabe["_vorlage_ist"]

    antwort = client.post(f"/uebungen-bewertung/{LAUF}/antwort",
                          json={"index": 0, "gewaehlt": vorlagen_seite})
    assert antwort.status_code == 200

    gespeichert = uebungen_bewertung._lauf_laden(LAUF)["antworten"]["0"]
    assert gespeichert["herkunft"] == "vorlage"

    andere = "b" if vorlagen_seite == "a" else "a"
    client.post(f"/uebungen-bewertung/{LAUF}/antwort",
                json={"index": 0, "gewaehlt": andere})
    assert uebungen_bewertung._lauf_laden(LAUF)["antworten"]["0"]["herkunft"] == "belegt"


def test_unsinnige_wahl_wird_abgelehnt():
    antwort = client.post(f"/uebungen-bewertung/{LAUF}/antwort",
                          json={"index": 0, "gewaehlt": "c"})
    assert antwort.status_code == 400


def test_unbekannte_aufgabe_wird_abgelehnt():
    antwort = client.post(f"/uebungen-bewertung/{LAUF}/antwort",
                          json={"index": 999, "gewaehlt": "a"})
    assert antwort.status_code == 404


# --- Auswahl der Paare -----------------------------------------------------


def test_paare_verteilen_sich_ueber_die_aufnahmen():
    """Sonst sagte das Ergebnis mehr ueber zwei Sets als ueber zwei
    Textsorten."""
    aufgaben = _aufgaben()
    aufnahmen = {a["fileName"] for a in aufgaben}
    assert len(aufnahmen) == 3, f"nur {aufnahmen} vertreten"
    # Reihum: erst je Aufnahme die staerkste Uebung.
    assert [a["fileName"] for a in aufgaben[:3]] == ["Set0.wav", "Set1.wav", "Set2.wav"]


def test_jede_aufgabe_ist_anspringbar():
    for a in _aufgaben():
        assert isinstance(a["atSec"], (int, float))
        assert a["fileName"]
