"""Tests fuer den asynchronen Job-Flow (Upload -> Polling -> Result)."""

import time

from fastapi.testclient import TestClient

from app.main import app
from tests.test_end_to_end import _synthetic_mix_wav

client = TestClient(app)


def _wait_for_job(job_id: str, timeout_seconds: float = 120.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        dto = client.get(f"/analysis/jobs/{job_id}").json()
        if dto["status"] in {"completed", "failed"}:
            return dto
        time.sleep(0.5)
    raise TimeoutError("Job wurde nicht fertig.")


def test_job_lifecycle_completes():
    wav = _synthetic_mix_wav()

    response = client.post(
        "/analysis/jobs",
        files={"file": ("synthetic_mix.wav", wav, "audio/wav")},
    )
    assert response.status_code == 200
    job_id = response.json()["jobId"]

    # Sofortiger Status-Abruf muss funktionieren (queued oder running).
    dto = client.get(f"/analysis/jobs/{job_id}").json()
    assert dto["status"] in {"queued", "running", "completed"}
    assert dto["fileName"] == "synthetic_mix.wav"
    assert dto["fileSize"] > 1000

    final = _wait_for_job(job_id)
    assert final["status"] == "completed", final.get("errorMessage")
    assert final["progress"] == 100
    assert final["analysisId"]

    # Ergebnis abholen - muss dem Frontend-Vertrag entsprechen.
    result = client.get(f"/analysis/{final['analysisId']}")
    assert result.status_code == 200
    payload = result.json()
    assert payload["fileName"] == "synthetic_mix.wav"
    assert "scores" in payload and "setTransitions" in payload
    assert payload["scores"]["eq"] is None  # ehrlich bleibt ehrlich


def test_job_reports_progress_stages():
    """Waehrend der Analyse muessen sinnvolle Stages gemeldet werden."""
    wav = _synthetic_mix_wav()
    job_id = client.post(
        "/analysis/jobs",
        files={"file": ("mix.wav", wav, "audio/wav")},
    ).json()["jobId"]

    seen_stages = set()
    deadline = time.time() + 120
    while time.time() < deadline:
        dto = client.get(f"/analysis/jobs/{job_id}").json()
        seen_stages.add(dto["stage"])
        if dto["status"] in {"completed", "failed"}:
            break
        time.sleep(0.2)

    assert dto["status"] == "completed", dto.get("errorMessage")
    # Mindestens Anfang und Ende der Pipeline muessen sichtbar gewesen sein.
    assert "completed" in seen_stages
    valid = {
        "queued", "preprocessing", "feature_extraction", "transition_detection",
        "beatgrid_detection", "phrase_detection", "key_detection",
        "transition_analysis", "coaching_generation", "report", "completed",
    }
    assert seen_stages <= valid, seen_stages


def test_corrupt_file_fails_cleanly():
    """Kaputte Datei -> Job failed mit Fehlermeldung, kein haengender Job."""
    response = client.post(
        "/analysis/jobs",
        files={"file": ("kaputt.wav", b"das ist kein audio", "audio/wav")},
    )
    assert response.status_code == 200  # Job wird angenommen...
    job_id = response.json()["jobId"]

    final = _wait_for_job(job_id, timeout_seconds=30)
    assert final["status"] == "failed"  # ...und scheitert sauber.
    assert final["errorMessage"]


def test_unsupported_format_rejected_immediately():
    response = client.post(
        "/analysis/jobs",
        files={"file": ("notizen.txt", b"text", "text/plain")},
    )
    assert response.status_code == 400


def test_unknown_job_and_analysis_return_404():
    assert client.get("/analysis/jobs/gibtsnicht").status_code == 404
    assert client.get("/analysis/gibtsnicht").status_code == 404


def test_completed_job_serves_audio_with_range_support():
    """Der DJ muss die bewerteten Stellen nachhoeren koennen:
    Audio abrufbar, Spulen (Range-Requests) funktioniert."""
    wav = _synthetic_mix_wav()
    job_id = client.post(
        "/analysis/jobs",
        files={"file": ("mix.wav", wav, "audio/wav")},
    ).json()["jobId"]

    final = _wait_for_job(job_id)
    assert final["status"] == "completed", final.get("errorMessage")
    analysis_id = final["analysisId"]

    # Result verweist auf das Audio.
    result = client.get(f"/analysis/{analysis_id}").json()
    assert result["audioPath"] == f"/analysis/{analysis_id}/audio"

    # Komplettes Audio abrufbar.
    full = client.get(f"/analysis/{analysis_id}/audio")
    assert full.status_code == 200
    assert full.headers["content-type"] == "audio/wav"
    assert full.headers["accept-ranges"] == "bytes"
    assert len(full.content) == len(wav)

    # Range-Request (Spulen): nur die angeforderten 100 Bytes.
    partial = client.get(
        f"/analysis/{analysis_id}/audio",
        headers={"Range": "bytes=1000-1099"},
    )
    assert partial.status_code == 206
    assert len(partial.content) == 100
    assert partial.content == wav[1000:1100]
    assert partial.headers["content-range"] == f"bytes 1000-1099/{len(wav)}"

    # Unsinniger Range -> 416, kein Crash.
    bad = client.get(
        f"/analysis/{analysis_id}/audio",
        headers={"Range": f"bytes={len(wav)+999}-"},
    )
    assert bad.status_code == 416


def test_audio_for_unknown_analysis_is_404():
    assert client.get("/analysis/abcdef1234/audio").status_code == 404
    # Pfad-Trick darf nicht funktionieren:
    assert client.get("/analysis/..%2F..%2Fetc/audio").status_code in {404, 422}
