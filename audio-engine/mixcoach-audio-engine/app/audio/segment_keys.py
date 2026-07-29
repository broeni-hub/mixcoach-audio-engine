"""Tonart-Erkennung pro Track-Segment (Krumhansl-Schluessel-Profile).

Portiert aus dem experimentellen Key-Detektor und auf Segmente eines
Sets angewendet. Pro Segment wird nur ein zentraler Ausschnitt analysiert
(guenstiger und robuster, weil Uebergaenge an den Raendern die Chroma-
Verteilung verschmieren wuerden).
"""

from typing import Dict, List, Optional

import librosa
import numpy as np

KEYS_MAJOR = [
    "C Major", "C# Major", "D Major", "D# Major", "E Major", "F Major",
    "F# Major", "G Major", "G# Major", "A Major", "A# Major", "B Major",
]

KEYS_MINOR = [
    "C Minor", "C# Minor", "D Minor", "D# Minor", "E Minor", "F Minor",
    "F# Minor", "G Minor", "G# Minor", "A Minor", "A# Minor", "B Minor",
]

MAJOR_PROFILE = np.array([
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
])

MINOR_PROFILE = np.array([
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
])

CAMELOT_MAP = {
    "C Major": "8B", "G Major": "9B", "D Major": "10B", "A Major": "11B",
    "E Major": "12B", "B Major": "1B", "F# Major": "2B", "C# Major": "3B",
    "G# Major": "4B", "D# Major": "5B", "A# Major": "6B", "F Major": "7B",
    "A Minor": "8A", "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A",
    "C# Minor": "12A", "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A",
    "F Minor": "4A", "C Minor": "5A", "G Minor": "6A", "D Minor": "7A",
}

# Maximal analysierte Laenge pro Segment (Sekunden) - Kosten begrenzen.
MAX_ANALYSIS_SECONDS = 45.0


def key_from_chroma_mean(chroma_mean: np.ndarray) -> Dict:
    """Krumhansl-Matching auf einem gemittelten Chroma-Vektor."""
    total = float(np.sum(chroma_mean))
    if total <= 0:
        return {"key": None, "camelot": None, "confidence": 0.0}

    chroma_norm = chroma_mean / np.linalg.norm(chroma_mean)

    scores = []
    for i in range(12):
        major = np.roll(MAJOR_PROFILE, i)
        minor = np.roll(MINOR_PROFILE, i)
        major = major / np.linalg.norm(major)
        minor = minor / np.linalg.norm(minor)
        scores.append((KEYS_MAJOR[i], float(np.dot(chroma_norm, major))))
        scores.append((KEYS_MINOR[i], float(np.dot(chroma_norm, minor))))

    scores.sort(key=lambda item: item[1], reverse=True)

    best_key, best_score = scores[0]
    second_score = scores[1][1]

    confidence = max(0.0, min(1.0, best_score - second_score + 0.5))

    return {
        "key": best_key,
        "camelot": CAMELOT_MAP.get(best_key),
        "confidence": round(confidence, 2),
    }


def detect_key_for_slice(waveform: np.ndarray, sample_rate: int) -> Dict:
    """Tonart eines Audio-Ausschnitts mit Konfidenz (0..1)."""
    if waveform.size == 0:
        return {"key": None, "camelot": None, "confidence": 0.0}

    chroma = librosa.feature.chroma_cqt(y=waveform, sr=sample_rate)
    return key_from_chroma_mean(np.mean(chroma, axis=1))


def detect_segment_keys_from_chroma(
    chroma: np.ndarray,
    sample_rate: int,
    segments: List[Dict],
    hop_length: int = 512,
) -> List[Dict]:
    """Tonart pro Segment aus einer bereits berechneten Chroma-Matrix."""
    frames_per_second = sample_rate / hop_length
    results: List[Dict] = []

    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        duration = end - start

        if duration < 10.0 or chroma.shape[1] == 0:
            results.append(_empty(segment["index"], start, end))
            continue

        window = min(duration * 0.6, MAX_ANALYSIS_SECONDS)
        center = (start + end) / 2
        a = max(0, int((center - window / 2) * frames_per_second))
        b = min(chroma.shape[1], int((center + window / 2) * frames_per_second))

        if b - a < 10:
            results.append(_empty(segment["index"], start, end))
            continue

        key = key_from_chroma_mean(np.mean(chroma[:, a:b], axis=1))
        results.append({"segment_index": segment["index"], "start": start, "end": end, **key})

    return results


def detect_segment_keys(audio, segments: List[Dict]) -> List[Dict]:
    """Tonart pro Segment - analysiert wird die Segment-Mitte."""
    sr = audio.sample_rate
    waveform = audio.waveform
    results: List[Dict] = []

    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        duration = end - start

        if duration < 10.0:
            results.append(_empty(segment["index"], start, end))
            continue

        # Zentraler Ausschnitt, gedeckelt auf MAX_ANALYSIS_SECONDS.
        window = min(duration * 0.6, MAX_ANALYSIS_SECONDS)
        center = (start + end) / 2
        slice_start = int(max(0, (center - window / 2)) * sr)
        slice_end = int(min(len(waveform) / sr, center + window / 2) * sr)

        key = detect_key_for_slice(waveform[slice_start:slice_end], sr)

        results.append(
            {
                "segment_index": segment["index"],
                "start": start,
                "end": end,
                **key,
            }
        )

    return results


def camelot_compatibility_score(camelot_a: Optional[str], camelot_b: Optional[str]) -> Optional[int]:
    """Harmonische Kompatibilitaet zweier Camelot-Codes (0-100).

    Gleiche Tonart: 100. Nachbar auf dem Rad (+-1): 95.
    Relative Dur/Moll (gleiche Zahl, anderer Modus): 90. Sonst: 40.
    None, wenn eine Tonart unbekannt ist - kein geratener Default.
    """
    if not camelot_a or not camelot_b:
        return None

    if camelot_a == camelot_b:
        return 100

    try:
        number_a, mode_a = int(camelot_a[:-1]), camelot_a[-1]
        number_b, mode_b = int(camelot_b[:-1]), camelot_b[-1]
    except (ValueError, IndexError):
        return None

    if mode_a == mode_b and abs(number_a - number_b) in {1, 11}:
        return 95

    if number_a == number_b and mode_a != mode_b:
        return 90

    return 40


def dominant_key(segment_keys: List[Dict], min_confidence: float = 0.5) -> Dict:
    """Dauer-gewichtete dominante Tonart des Sets (fuer die Kopfzeile)."""
    weights: Dict[str, float] = {}
    camelots: Dict[str, Optional[str]] = {}

    for entry in segment_keys:
        key = entry.get("key")
        if not key or float(entry.get("confidence", 0)) < min_confidence:
            continue
        duration = float(entry["end"]) - float(entry["start"])
        weights[key] = weights.get(key, 0.0) + duration
        camelots[key] = entry.get("camelot")

    if not weights:
        return {"key": None, "camelot": None}

    best = max(weights, key=weights.get)
    return {"key": best, "camelot": camelots.get(best)}


def _empty(index: int, start: float, end: float) -> Dict:
    return {
        "segment_index": index,
        "start": start,
        "end": end,
        "key": None,
        "camelot": None,
        "confidence": 0.0,
    }
