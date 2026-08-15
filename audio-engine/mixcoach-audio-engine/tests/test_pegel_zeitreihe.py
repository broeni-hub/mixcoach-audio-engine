"""Die Pegel-Zeitreihe im Coach-Profil (A).

Vier Fehler wuerden die Kurve verfaelschen, und jeder ist hier festgehalten:
Testdateien mitzaehlen, nach Reports statt nach Aufnahmen zaehlen, Reports
verschiedener Rechenvorschriften nebeneinander zeichnen - und das
Vorzeichen verwechseln, weil hier ausnahmsweise NIEDRIGER BESSER ist.
"""

import pytest

from app.coach import profile
from app.coach.profile import pegel_trend, pegel_zeitreihe


def _report(datei, tag, spruenge, version=3, aid=None):
    return {
        "id": aid or f"{datei}-{tag}",
        "fileName": datei,
        "createdAt": f"2026-07-{tag:02d}T10:00:00Z",
        "scoringVersion": version,
        "setTransitions": [
            {"index": i, "mid_sec": 100.0 * i, "loudness_jump_db": s}
            for i, s in enumerate(spruenge, start=1)
        ],
    }


@pytest.fixture(autouse=True)
def _ohne_feedback(monkeypatch):
    """Kein Ground-Truth-Zugriff in diesen Tests."""
    monkeypatch.setattr(profile, "_filtered_transitions",
                        lambda r: r.get("setTransitions") or [])


# --- Die drei Ausschluesse -------------------------------------------------


def test_testdateien_zaehlen_nicht_mit():
    """mix.wav steht mit 0,00 dB im Bestand und waere das perfekte Set."""
    reihe = pegel_zeitreihe([
        _report("REC001.WAV", 6, [3.0, 4.0]),
        _report("mix.wav", 7, [0.0]),
        _report("synthetic_mix.wav", 8, [0.0]),
    ])
    assert [e["fileName"] for e in reihe] == ["REC001.WAV"]


def test_nach_aufnahme_entdoppelt_nicht_nach_report():
    """REC001 liegt im echten Bestand elfmal vor - das darf einmal zaehlen."""
    reihe = pegel_zeitreihe([
        _report("REC001.WAV", 6, [3.0], aid="a"),
        _report("REC001.WAV", 7, [1.0], aid="b"),
        _report("REC001.WAV", 8, [2.0], aid="c"),
    ])
    assert len(reihe) == 1
    assert reihe[0]["analyses"] == 3
    # Die NEUESTE Analyse liefert den Wert...
    assert reihe[0]["medianJumpDb"] == 2.0
    # ...aber der Zeitpunkt bleibt der frueheste Lauf, sonst wandert eine
    # alte Aufnahme allein durchs Nachrechnen nach rechts.
    assert reihe[0]["createdAt"].startswith("2026-07-06")


def test_nur_vergleichbare_reports():
    reihe = pegel_zeitreihe([
        _report("REC001.WAV", 6, [3.0]),
        _report("REC002.WAV", 7, [1.0], version=None),
        _report("REC003.WAV", 8, [1.0], version=2),
    ])
    assert [e["fileName"] for e in reihe] == ["REC001.WAV"]


def test_ohne_pegelwerte_kein_eintrag():
    reihe = pegel_zeitreihe([{
        "id": "x", "fileName": "REC009.WAV", "createdAt": "2026-07-06T10:00:00Z",
        "scoringVersion": 3,
        "setTransitions": [{"index": 1, "mid_sec": 10.0}],
    }])
    assert reihe == []


# --- Die Kennzahlen --------------------------------------------------------


def test_median_statt_mittelwert():
    """Ein Ausreisser darf eine ganze Aufnahme nicht verschieben."""
    reihe = pegel_zeitreihe([_report("REC001.WAV", 6, [1.0, 1.0, 1.0, 10.1])])
    assert reihe[0]["medianJumpDb"] == 1.0        # Mittelwert waere 3,28


def test_anteil_ueber_der_schwelle():
    reihe = pegel_zeitreihe([_report("REC001.WAV", 6, [1.0, 2.9, 3.0, 5.0])])
    assert reihe[0]["shareAboveThresholdPct"] == 50.0   # 3,0 zaehlt mit


def test_betrag_zaehlt_nicht_die_richtung():
    """Zu leise ist genauso unsauber wie zu laut."""
    reihe = pegel_zeitreihe([_report("REC001.WAV", 6, [-4.0, -4.0])])
    assert reihe[0]["medianJumpDb"] == 4.0
    assert reihe[0]["shareAboveThresholdPct"] == 100.0


# --- Der Trend, und sein Vorzeichen ---------------------------------------


def test_niedriger_ist_besser_und_das_steht_dabei():
    """Der haeufigste Fehler waere, Fortschritt als Rueckschritt zu zeigen."""
    reihe = pegel_zeitreihe([
        _report("A.WAV", 1, [4.0]), _report("B.WAV", 2, [4.0]),
        _report("C.WAV", 3, [4.0]), _report("D.WAV", 4, [1.0]),
        _report("E.WAV", 5, [1.0]), _report("F.WAV", 6, [1.0]),
    ])
    t = pegel_trend(reihe)
    assert t["lowerIsBetter"] is True
    assert t["delta"] < 0, "Verbesserung muss ein negatives delta ergeben"
    assert t["current"] == 1.0
    assert t["deltaSharePct"] < 0


def test_verschlechterung_ergibt_positives_delta():
    reihe = pegel_zeitreihe([
        _report("A.WAV", 1, [1.0]), _report("B.WAV", 2, [1.0]),
        _report("C.WAV", 3, [1.0]), _report("D.WAV", 4, [4.0]),
        _report("E.WAV", 5, [4.0]), _report("F.WAV", 6, [4.0]),
    ])
    assert pegel_trend(reihe)["delta"] > 0


def test_zu_wenig_aufnahmen_erfindet_keine_null():
    """None heisst 'noch nicht sagbar'. 0.0 hiesse 'keine Veraenderung'."""
    reihe = pegel_zeitreihe([
        _report("A.WAV", 1, [2.0]), _report("B.WAV", 2, [2.0]),
        _report("C.WAV", 3, [2.0]),
    ])
    t = pegel_trend(reihe)
    assert t["delta"] is None
    assert t["deltaSharePct"] is None
    assert t["current"] is not None      # der Stand ist trotzdem sagbar
    assert t["recordings"] == 3


def test_leere_reihe_bleibt_leer():
    t = pegel_trend([])
    assert t["current"] is None and t["delta"] is None and t["recordings"] == 0


# --- Eigene gegen fremde Aufnahmen ----------------------------------------


def test_fremde_sets_zaehlen_nicht_in_den_trend():
    """Sechs fremde DJ-Sets im Bestand sind professionell gemastert und
    liegen zeitlich vorn - sie wuerden den eigenen Fortschritt ueberdecken."""
    reihe = pegel_zeitreihe([
        _report("Dixon WE2 Tomorrowland.mp3", 1, [0.5]),
        _report("Joris Voorn Upclose.mp3", 2, [0.5]),
        _report("A.WAV", 3, [4.0]), _report("B.WAV", 4, [4.0]),
        _report("C.WAV", 5, [1.0]), _report("D.WAV", 6, [1.0]),
        _report("E.WAV", 7, [1.0]),
    ])
    # Sichtbar bleiben sie - nur gezaehlt werden sie nicht.
    assert len(reihe) == 7
    assert sum(1 for e in reihe if not e["ownRecording"]) == 2

    t = pegel_trend(reihe)
    assert t["recordings"] == 5
    assert t["excludedForeign"] == 2
    assert t["delta"] < 0
