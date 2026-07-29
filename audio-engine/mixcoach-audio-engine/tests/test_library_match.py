"""Tests fuer Library-Fingerprinting: rekordbox-Import + Track-Matching."""

import numpy as np
import pytest

from app.audio.library_match import (
    SCREEN_MIN_LIBRARY,
    SCREEN_TEMPLATE_FRAMES,
    _prefilter_candidates,
    decimate_chroma,
    match_library,
    merge_with_fingerprints,
    transitions_from_matches,
)
from app.library.manager import parse_rekordbox_xml

FINE_FPS = 22050 / 512


def _fine_chroma(seconds, rng, wobble=128):
    """Zeitlich korrelierte Zufalls-Harmonik in feiner Aufloesung."""
    n = int(seconds * FINE_FPS)
    base = rng.random((12, n // wobble + 2))
    x = np.linspace(0, base.shape[1] - 1, n)
    return np.vstack([np.interp(x, np.arange(base.shape[1]), base[b]) for b in range(12)])


@pytest.fixture(scope="module")
def scenario():
    """Set: Track A (0-300s) blendet ab 280s in Track B (280-580s)."""
    rng = np.random.default_rng(7)
    fa, fb, fc = _fine_chroma(300, rng), _fine_chroma(300, rng), _fine_chroma(300, rng)
    setc = np.zeros((12, int(580 * FINE_FPS)))
    setc[:, : fa.shape[1]] += fa
    b0 = int(280 * FINE_FPS)
    setc[:, b0: b0 + fb.shape[1]] += 0.9 * fb
    setc += 0.2 * rng.random(setc.shape)
    library = [
        {"id": "A", "title": "Alpha", "artist": "DJ X", "chroma": decimate_chroma(fa)},
        {"id": "B", "title": "Beta", "artist": "DJ Y", "chroma": decimate_chroma(fb)},
        {"id": "C", "title": "Gamma", "artist": "DJ Z", "chroma": decimate_chroma(fc)},
    ]
    return setc, library


def test_matching_findet_gespielte_tracks_exakt(scenario):
    setc, library = scenario
    matches = match_library(setc, library, 22050, 512)

    assert [m["id"] for m in matches] == ["A", "B"], matches
    assert abs(matches[0]["start"] - 0) < 15
    assert abs(matches[1]["start"] - 280) < 15


def test_nicht_gespielter_track_wird_abgelehnt(scenario):
    setc, library = scenario
    matches = match_library(setc, library, 22050, 512)
    assert all(m["id"] != "C" for m in matches)


def test_uebergang_aus_spannen_abgeleitet(scenario):
    setc, library = scenario
    transitions = transitions_from_matches(match_library(setc, library, 22050, 512))

    assert len(transitions) == 1
    t = transitions[0]
    assert abs(t["blend_start"] - 280) < 15
    assert t["from_title"] == "Alpha" and t["to_title"] == "Beta"


def test_matching_ueberlebt_tempo_pitch():
    """Track im Set um +4% gepitcht -> Stretch-Suche muss ihn finden."""
    rng = np.random.default_rng(3)
    fa = _fine_chroma(300, rng)
    n = fa.shape[1]
    stretched_n = int(n / 1.04)
    x = np.linspace(0, n - 1, stretched_n)
    fa_pitched = np.vstack([np.interp(x, np.arange(n), fa[b]) for b in range(12)])

    setc = np.zeros((12, int(400 * FINE_FPS)))
    off = int(50 * FINE_FPS)
    setc[:, off: off + stretched_n] += fa_pitched
    setc += 0.2 * rng.random(setc.shape)

    matches = match_library(setc, [{"id": "A", "title": "Alpha", "artist": "",
                                    "chroma": decimate_chroma(fa)}], 22050, 512)
    assert len(matches) == 1
    assert abs(matches[0]["start"] - 50) < 15
    assert matches[0]["stretch"] != 1.0


def test_merge_korrigiert_ml_und_entfernt_fehlalarme():
    matches = [
        {"start": 0.0, "end": 300.0, "score": 0.9},
        {"start": 280.0, "end": 580.0, "score": 0.9},
    ]
    fp_transitions = [{"blend_start": 280.0, "mid": 292.0, "blend_end": 304.0,
                       "from_title": "Alpha", "from_artist": "", "to_title": "Beta",
                       "to_artist": "", "confidence": 0.9}]
    ml_zones = [
        {"time": 310.0, "blend_start": 300.0, "score": 5.0},  # nahe dran -> korrigieren
        {"time": 150.0, "blend_start": 140.0, "score": 4.0},  # mitten in Track A -> raus
    ]
    merged = merge_with_fingerprints(ml_zones, fp_transitions, matches)

    assert len(merged) == 1
    z = merged[0]
    assert z["time"] == 292.0 and z["blend_start"] == 280.0
    assert z["type"] == "fingerprint" and z["to_title"] == "Beta"


def test_ml_zone_in_luecke_bleibt():
    matches = [{"start": 0.0, "end": 300.0, "score": 0.9},
               {"start": 700.0, "end": 1000.0, "score": 0.9}]
    ml_zones = [{"time": 500.0, "blend_start": 490.0}]  # unerkannter Abschnitt
    merged = merge_with_fingerprints(ml_zones, [], matches)
    assert len(merged) == 1 and merged[0]["time"] == 500.0


REKORDBOX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="2">
    <TRACK TrackID="1" Name="Nachtfahrt" Artist="Basti B"
           TotalTime="372" AverageBpm="126.00" Tonality="8A"
           Location="file://localhost/C:/Users/Sebro/Music/Techno%20Neu/nachtfahrt.mp3"/>
    <TRACK TrackID="2" Name="Ohne Pfad" Artist="X"/>
  </COLLECTION>
</DJ_PLAYLISTS>"""


def test_prefilter_behaelt_nicht_screenbare_tracks():
    """Ein Track, der zu kurz fuer den Screen-Vorfilter ist (-> inf), muss
    trotz grosser Library IMMER durchgelassen werden ('zu kurz -> immer voll
    pruefen'). Frueher schob der Minus-Sortierschluessel genau diese Tracks
    ans Ende und schnitt sie weg (Vorzeichen-Bug, 2026-07-14)."""
    rng = np.random.default_rng(11)
    # coarse-Chroma direkt bauen (12 x N). Der Screen braucht nach der
    # SCREEN_POOL-Verdichtung >= SCREEN_TEMPLATE_FRAMES+6 Frames; ein sehr
    # kurzer Track unterschreitet das und ist damit "nicht screenbar".
    short_coarse = rng.random((12, 8))
    short_coarse /= np.linalg.norm(short_coarse, axis=0, keepdims=True)
    short = {"id": "SHORT", "title": "Kurz", "artist": "", "chroma": short_coarse}

    long_lib = []
    for i in range(SCREEN_MIN_LIBRARY + 50):
        c = rng.random((12, SCREEN_TEMPLATE_FRAMES * 12))
        c /= np.linalg.norm(c, axis=0, keepdims=True)
        long_lib.append({"id": f"L{i}", "title": f"Lang {i}", "artist": "", "chroma": c})

    set_coarse = rng.random((12, SCREEN_TEMPLATE_FRAMES * 20))
    set_coarse /= np.linalg.norm(set_coarse, axis=0, keepdims=True)

    kept = _prefilter_candidates(set_coarse, long_lib + [short])
    assert any(fp["id"] == "SHORT" for fp in kept), "nicht-screenbarer Track wurde faelschlich verworfen"


def test_prefilter_inaktiv_bei_kleiner_library():
    """Unter SCREEN_MIN_LIBRARY bleibt der volle Pool erhalten (kein Filter)."""
    rng = np.random.default_rng(5)
    lib = [{"id": str(i), "chroma": rng.random((12, 30))} for i in range(10)]
    set_coarse = rng.random((12, 200))
    assert len(_prefilter_candidates(set_coarse, lib)) == len(lib)


def test_library_manager_teilt_datenstamm_mit_app_paths():
    """Der Library-Manager muss denselben Datenstamm nutzen wie der Rest der
    App (app.paths.DATA_ROOT) - sonst sucht die Library ihre Fingerprints an
    einem anderen Ort als analysis_results/ground_truth liegen."""
    from app.paths import DATA_ROOT
    from app.library import manager

    assert manager.LIBRARY_DIR == DATA_ROOT / "library"
    assert manager.INDEX_PATH == DATA_ROOT / "library" / "index.json"


def test_rekordbox_xml_parsing():
    tracks = parse_rekordbox_xml(REKORDBOX_XML.encode("utf-8"))

    assert len(tracks) == 1  # Eintrag ohne Location wird ignoriert
    t = tracks[0]
    assert t["title"] == "Nachtfahrt"
    assert t["artist"] == "Basti B"
    assert t["bpm"] == 126.0
    assert t["key"] == "8A"
    assert t["path"] == "C:/Users/Sebro/Music/Techno Neu/nachtfahrt.mp3"


def test_library_endpoints_ohne_import():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    status = client.get("/library/status")
    assert status.status_code == 200
    assert status.json()["running"] is False

    response = client.post(
        "/library/rekordbox",
        files={"file": ("kaputt.xml", b"<das ist kein xml", "text/xml")},
    )
    assert response.status_code == 400
