from typing import Dict, List

from app.experimental.models import TrackAnalysis

from app.experimental.scoring.tempo import tempo_score
from app.experimental.scoring.harmonic import harmonic_score
from app.experimental.scoring.phrase import phrase_score
from app.experimental.scoring.energy import energy_score
from app.experimental.scoring.overall import weighted_overall_score
from app.experimental.scoring.recommendations import generate_recommendations
from app.experimental.scoring.transition_timing import transition_timing_score


def compare_tracks(track_a: TrackAnalysis, track_b: TrackAnalysis) -> Dict:
    tempo_result = tempo_score(track_a, track_b)
    tempo = tempo_result["score"]
    tempo_diff = tempo_result["tempo_diff"]

    harmonic = harmonic_score(track_a, track_b)
    phrase = phrase_score(track_a, track_b)
    energy = energy_score(track_a, track_b)
    transition_timing = transition_timing_score(track_a, track_b)

    overall, breakdown = weighted_overall_score(
        tempo,
        harmonic,
        phrase,
        energy,
        transition_timing,
    )

    recommendations = generate_recommendations(
        tempo,
        harmonic,
        phrase,
        energy,
    )

    recommendations.extend(
        generate_vocal_mix_recommendations(track_a, track_b)
    )

    return {
        "track_a": track_a.filename,
        "track_b": track_b.filename,
        "tempo_diff": tempo_diff,
        "tempo_score": tempo,
        "harmonic_score": harmonic,
        "phrase_score": phrase,
        "energy_score": energy,
        "transition_timing_score": transition_timing,
        "overall_score": overall,
        "score_breakdown": breakdown,
        "recommendations": recommendations,
    }


def generate_vocal_mix_recommendations(
    track_a: TrackAnalysis,
    track_b: TrackAnalysis,
) -> List[str]:
    vocals_a = _get_vocals(track_a)
    vocals_b = _get_vocals(track_b)

    if not vocals_a or not vocals_b:
        return []

    has_vocals_a = bool(vocals_a.get("has_vocals", False))
    has_vocals_b = bool(vocals_b.get("has_vocals", False))

    recommendations = []

    if has_vocals_a and has_vocals_b:
        recommendations.append(
            "Beide Tracks wirken vocal-lastig. Übergang besser über Intro/Outro oder Instrumental-Part legen."
        )

    elif has_vocals_a and not has_vocals_b:
        recommendations.append(
            "Track A hat wahrscheinlich Vocals, Track B eher nicht. Guter Kandidat für sauberes Herausmixen unter laufender Hook."
        )

    elif not has_vocals_a and has_vocals_b:
        recommendations.append(
            "Track B hat wahrscheinlich Vocals. Übergang so planen, dass die Vocals von Track B erst nach dem Mix-in einsetzen."
        )

    else:
        recommendations.append(
            "Beide Tracks wirken eher instrumental. Mehr Freiheit für längere Blends."
        )

    return recommendations


def _get_vocals(track: TrackAnalysis) -> Dict:
    if not track.raw:
        return {}

    vocals = track.raw.get("vocals")

    if not isinstance(vocals, dict):
        return {}

    return vocals