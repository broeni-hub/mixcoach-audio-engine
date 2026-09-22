"""Ausdrueckliche Kennzeichnung schlaegt die Endungs-Heuristik."""

from app.coach.profile import (
    _selbst_aufgenommen,
    ist_eigene_aufnahme,
    pegel_trend,
    pegel_zeitreihe,
)


def _report(name, **felder):
    r = {"id": "a" * 8, "fileName": name, "scoringVersion": 3, "createdAt": "2026-09-22T10:00:00Z",
         "setTransitions": [{"index": i, "mid_sec": 60.0 * i, "loudness_jump_db": 2.0 + i}
                            for i in range(1, 5)]}
    r.update(felder)
    return r


def test_ohne_feld_entscheidet_weiter_die_endung():
    assert ist_eigene_aufnahme(_report("REC001.WAV")) is True
    assert ist_eigene_aufnahme(_report("Dixon WE2.mp3")) is False


def test_fremdes_set_als_wav_wird_nicht_als_eigen_gezaehlt():
    # Der Fall vom 22.09.2026: Set eines befreundeten DJs, als .wav geliefert.
    r = _report("01 Set for Basti - 20.9.2026.wav", ownRecording=False)
    assert _selbst_aufgenommen(r["fileName"]) is True, "Endung sagt weiterhin eigen"
    assert ist_eigene_aufnahme(r) is False, "die Kennzeichnung gewinnt"


def test_eigene_aufnahme_als_mp3_wird_mitgezaehlt():
    r = _report("eigenes Set.mp3", ownRecording=True)
    assert ist_eigene_aufnahme(r) is True


def test_nur_ein_bool_gilt_als_kennzeichnung():
    for wert in ("false", "", 0, 1, None):
        r = _report("REC001.WAV", ownRecording=wert)
        assert ist_eigene_aufnahme(r) is True, wert


def test_gekennzeichnetes_fremdset_faellt_aus_der_kurve():
    eigen = _report("REC001.WAV")
    fremd = dict(_report("01 Set for Basti - 20.9.2026.wav", ownRecording=False), id="b" * 8)
    # pegel_trend erwartet die Zeitreihe, nicht die Reports.
    trend = pegel_trend(pegel_zeitreihe([eigen, fremd]))
    assert trend["recordings"] == 1
    assert trend["excludedForeign"] == 1
