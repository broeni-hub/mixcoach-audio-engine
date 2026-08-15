import json
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from app.api.analysis_mapper import map_set_analysis_to_frontend_result
from app.audio.loader import load_audio_file
from app.audio.set_analyzer import analyze_set
from app.jobs import job_manager

APP_VERSION = "0.3.0"

SUPPORTED_SUFFIXES = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"}

app = FastAPI(title="MixCoach Audio Engine", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zweite, blinde Labelrunde (K1) - eigener Router, eigene Seite, damit die
# bestehenden Endpoints und Frontend-Seiten unberuehrt bleiben. Siehe
# app/api/relabel.py fuer die Blindheits-Anforderungen.
from app.api.relabel import router as relabel_router  # noqa: E402

app.include_router(relabel_router)

# Blinder Vergleich alte Vorlage / belegte Uebung (J7) - dieselbe Bauart und
# derselbe Grund wie oben. Ebenfalls ein lokales Messwerkzeug ohne Sitzung:
# bringt F2 die Auth-Pflicht, gehoert dieser Router in dieselbe Ausnahme wie
# der Relabel-Router.
from app.api.uebungen_bewertung import router as uebungen_bewertung_router  # noqa: E402

app.include_router(uebungen_bewertung_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mixcoach-audio-engine",
        "version": APP_VERSION,
    }


# ---------------------------------------------------------------------
# Asynchroner Job-Flow (empfohlen): Upload -> jobId -> Polling -> Result.
# Vertrag entspricht exakt dem remoteProvider des Frontends.
# ---------------------------------------------------------------------


@app.post("/analysis/jobs")
async def create_analysis_job(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {suffix or '(keine Endung)'}",
        )

    # Datei auf Platte streamen (Sets sind hunderte MB - nicht in den RAM).
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        size = tmp.tell()
    finally:
        tmp.close()

    if size == 0:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Leere Datei.")

    job = job_manager.create_job(
        temp_path=tmp.name,
        file_name=file.filename,
        file_size=size,
    )

    return {"jobId": job.job_id}


@app.get("/analysis/jobs/{job_id}")
def get_analysis_job(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return job.to_dto()


@app.get("/analysis/jobs")
def list_analysis_jobs():
    return [job.to_dto() for job in job_manager.list_jobs()]


@app.post("/analysis/jobs/{job_id}/retry")
def retry_analysis_job(job_id: str):
    job = job_manager.retry_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=410,
            detail="Retry nicht moeglich - Originaldatei liegt nicht mehr vor. Bitte neu hochladen.",
        )
    return {"jobId": job.job_id}


@app.get("/analysis")
def list_analyses():
    """Alle serverseitig gespeicherten Analysen (Kurzform) - damit das
    Frontend Reports wiederfinden kann, die im Browser-Store fehlen (z.B.
    weil die App waehrend eines Laufs auf den Browser-Fallback gewechselt
    ist, waehrend die Engine serverseitig fertig analysiert hat - real
    passiert bei MixCoach2.WAV, 2026-07-17: Engine-Report mit 10
    Uebergaengen existierte, die App zeigte den schwachen Fallback-Report)."""
    from app.jobs.job_manager import RESULTS_DIR

    entries = []
    if RESULTS_DIR.exists():
        for path in RESULTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict) or not data.get("id"):
                continue
            entries.append({
                "id": data.get("id"),
                "fileName": data.get("fileName"),
                "createdAt": data.get("createdAt"),
                "transitions": len(data.get("setTransitions") or []),
                "libraryMatches": len((data.get("library") or {}).get("matches") or []),
            })
    entries.sort(key=lambda e: e.get("createdAt") or "", reverse=True)
    return {"analyses": entries}


@app.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    result = job_manager.get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return result


# ---------------------------------------------------------------------
# Ground-Truth-Feedback: DJs bestaetigen/korrigieren erkannte Uebergaenge
# direkt im Report. Jede Rueckmeldung verbessert die Erkennungs-Engine.
# ---------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from app.jobs import feedback_store


class VerdictPayload(BaseModel):
    index: int
    midSec: float
    verdict: Literal["correct", "not_a_transition", "timing_off"]
    # Bei "timing_off": die vom DJ angesteuerte echte Startstelle.
    correctedSec: Optional[float] = None


class MissedPayload(BaseModel):
    sec: float = Field(ge=0)


@app.get("/analysis/{analysis_id}/feedback")
def get_feedback(analysis_id: str):
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return feedback_store.load_feedback(analysis_id)


@app.post("/analysis/{analysis_id}/feedback/verdict")
def post_verdict(analysis_id: str, payload: VerdictPayload):
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return feedback_store.save_verdict(
        analysis_id, payload.index, payload.midSec, payload.verdict,
        corrected_sec=payload.correctedSec,
    )


@app.post("/analysis/{analysis_id}/feedback/missed")
def post_missed(analysis_id: str, payload: MissedPayload):
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return feedback_store.save_missed(analysis_id, payload.sec)


@app.post("/analysis/{analysis_id}/rematch")
def post_rematch(analysis_id: str):
    """Track-Erkennung anhand der DJ-Korrekturen neu bestimmen (Vision-
    Datenschleife). Nutzt die korrigierten Uebergangsgrenzen als exakte
    Segmentquelle - holt Tracks nach, die der automatische Lauf an
    unsauberen Grenzen verfehlte (siehe app/audio/rematch.py). Aktualisiert
    den gespeicherten Report (library.matches + Tracknamen der Uebergaenge)
    und liefert ihn zurueck."""
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")

    result = job_manager.get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")

    audio_path = None
    for suffix in AUDIO_MIME:
        candidate = job_manager.RESULTS_DIR / f"{analysis_id}{suffix}"
        if candidate.exists():
            audio_path = candidate
            break
    if audio_path is None:
        raise HTTPException(status_code=404, detail="Original-Audio fehlt - Nachmatchen nicht moeglich.")

    import librosa

    from app.audio.rematch import apply_rematch

    feedback = feedback_store.load_feedback(analysis_id)
    # Ganzes Set laden (load_audio_file kappt bei 120s - fuer die
    # Segment-Grenzen brauchen wir die volle Laenge).
    waveform, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    updated = apply_rematch(result, feedback, waveform, sr)

    (job_manager.RESULTS_DIR / f"{analysis_id}.json").write_text(
        json.dumps(updated), encoding="utf-8",
    )
    job_manager._results[analysis_id] = updated
    return updated


AUDIO_MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
}

# Nur UUID-artige IDs zulassen - verhindert Pfad-Tricks wie "../".
_SAFE_ID = re.compile(r"^[a-fA-F0-9-]{8,64}$")


@app.get("/analysis/{analysis_id}/audio")
def get_analysis_audio(analysis_id: str, range_header: str | None = Header(None, alias="Range")):
    """Original-Audio der Analyse - mit HTTP-Range-Support, damit der
    Browser-Player an jede Stelle spulen kann, ohne alles zu laden."""
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Audio nicht gefunden.")

    audio_file = None
    for suffix, mime in AUDIO_MIME.items():
        candidate = job_manager.RESULTS_DIR / f"{analysis_id}{suffix}"
        if candidate.exists():
            audio_file = (candidate, mime)
            break

    if audio_file is None:
        raise HTTPException(status_code=404, detail="Audio nicht gefunden.")

    path, mime = audio_file
    file_size = path.stat().st_size

    def stream(start: int, end: int, chunk: int = 1024 * 512):
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    common = {"Accept-Ranges": "bytes", "Content-Type": mime}

    if range_header:
        match = re.match(r"bytes=(\d*)-(\d*)", range_header)
        if not match:
            raise HTTPException(status_code=416, detail="Ungueltiger Range-Header.")
        start = int(match.group(1)) if match.group(1) else 0
        end = int(match.group(2)) if match.group(2) else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            return Response(
                status_code=416,
                headers={**common, "Content-Range": f"bytes */{file_size}"},
            )
        return StreamingResponse(
            stream(start, end),
            status_code=206,
            headers={
                **common,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(end - start + 1),
            },
        )

    return StreamingResponse(
        stream(0, file_size - 1),
        headers={**common, "Content-Length": str(file_size)},
    )


@app.delete("/analysis/{analysis_id}")
def delete_analysis(analysis_id: str):
    """Loescht eine Analyse nicht hart, sondern archiviert sie (siehe
    job_manager.delete_result) - der DJ kann sie im Frontend nicht mehr
    sehen, aber die Daten bleiben fuer Retrain/Nachvollziehbarkeit da."""
    if not _SAFE_ID.match(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    if not job_manager.delete_result(analysis_id):
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return {"ok": True}


# ---------------------------------------------------------------------
# Synchroner Endpunkt (fuer kurze Dateien und Tests). Bei langen Sets
# den Job-Flow verwenden - dieser Request blockiert minutenlang.
# ---------------------------------------------------------------------


@app.post("/analyze/set")
async def analyze_set_endpoint(file: UploadFile = File(...)):
    try:
        audio = load_audio_file(
            file=file.file,
            filename=file.filename,
            max_duration_seconds=7200,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    analysis = analyze_set(audio)

    return map_set_analysis_to_frontend_result(
        filename=file.filename,
        analysis=analysis,
    )


# ---------------------------------------------------------------------
# Track-Library (rekordbox-Import) fuer die Fingerprint-Erkennung.
# ---------------------------------------------------------------------

from app.library import manager as library_manager


@app.post("/library/rekordbox")
async def import_rekordbox(file: UploadFile = File(...)):
    data = await file.read()
    try:
        tracks = library_manager.parse_rekordbox_xml(data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Keine gueltige rekordbox-XML-Datei.")
    if not tracks:
        raise HTTPException(status_code=400, detail="Keine Tracks mit Dateipfad in der XML gefunden.")
    if not library_manager.start_import(tracks):
        raise HTTPException(status_code=409, detail="Ein Import laeuft bereits.")
    return {"found": len(tracks)}


@app.get("/library/status")
def library_status():
    return library_manager.get_status()


@app.get("/library/tracks")
def library_tracks():
    tracks = library_manager.list_tracks()
    return {"count": len(tracks), "tracks": tracks}


# ---------------------------------------------------------------------
# Coach-Profil: Trends, Muster und Uebungen ueber alle Sets.
# ---------------------------------------------------------------------

from app.coach.profile import build_profile


@app.get("/coach/profile")
def coach_profile(lang: str = "de"):
    return build_profile(lang if lang in ("de", "en") else "de")


# ---------------------------------------------------------------------
# Retrain-Automatik: Fortschritt bis zum naechsten automatischen Modell-
# Training (jedes Feedback bringt den DJ dem naeher). Nur Status - der
# eigentliche (rechenintensive) Lauf laeuft ueber MixCoach-Retrain.bat.
# ---------------------------------------------------------------------


@app.get("/calibration/status")
def calibration_status():
    from app.calibration.auto_retrain import count_new_sets

    return count_new_sets()
