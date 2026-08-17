from typing import Dict, List

from app.experimental.mix_analyzer import compare_tracks
from app.experimental.models import TrackAnalysis


def rank_next_tracks(
    current_track: TrackAnalysis,
    candidates: List[TrackAnalysis],
    limit: int = 10,
) -> List[Dict]:
    results: List[Dict] = []

    for candidate in candidates:
        if candidate.filename == current_track.filename:
            continue

        comparison = compare_tracks(current_track, candidate)
        results.append(comparison)

    results.sort(
        key=lambda item: item["overall_score"],
        reverse=True,
    )

    return results[:limit]