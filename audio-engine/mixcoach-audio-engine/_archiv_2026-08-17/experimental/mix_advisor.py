from typing import Dict, List

from app.experimental.models import TrackAnalysis
from app.experimental.mix_analyzer import compare_tracks


def advise_next_track(
    current_track: TrackAnalysis,
    candidate_track: TrackAnalysis,
) -> Dict:
    comparison = compare_tracks(current_track, candidate_track)

    reasons = _build_reasons(comparison)
    warnings = _build_warnings(comparison)
    action_plan = _build_action_plan(comparison)

    return {
        "current_track": current_track.filename,
        "recommended_track": candidate_track.filename,
        "confidence": comparison["overall_score"],
        "scores": {
            "tempo": comparison["tempo_score"],
            "harmonic": comparison["harmonic_score"],
            "phrase": comparison["phrase_score"],
            "energy": comparison["energy_score"],
            "transition": comparison["transition_timing_score"],
            "overall": comparison["overall_score"],
        },
        "reasons": reasons,
        "warnings": warnings,
        "action_plan": action_plan,
    }


def _build_reasons(comparison: Dict) -> List[str]:
    reasons = []

    if comparison["tempo_score"] >= 85:
        reasons.append("Tempo liegt nah genug beieinander für einen sauberen Beatmatch.")

    if comparison["harmonic_score"] >= 85:
        reasons.append("Harmonisch passt der Übergang gut.")

    if comparison["phrase_score"] >= 85:
        reasons.append("Phrasenstruktur ist gut kompatibel.")

    if comparison["energy_score"] >= 85:
        reasons.append("Energielevel passt gut zusammen.")

    if comparison["transition_timing_score"] >= 85:
        reasons.append("Übergangspunkt liegt musikalisch günstig.")

    if not reasons:
        reasons.append("Der Track ist grundsätzlich mixbar, aber nicht ideal.")

    return reasons


def _build_warnings(comparison: Dict) -> List[str]:
    warnings = []

    if comparison["tempo_score"] < 60:
        warnings.append("Tempo-Unterschied ist groß. Pitch-Anpassung nötig.")

    if comparison["harmonic_score"] < 60:
        warnings.append("Harmonischer Clash möglich. Besser über Percussion/Break mixen.")

    if comparison["phrase_score"] < 60:
        warnings.append("Phrasen passen schlecht. Übergang genau planen.")

    if comparison["energy_score"] < 60:
        warnings.append("Energiesprung könnte hart wirken.")

    if comparison["transition_timing_score"] < 60:
        warnings.append("Kein optimaler Übergangspunkt erkannt.")

    return warnings


def _build_action_plan(comparison: Dict) -> List[str]:
    plan = []

    tempo_diff = comparison["tempo_diff"]

    if tempo_diff > 0:
        plan.append(f"Tempo um ca. {tempo_diff} BPM angleichen.")

    if comparison["harmonic_score"] < 70:
        plan.append("EQ vorsichtig einsetzen: Bass nicht gleichzeitig voll offen lassen.")

    if comparison["phrase_score"] >= 80:
        plan.append("Mix am Anfang einer 8- oder 16-Bar-Phrase starten.")
    else:
        plan.append("Übergang kurz halten und auf Downbeat achten.")

    if comparison["energy_score"] >= 80:
        plan.append("Längerer Blend ist möglich.")
    else:
        plan.append("Schnellerer Übergang empfohlen.")

    return plan