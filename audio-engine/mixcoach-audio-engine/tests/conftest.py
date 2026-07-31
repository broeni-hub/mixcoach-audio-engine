"""Testlaeufe schreiben nicht mehr in den echten Datenstamm.

Warum das noetig wurde: test_async_jobs und test_end_to_end laden eine
synthetische WAV durch die ECHTE API. job_manager legt das Ergebnis daraufhin
unter RESULTS_DIR ab - und weil MIXCOACH_DATA_DIR beim Testen nicht gesetzt
ist, faellt app/paths.py auf den Engine-Ordner zurueck. Jeder pytest-Lauf
hinterliess so ein bis zwei Analyse-JSONs in analysis_results/.

Das ist nicht nur Unordnung, sondern ein Messfehler: die Dateien heissen
mix.wav und synthetic_mix.wav, haben genau einen Uebergang, und jede
Auswertung ueber analysis_results/ zaehlt sie mit. Am 31.07.2026 waren
davon 62 Stueck aufgelaufen - sie allein lieferten 64-mal denselben
phrase_beats_off-Wert (15,08) und haben eine Verteilungsmessung so weit
verschoben, dass der Median um 1,8 Beats danebenlag. Der Fehler faellt
nicht auf, weil er wie ein Befund aussieht.

autouse: keine Testdatei muss daran denken. Wer den echten Ordner braucht,
setzt ihn im Test selbst wieder (wie test_coach_profile es fuer seine
eigene Sicht tut).
"""

import pytest

from app.jobs import job_manager


@pytest.fixture(autouse=True)
def _ergebnisse_in_den_tmp_ordner(tmp_path, monkeypatch):
    # Eigener, unverwechselbarer Ordnername: Tests bekommen denselben
    # tmp_path und legen dort teils selbst ein "analysis_results" an
    # (test_fit_composite_weights tut das mit mkdir() ohne exist_ok).
    ziel = tmp_path / "_job_manager_ergebnisse"
    ziel.mkdir(parents=True, exist_ok=True)
    # job_manager bindet RESULTS_DIR per 'from app.paths import RESULTS_DIR'
    # ein - der Name muss deshalb IM MODUL ersetzt werden, ein Patch auf
    # app.paths.RESULTS_DIR liefe ins Leere.
    monkeypatch.setattr(job_manager, "RESULTS_DIR", ziel)
    return ziel
