"""Die zweite Achse (Beat-Jitter) und die Rangkorrelation.

Der wichtigste Test ist test_delta_taeuscht_in_beide_richtungen: im echten
Bestand zeigt der Jitter delta = -3,8 ms bei einer Rangkorrelation von
-0,004, und der Pegelsprung delta = 0,0 bei -0,73. Das Fenster "letzte drei
gegen die drei davor" taeuscht also in BEIDE Richtungen - einmal Fortschritt,
wo keiner ist, einmal keiner, wo Fortschritt ist.

Ohne developmentVisible haette die Oberflaeche fuer den Jitter einen gruenen
Pfeil gezeigt.
"""

import pytest

from app.coach import profile
from app.coach.profile import _rangkorrelation, jitter_zeitreihe, trend, zeitreihe


def _report(datei, tag, werte, feld="loudness_jump_db"):
    return {
        "id": f"{datei}-{tag}", "fileName": datei,
        "createdAt": f"2026-07-{tag:02d}T10:00:00Z", "scoringVersion": 3,
        "setTransitions": [{"index": i, "mid_sec": 100.0 * i, feld: w}
                           for i, w in enumerate(werte, start=1)],
    }


@pytest.fixture(autouse=True)
def _ohne_feedback(monkeypatch):
    monkeypatch.setattr(profile, "_filtered_transitions",
                        lambda r: r.get("setTransitions") or [])


# --- Die Rangkorrelation --------------------------------------------------


def test_fallende_reihe_gibt_negative_korrelation():
    assert _rangkorrelation([5.0, 4.0, 3.0, 2.0, 1.0]) == pytest.approx(-1.0)


def test_steigende_reihe_gibt_positive_korrelation():
    assert _rangkorrelation([1.0, 2.0, 3.0, 4.0, 5.0]) == pytest.approx(1.0)


def test_flache_reihe_gibt_nichts():
    """Alle Werte gleich - es gibt keine Rangordnung."""
    assert _rangkorrelation([3.0, 3.0, 3.0, 3.0]) is None


def test_unter_vier_aufnahmen_keine_aussage():
    assert _rangkorrelation([1.0, 2.0, 3.0]) is None


# --- Die zweite Achse -----------------------------------------------------


def test_jitter_bekommt_eine_eigene_kurve():
    reihe = jitter_zeitreihe([
        _report("MixCoach1.WAV", 6, [9.0, 10.0, 11.0], feld="beat_jitter_ms"),
        _report("MixCoach2.WAV", 7, [12.0, 13.0, 14.0], feld="beat_jitter_ms"),
    ])
    assert [e["fileName"] for e in reihe] == ["MixCoach1.WAV", "MixCoach2.WAV"]
    assert [e["medianJumpDb"] for e in reihe] == [10.0, 13.0]


def test_der_jitter_zaehlt_ohne_betrag():
    """Der Pegelsprung nimmt den Betrag (zu leise ist so unsauber wie zu
    laut), der Jitter ist eine Streuung und hat keine Richtung."""
    pegel = zeitreihe([_report("A.WAV", 6, [-4.0, -4.0, -4.0])], "loudness_jump_db")
    assert pegel[0]["medianJumpDb"] == 4.0


def test_die_einheit_steht_in_der_antwort():
    p = trend(zeitreihe([_report("A.WAV", i, [3.0, 3.0, 3.0]) for i in range(1, 8)]),
              "loudness_jump_db")
    assert p["unit"] == "dB"
    j = trend(jitter_zeitreihe(
        [_report("A.WAV", i, [9.0, 9.0, 9.0], feld="beat_jitter_ms")
         for i in range(1, 8)]), "beat_jitter_ms")
    assert j["unit"] == "ms"


# --- Der Kern -------------------------------------------------------------


def test_delta_taeuscht_in_beide_richtungen():
    """Eine Reihe, die insgesamt NICHT faellt, deren letzte drei aber
    niedriger liegen als die drei davor: delta meldet Fortschritt, die
    Rangkorrelation nicht."""
    werte = [9.0, 9.0, 9.0, 9.0, 14.0, 14.0, 14.0, 9.0, 9.0, 9.0]
    reihe = [_report(f"MixCoach{i}.WAV", i + 1, [w, w, w], feld="beat_jitter_ms")
             for i, w in enumerate(werte)]
    t = trend(jitter_zeitreihe(reihe), "beat_jitter_ms")

    assert t["delta"] < 0, "das Fenster meldet eine Verbesserung"
    assert t["developmentVisible"] is False, \
        "die ganze Reihe zeigt keine - und das muss gewinnen"


def test_echte_entwicklung_wird_erkannt():
    werte = [14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0]
    reihe = [_report(f"MixCoach{i}.WAV", i + 1, [w, w, w], feld="beat_jitter_ms")
             for i, w in enumerate(werte)]
    t = trend(jitter_zeitreihe(reihe), "beat_jitter_ms")
    assert t["rankCorrelation"] < -0.9
    assert t["developmentVisible"] is True


def test_zu_wenige_aufnahmen_melden_keine_entwicklung():
    reihe = [_report(f"A{i}.WAV", i + 1, [9.0, 9.0, 9.0], feld="beat_jitter_ms")
             for i in range(2)]
    t = trend(jitter_zeitreihe(reihe), "beat_jitter_ms")
    assert t["developmentVisible"] is False
    assert t["rankCorrelation"] is None
