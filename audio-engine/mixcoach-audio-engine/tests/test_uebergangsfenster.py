"""Der Uebergang als Fenster statt als Sekundenangabe (A1/K3).

Der wichtigste Test ist test_anker_ist_start_sec: der Punkt, den der Report
bisher zeigte (mid_sec), trifft die menschliche Korrektur in 5 % der Faelle
auf 8 s genau. start_sec liegt im Median 7 s daneben statt 28 s. Wer den
Anker zurueckdreht, macht die teuerste Sekunde des Produkts wieder kaputt -
den ersten Klick eines fremden DJs.
"""

import pytest

from app.audio.uebergangsfenster import (ABDECKUNG_PCT, NACH_S, VOR_S,
                                         annotate_fenster, fenster)


def test_anker_ist_start_sec():
    """Nicht mid_sec - gemessen ueber 132 Korrekturen am 27.08.2026."""
    f = fenster({"start_sec": 872.0, "mid_sec": 900.0})
    assert f["anker"] == "start_sec"
    assert f["vonSec"] == 872.0 - VOR_S
    assert f["bisSec"] == 872.0 + NACH_S


def test_ohne_start_sec_faellt_es_auf_mid_sec_zurueck():
    """Schlechter, aber immer noch ehrlicher als ein Punkt."""
    f = fenster({"mid_sec": 900.0})
    assert f["anker"] == "mid_sec"
    assert f["vonSec"] == 900.0 - VOR_S


def test_das_fenster_nennt_seine_abdeckung():
    """Eine Spanne ohne Angabe, was sie abdeckt, ist wieder eine Behauptung."""
    assert fenster({"start_sec": 500.0})["abdeckungPct"] == ABDECKUNG_PCT
    assert 50 <= ABDECKUNG_PCT <= 95


def test_das_fenster_ist_breiter_als_der_blend():
    """Das Blend-Fenster ist im Median 34 s breit und enthaelt nur 32 % der
    Korrekturen. Wer es als 'der Uebergang' anzeigt, liegt zweimal von drei
    Malen falsch."""
    assert VOR_S + NACH_S > 34


def test_am_set_anfang_wird_nicht_negativ():
    f = fenster({"start_sec": 20.0})
    assert f["vonSec"] == 0.0
    assert f["bisSec"] == 70.0


def test_am_set_ende_wird_nicht_ueberhangen():
    f = fenster({"start_sec": 1700.0}, gesamtdauer_s=1720.0)
    assert f["bisSec"] == 1720.0


def test_ohne_zeitangabe_kein_fenster():
    """Ehrlichkeitslinie: lieber keine Spanne als eine erfundene."""
    assert fenster({}) is None
    assert fenster({"start_sec": None, "mid_sec": None}) is None


def test_annotate_haengt_an_jeden_uebergang():
    ts = [{"start_sec": 100.0}, {"mid_sec": 500.0}, {}]
    annotate_fenster(ts, gesamtdauer_s=1800.0)
    assert ts[0]["window"]["anker"] == "start_sec"
    assert ts[1]["window"]["anker"] == "mid_sec"
    assert ts[2]["window"] is None


def test_die_messungen_bleiben_unberuehrt():
    """Das Fenster sagt, WO man hinhoert. Was gemessen wurde, aendert es
    nicht - loudness_jump_db und beat_jitter_ms rechnen weiter ueber den
    Blend."""
    t = {"start_sec": 100.0, "end_sec": 134.0, "mid_sec": 117.0,
         "loudness_jump_db": 4.2, "beat_jitter_ms": 12.0}
    annotate_fenster([t])
    assert t["start_sec"] == 100.0 and t["end_sec"] == 134.0
    assert t["mid_sec"] == 117.0
    assert t["loudness_jump_db"] == 4.2 and t["beat_jitter_ms"] == 12.0
