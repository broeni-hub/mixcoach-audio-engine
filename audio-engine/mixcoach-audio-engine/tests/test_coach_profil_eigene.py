"""best/worst und die Uebungen kommen nur aus eigenen Aufnahmen.

Die Oberflaeche sagt woertlich "Deine Uebungen (aus deinen eigenen Sets)"
und "Dein bester Uebergang" (CoachProfilePanel.tsx). Bis zum 27.08.2026 zog
das Profil aus ALLEN Reports - und zeigte damit Dixon als Sebastians besten
Uebergang und eine Uebung "Aus 'RUEFUES DU SOL - Mayan Warrior': mixe
dieselben Tracks erneut".

Zwei Fehler in einem: die Ueberschrift behauptet etwas Falsches, und die
Uebung ist nicht ausfuehrbar - er hat diese Tracks nicht.
"""

import pytest

from app.coach import profile
from app.coach.profile import _highlights_and_exercises


def _report(datei, spruenge, jitter=None, aid=None):
    return {
        "id": aid or datei,
        "fileName": datei,
        "createdAt": "2026-07-20T10:00:00Z",
        "scoringVersion": 3,
        "setTransitions": [
            {"index": i, "mid_sec": 100.0 * i, "start_sec": 100.0 * i - 16,
             "loudness_jump_db": s,
             **({"beat_jitter_ms": jitter} if jitter is not None else {})}
            for i, s in enumerate(spruenge, start=1)
        ],
    }


@pytest.fixture(autouse=True)
def _ohne_feedback(monkeypatch):
    monkeypatch.setattr(profile, "_filtered_transitions",
                        lambda r: r.get("setTransitions") or [])


def test_fremde_sets_liefern_keinen_besten_uebergang():
    """Ein Dixon-Set ist sauberer gemastert als jede eigene Aufnahme - ohne
    Filter gewinnt es jeden Vergleich, und die App nennt es 'deins'."""
    ergebnis = _highlights_and_exercises([
        _report("Dixon WE2 Tomorrowland.mp3", [0.0, 0.1, 0.0]),
        _report("MixCoach5.WAV", [4.0, 5.0, 6.0]),
    ])
    assert ergebnis["best"]["fileName"] == "MixCoach5.WAV"
    assert ergebnis["worst"]["fileName"] == "MixCoach5.WAV"
    assert ergebnis["excludedForeignReports"] == 1


def test_keine_uebung_aus_einem_fremden_set():
    """Der Kern: 'mixe dieselben Tracks erneut' ist nicht ausfuehrbar, wenn
    er die Tracks nicht hat und nicht am Mixer stand."""
    ergebnis = _highlights_and_exercises([
        _report("RUEFUES DU SOL - Mayan Warrior.mp3", [10.1, 9.0, 8.0]),
        _report("MixCoach5.WAV", [4.0, 4.0, 4.0]),
    ])
    # Die Uebung traegt analysisId, der Dateiname steht im Text.
    assert {u["analysisId"] for u in ergebnis["exercises"]} == {"MixCoach5.WAV"}
    for u in ergebnis["exercises"]:
        assert "Mayan Warrior" not in u["description"]


def test_ohne_eigene_aufnahmen_lieber_nichts():
    """Kein Rueckfall auf fremde Sets, wenn nichts Eigenes da ist."""
    ergebnis = _highlights_and_exercises([
        _report("Four Tet - Sonar 2025.mp3", [5.0, 6.0, 7.0]),
    ])
    assert ergebnis["best"] is None
    assert ergebnis["worst"] is None
    assert ergebnis["exercises"] == []
    assert ergebnis["excludedForeignReports"] == 1


def test_der_ausschluss_ist_sichtbar():
    """Eine stille Auswahl ist eine, ueber die niemand nachfragen kann."""
    ergebnis = _highlights_and_exercises([
        _report("Dixon A.mp3", [1.0, 1.0, 1.0]),
        _report("Joris Voorn B.mp3", [1.0, 1.0, 1.0]),
        _report("MixCoach5.WAV", [4.0, 4.0, 4.0]),
    ])
    assert ergebnis["excludedForeignReports"] == 2


def test_eigene_aufnahmen_bleiben_vollstaendig():
    ergebnis = _highlights_and_exercises([
        _report("REC001.WAV", [3.5, 4.0, 4.5]),
        _report("MixCoach2.WAV", [5.0, 5.5, 6.0]),
    ])
    assert ergebnis["excludedForeignReports"] == 0
    assert {u["analysisId"] for u in ergebnis["exercises"]} == {
        "REC001.WAV", "MixCoach2.WAV"}


# --- Kopfzahlen und Muster (27.08.2026) -----------------------------------


def test_das_abzeichen_zaehlt_aufnahmen_nicht_reports():
    """Es stand "56 Sets - 379 Uebergaenge gemessen" bei 24 Aufnahmen -
    REC001 allein lag elfmal vor. Denselben Fehler hat die Referenzmetrik
    einmal gemacht (--mode dedup) und pegel_zeitreihe seit dem 15.08. nicht
    mehr."""
    from app.coach.profile import je_aufnahme

    reports = [
        _report("REC001.WAV", [3.0, 3.0, 3.0], aid="a"),
        _report("REC001.WAV", [1.0, 1.0, 1.0], aid="b"),
        _report("REC001.WAV", [2.0, 2.0, 2.0], aid="c"),
        _report("MixCoach2.WAV", [4.0, 4.0, 4.0], aid="d"),
    ]
    assert len(je_aufnahme(reports)) == 2


def test_die_neueste_analyse_einer_aufnahme_gewinnt():
    from app.coach.profile import je_aufnahme

    alt = _report("REC001.WAV", [9.0, 9.0, 9.0], aid="alt")
    alt["createdAt"] = "2026-07-01T10:00:00Z"
    neu = _report("REC001.WAV", [1.0, 1.0, 1.0], aid="neu")
    neu["createdAt"] = "2026-07-20T10:00:00Z"

    gewaehlt = je_aufnahme([alt, neu])
    assert len(gewaehlt) == 1
    assert gewaehlt[0]["id"] == "neu"
