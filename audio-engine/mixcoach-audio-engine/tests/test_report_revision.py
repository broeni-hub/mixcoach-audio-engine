"""Tests fuer reportRevision - den Weg, auf dem eine Datenkorrektur ankommt.

Die scoringVersion beantwortet "nach welcher Rechenvorschrift sind die
Zahlen entstanden". Sie darf fuer eine reine Datenkorrektur ausdruecklich
NICHT erhoeht werden (scoring_version.py: "wer eine Rechenvorschrift
aendert, erhoeht sie"). Genau deshalb konnte eine Korrektur bis zum
13.08.2026 keinen Browser erreichen, der die Analyse schon kannte - der
Korrekturweg ordnete nur nach Version.

reportRevision beantwortet die zweite Frage: ist DIESE Datei neuer als
deine Kopie? Gegenstueck im Frontend: lib/scoring-version.ts.
"""

from app.audio.pipeline.scoring_version import (
    ERSTE_REVISION,
    naechste_revision,
    revision_von,
    scoring_stamp,
)
from tools.backfill_reports import nachziehen


def test_frisch_gerechnet_traegt_revision_eins():
    """Ein neuer Report hat nichts zu berichtigen."""
    assert scoring_stamp()["reportRevision"] == ERSTE_REVISION


def test_fehlende_revision_gilt_als_null():
    assert revision_von({}) == 0
    assert revision_von({"reportRevision": None}) == 0
    assert revision_von({"reportRevision": 0}) == 0
    assert revision_von({"reportRevision": 2}) == 2


def test_naechste_revision_zaehlt_hoch():
    assert naechste_revision({}) == 1
    assert naechste_revision({"reportRevision": 1}) == 2
    assert naechste_revision({"reportRevision": 7}) == 8


def test_backfill_zaehlt_bei_einer_korrektur_hoch():
    """Wer etwas berichtigt, muss es auch weitergeben koennen."""
    alt = {"createdAt": "2026-07-20T10:00:00Z", "scoringVersion": 3,
           "scores": {"beatmatching": 100, "timing": 61}, "notMeasured": []}
    neu, aenderungen = nachziehen(alt)

    assert neu["scores"]["beatmatching"] is None
    assert neu["scores"]["timing"] is None
    assert neu["reportRevision"] == 1
    assert any("reportRevision" in a for a in aenderungen)


def test_backfill_holt_die_erste_revision_auch_ohne_andere_korrektur():
    """Ein Report ganz ohne Revision kann nichts weitergeben - 0 > 0 ist
    falsch. Die erste Revision ist deshalb selbst eine Aenderung."""
    schon_ehrlich = {
        "createdAt": "2026-07-20T10:00:00Z", "scoringVersion": 3,
        "scores": {"beatmatching": None, "timing": None},
        "notMeasured": ["eq", "creativity", "frequency", "beatmatching", "timing"],
    }
    neu, aenderungen = nachziehen(schon_ehrlich)

    assert neu["reportRevision"] == 1
    assert aenderungen == ["reportRevision: fehlt -> 1"]


def test_backfill_laesst_eine_vorhandene_revision_in_ruhe():
    """Zweiter Lauf ohne neue Korrektur darf nicht weiterzaehlen - sonst
    wuerde jeder Lauf alle Browser-Kopien grundlos austauschen."""
    fertig = {
        "createdAt": "2026-07-20T10:00:00Z", "scoringVersion": 3,
        "scores": {"beatmatching": None, "timing": None},
        "notMeasured": ["eq", "creativity", "frequency", "beatmatching", "timing"],
        "reportRevision": 1,
    }
    neu, aenderungen = nachziehen(fertig)

    assert aenderungen == []
    assert neu["reportRevision"] == 1


def test_unbelegter_stempel_faellt_weg_und_wird_weitergegeben():
    """Die sechs Reports vom 02.07.: Stempel 3 ohne Beleg. Er verschwindet -
    und die Revision sorgt dafuer, dass diese Korrektur trotzdem ankommt,
    obwohl die Version dabei SINKT."""
    alt = {"createdAt": "2026-07-02T10:00:00Z", "scoringVersion": 3,
           "scores": {"beatmatching": None, "timing": None},
           "notMeasured": ["eq", "creativity", "frequency", "beatmatching", "timing"]}
    neu, aenderungen = nachziehen(alt)

    assert "scoringVersion" not in neu
    assert neu["reportRevision"] == 1
    assert any("nicht belegt" in a for a in aenderungen)
