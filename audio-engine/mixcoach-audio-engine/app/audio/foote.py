"""Foote-Novelty: beat-synchrone Selbstaehnlichkeits-Segmentierung.

Das Standardverfahren der Musik-Struktur-Analyse (Foote 2000): Das Set
wird als Aehnlichkeitsmatrix auf Beat-Ebene betrachtet. Ein Trackwechsel
erzeugt eine "Schachbrett-Ecke": davor homogen, danach homogen, dazwischen
unaehnlich. Ein Checkerboard-Kernel entlang der Diagonale macht daraus
eine Novelty-Kurve mit Beat-genauen Spitzen.

Gegenueber den 60s-Fenster-Distanzen loest das zwei Probleme:
- Zeitaufloesung ~1 Beat statt ~20s (Start-Genauigkeit!)
- empfindlich fuer Textur-Wechsel auch OHNE Energie-Einbruch
"""

from typing import Dict, List, Optional

import numpy as np

KERNEL_BEATS = 64        # 16 Bars pro Seite - Trackwechsel-Zeitskala
MIN_PEAK_DIST_BEATS = 32 # Peaks mindestens 8 Bars auseinander


def beat_sync_features(chroma: np.ndarray, mfcc: np.ndarray,
                       beats: List[float], sample_rate: int,
                       hop_length: int = 512) -> np.ndarray:
    """Chroma+MFCC pro Beat-Intervall gemittelt, Spalten L2-normalisiert."""
    fps = sample_rate / hop_length
    frames = [int(b * fps) for b in beats]

    if len(frames) < 4 or chroma.shape[1] == 0:
        return np.zeros((chroma.shape[0] + max(0, mfcc.shape[0] - 1), 0))

    stacked = np.vstack([chroma, mfcc[1:] if mfcc.shape[0] > 1 else mfcc])
    n_frames = stacked.shape[1]

    cols = []
    for i in range(len(frames) - 1):
        a = min(frames[i], n_frames - 1)
        b = min(max(frames[i + 1], a + 1), n_frames)
        cols.append(stacked[:, a:b].mean(axis=1))
    matrix = np.array(cols).T  # (D x B)

    norms = np.linalg.norm(matrix, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def foote_novelty(feat_sync: np.ndarray, kernel_beats: int = KERNEL_BEATS) -> np.ndarray:
    """Checkerboard-Novelty pro Beat.

    novelty[i] = Homogenitaet(vorher) + Homogenitaet(nachher)
                 - 2 * Aehnlichkeit(vorher, nachher)
    Hoch genau dann, wenn beide Seiten in sich aehnlich, aber zueinander
    verschieden sind - die Signatur eines Trackwechsels, unabhaengig von
    Energie.
    """
    D, B = feat_sync.shape
    L = kernel_beats
    novelty = np.zeros(B)

    if B < 2 * L:
        return novelty

    for i in range(L, B - L):
        before = feat_sync[:, i - L:i]
        after = feat_sync[:, i:i + L]
        s_aa = float(np.mean(before.T @ before))
        s_bb = float(np.mean(after.T @ after))
        s_ab = float(np.mean(before.T @ after))
        novelty[i] = max(0.0, s_aa + s_bb - 2.0 * s_ab)

    return novelty


def foote_peaks(novelty: np.ndarray, beats: List[float],
                min_dist_beats: int = MIN_PEAK_DIST_BEATS,
                threshold_std: float = 1.0) -> List[Dict]:
    """Beat-genaue Novelty-Spitzen (potenzielle Trackgrenzen)."""
    if len(novelty) == 0 or novelty.max() <= 0:
        return []

    active = novelty[novelty > 0]
    if len(active) < 10:
        return []
    # Zwei Bedingungen: statistisch auffaellig UND deutlich ueber dem
    # Median. Letzteres verhindert Peak-Fluten auf flachem Material
    # (Rauschen hat mean+std nah am Median - echte Ecken liegen weit drueber).
    threshold = max(
        float(active.mean() + threshold_std * active.std()),
        2.0 * float(np.median(active)),
    )

    order = np.argsort(-novelty)
    selected: List[int] = []
    for i in order:
        if novelty[i] < threshold:
            break
        if all(abs(int(i) - s) >= min_dist_beats for s in selected):
            selected.append(int(i))

    peaks = []
    for i in sorted(selected):
        if i < len(beats):
            peaks.append({
                "beat_index": i,
                "time": round(float(beats[i]), 3),
                "strength": round(float(novelty[i]), 4),
            })
    return peaks


def novelty_zscore_at(times: List[float], beats: List[float],
                      novelty: np.ndarray) -> List[float]:
    """Novelty (als z-Score des Sets) an beliebigen Zeitpunkten.

    Nimmt das Maximum im +-8-Beat-Umfeld, damit Kandidaten-Zeitpunkte
    (20s-Raster) den nahen Peak nicht knapp verfehlen.
    """
    if len(novelty) == 0:
        return [0.0 for _ in times]
    active = novelty[novelty > 0]
    if len(active) < 10:
        return [0.0 for _ in times]
    mu, sigma = float(active.mean()), float(active.std() or 1.0)

    beats_arr = np.asarray(beats[:len(novelty)])
    values = []
    for t in times:
        if len(beats_arr) == 0:
            values.append(0.0)
            continue
        idx = int(np.argmin(np.abs(beats_arr - t)))
        lo, hi = max(0, idx - 8), min(len(novelty), idx + 9)
        local_max = float(novelty[lo:hi].max()) if hi > lo else 0.0
        values.append((local_max - mu) / sigma)
    return values


def refine_boundary(t: float, beats: List[float], novelty: np.ndarray,
                    window_seconds: float = 30.0) -> Optional[Dict]:
    """Verfeinert eine grob gewaehlte Boundary auf Beat-Genauigkeit.

    - peak: naechstgelegene Novelty-Spitze (= Kern des Wechsels)
    - start: Beginn des Novelty-Anstiegs davor (= plausibler Blend-START,
      die Stelle, die DJs als 'Uebergang ab hier' hoeren)
    """
    if len(novelty) == 0 or len(beats) < 2:
        return None

    beats_arr = np.asarray(beats[:len(novelty)])
    mask = np.abs(beats_arr - t) <= window_seconds
    if not mask.any():
        return None
    candidates = np.where(mask)[0]
    peak_idx = int(candidates[np.argmax(novelty[candidates])])
    if novelty[peak_idx] <= 0:
        return None

    # Rueckwaerts: wo faellt die Novelty unter 25% des Peaks? -> Anstiegsbeginn
    rise_level = 0.25 * novelty[peak_idx]
    start_idx = peak_idx
    limit = max(0, peak_idx - 256)  # max ~64 Bars rueckwaerts
    while start_idx > limit and novelty[start_idx] > rise_level:
        start_idx -= 1

    return {
        "peak_time": round(float(beats_arr[peak_idx]), 3),
        "start_time": round(float(beats_arr[start_idx]), 3),
        "strength": round(float(novelty[peak_idx]), 4),
    }
