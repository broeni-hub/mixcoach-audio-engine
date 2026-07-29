"""Qualitaets-Bewertung pro Uebergang - das Kernversprechen von MixCoach.

Jeder erkannte Uebergang wird musikalisch bewertet:
- Phrase-Timing: Liegt der Uebergang auf einem Phrasenstart? (in Beats!)
- Tempo-Match: Passen die BPM der beiden Segmente zusammen?
- Harmonie: Passen die Tonarten (Camelot-Rad)?
- Energie: Wie tief ist der Energie-Einbruch?

Jede Metrik ist None, wenn sie nicht messbar war. Der Score wird nur
aus messbaren Teilen gebildet und das Feedback nennt konkrete Zahlen.
"""

from typing import Dict, List, Optional

from app.audio.phrase_grid import phrase_distance_beats
from app.audio.segment_keys import camelot_compatibility_score


def evaluate_transitions(
    transition_zones: List[Dict],
    segments: List[Dict],
    segment_tempos: List[Dict],
    segment_keys: List[Dict],
    phrase_boundaries: List[Dict],
    duration: float,
) -> List[Dict]:
    """Bewertet jeden Uebergang zwischen zwei benachbarten Segmenten."""
    tempo_by_index = {t["segment_index"]: t["bpm"] for t in segment_tempos}
    key_by_index = {k["segment_index"]: k for k in segment_keys}

    results: List[Dict] = []

    for i, zone in enumerate(transition_zones):
        center = float(zone["time"])

        # Zone i trennt Segment i+1 (davor) von Segment i+2 (danach) -
        # build_set_segments vergibt 1-basierte Indizes in Zeit-Reihenfolge.
        before_index = i + 1
        after_index = i + 2

        bpm_before = tempo_by_index.get(before_index)
        bpm_after = tempo_by_index.get(after_index)

        key_before = key_by_index.get(before_index, {})
        key_after = key_by_index.get(after_index, {})

        bpm_drift = (
            round(abs(bpm_before - bpm_after), 2)
            if bpm_before is not None and bpm_after is not None
            else None
        )

        tempo_score = _tempo_match_score(bpm_drift)
        harmonic_score = camelot_compatibility_score(
            key_before.get("camelot"), key_after.get("camelot"),
        )

        # WICHTIG: Nur das Phrasen-Raster des AUSLAUFENDEN Tracks verwenden.
        # Das Raster des neuen Segments ankert am Uebergang selbst - dagegen
        # zu messen waere ein Zirkelschluss (Ergebnis immer ~0 Beats).
        # Das Raster des auslaufenden Tracks ankert am vorherigen Uebergang
        # und misst, ob DIESER Uebergang auf dessen 32-Beat-Raster faellt.
        outgoing_boundaries = [
            b for b in phrase_boundaries
            if b.get("segment_index") == before_index
        ]
        beats_off = phrase_distance_beats(
            outgoing_boundaries, center, bpm_before or bpm_after,
        )
        phrase_score = _phrase_alignment_score(beats_off)

        energy_dip_pct = _energy_dip_pct(zone)
        energy_score = _energy_dip_score(energy_dip_pct)

        quality = _combined_score(
            phrase=phrase_score,
            tempo=tempo_score,
            harmonic=harmonic_score,
            energy=energy_score,
        )

        blend_start = zone.get("blend_start")
        results.append(
            {
                "index": i + 1,
                "start_sec": round(float(blend_start), 2) if blend_start is not None
                             else round(max(0.0, center - 16.0), 2),
                "mid_sec": round(center, 2),
                "end_sec": round(min(duration, center + 16.0), 2),
                "type": zone.get("type", "possible_transition"),
                "detection_confidence": zone.get("confidence"),
                "bpm_before": bpm_before,
                "bpm_after": bpm_after,
                "bpm_drift": bpm_drift,
                "key_before": key_before.get("key"),
                "key_after": key_after.get("key"),
                "camelot_before": key_before.get("camelot"),
                "camelot_after": key_after.get("camelot"),
                "phrase_beats_off": beats_off,
                "scores": {
                    "phrase": phrase_score,
                    "tempo": tempo_score,
                    "harmonic": harmonic_score,
                    "energy": energy_score,
                },
                "energy_dip_pct": energy_dip_pct,
                "quality_score": quality,
                "label": _label(quality),
                "feedback": _feedback(
                    center, beats_off, bpm_before, bpm_after, bpm_drift,
                    key_before, key_after, harmonic_score, quality,
                ),
                "feedback_en": _feedback_en(
                    center, beats_off, bpm_before, bpm_after, bpm_drift,
                    key_before, key_after, harmonic_score, quality,
                ),
            }
        )

    return results


def aggregate_transition_scores(transitions: List[Dict]) -> Dict:
    """Mittelt die Teil-Scores ueber alle Uebergaenge (nur gemessene)."""
    def mean_of(key: str) -> Optional[float]:
        values = [
            t["scores"][key] for t in transitions
            if t["scores"].get(key) is not None
        ]
        return round(sum(values) / len(values), 2) if values else None

    return {
        "phrase_timing": mean_of("phrase"),
        "beatmatching": mean_of("tempo"),
        "harmonic": mean_of("harmonic"),
        "energy_shape": mean_of("energy"),
    }


# ---------- Teil-Scores ----------


def _tempo_match_score(bpm_drift: Optional[float]) -> Optional[int]:
    if bpm_drift is None:
        return None
    if bpm_drift <= 1:
        return 100
    if bpm_drift <= 2:
        return 95
    if bpm_drift <= 4:
        return 85
    if bpm_drift <= 6:
        return 70
    if bpm_drift <= 8:
        return 55
    if bpm_drift <= 10:
        return 40
    return 20


def _phrase_alignment_score(beats_off: Optional[float]) -> Optional[int]:
    if beats_off is None:
        return None
    if beats_off <= 1:
        return 100
    if beats_off <= 2:
        return 90
    if beats_off <= 4:
        return 75
    if beats_off <= 8:
        return 55
    return 30


def _energy_dip_pct(zone: Dict) -> Optional[int]:
    before = zone.get("energy_before")
    current = zone.get("energy_current")

    if before is None or current is None or float(before) <= 0:
        return None

    dip = max(0.0, 1.0 - float(current) / float(before)) * 100
    return int(round(min(100.0, dip)))


def _energy_dip_score(dip_pct: Optional[int]) -> Optional[int]:
    """Sweet Spot ~30-50% Einbruch: hoerbar, aber kein Loch im Set."""
    if dip_pct is None:
        return None
    return int(round(max(0.0, 100.0 - abs(dip_pct - 40) * 1.5)))


def _combined_score(
    phrase: Optional[int],
    tempo: Optional[int],
    harmonic: Optional[int],
    energy: Optional[int],
) -> Optional[int]:
    weighted = [
        (phrase, 0.35),
        (tempo, 0.35),
        (harmonic, 0.15),
        (energy, 0.15),
    ]
    available = [(score, weight) for score, weight in weighted if score is not None]

    if not available:
        return None

    total_weight = sum(weight for _, weight in available)
    value = sum(score * weight for score, weight in available) / total_weight

    return int(round(value))


def _label(quality: Optional[int]) -> str:
    if quality is None:
        return "neutral"
    if quality >= 75:
        return "smooth"
    if quality < 55:
        return "rough"
    return "neutral"


# ---------- Feedback-Texte ----------


def _mmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def _feedback(
    center: float,
    beats_off: Optional[float],
    bpm_before: Optional[float],
    bpm_after: Optional[float],
    bpm_drift: Optional[float],
    key_before: Dict,
    key_after: Dict,
    harmonic_score: Optional[int],
    quality: Optional[int],
) -> str:
    """Ein konkreter, umsetzbarer Satz pro Uebergang - mit echten Zahlen."""
    at = _mmss(center)
    issues: List[str] = []

    if beats_off is not None and beats_off > 4:
        issues.append(
            f"liegt {beats_off:.0f} Beats neben dem Phrasenstart - "
            f"starte den Uebergang ca. {beats_off:.0f} Beats frueher oder spaeter, "
            "damit er auf der 8-Bar-Grenze landet"
        )

    if bpm_drift is not None and bpm_drift > 4:
        issues.append(
            f"springt von {bpm_before:.0f} auf {bpm_after:.0f} BPM - "
            "gleiche die Tempi vor dem Blend an oder nutze einen Cut statt eines Blends"
        )

    if harmonic_score is not None and harmonic_score <= 40:
        issues.append(
            f"wechselt harmonisch weit ({key_before.get('key')} -> {key_after.get('key')}, "
            f"Camelot {key_before.get('camelot')} -> {key_after.get('camelot')}) - "
            "waehle einen Track im Nachbarfeld des Camelot-Rads"
        )

    if issues:
        return f"Uebergang bei {at} " + "; ausserdem ".join(issues) + "."

    if quality is not None and quality >= 75:
        return f"Uebergang bei {at} sitzt: Timing, Tempo und Energie passen zusammen."

    return f"Uebergang bei {at} ist solide, aber nicht herausragend - vergleiche ihn im Player mit deinem besten Uebergang."


def _feedback_en(
    center: float,
    beats_off: Optional[float],
    bpm_before: Optional[float],
    bpm_after: Optional[float],
    bpm_drift: Optional[float],
    key_before: Dict,
    key_after: Dict,
    harmonic_score: Optional[int],
    quality: Optional[int],
) -> str:
    """Englische Variante von _feedback - identische Logik und Zahlen."""
    at = _mmss(center)
    issues: List[str] = []

    if beats_off is not None and beats_off > 4:
        issues.append(
            f"lands {beats_off:.0f} beats off the phrase start - "
            f"start the transition about {beats_off:.0f} beats earlier or later "
            "so it hits the 8-bar boundary"
        )

    if bpm_drift is not None and bpm_drift > 4:
        issues.append(
            f"jumps from {bpm_before:.0f} to {bpm_after:.0f} BPM - "
            "match tempos before the blend or use a cut instead"
        )

    if harmonic_score is not None and harmonic_score <= 40:
        issues.append(
            f"makes a distant key change ({key_before.get('key')} -> {key_after.get('key')}, "
            f"Camelot {key_before.get('camelot')} -> {key_after.get('camelot')}) - "
            "pick a track from a neighbouring Camelot field"
        )

    if issues:
        return f"Transition at {at} " + "; also ".join(issues) + "."

    if quality is not None and quality >= 75:
        return f"Transition at {at} sits: timing, tempo and energy line up."

    return f"Transition at {at} is solid but not outstanding - compare it in the player with your best one."
