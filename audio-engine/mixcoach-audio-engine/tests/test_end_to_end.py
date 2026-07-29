"""End-to-End-Test: kompletter Durchlauf vom Upload bis zum Frontend-Result.

Erzeugt einen kuenstlichen ~4-Minuten-'Mix' (zwei Beat-Abschnitte mit
128 BPM und einem deutlichen Energie-Einbruch in der Set-Mitte) und schickt
ihn durch den echten /analyze/set Endpunkt - inklusive Phase-2-Analyse
(Beats, Phrasen, Tempo pro Segment, Uebergangs-Qualitaet).
"""

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

SR = 22050


def _synthetic_mix_wav() -> bytes:
    """Fake-Mix: Beat-Abschnitt A, Energie-Dip, Beat-Abschnitt B (alle 128 BPM)."""
    rng = np.random.default_rng(42)

    def beat_section(seconds, level):
        n = int(seconds * SR)
        signal = rng.normal(0, 0.05, n).astype(np.float32)
        beat_interval = int(SR * 60 / 128)
        for start in range(0, n - 2000, beat_interval):
            t = np.arange(2000) / SR
            kick = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 30)
            signal[start:start + 2000] += kick.astype(np.float32) * 2.0
        return signal * level

    # Uebergang in der SET-MITTE (~116s): Randzonen (<90s / letzte 60s)
    # werden vom Klassifikator bewusst nie als Trackwechsel gewertet.
    part_a = beat_section(110, 0.8)  # lauter erster Track
    dip = beat_section(12, 0.15)     # leiser Uebergang
    part_b = beat_section(100, 0.8)  # lauter zweiter Track

    waveform = np.concatenate([part_a, dip, part_b])

    buffer = io.BytesIO()
    sf.write(buffer, waveform, SR, format="WAV")
    return buffer.getvalue()


@pytest.fixture(scope="module")
def analysis_result():
    client = TestClient(app)
    wav_bytes = _synthetic_mix_wav()

    response = client.post(
        "/analyze/set",
        files={"file": ("synthetic_mix.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200, response.text
    return response.json()


def test_pipeline_returns_valid_result(analysis_result):
    result = analysis_result

    assert result["fileName"] == "synthetic_mix.wav"
    assert result["totalDurationSec"] == 222

    assert result["bpm"] is not None
    assert 60 <= result["bpm"] <= 200


def test_pipeline_detects_the_transition(analysis_result):
    """Der eingebaute Energie-Dip (bei ~110-122s) muss gefunden werden."""
    transitions = analysis_result["setTransitions"]

    assert len(transitions) >= 1
    assert any(95 <= t["mid_sec"] <= 140 for t in transitions), transitions


def test_transitions_have_phase2_measurements(analysis_result):
    """Jeder Uebergang traegt jetzt echte musikalische Messwerte."""
    transitions = analysis_result["setTransitions"]
    t = transitions[0]

    # Frontend-Vertrag (snake_case).
    for field in (
        "start_sec", "mid_sec", "end_sec", "bpm_before", "bpm_after",
        "phrase_alignment_score", "quality_score", "label", "feedback",
    ):
        assert field in t, f"Feld {field} fehlt"

    # Beide Segmente haben ein klares 128-BPM-Kick-Pattern.
    # Der Beat-Tracker darf leicht abweichen oder auf der Haelfte einrasten.
    for bpm in (t["bpm_before"], t["bpm_after"]):
        if bpm is not None:
            assert 55 <= bpm <= 200, f"BPM {bpm} unplausibel"

    assert t["label"] in {"smooth", "neutral", "rough"}
    assert isinstance(t["feedback"], str) and len(t["feedback"]) > 10

    if t["quality_score"] is not None:
        assert 0 <= t["quality_score"] <= 100


def test_no_fake_values_in_live_result(analysis_result):
    result = analysis_result

    # Weiterhin nicht gemessen -> null.
    assert result["scores"]["eq"] is None
    assert result["scores"]["creativity"] is None

    # Gemessene Scores sind im gueltigen Bereich (oder ehrlich null).
    for name in ("beatmatching", "timing", "musicality", "flow", "overall"):
        value = result["scores"][name]
        if value is not None:
            assert 0 <= value <= 100, f"{name}={value}"

    # Auf synthetischem Rauschen darf die Key-Erkennung nichts vorgaukeln:
    # entweder null oder ein echter Kandidat - aber niemals "Unknown"-String.
    assert result["key"] is None or isinstance(result["key"], str)
    assert result["key"] != "Unknown"


def test_energy_curve_reflects_the_dip(analysis_result):
    curve = analysis_result["energyCurve"]

    assert len(curve) > 10

    dip_values = [p["value"] for p in curve if 111 <= p["t"] <= 121]
    loud_values = [p["value"] for p in curve if p["t"] < 105]

    assert dip_values, "Keine Kurvenpunkte im Dip-Bereich"
    assert min(dip_values) < (sum(loud_values) / len(loud_values)) * 0.5


def test_unsupported_format_returns_400():
    client = TestClient(app)

    response = client.post(
        "/analyze/set",
        files={"file": ("notes.txt", b"kein audio", "text/plain")},
    )

    assert response.status_code == 400
