"""Lautheits-Analyse nach dem Rundfunk-Standard ITU-R BS.1770 (K-Gewichtung).

Warum das fuer DJs zaehlt: Ein Track, der 3 dB lauter einfliegt, klingt
"besser" (Lautheits-Taeuschung) - aber der Dancefloor hoert den Sprung,
und ueber ein Set schaukelt sich der Pegel hoch. Gute DJs halten die
Lautheit beim Uebergang stabil (Gain-Staging).

Gemessen wird eine Kurzzeit-Lautheitskurve (3s-Fenster, 1s-Schritt) auf
K-gewichtetem Signal. Fuer das Coaching zaehlt der RELATIVE Sprung
zwischen "vor dem Uebergang" und "nach dem Uebergang" in dB - der ist
unabhaengig von Aufnahmepegel und Kalibrierung.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import sosfilt

# Fensterung der Kurzzeit-Lautheit
WINDOW_SECONDS = 3.0
HOP_SECONDS = 1.0

# Ab diesem Sprung wird es als hoerbar gemeldet
JUMP_NOTICEABLE_DB = 2.0
JUMP_STRONG_DB = 4.0

# Messfenster relativ zum Uebergang (Blend selbst wird ausgespart,
# weil dort beide Tracks gleichzeitig laufen)
BEFORE_WINDOW = (-45.0, -10.0)
AFTER_WINDOW = (10.0, 45.0)


def _k_weighting_sos(sample_rate: int) -> np.ndarray:
    """BS.1770-K-Gewichtung: High-Shelf (+4 dB ab ~1.7 kHz, 'Kopf-Effekt')
    plus Hochpass bei ~38 Hz. Analytisch fuer beliebige Sampleraten
    entworfen (Audio-EQ-Cookbook-Biquads, Parameter aus dem Standard)."""
    # Stufe 1: High-Shelf
    f0, gain_db, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    b0 = a * ((a + 1) + (a - 1) * cos_w0 + 2 * math.sqrt(a) * alpha)
    b1 = -2 * a * ((a - 1) + (a + 1) * cos_w0)
    b2 = a * ((a + 1) + (a - 1) * cos_w0 - 2 * math.sqrt(a) * alpha)
    a0 = (a + 1) - (a - 1) * cos_w0 + 2 * math.sqrt(a) * alpha
    a1 = 2 * ((a - 1) - (a + 1) * cos_w0)
    a2 = (a + 1) - (a - 1) * cos_w0 - 2 * math.sqrt(a) * alpha
    shelf = np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])

    # Stufe 2: Hochpass
    f0, q = 38.13547087602444, 0.5003270373238773
    w0 = 2.0 * math.pi * f0 / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    b0 = (1 + cos_w0) / 2
    b1 = -(1 + cos_w0)
    b2 = (1 + cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha
    hp = np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])

    return np.vstack([shelf, hp])


def loudness_curve(waveform: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """Kurzzeit-Lautheit in LUFS-artigen dB. Liefert (Zeiten, Werte)."""
    if waveform.size < int(sample_rate * WINDOW_SECONDS):
        return np.array([]), np.array([])
    filtered = sosfilt(_k_weighting_sos(sample_rate), waveform.astype(np.float64))
    squared = filtered * filtered

    win = int(sample_rate * WINDOW_SECONDS)
    hop = int(sample_rate * HOP_SECONDS)
    # Fenster-Mittelwerte ueber kumulative Summe (schnell, kein Python-Loop)
    csum = np.concatenate([[0.0], np.cumsum(squared)])
    starts = np.arange(0, squared.size - win + 1, hop)
    means = (csum[starts + win] - csum[starts]) / win
    values = -0.691 + 10.0 * np.log10(np.maximum(means, 1e-12))
    times = (starts + win / 2.0) / sample_rate
    return times, values


def _window_loudness(times: np.ndarray, values: np.ndarray,
                     a: float, b: float) -> Optional[float]:
    if times.size == 0 or b <= a:
        return None
    mask = (times >= a) & (times <= b)
    if mask.sum() < 3:
        return None
    return float(np.median(values[mask]))


def annotate_transitions(transitions_detailed: List[Dict],
                         times: np.ndarray, values: np.ndarray,
                         duration: float) -> None:
    """Haengt an jeden Uebergang den Lautheits-Sprung in dB (nach - vor).

    None, wenn eines der Messfenster nicht sauber messbar ist (Set-Rand).
    Ehrlichkeit: lieber kein Wert als ein wackliger."""
    for t in transitions_detailed:
        start = t.get("start_sec")
        end = t.get("end_sec")
        if start is None or end is None:
            t["loudness_jump_db"] = None
            continue
        before = _window_loudness(times, values,
                                  max(0.0, start + BEFORE_WINDOW[0]),
                                  start + BEFORE_WINDOW[1])
        after = _window_loudness(times, values,
                                 end + AFTER_WINDOW[0],
                                 min(duration, end + AFTER_WINDOW[1]))
        if before is None or after is None:
            t["loudness_jump_db"] = None
            continue
        jump = round(after - before, 1)
        t["loudness_jump_db"] = jump
        if abs(jump) >= JUMP_STRONG_DB:
            richtung = "lauter" if jump > 0 else "leiser"
            direction = "louder" if jump > 0 else "quieter"
            t["feedback"] = (t.get("feedback") or "").rstrip() + (
                f" Achtung: Der neue Track kommt {abs(jump):.1f} dB {richtung} - "
                f"deutlich hoerbarer Pegelsprung, Gain vorher angleichen."
            )
            if t.get("feedback_en") is not None:
                t["feedback_en"] = t["feedback_en"].rstrip() + (
                    f" Warning: the new track comes in {abs(jump):.1f} dB {direction} - "
                    f"a clearly audible level jump, match gains beforehand."
                )
        elif abs(jump) >= JUMP_NOTICEABLE_DB:
            richtung = "lauter" if jump > 0 else "leiser"
            direction = "louder" if jump > 0 else "quieter"
            t["feedback"] = (t.get("feedback") or "").rstrip() + (
                f" Der neue Track ist {abs(jump):.1f} dB {richtung} - "
                f"leichter Pegelsprung."
            )
            if t.get("feedback_en") is not None:
                t["feedback_en"] = t["feedback_en"].rstrip() + (
                    f" The new track is {abs(jump):.1f} dB {direction} - "
                    f"a slight level jump."
                )


def set_loudness_summary(times: np.ndarray, values: np.ndarray) -> Optional[Dict]:
    """Set-weite Kennzahlen: Spannweite und Drift der Lautheit."""
    if values.size < 30:
        return None
    p10, p95 = np.percentile(values, [10, 95])
    third = values.size // 3
    drift = float(np.median(values[-third:]) - np.median(values[:third]))
    return {
        "range_db": round(float(p95 - p10), 1),
        "drift_db": round(drift, 1),
    }
