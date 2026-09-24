# -*- coding: utf-8 -*-
"""Ein Massstab, nicht zwei.

Bis zum 23.09.2026 hielt tools/set_report.py - das Werkzeug, aus dem die an
fremde DJs verschickten Seiten entstehen - drei eigene Regeln:

  1. vier Schwellen (3,0 dB / 1,0 dB / 15,0 ms / 10,0 ms), woertlich kopiert
     aus app/coach/uebungen.py
  2. eine eigene Stufen-Einteilung mit eigener abs(wert)/schwelle-Rechnung -
     die dritte Fassung derselben Formel
  3. die Profi-Spannen, die es NUR dort gab - die App kannte sie nicht

Punkt 3 ist der teure: die verschickte Seite war deshalb kein Bild des
Produkts, sondern ein zweites Produkt. Diese Tests halten fest, dass es dabei
nicht wieder auseinanderlaeuft.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.coach import referenz
from app.coach.uebungen import (
    GROESSEN,
    sauberkeit,
    stufe,
    unter_allen_schwellen,
)

WERKZEUG = Path(__file__).resolve().parents[1] / "tools" / "set_report.py"


# --- Die Stufen-Regel ----------------------------------------------------

def test_stufen_liegen_an_der_eigenen_schwelle():
    """Die Grenzen sind Vielfache der eigenen Schwelle, keine festen Werte.

    Nur so heisst der Vergleich ueber Einheiten hinweg etwas: 4,2 dB und
    21,0 ms sind beide "ernst", weil beide 1,4-fach ueber ihrer Schwelle
    liegen.
    """
    assert stufe("loudness_jump_db", 4.2) == "ernst"
    assert stufe("beat_jitter_ms", 21.0) == "ernst"


def test_stufen_an_den_raendern():
    """Die Grenzen 1,00 / 1,35 / 1,75 aus STUFEN, gepruefte Seiten.

    Nicht exakt AUF 1,35 geprueft: 4,05 / 3,0 ergibt in Fliesskomma
    1,3499999999999999 und faellt damit auf die untere Seite. Das ist kein
    Fehler und war in der alten Fassung in set_report.py genauso - es zeigt
    nur, dass ein Test auf einer nicht darstellbaren Grenze nichts ueber die
    Regel aussagt, sondern ueber die Binaerdarstellung.
    """
    assert stufe("loudness_jump_db", 2.99) == "gut"
    assert stufe("loudness_jump_db", 3.0) == "warnung"      # genau 1,00-fach
    assert stufe("loudness_jump_db", 4.04) == "warnung"     # knapp unter 1,35
    assert stufe("loudness_jump_db", 4.06) == "ernst"       # knapp darueber
    assert stufe("loudness_jump_db", 5.24) == "ernst"       # knapp unter 1,75
    assert stufe("loudness_jump_db", 5.25) == "kritisch"    # genau 1,75-fach


def test_der_pegelsprung_zaehlt_im_betrag_der_jitter_nicht():
    """-4,2 dB ist genauso schwer wie +4,2 dB. Der Jitter hat keine Richtung."""
    assert stufe("loudness_jump_db", -4.2) == stufe("loudness_jump_db", 4.2)


def test_ohne_wert_keine_stufe():
    assert stufe("loudness_jump_db", None) == "keine"


# --- Die Referenz --------------------------------------------------------

def test_referenz_ist_eine_spanne_und_kein_punkt():
    for metrik, regel in referenz.SPANNEN.items():
        assert regel["min"] < regel["max"], metrik


def test_der_fall_des_test_djs():
    """11,2 ms liegt INNERHALB der sechs - das war der ganze Streitpunkt.

    Am 23.09.2026 schrieb ein Test-DJ zu seinem Report: "maybe I'm not a
    machine but I believe 10ms is fucking amazing haha". Die Skala hatte ihr
    Band von 0 bis zum Median (10,0 ms) gezeichnet, sein Wert lag darueber
    und las sich als Rueckstand. Gegen kein einziges Referenz-Set war ein
    Unterschied nachweisbar (Mann-Whitney, alle p > 0,09).
    """
    assert referenz.innerhalb("beat_jitter_ms", 11.2) is True
    assert referenz.innerhalb("beat_jitter_ms", 11.9) is True    # Dixon WE2
    assert referenz.innerhalb("beat_jitter_ms", 14.0) is False


def test_der_pegel_wird_im_betrag_verglichen():
    assert referenz.innerhalb("loudness_jump_db", -1.2) is True


def test_ohne_wert_keine_aussage():
    assert referenz.innerhalb("beat_jitter_ms", None) is None
    assert referenz.innerhalb("gibt_es_nicht", 1.0) is None


def test_die_dichte_ist_als_unbelegt_gekennzeichnet():
    """Fabi hat am 13.09.2026 gefragt, ob schnellere Wechsel empfohlen sind -
    weil die Kachel gleichrangig neben zwei belegten Groessen stand. Gemessen:
    rho -0,094, p = 0,67. Kein Zusammenhang."""
    assert referenz.SPANNEN[referenz.DICHTE]["belegt"] is False
    assert referenz.SPANNEN["loudness_jump_db"]["belegt"] is True
    assert referenz.SPANNEN["beat_jitter_ms"]["belegt"] is True


def test_die_spannen_stimmen_noch_mit_dem_datenstamm():
    """Selbstpruefung: die Konstanten gegen die Daten nachgerechnet.

    Dieselbe Bauart wie der Selbsttest der Referenzmetrik. Laeuft ein Set neu
    durch die Analyse, aendern sich die Raender - und dann muss jemand die
    Zahlen hier nachziehen, statt dass die Seite still einen alten Massstab
    zeigt.
    """
    from app.paths import RESULTS_DIR

    gerechnet = referenz.neu_berechnen(RESULTS_DIR)
    if not gerechnet:
        pytest.skip(
            "Kein Datenstamm sichtbar - MIXCOACH_DATA_DIR ist nicht gesetzt. "
            "Diese Pruefung braucht die sechs Profi-Sets in analysis_results/."
        )

    for metrik, regel in referenz.SPANNEN.items():
        ist = gerechnet.get(metrik)
        assert ist, f"{metrik} nicht nachrechenbar"
        assert ist["sets"] == 6, f"{metrik}: {ist['sets']} statt 6 Referenz-Sets"
        # Die Konstanten sind auf eine Nachkommastelle gerundet abgelegt.
        assert abs(ist["min"] - regel["min"]) <= 0.06, (metrik, ist["min"], regel["min"])
        assert abs(ist["max"] - regel["max"]) <= 0.06, (metrik, ist["max"], regel["max"])
        assert (ist["min_set"], ist["max_set"]) == regel["raender"], metrik


# --- Und dass das Werkzeug keine eigenen Zahlen zurueckbekommt ------------

def test_das_werkzeug_definiert_keine_eigene_schwelle():
    """Liest den Quelltext. Ein Test auf die Werte allein wuerde nicht
    anschlagen, wenn jemand dieselbe Zahl erneut hinschreibt - und genau so
    ist die Kopie urspruenglich entstanden.
    """
    quelltext = WERKZEUG.read_text(encoding="utf-8")
    verdaechtig = []
    for zeile in quelltext.splitlines():
        if not re.match(r"^(SCHWELLE|ZIEL|PROFI)\w*\s*(,\s*\w+\s*)?=", zeile):
            continue
        if "GROESSEN[" in zeile or "PROFI_SPANNEN[" in zeile:
            continue
        if re.search(r"=\s*.*\d", zeile):
            verdaechtig.append(zeile.strip())
    assert not verdaechtig, (
        "tools/set_report.py definiert wieder eigene Zahlen statt sie aus "
        "app/coach/uebungen.py und app/coach/referenz.py zu lesen:\n  "
        + "\n  ".join(verdaechtig)
    )


def test_das_werkzeug_bringt_keine_eigene_stufen_einteilung_mit():
    quelltext = WERKZEUG.read_text(encoding="utf-8")
    assert "def stufe(" not in quelltext
    assert "from app.coach.uebungen import" in quelltext


def test_die_schwellen_im_werkzeug_sind_die_der_regel():
    import tools.set_report as sr

    assert sr.SCHWELLE_PEGEL == GROESSEN["loudness_jump_db"]["schwelle"]
    assert sr.ZIEL_PEGEL == GROESSEN["loudness_jump_db"]["ziel"]
    assert sr.SCHWELLE_JIT == GROESSEN["beat_jitter_ms"]["schwelle"]
    assert sr.ZIEL_JIT == GROESSEN["beat_jitter_ms"]["ziel"]
    assert (sr.PROFI_JIT_MIN, sr.PROFI_JIT_MAX) == referenz.spanne("beat_jitter_ms")


# --- "Was schon sitzt" ---------------------------------------------------

def test_sitzt_nur_wenn_beide_groessen_gemessen_sind():
    """Ein Uebergang ohne Pegelwert ist nicht sauber, sondern unbekannt.

    Wuerde er als Lob auftauchen, stuende unter "Was schon sitzt" eine
    Behauptung ueber etwas, das gar nicht gemessen wurde - dieselbe
    Ehrlichkeitslinie wie bei notMeasured.
    """
    assert unter_allen_schwellen({"loudness_jump_db": 1.0, "beat_jitter_ms": 9.0}) is True
    assert unter_allen_schwellen({"loudness_jump_db": 1.0}) is False
    assert unter_allen_schwellen({"beat_jitter_ms": 9.0}) is False
    assert unter_allen_schwellen({}) is False


def test_sitzt_nicht_wenn_eine_groesse_reisst():
    assert unter_allen_schwellen({"loudness_jump_db": 4.0, "beat_jitter_ms": 9.0}) is False
    assert unter_allen_schwellen({"loudness_jump_db": 1.0, "beat_jitter_ms": 19.0}) is False


def test_sauberkeit_vergleicht_einheitenfrei():
    """Ohne Magic-Value.

    Bis zum 23.09.2026 rangierte set_report.py mit `abs(pegel) + jitter / 5`.
    Die 5 stand nirgends begruendet und machte dB und ms per Dekret
    vergleichbar. Jetzt ist es die Summe der Ueberschreitungen - derselbe
    einheitenfreie Vergleich, den ueberschreitung() begruendet.

    Gegengeprueft ueber die vier fremden Sets im Bestand: dieselbe sauberste
    Stelle wie vorher, vier von vier. Die alte Gewichtung war also nicht
    falsch - sie war nur unbegruendet.
    """
    sehr_sauber = {"loudness_jump_db": 0.2, "beat_jitter_ms": 3.0}
    weniger = {"loudness_jump_db": 2.0, "beat_jitter_ms": 12.0}
    assert sauberkeit(sehr_sauber) < sauberkeit(weniger)

    # Gleiche relative Last auf beiden Achsen -> gleiche Sauberkeit.
    halb_pegel = {"loudness_jump_db": 1.5, "beat_jitter_ms": 0.0}
    halb_jitter = {"loudness_jump_db": 0.0, "beat_jitter_ms": 7.5}
    assert sauberkeit(halb_pegel) == pytest.approx(sauberkeit(halb_jitter))


# --- Der Vergleich, wie ihn der Report traegt ----------------------------

def test_vergleich_nennt_spanne_und_lage():
    ts = [{"loudness_jump_db": -1.4, "beat_jitter_ms": 11.2},
          {"loudness_jump_db": 2.0, "beat_jitter_ms": 9.0},
          {"loudness_jump_db": 1.5, "beat_jitter_ms": 13.0}]
    v = {e["metrik"]: e for e in referenz.vergleich(ts)}

    assert set(v) == {"loudness_jump_db", "beat_jitter_ms"}
    jit = v["beat_jitter_ms"]
    assert jit["wert"] == 11.2
    assert (jit["min"], jit["max"]) == (5.8, 11.9)
    assert jit["innerhalb"] is True
    assert jit["schwelle"] == GROESSEN["beat_jitter_ms"]["schwelle"]


def test_vergleich_rechnet_den_pegel_im_betrag():
    """-4 dB ist ein Sprung von 4 dB, nicht von -4."""
    ts = [{"loudness_jump_db": -4.0}, {"loudness_jump_db": -4.0}]
    v = referenz.vergleich(ts)[0]
    assert v["wert"] == 4.0
    assert v["innerhalb"] is False


def test_vergleich_enthaelt_die_dichte_nicht():
    """Sie hat keinen belegten Zusammenhang (rho -0,094, p 0,67) und gehoert
    deshalb nicht neben zwei Groessen, die einen haben."""
    ts = [{"loudness_jump_db": 1.0, "beat_jitter_ms": 9.0}]
    assert referenz.DICHTE not in {e["metrik"] for e in referenz.vergleich(ts)}


def test_ohne_messwerte_kein_vergleich():
    """Kein Platzhalter, keine Null - die Zeile faellt weg."""
    assert referenz.vergleich([]) == []
    assert referenz.vergleich([{"quality_score": 80}]) == []
    assert referenz.vergleich(None) == []


def test_nur_die_gemessene_groesse_erscheint():
    ts = [{"beat_jitter_ms": 9.0}]
    assert [e["metrik"] for e in referenz.vergleich(ts)] == ["beat_jitter_ms"]


def test_der_report_traegt_den_vergleich():
    """Gegenprobe am Mapper: das Feld kommt wirklich im Report an."""
    from app.api.analysis_mapper import map_set_analysis_to_frontend_result

    r = map_set_analysis_to_frontend_result("probe.wav", {
        "duration": 600.0,
        "transitions_detailed": [
            {"index": 1, "mid_sec": 100.0, "start_sec": 90.0, "end_sec": 110.0,
             "loudness_jump_db": 1.2, "beat_jitter_ms": 9.0, "scores": {}},
        ],
    })
    metriken = {e["metrik"] for e in (r.get("referenz") or [])}
    assert "beat_jitter_ms" in metriken
