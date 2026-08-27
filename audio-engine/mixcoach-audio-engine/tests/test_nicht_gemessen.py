"""B5: notMeasured aus dem Ist-Stand, an genau einer Stelle.

Der wichtigste Test ist test_beatmatching_faellt_heraus_sobald_der_jitter_da_ist:
er haelt den Widerspruch fest, der vom 20. bis 27.08.2026 in allen 56 Reports
stand - "beatmatching: nicht gemessen" neben einer Beatmatching-Uebung mit
Zahl.

Der zweitwichtigste ist test_befuellt_ist_nicht_gemessen: phrase_beats_off
steht in 100 % der Uebergaenge und sagt nichts (rho -0,04). Wer die Regel auf
"Feld ist nicht None" verkuerzt, baut genau die Pseudo-Praezision, gegen die
dieses Projekt antritt.
"""

import pytest

from app.audio.beat_jitter import (PUNKTE_0_MS, PUNKTE_100_MS, radar_punkte)
from app.audio.nicht_gemessen import DIMENSIONEN, aus_report, bestimmen

VOLLE_SCORES = {"flow": 70, "musicality": 60, "overall": 65}


def test_ohne_uebergaenge_traegt_der_report_nichts():
    assert bestimmen([], VOLLE_SCORES) == [
        "beatmatching", "creativity", "eq", "frequency", "timing"]


def test_beatmatching_faellt_heraus_sobald_der_jitter_da_ist():
    """Der Widerspruch, um den es geht."""
    ohne = bestimmen([{"phrase_beats_off": 3.0}], VOLLE_SCORES)
    mit = bestimmen([{"beat_jitter_ms": 12.0}], VOLLE_SCORES)
    assert "beatmatching" in ohne
    assert "beatmatching" not in mit


def test_ein_einziger_gemessener_uebergang_reicht():
    """Ein Report, in dem nur ein Uebergang einen Jitter traegt, hat die
    Groesse gemessen - nur eben selten. 'Nicht gemessen' waere falsch."""
    assert "beatmatching" not in bestimmen(
        [{"x": 1}, {"beat_jitter_ms": 9.0}, {"x": 2}], VOLLE_SCORES)


def test_befuellt_ist_nicht_gemessen():
    """phrase_beats_off steht ueberall und sagt nichts - timing bleibt drin."""
    assert "timing" in bestimmen(
        [{"phrase_beats_off": 3.0, "beat_jitter_ms": 9.0}], VOLLE_SCORES)
    assert DIMENSIONEN["timing"]["belegt"] is False


def test_jede_dimension_nennt_ihren_grund():
    """Ohne Beleg keine Entscheidung - und ohne Text keine Nachpruefbarkeit."""
    for name, regel in DIMENSIONEN.items():
        assert regel.get("beleg"), f"{name} ohne Begruendung"
        if regel.get("belegt"):
            assert any(z.isdigit() for z in regel["beleg"]), \
                f"{name} gilt als belegt, nennt aber keine Zahl"


def test_frequency_haengt_am_feld_oberster_ebene():
    assert "frequency" in bestimmen([{"beat_jitter_ms": 9.0}], VOLLE_SCORES, None)
    assert "frequency" not in bestimmen(
        [{"beat_jitter_ms": 9.0}], VOLLE_SCORES, {"low": 1})


def test_eine_kopfzahl_die_none_ist_sagt_das_auch():
    """flow/musicality stehen nicht in DIMENSIONEN, koennen aber fehlen."""
    assert "flow" in bestimmen([{"beat_jitter_ms": 9.0}],
                               {"flow": None, "musicality": 60, "overall": 65})


def test_overall_zaehlt_nicht_als_achse():
    assert "overall" not in bestimmen([{"beat_jitter_ms": 9.0}],
                                      {"flow": 70, "overall": None})


def test_aus_report_liest_dieselben_teile():
    report = {"setTransitions": [{"beat_jitter_ms": 9.0}],
              "scores": VOLLE_SCORES, "frequency": None}
    assert aus_report(report) == bestimmen(
        report["setTransitions"], report["scores"], None)


# --- Die Kopfzahl fuers Radar ---------------------------------------------


def test_radar_punkte_nutzen_die_ganze_skala():
    """Die Lehre aus beat_alignment_score: dessen Spanne war 83-98 von 100.
    Hier muessen p10 und p90 der echten Verteilung weit auseinanderliegen."""
    p10 = radar_punkte([{"beat_jitter_ms": 8.1}])
    p90 = radar_punkte([{"beat_jitter_ms": 18.8}])
    assert p10 - p90 > 40, f"Skala zu eng: {p90} bis {p10}"


def test_radar_punkte_kennen_ihre_anker():
    assert radar_punkte([{"beat_jitter_ms": PUNKTE_100_MS}]) == 100
    assert radar_punkte([{"beat_jitter_ms": PUNKTE_0_MS}]) == 0


def test_radar_punkte_bleiben_in_der_skala():
    assert radar_punkte([{"beat_jitter_ms": 0.1}]) == 100
    assert radar_punkte([{"beat_jitter_ms": 500.0}]) == 0


def test_radar_punkte_nehmen_den_median():
    """Ein ausgerissener Uebergang darf die Kopfzahl nicht verschieben."""
    mit_ausreisser = radar_punkte([{"beat_jitter_ms": v}
                                   for v in (9.0, 9.0, 9.0, 200.0)])
    assert mit_ausreisser == radar_punkte([{"beat_jitter_ms": 9.0}])


def test_ohne_jitter_keine_punktzahl():
    assert radar_punkte([{"x": 1}]) is None
    assert radar_punkte([]) is None
