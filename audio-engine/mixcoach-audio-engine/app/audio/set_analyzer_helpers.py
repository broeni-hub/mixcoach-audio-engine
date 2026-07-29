from typing import Dict, List

import numpy as np


def detect_set_transition_zones(energy: Dict) -> List[Dict]:
    points = energy.get("points", [])

    if len(points) < 30:
        return []

    times = np.array([float(p["time"]) for p in points])
    rms = np.array([float(p["rms"]) for p in points])
    peaks = np.array([float(p["peak"]) for p in points])

    max_rms = float(np.max(rms))
    max_peak = float(np.max(peaks))

    if max_rms <= 0:
        return []

    rms_norm = rms / max_rms
    peak_norm = peaks / max_peak if max_peak > 0 else peaks

    rms_smooth = _moving_average(rms_norm, window=7)
    peak_smooth = _moving_average(peak_norm, window=7)

    candidates: List[Dict] = []

    for i in range(15, len(rms_smooth) - 15):
        before = float(np.mean(rms_smooth[i - 15:i - 5]))
        middle = float(np.mean(rms_smooth[i - 5:i + 5]))
        after = float(np.mean(rms_smooth[i + 5:i + 15]))

        peak_before = float(np.mean(peak_smooth[i - 15:i - 5]))
        peak_middle = float(np.mean(peak_smooth[i - 5:i + 5]))
        peak_after = float(np.mean(peak_smooth[i + 5:i + 15]))

        blend_score = _score_blend_transition(before, middle, after, peak_before, peak_after)
        drop_score = _score_drop_transition(before, middle, after, peak_before, peak_middle, peak_after)
        bass_swap_score = _score_bass_swap_like_change(before, after, peak_before, peak_after)

        total_score = max(
            blend_score,
            drop_score,
            bass_swap_score,
        )

        if total_score < 35:
            continue

        transition_type = _transition_type(
            blend_score=blend_score,
            drop_score=drop_score,
            bass_swap_score=bass_swap_score,
        )

        candidates.append(
            {
                "time": round(float(times[i]), 2),
                "type": transition_type,
                "confidence": round(min(1.0, total_score / 100), 3),
                "score": round(total_score, 2),
                "energy_before": round(before, 3),
                "energy_current": round(middle, 3),
                "energy_after": round(after, 3),
                "signals": {
                    "blend_score": round(blend_score, 2),
                    "drop_score": round(drop_score, 2),
                    "bass_swap_score": round(bass_swap_score, 2),
                },
                "reason": "Hybrid detector found blend/drop/bass-swap transition evidence.",
            }
        )

    return _deduplicate_candidates(candidates, min_distance_seconds=35.0)


def _score_blend_transition(
    before: float,
    middle: float,
    after: float,
    peak_before: float,
    peak_after: float,
) -> float:
    long_shift = abs(after - before)
    stable_middle = 1.0 - min(1.0, abs(middle - ((before + after) / 2)) * 3)
    peak_shift = abs(peak_after - peak_before)

    score = 0.0
    score += min(45.0, long_shift * 180)
    score += min(25.0, stable_middle * 25)
    score += min(30.0, peak_shift * 160)

    return score


def _score_drop_transition(
    before: float,
    middle: float,
    after: float,
    peak_before: float,
    peak_middle: float,
    peak_after: float,
) -> float:
    dip = max(0.0, min(before, after) - middle)
    rebound = max(0.0, after - middle)
    peak_rebound = max(0.0, peak_after - peak_middle)

    score = 0.0
    score += min(40.0, dip * 220)
    score += min(35.0, rebound * 180)
    score += min(25.0, peak_rebound * 160)

    return score


def _score_bass_swap_like_change(
    before: float,
    after: float,
    peak_before: float,
    peak_after: float,
) -> float:
    energy_shift = abs(after - before)
    peak_shift = abs(peak_after - peak_before)

    # Bass-Swaps wirken oft wie ein deutlicher Peak-/Punch-Wechsel,
    # ohne dass die Gesamtenergie massiv droppt.
    score = 0.0
    score += min(45.0, peak_shift * 220)
    score += min(35.0, energy_shift * 150)

    if peak_shift > 0.08 and energy_shift < 0.18:
        score += 20.0

    return score


def _transition_type(
    blend_score: float,
    drop_score: float,
    bass_swap_score: float,
) -> str:
    best = max(blend_score, drop_score, bass_swap_score)

    if best == drop_score:
        return "drop_transition"

    if best == bass_swap_score:
        return "bass_swap_transition"

    return "blend_transition"


def build_set_segments(duration: float, transition_zones: List[Dict]) -> List[Dict]:
    segments = []
    start = 0.0

    for index, zone in enumerate(transition_zones, start=1):
        end = float(zone["time"])

        if end <= start:
            continue

        segments.append(
            {
                "index": index,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "type": "track_segment",
            }
        )

        start = end

    if start < duration:
        segments.append(
            {
                "index": len(segments) + 1,
                "start": round(start, 2),
                "end": round(duration, 2),
                "duration": round(duration - start, 2),
                "type": "track_segment",
            }
        )

    return segments


def analyze_set_dramaturgy(energy: Dict) -> Dict:
    points = energy.get("points", [])

    if not points:
        return {
            "average_energy": 0.0,
            "peak_energy": 0.0,
            "energy_trend": "unknown",
        }

    values = [float(point["rms"]) for point in points]
    first_half = values[: len(values) // 2]
    second_half = values[len(values) // 2 :]

    average_energy = float(np.mean(values))
    peak_energy = float(np.max(values))

    first_average = float(np.mean(first_half)) if first_half else average_energy
    second_average = float(np.mean(second_half)) if second_half else average_energy

    if second_average > first_average * 1.08:
        trend = "rising"
    elif second_average < first_average * 0.92:
        trend = "falling"
    else:
        trend = "stable"

    return {
        "average_energy": round(average_energy, 5),
        "peak_energy": round(peak_energy, 5),
        "energy_trend": trend,
    }


def score_set_quality(
    duration: float,
    energy: Dict,
    transition_zones: List[Dict],
    dramaturgy: Dict,
) -> Dict:
    flow_score = _score_energy_flow(energy)
    transition_score = _score_transition_density(duration, transition_zones)
    dramaturgy_score = _score_dramaturgy(dramaturgy)

    overall = round(
        (flow_score * 0.45)
        + (transition_score * 0.30)
        + (dramaturgy_score * 0.25),
        2,
    )

    return {
        "overall": overall,
        "energy_flow": flow_score,
        "transition_density": transition_score,
        "dramaturgy": dramaturgy_score,
        "rating": _quality_label(overall),
    }


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) < window:
        return values

    # Rand-Werte wiederholen statt mit Nullen auffuellen. Sonst entsteht an
    # Set-Anfang und -Ende ein kuenstlicher Energie-Abfall, den der Detektor
    # faelschlicherweise als Uebergang meldet (Bug, gefunden durch Unit-Test).
    pad = window // 2
    padded = np.pad(values, pad, mode="edge")
    kernel = np.ones(window) / window

    smoothed = np.convolve(padded, kernel, mode="valid")

    return smoothed[: len(values)]


def _deduplicate_candidates(
    candidates: List[Dict],
    min_distance_seconds: float,
) -> List[Dict]:
    sorted_candidates = sorted(
        candidates,
        key=lambda item: item["confidence"],
        reverse=True,
    )

    selected: List[Dict] = []

    for candidate in sorted_candidates:
        time = float(candidate["time"])

        too_close = any(
            abs(time - float(existing["time"])) < min_distance_seconds
            for existing in selected
        )

        if not too_close:
            selected.append(candidate)

    return sorted(selected, key=lambda item: item["time"])


def _score_energy_flow(energy: Dict) -> float:
    points = energy.get("points", [])

    if len(points) < 3:
        return 50.0

    values = np.array([float(point["rms"]) for point in points])

    if float(np.mean(values)) <= 0:
        return 50.0

    volatility = float(np.std(values) / np.mean(values))
    score = 100 - volatility * 100

    return round(max(0.0, min(100.0, score)), 2)


def _score_transition_density(duration: float, transition_zones: List[Dict]) -> float:
    if duration <= 0:
        return 50.0

    minutes = duration / 60.0
    transitions_per_10_min = len(transition_zones) / max(minutes / 10.0, 1)

    if 2 <= transitions_per_10_min <= 6:
        return 100.0

    if transitions_per_10_min < 2:
        return round(50 + transitions_per_10_min * 20, 2)

    return round(max(40.0, 100 - (transitions_per_10_min - 6) * 10), 2)


def _score_dramaturgy(dramaturgy: Dict) -> float:
    trend = dramaturgy.get("energy_trend")

    if trend == "rising":
        return 90.0

    if trend == "stable":
        return 75.0

    if trend == "falling":
        return 60.0

    return 50.0


def _quality_label(score: float) -> str:
    if score >= 90:
        return "excellent"

    if score >= 75:
        return "good"

    if score >= 60:
        return "okay"

    return "needs_work"
