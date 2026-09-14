"""Ankerregel: ein Set traegt Fingerprint-Treffer nur mit einem eindeutigen.

Hintergrund und Messung: app/audio/library_match.py, ANKER_MIN_SCORE.
Die Score-Profile unten sind die echten Werte aus dem Bestand (13.09.2026).
"""

import numpy as np

from app.audio import rematch
from app.audio.library_match import (
    ANKER_MIN_SCORE,
    merge_with_fingerprints,
    nur_verankert,
    transitions_from_matches,
)


def _treffer(scores, laenge=300.0):
    return [{"title": f"T{i}", "artist": "A", "start": i * (laenge - 20),
             "end": i * (laenge - 20) + laenge, "score": s}
            for i, s in enumerate(scores)]


def test_leer_bleibt_leer():
    assert nur_verankert([]) == []


def test_ohne_eindeutigen_treffer_wird_alles_verworfen():
    assert nur_verankert(_treffer([0.45, 0.40, 0.33])) == []


def test_ein_eindeutiger_treffer_verankert_auch_die_grauzone():
    # Die Regel entscheidet je SET, nicht je Treffer: in einem verankerten
    # Set bleibt alles wie bisher - eigene Sets aendern sich nicht.
    t = _treffer([0.36, 0.62, 0.34])
    assert nur_verankert(t) == t


def test_genau_auf_der_schwelle_ist_verankert():
    t = _treffer([ANKER_MIN_SCORE])
    assert nur_verankert(t) == t


def test_fremdes_set_aus_dem_bestand_wird_verworfen():
    # Fabi, "Turn Up The Tempo" (Dec23): hoechster Treffer 0,476 - darunter
    # "Dave Brubeck - Take Five" mit 0,324 in einem Techno-Set.
    fabi = _treffer([0.476, 0.340, 0.327, 0.438, 0.362, 0.324, 0.386, 0.322, 0.388, 0.373])
    assert nur_verankert(fabi) == []


def test_knappstes_eigenes_set_aus_dem_bestand_bleibt():
    # REC002.WAV: der niedrigste Hoechstwert unter allen echten eigenen Aufnahmen.
    rec002 = _treffer([0.547, 0.457])
    assert nur_verankert(rec002) == rec002


def test_verworfene_treffer_verschieben_keine_uebergaenge():
    # Der eigentliche Schaden war nicht der Name, sondern die Grenze:
    # merge_with_fingerprints schiebt ML-Zonen auf die Trefferzeit.
    zonen = [{"time": 600.0, "type": "blend_transition"}]
    fremd = _treffer([0.42, 0.38])
    ungefiltert = merge_with_fingerprints(zonen, transitions_from_matches(fremd), fremd)
    assert any(z.get("type") == "fingerprint" for z in ungefiltert)

    gefiltert = nur_verankert(fremd)
    bleibt = merge_with_fingerprints(zonen, transitions_from_matches(gefiltert), gefiltert)
    assert bleibt == zonen


def _rematch_ohne_audio(monkeypatch, alte_matches, neue_treffer):
    monkeypatch.setattr("app.library.manager.load_fingerprints", lambda: [{"id": "x"}])
    monkeypatch.setattr("app.audio.track_change_classifier.compute_chroma_matrix",
                        lambda w, sr: np.zeros((12, 10)))
    monkeypatch.setattr(rematch, "rematch_from_boundaries", lambda *a, **k: neue_treffer)
    report = {
        "library": {"matches": alte_matches},
        "setTransitions": [{"mid_sec": 290.0, "track_out": "A - Take Five",
                            "track_in": "A - Ditto", "detection": "fingerprint"},
                           {"mid_sec": 900.0, "track_out": None, "track_in": None,
                            "detection": None}],
    }
    feedback = {"verdicts": {"1": {"verdict": "correct", "midSec": 290.0}}}
    return rematch.apply_rematch(report, feedback, np.zeros(10), 22050)


def test_nachmatchen_holt_verworfene_treffer_nicht_zurueck(monkeypatch):
    alt = _treffer([0.36, 0.33])
    neu = [dict(t, title="Neu", score=0.41) for t in _treffer([0.41])]
    r = _rematch_ohne_audio(monkeypatch, alt, neu)
    assert r["library"]["matches"] == []
    assert r["rematch"]["matchesAfter"] == 0
    # Vorher meldete das Nachmatchen hier "1 hinzugefuegt".
    assert r["rematch"]["added"] == 0


def test_nachmatchen_raeumt_alte_namen_ab_wenn_nichts_bleibt(monkeypatch):
    r = _rematch_ohne_audio(monkeypatch, _treffer([0.36, 0.33]), [])
    t = r["setTransitions"][0]
    assert (t["track_out"], t["track_in"], t["detection"]) == (None, None, None)


def test_nachmatchen_in_verankertem_set_unveraendert(monkeypatch):
    alt = _treffer([0.62, 0.36])
    r = _rematch_ohne_audio(monkeypatch, alt, [])
    assert len(r["library"]["matches"]) == 2
    assert r["rematch"]["added"] == 0
