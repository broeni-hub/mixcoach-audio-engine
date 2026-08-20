"""Tests fuer den Beat-Jitter (app/audio/beat_jitter.py).

Der wichtigste Test ist test_jitter_und_score_sind_dieselbe_messung: er haelt
fest, dass beat_jitter_ms und beat_alignment_score nicht auseinanderlaufen.
Es sind zwei Ansichten derselben Groesse an zwei Stellen im Code - der Score
in app/audio/scoring/ (nicht anfassbar, speist den Composite), der Jitter
daneben (speist Report und Coach). Faellt dieser Test, zeigt die App zwei
verschiedene Wahrheiten ueber dieselbe Messung an.
"""

import numpy as np
import pytest

from app.audio.beat_jitter import (MIN_BEATS_IM_FENSTER, annotate_beat_jitter,
                                   jitter_ms)
# Bewusst die private Funktion: genau sie ist der Bezugspunkt, gegen den
# gleichgehalten wird.
from app.audio.scoring.beat_alignment import (CV_AT_ZERO_SCORE, _interval_cv,
                                              annotate_beat_alignment)


def _puls(n: int, abstand: float = 0.46875, streuung: float = 0.0,
          seed: int = 7) -> list[float]:
    """Beat-Zeitpunkte mit definierter Streuung. 0.46875 s = 128 BPM."""
    rng = np.random.default_rng(seed)
    abstaende = rng.normal(abstand, streuung, n - 1) if streuung else np.full(n - 1, abstand)
    return list(np.concatenate([[0.0], np.cumsum(abstaende)]))


def test_perfekter_puls_hat_keinen_jitter():
    assert jitter_ms(_puls(40)) == pytest.approx(0.0, abs=1e-9)


def test_jitter_trifft_die_vorgegebene_streuung():
    """20 ms hineingegeben, rund 20 ms herausbekommen - die Einheit stimmt."""
    gemessen = jitter_ms(_puls(400, streuung=0.020))
    assert gemessen == pytest.approx(20.0, rel=0.15)


def test_jitter_und_score_sind_dieselbe_messung():
    """Der Kern: jitter / mittlerer Abstand muss der cv des Scores sein.

    Damit ist beat_jitter_ms nachweislich keine zweite, eigene Messung,
    sondern dieselbe ohne die 0-100-Skala.
    """
    for streuung in (0.002, 0.008, 0.020, 0.040):
        beats = _puls(300, streuung=streuung)
        cv = _interval_cv(beats)
        mittlerer_abstand_ms = float(np.mean(np.diff(np.array(beats)))) * 1000.0
        assert jitter_ms(beats) == pytest.approx(cv * mittlerer_abstand_ms, rel=1e-6)


def test_score_laesst_sich_aus_dem_jitter_zurueckrechnen():
    """Die Umrechnung, auf der tools/eval/beat_jitter.py und der Backfill
    beruhen: score = 100 - (jitter / mittlerer Abstand) / 0,35 * 100."""
    beats = _puls(300, streuung=0.015)
    uebergaenge = [{"start_sec": 0.0, "end_sec": beats[-1] + 1.0}]
    annotate_beat_alignment(uebergaenge, beats)
    annotate_beat_jitter(uebergaenge, beats)

    mittlerer_abstand_ms = float(np.mean(np.diff(np.array(beats)))) * 1000.0
    cv = uebergaenge[0]["beat_jitter_ms"] / mittlerer_abstand_ms
    erwartet = round(100.0 - (cv / CV_AT_ZERO_SCORE) * 100.0)
    assert abs(erwartet - uebergaenge[0]["beat_alignment_score"]) <= 1


def test_zu_wenige_beats_geben_nichts_statt_irgendwas():
    """Ehrlichkeitslinie: lieber leer als eine Streuung aus zwei Abstaenden."""
    assert jitter_ms(_puls(MIN_BEATS_IM_FENSTER - 1)) is None


def test_annotate_setzt_wert_und_stichprobe():
    beats = _puls(120, streuung=0.010)
    uebergaenge = [{"start_sec": 10.0, "end_sec": 30.0}]
    annotate_beat_jitter(uebergaenge, beats)

    t = uebergaenge[0]
    assert t["beat_jitter_ms"] > 0
    assert t["beat_jitter_beats"] == len([b for b in beats if 10.0 <= b <= 30.0])


def test_annotate_ohne_fenster_setzt_none():
    uebergaenge = [{"start_sec": None, "end_sec": 30.0}, {}]
    annotate_beat_jitter(uebergaenge, _puls(120))
    for t in uebergaenge:
        assert t["beat_jitter_ms"] is None
        assert t["beat_jitter_beats"] is None


def test_annotate_setzt_none_wenn_das_fenster_leer_ist():
    """Set-Rand: Fenster ausserhalb des Beat-Rasters."""
    uebergaenge = [{"start_sec": 9000.0, "end_sec": 9100.0}]
    annotate_beat_jitter(uebergaenge, _puls(120))
    assert uebergaenge[0]["beat_jitter_ms"] is None
