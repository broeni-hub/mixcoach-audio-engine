from pathlib import Path
from typing import Dict, List

from app.experimental.engine import analyze_audio
from app.experimental.library_ranker import rank_next_tracks
from app.audio.loader import load_audio_file


SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".aiff",
    ".aif",
    ".flac",
    ".m4a",
}


def analyze_audio_folder(folder_path: str) -> List:
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")

    analyses = []

    for file_path in folder.iterdir():
        if file_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            continue

        with file_path.open("rb") as audio_file:
            audio = load_audio_file(audio_file, file_path.name)

        analyses.append(analyze_audio(audio))

    return analyses


def find_best_mixes_for_folder(
    folder_path: str,
    limit_per_track: int = 5,
) -> Dict:
    analyses = analyze_audio_folder(folder_path)

    results = {}

    for track in analyses:
        candidates = [
            candidate
            for candidate in analyses
            if candidate.filename != track.filename
        ]

        results[track.filename] = rank_next_tracks(
            current_track=track,
            candidates=candidates,
            limit=limit_per_track,
        )

    return results