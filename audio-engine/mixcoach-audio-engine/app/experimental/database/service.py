import hashlib
from pathlib import Path
from typing import Optional

from app.experimental.engine import analyze_audio
from app.audio.loader import load_audio_file
from app.database.repository import get_track_by_filename, save_track_analysis


def calculate_file_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def analyze_and_store_track(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_hash = calculate_file_hash(path)
    existing = get_track_by_filename(path.name)

    if existing and existing["file_hash"] == file_hash:
        return existing["analysis"]

    with path.open("rb") as file:
        audio = load_audio_file(file, path.name)

    analysis = analyze_audio(audio)
    analysis_dict = analysis.model_dump()

    save_track_analysis(
        filename=analysis.filename,
        file_path=str(path),
        file_hash=file_hash,
        duration=analysis.duration,
        tempo=analysis.tempo,
        musical_key=analysis.key.key,
        camelot=analysis.key.camelot,
        analysis=analysis_dict,
    )

    return analysis_dict