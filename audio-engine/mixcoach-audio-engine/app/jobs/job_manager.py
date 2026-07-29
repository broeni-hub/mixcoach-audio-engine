"""Asynchrone Analyse-Jobs.

Ein 30-Minuten-Set braucht 2-3 Minuten Analyse - viel zu lang fuer einen
synchronen HTTP-Request. Ablauf:

    POST /analysis/jobs          -> Datei wird angenommen, Job startet im
                                    Hintergrund-Thread, jobId kommt sofort
    GET  /analysis/jobs/{jobId}  -> Status + Fortschritt (Frontend pollt)
    GET  /analysis/{analysisId}  -> fertiges Ergebnis

Der Job-Store ist in-memory; fertige Ergebnisse werden zusaetzlich als
JSON auf Platte gelegt (ueberleben einen Server-Neustart).
Stage-Namen entsprechen exakt dem PipelineStage-Enum des Frontends.

Ablageort: siehe app/paths.py - ein gemeinsamer Datenstamm fuer
Ergebnisse UND Ground Truth, verankert am Projektordner (Override
per MIXCOACH_DATA_DIR).
"""

import json
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from app.audio.loader import load_audio_file
from app.audio.set_analyzer import analyze_set
from app.api.analysis_mapper import map_set_analysis_to_frontend_result
from app.paths import RESULTS_DIR

# Ein Worker: Audio-Analyse ist CPU-schwer; parallele Analysen wuerden
# sich gegenseitig ausbremsen. Weitere Jobs warten in der Queue.
_executor = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()


@dataclass
class Job:
    job_id: str
    file_name: str
    file_size: int
    temp_path: str
    status: str = "queued"          # queued | running | completed | failed
    stage: str = "queued"
    progress: int = 0
    stage_progress: int = 0
    analysis_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: float = field(default_factory=lambda: time.time())
    finished_at: Optional[float] = None
    attempts: int = 1

    def to_dto(self) -> Dict:
        elapsed = time.time() - self.started_at
        remaining = None
        if self.status == "running" and 5 < self.progress < 100:
            remaining = max(1, round(elapsed * (100 - self.progress) / self.progress))
        return {
            "jobId": self.job_id,
            "analysisId": self.analysis_id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "stageProgress": self.stage_progress,
            "startedAt": int(self.started_at * 1000),
            "finishedAt": int(self.finished_at * 1000) if self.finished_at else None,
            "errorMessage": self.error_message,
            "estimatedRemainingSeconds": remaining,
            "fileName": self.file_name,
            "fileSize": self.file_size,
            "attempts": self.attempts,
        }


_jobs: Dict[str, Job] = {}
_results: Dict[str, Dict] = {}


def create_job(temp_path: str, file_name: str, file_size: int) -> Job:
    job = Job(
        job_id=str(uuid.uuid4()),
        file_name=file_name,
        file_size=file_size,
        temp_path=temp_path,
    )
    with _lock:
        _jobs[job.job_id] = job
    _executor.submit(_run_job, job.job_id)
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def list_jobs() -> list:
    return sorted(_jobs.values(), key=lambda j: -j.started_at)


def get_result(analysis_id: str) -> Optional[Dict]:
    result = _results.get(analysis_id)
    if result is not None:
        return result
    # Fallback: von Platte (nach Server-Neustart)
    path = RESULTS_DIR / f"{analysis_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def delete_result(analysis_id: str) -> bool:
    """Archiviert eine Analyse statt sie hart zu loeschen.

    Verschiebt JSON + evtl. Audio-Kopie nach RESULTS_DIR/archived/, damit
    export_labels_v3.py sie beim naechsten Lauf nicht mehr einliest, aber
    nichts endgueltig verloren geht. False, wenn nichts zu verschieben war.
    """
    _results.pop(analysis_id, None)
    archived_dir = RESULTS_DIR / "archived"
    archived_dir.mkdir(exist_ok=True)

    moved = False
    for path in RESULTS_DIR.glob(f"{analysis_id}.*"):
        if not path.is_file():
            continue
        shutil.move(str(path), str(archived_dir / path.name))
        moved = True
    return moved


def retry_job(job_id: str) -> Optional[Job]:
    old = _jobs.get(job_id)
    if old is None or not Path(old.temp_path).exists():
        return None
    job = Job(
        job_id=str(uuid.uuid4()),
        file_name=old.file_name,
        file_size=old.file_size,
        temp_path=old.temp_path,
        attempts=old.attempts + 1,
    )
    with _lock:
        _jobs[job.job_id] = job
    _executor.submit(_run_job, job.job_id)
    return job


def _run_job(job_id: str) -> None:
    job = _jobs[job_id]
    job.status = "running"
    job.stage = "preprocessing"
    job.progress = 2

    def on_progress(stage: str, pct: int):
        job.stage = stage
        job.progress = int(pct)
        job.stage_progress = 50  # grobe Naeherung innerhalb der Stage

    try:
        with open(job.temp_path, "rb") as f:
            audio = load_audio_file(
                file=f,
                filename=job.file_name,
                max_duration_seconds=7200,
            )

        analysis = analyze_set(audio, progress=on_progress)

        result = map_set_analysis_to_frontend_result(
            filename=job.file_name,
            analysis=analysis,
        )

        analysis_id = result["id"]

        # Audio aufbewahren, damit der DJ die bewerteten Stellen im
        # Report nachhoeren kann (GET /analysis/{id}/audio).
        suffix = Path(job.file_name or "").suffix.lower() or ".wav"
        try:
            audio_target = RESULTS_DIR / f"{analysis_id}{suffix}"
            shutil.move(job.temp_path, audio_target)
            result["audioPath"] = f"/analysis/{analysis_id}/audio"
        except OSError:
            result["audioPath"] = None  # Playback dann nicht verfuegbar

        _results[analysis_id] = result

        try:
            (RESULTS_DIR / f"{analysis_id}.json").write_text(
                json.dumps(result), encoding="utf-8",
            )
        except OSError:
            pass  # Platte optional - Ergebnis bleibt im Speicher

        job.analysis_id = analysis_id
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
    except Exception as error:  # noqa: BLE001 - Fehler MUESSEN am Job landen
        job.status = "failed"
        job.stage = "failed"
        job.error_message = str(error)
    finally:
        job.finished_at = time.time()
        # Bei Erfolg wurde die Datei bereits nach analysis_results/
        # verschoben; bei Fehlern bleibt sie fuer einen Retry liegen.
