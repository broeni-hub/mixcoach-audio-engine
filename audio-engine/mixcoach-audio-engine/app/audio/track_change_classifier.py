"""Unterscheidet echte Trackwechsel von Energie-Events innerhalb eines Tracks.

Erkenntnis aus der ersten Ground-Truth-Kalibrierung (REC002, 5 annotierte
Uebergaenge): Der Energie-Detektor findet ALLE echten Uebergaenge (Recall
5/5), aber auch ~6x so viele Breakdowns/Drops (Precision 15%).

Klassifikations-Signale:
1. Harmonie-Wechsel: Chroma-Verteilung 60s vor vs. 60s nach der Zone.
   Ein neuer Track bringt meist neues harmonisches Material.
2. Detektor-Score der Zone selbst.
3. Zeitlicher Mindestabstand: Tracks in DJ-Sets laufen typischerweise
   mehrere Minuten - zwei "Trackwechsel" 40s auseinander sind fast immer
   Break + Drop desselben Tracks.

KALIBRIERUNGS-STAND: n=1 Set (REC002: Precision 15% -> ~50% bei Recall 4/5).
Die Konstanten unten MUESSEN mit weiteren annotierten Sets nachkalibriert
werden. Deshalb werden Events nicht verworfen, sondern nur klassifiziert.
"""

from typing import Dict, List

import librosa
import numpy as np

# --- Kalibrierungs-Konstanten ---
# Stand: 3 annotierte Sets (REC001, REC002, REC013 / 19 echte Uebergaenge).
# Beste Konfiguration im Grid-Search: Recall 79%, Precision 60% (F1 0.68).
# Bekannte strukturelle Grenze: Doppel-Uebergaenge <150s Abstand (REC001
# hat ein 82s-Paar) kann die Greedy-Auswahl prinzipiell nicht beide melden.
MIN_TRACK_GAP_SECONDS = 150.0   # Mindestabstand zwischen Trackwechseln
CHROMA_WEIGHT = 100.0           # Gewicht Harmonie-Wechsel im Kombi-Score
DETECTOR_WEIGHT = 0.05          # Gewicht Detektor-Score im Kombi-Score
WINDOW_SECONDS = 60.0           # Analyse-Fenster vor/nach der Zone
ZONE_MARGIN_SECONDS = 15.0      # Abstand zum Zonen-Zentrum (Blend-Bereich)
# Beide annotierten Sets zeigten einen Fehlalarm <40s nach Set-Start:
# Der Set-Anfang (Intro-Aufbau) sieht fuer den Energie-Detektor wie ein
# Uebergang aus, ist aber keiner. Randzonen sind keine Trackwechsel.
EDGE_START_SECONDS = 90.0
EDGE_END_SECONDS = 60.0


def compute_chroma_matrix(waveform, sample_rate: int, hop_length: int = 512,
                          chunk_seconds: float = 240.0) -> np.ndarray:
    """Chroma fuer das gesamte Set, in Chunks (Speicher/CPU-schonend)."""
    n = len(waveform)
    step = int(chunk_seconds * sample_rate)
    parts = []

    for start in range(0, n, step):
        segment = np.asarray(waveform[start:start + step])
        if len(segment) < sample_rate:
            break
        parts.append(
            librosa.feature.chroma_cqt(y=segment, sr=sample_rate, hop_length=hop_length)
        )

    if not parts:
        return np.zeros((12, 0))

    return np.concatenate(parts, axis=1)


def classify_transition_zones(
    zones: List[Dict],
    chroma: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    duration: float = None,
) -> List[Dict]:
    """Markiert jede Zone als wahrscheinlichen Trackwechsel oder Energie-Event.

    Gibt die Zonen angereichert zurueck:
    - chroma_change: Harmonie-Distanz vor/nach (0..2)
    - track_change_score: Kombi-Score
    - is_likely_track_change: bool (Greedy-Auswahl mit Mindestabstand)
    """
    frames_per_second = sample_rate / hop_length

    def window_vector(t_start: float, t_end: float):
        a = max(0, int(t_start * frames_per_second))
        b = min(chroma.shape[1], int(t_end * frames_per_second))
        if b - a < 10:
            return None
        v = np.mean(chroma[:, a:b], axis=1)
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else None

    enriched: List[Dict] = []
    for zone in zones:
        t = float(zone["time"])
        before = window_vector(t - ZONE_MARGIN_SECONDS - WINDOW_SECONDS, t - ZONE_MARGIN_SECONDS)
        after = window_vector(t + ZONE_MARGIN_SECONDS, t + ZONE_MARGIN_SECONDS + WINDOW_SECONDS)

        chroma_change = (
            float(1 - np.dot(before, after))
            if before is not None and after is not None
            else 0.0
        )

        combo = chroma_change * CHROMA_WEIGHT + float(zone.get("score", 0)) * DETECTOR_WEIGHT

        enriched.append(
            {
                **zone,
                "chroma_change": round(chroma_change, 4),
                "track_change_score": round(combo, 2),
                "is_likely_track_change": False,
            }
        )

    if duration is None:
        duration = chroma.shape[1] * hop_length / sample_rate

    # Greedy-Auswahl: bester Kombi-Score zuerst, Mindestabstand einhalten.
    # Randzonen (Set-Intro/-Outro) sind nie Trackwechsel.
    selected_times: List[float] = []
    for zone in sorted(enriched, key=lambda z: -z["track_change_score"]):
        t = float(zone["time"])

        if t < EDGE_START_SECONDS or t > duration - EDGE_END_SECONDS:
            continue

        if all(abs(t - s) >= MIN_TRACK_GAP_SECONDS for s in selected_times):
            zone["is_likely_track_change"] = True
            selected_times.append(t)

    return enriched


# ======================================================================
# Boundary-Detection v2: Fusion aus Novelty-Peaks + Zonen-Klassifikator
#
# Validierung auf 3 annotierten Sets (19 echte Uebergaenge):
#   Zonen-Klassifikator allein:  Recall 79% / Precision 60%
#   Novelty-Peaks allein:        Recall 79% / Precision 62%
#   FUSION (Union):              Recall 95% / Precision 64%
# Die beiden Detektoren finden unterschiedliche Uebergaenge - die Union
# loest das Verdraengungs-Problem und findet auch schnelle Uebergaenge.
# ======================================================================

NOVELTY_WINDOW_SECONDS = 45.0    # Harmonie-Fenster vor/nach dem Zeitpunkt
NOVELTY_GAP_SECONDS = 10.0       # Aussparung um den Blend-Bereich
NOVELTY_STEP_SECONDS = 2.0       # Abtastung der Novelty-Kurve
NOVELTY_MIN_DIST_SECONDS = 60.0  # Mindestabstand zwischen Peaks
NOVELTY_THRESHOLD_STD = 0.5      # Peak-Schwelle: Mittel + k * Streuung
FUSION_MERGE_SECONDS = 60.0      # Novelty-Peak und Zone gelten als derselbe
                                 # Uebergang, wenn sie <60s auseinander liegen


def harmonic_novelty_peaks(
    chroma: np.ndarray,
    sample_rate: int,
    duration: float,
    hop_length: int = 512,
) -> List[Dict]:
    """Spitzen der Harmonie-Novelty-Kurve = Kandidaten fuer Trackwechsel.

    Fuer jeden Zeitpunkt: Wie stark unterscheidet sich das harmonische
    Material der 45s davor vom Material der 45s danach?
    """
    frames_per_second = sample_rate / hop_length

    if chroma.shape[1] < 100:
        return []

    csum = np.cumsum(chroma, axis=1)

    def window_mean(t0: float, t1: float):
        a = max(0, int(t0 * frames_per_second))
        b = min(chroma.shape[1], int(t1 * frames_per_second))
        if b - a < 10:
            return None
        v = (csum[:, b - 1] - (csum[:, a - 1] if a > 0 else 0)) / (b - a)
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else None

    times: List[float] = []
    values: List[float] = []
    t = NOVELTY_WINDOW_SECONDS + NOVELTY_GAP_SECONDS

    while t < duration - NOVELTY_WINDOW_SECONDS - NOVELTY_GAP_SECONDS:
        before = window_mean(t - NOVELTY_GAP_SECONDS - NOVELTY_WINDOW_SECONDS, t - NOVELTY_GAP_SECONDS)
        after = window_mean(t + NOVELTY_GAP_SECONDS, t + NOVELTY_GAP_SECONDS + NOVELTY_WINDOW_SECONDS)
        if before is not None and after is not None:
            times.append(t)
            values.append(float(1 - np.dot(before, after)))
        t += NOVELTY_STEP_SECONDS

    if not values:
        return []

    times_arr = np.array(times)
    values_arr = np.array(values)
    threshold = values_arr.mean() + NOVELTY_THRESHOLD_STD * values_arr.std()

    peaks: List[Dict] = []
    for i in np.argsort(-values_arr):
        if values_arr[i] < threshold:
            break
        if all(abs(times_arr[i] - p["time"]) >= NOVELTY_MIN_DIST_SECONDS for p in peaks):
            peaks.append({"time": float(times_arr[i]), "novelty": round(float(values_arr[i]), 4)})

    return sorted(peaks, key=lambda p: p["time"])


def detect_track_changes(
    zones: List[Dict],
    chroma: np.ndarray,
    sample_rate: int,
    duration: float,
    hop_length: int = 512,
):
    """Fusion beider Detektoren. Liefert (track_changes, classified_zones).

    track_changes sind zonen-artige Dicts (kompatibel zu
    evaluate_transitions); Novelty-Funde ohne passende Energie-Zone
    bekommen ehrliche None-Energiewerte statt erfundener.
    """
    classified = classify_transition_zones(zones, chroma, sample_rate, hop_length, duration)
    zone_selected = [z for z in classified if z["is_likely_track_change"]]
    peaks = harmonic_novelty_peaks(chroma, sample_rate, duration, hop_length)

    boundaries: List[Dict] = []

    def nearest_zone(t: float):
        candidates = [z for z in classified if abs(float(z["time"]) - t) <= FUSION_MERGE_SECONDS]
        return min(candidates, key=lambda z: abs(float(z["time"]) - t)) if candidates else None

    # 1) Novelty-Peaks (Randzonen ausgeschlossen), Energie-Infos der
    #    naechsten Zone uebernehmen, wenn vorhanden.
    for peak in peaks:
        t = peak["time"]
        if t < EDGE_START_SECONDS or t > duration - EDGE_END_SECONDS:
            continue
        zone = nearest_zone(t)
        boundaries.append(
            {
                "time": round(float(zone["time"]) if zone else t, 2),
                "type": zone.get("type") if zone else "harmonic_change",
                "confidence": zone.get("confidence") if zone else round(min(1.0, peak["novelty"] * 10), 3),
                "score": zone.get("score") if zone else None,
                "energy_before": zone.get("energy_before") if zone else None,
                "energy_current": zone.get("energy_current") if zone else None,
                "energy_after": zone.get("energy_after") if zone else None,
                "novelty": peak["novelty"],
                "detected_by": "both" if zone else "novelty",
            }
        )

    # 2) Zonen-Auswahl ergaenzen, wo kein Novelty-Peak in der Naehe liegt.
    for zone in zone_selected:
        t = float(zone["time"])
        if all(abs(t - b["time"]) >= FUSION_MERGE_SECONDS for b in boundaries):
            boundaries.append(
                {
                    "time": round(t, 2),
                    "type": zone.get("type"),
                    "confidence": zone.get("confidence"),
                    "score": zone.get("score"),
                    "energy_before": zone.get("energy_before"),
                    "energy_current": zone.get("energy_current"),
                    "energy_after": zone.get("energy_after"),
                    "novelty": zone.get("chroma_change"),
                    "detected_by": "energy",
                }
            )

    boundaries.sort(key=lambda b: b["time"])
    return boundaries, classified
