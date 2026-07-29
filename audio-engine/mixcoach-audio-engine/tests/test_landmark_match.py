"""Tests fuer das Landmark-Fingerprinting (app/audio/landmark_match.py).

Prueft die Kern-Invarianten ohne echte Musik: ein Track matcht sich selbst
mit klarem Offset-Peak, ein zeitversetzter Ausschnitt findet den richtigen
Versatz, und unabhaengiges Rauschen erzeugt KEINEN kohaerenten Peak.
"""

import numpy as np

from app.audio import landmark_match as lm


def _tone_sequence(seed: int, seconds: float = 30.0, sr: int = lm.SR) -> np.ndarray:
    """Reproduzierbares, spektral strukturiertes Signal (wechselnde Toene)
    als Stellvertreter fuer einen Track - erzeugt echte Konstellations-Peaks."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    # mehrere zeitlich wandernde Sinus-Partialtoene -> markante Peaks
    for _ in range(6):
        f0 = rng.uniform(200, 4000)
        start = rng.uniform(0, seconds * 0.7)
        dur = rng.uniform(1.0, 4.0)
        mask = (t >= start) & (t < start + dur)
        sig[mask] += np.sin(2 * np.pi * f0 * t[mask])
    return sig + 0.01 * rng.standard_normal(n)


def test_self_match_has_strong_peak():
    sig = _tone_sequence(seed=1)
    fp = lm.fingerprint(sig)
    result = lm.match(fp, fp)
    assert result["peak"] >= 20
    assert abs(result["offset_frames"]) <= lm.OFFSET_BIN


def test_shifted_excerpt_recovers_offset():
    sig = _tone_sequence(seed=2, seconds=40.0)
    full_fp = lm.fingerprint(sig)
    # Ausschnitt ab 10s als "Mix" -> Track sollte bei -10s Versatz einrasten
    shift_samples = int(10.0 * lm.SR)
    mix_fp = lm.fingerprint(sig[shift_samples:])
    result = lm.match(mix_fp, full_fp)
    assert result["peak"] >= 15
    got = lm.frames_to_seconds(result["offset_frames"])
    assert abs(got + 10.0) < 1.0  # Track startet 10s VOR dem Mix-Anfang


def test_unrelated_signals_no_coherent_peak():
    a = lm.fingerprint(_tone_sequence(seed=3))
    b = lm.fingerprint(_tone_sequence(seed=999))
    self_peak = lm.match(a, a)["peak"]
    cross_peak = lm.match(a, b)["peak"]
    # fremdes Signal: deutlich schwaecherer kohaerenter Peak als Selbst-Match
    assert cross_peak < self_peak * 0.5


def test_pack_roundtrip_within_bits():
    # Hash-Packung darf die Felder nicht ueberlaufen lassen.
    h = lm._pack(2047, 1000, 30)
    assert 0 <= h < (1 << 27)


def _index_entry(sig: np.ndarray, dur: float, tid: str) -> dict:
    fp = lm.fingerprint(sig)
    return {"hashes": fp["hashes"], "frames": fp["frames"], "duration": dur,
            "path": f"{tid}.mp3", "title": tid, "artist": "x"}


def test_gap_fill_finds_track_in_uncovered_region():
    # Set = Track A (0-40s) + Track B (40-80s). Chroma erkannte NUR A;
    # Landmark soll B in der Luecke 40-80s finden, den Fremd-Track NICHT.
    track_b = _tone_sequence(seed=11, seconds=40.0)
    mix = np.concatenate([_tone_sequence(seed=10, seconds=40.0), track_b])
    mix_fp = lm.fingerprint(mix)
    index = {"B": _index_entry(track_b, 40.0, "B"),
             "foreign": _index_entry(_tone_sequence(seed=777, seconds=40.0), 40.0, "foreign")}
    chroma = [{"start": 0.0, "end": 40.0, "path": "A.mp3", "score": 0.9}]

    # Schwellen fuer den Test lokal senken (Testsignale sind kuerzer/aermer
    # an Hashes als echte Tracks -> absolute Peaks kleiner).
    old = (lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS)
    lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = 15, 3.0, 20.0
    try:
        filled = lm.gap_fill(mix_fp, index, chroma, set_len_seconds=80.0)
    finally:
        lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = old

    paths = [m["path"] for m in filled]
    assert "B.mp3" in paths
    assert "foreign.mp3" not in paths
    b = next(m for m in filled if m["path"] == "B.mp3")
    assert abs(b["start"] - 40.0) < 5.0
    assert b["source"] == "landmark"


def test_gap_fill_skips_region_already_covered_by_chroma():
    # Deckt Chroma denselben Bereich schon ab, fuellt Landmark NICHT nach.
    track_b = _tone_sequence(seed=12, seconds=40.0)
    mix = np.concatenate([_tone_sequence(seed=13, seconds=40.0), track_b])
    mix_fp = lm.fingerprint(mix)
    index = {"B": _index_entry(track_b, 40.0, "B")}
    chroma = [{"start": 0.0, "end": 40.0, "path": "A.mp3", "score": 0.9},
              {"start": 40.0, "end": 80.0, "path": "B.mp3", "score": 0.9}]
    old_peak, old_dom = lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE
    lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE = 15, 3.0
    try:
        filled = lm.gap_fill(mix_fp, index, chroma, set_len_seconds=80.0)
    finally:
        lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE = old_peak, old_dom
    assert filled == []


def test_gap_fill_finds_track_longer_than_the_gap_itself():
    # Tracks werden im Set nur TEILWEISE gespielt (dieselbe Annahme wie in
    # library_match.py) - ein indizierter Track, dessen VOLLE Dauer laenger
    # ist als die Luecke, darf trotzdem gefunden werden, wenn er dort nur
    # angespielt wurde. Ein frueherer "zu lang -> ueberspringen"-Vorfilter
    # hat genau das faelschlich verworfen (Boratto-Fall: Track ~400s,
    # gespielter Ausschnitt nur 262s, 2026-07-16) und wurde entfernt.
    track_b = _tone_sequence(seed=14, seconds=40.0)
    mix = np.concatenate([_tone_sequence(seed=15, seconds=40.0), track_b])
    mix_fp = lm.fingerprint(mix)
    # gespeicherte Dauer (1000s) ist BEWUSST viel laenger als die Luecke
    # (40s) - simuliert einen Track, der nur angespielt wurde.
    index = {"B": _index_entry(track_b, 1000.0, "B")}
    chroma = [{"start": 0.0, "end": 40.0, "path": "A.mp3", "score": 0.9}]
    old = (lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS)
    lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = 15, 3.0, 20.0
    try:
        filled = lm.gap_fill(mix_fp, index, chroma, set_len_seconds=80.0)
    finally:
        lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = old
    assert [m["path"] for m in filled] == ["B.mp3"]


def test_gap_fill_skips_track_shorter_than_gap_minimum():
    # Ein Track, der selbst voll gespielt kuerzer als GAP_MIN_SECONDS waere,
    # kann NIE einen gueltigen Treffer liefern - das ist die einzige sichere
    # Dauer-basierte Kostenschranke (untere, nicht obere Grenze).
    track_b = _tone_sequence(seed=18, seconds=40.0)
    mix = np.concatenate([_tone_sequence(seed=19, seconds=40.0), track_b])
    mix_fp = lm.fingerprint(mix)
    index = {"B": _index_entry(track_b, 5.0, "B")}  # kuerzer als GAP_MIN_SECONDS
    chroma = [{"start": 0.0, "end": 40.0, "path": "A.mp3", "score": 0.9}]
    old = (lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS)
    lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = 15, 3.0, 20.0
    try:
        filled = lm.gap_fill(mix_fp, index, chroma, set_len_seconds=80.0)
    finally:
        lm.LANDMARK_MIN_PEAK, lm.LANDMARK_MIN_DOMINANCE, lm.GAP_MIN_SECONDS = old
    assert filled == []


def test_gap_fill_returns_early_when_fully_covered():
    # Keine Luecke >= GAP_MIN_SECONDS -> gar kein match()-Aufruf noetig.
    mix_fp = lm.fingerprint(_tone_sequence(seed=16, seconds=40.0))
    index = {"B": _index_entry(_tone_sequence(seed=17, seconds=10.0), 10.0, "B")}
    chroma = [{"start": 0.0, "end": 40.0, "path": "A.mp3", "score": 0.9}]
    assert lm.gap_fill(mix_fp, index, chroma, set_len_seconds=40.0) == []
