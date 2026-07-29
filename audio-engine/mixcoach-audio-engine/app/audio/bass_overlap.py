"""Bass-Overlap-Messung: liefen im Blend BEIDE Baesse gleichzeitig?

Erst durch das Library-Fingerprinting messbar: Wir wissen, WELCHER Track
WANN im Set lief (inkl. Tempo-Faktor und Track-Position). Damit laesst
sich der Tieftonbereich (<120 Hz) der Aufnahme mit dem Tiefton der
beteiligten Original-Tracks vergleichen:

1. Kalibrierung: Kurz VOR dem Blend spielt nur Track A -> Verhaeltnis
   Aufnahme/Track-A ergibt den Wiedergabe-Gain von A. Kurz NACH dem
   Blend analog fuer B.
2. Im Blend: Ist die Tiefton-Energie der Aufnahme naeher an
   "A + B gleichzeitig" oder an "nur der lautere von beiden"?
   Das Verhaeltnis (0..1) wird zum Score 0-100 (hoch = beide Baesse
   liefen uebereinander = matschig).

Ehrlichkeit: Gemessen wird nur, wenn beide Tracks sicher erkannt wurden,
die Original-Dateien lesbar sind und saubere Solo-Fenster fuer die
Kalibrierung existieren. Sonst bleibt der Wert null.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

LOWBAND_HZ = 120.0
HOP_SECONDS = 0.25
CALIB_GAP = 4.0          # Abstand der Solo-Fenster zum Blend (s)
CALIB_LEN = 14.0         # Laenge der Solo-Fenster (s)
MIN_CALIB_POINTS = 20
ENERGY_FLOOR = 1e-10
OVERLAP_BAD = 60         # ab hier gilt: hoerbar matschig


def lowband_envelope(waveform: np.ndarray, sample_rate: int,
                     hop_seconds: float = HOP_SECONDS):
    """Tiefton-Energie (<120 Hz) in Fenstern von hop_seconds.

    Liefert (zeiten, energie) - Energie linear (nicht dB), damit sich
    Anteile addieren lassen.
    """
    sos = butter(4, LOWBAND_HZ, btype="low", fs=sample_rate, output="sos")
    low = sosfilt(sos, waveform.astype(np.float64))
    squared = low * low
    hop = max(1, int(hop_seconds * sample_rate))
    n = squared.size // hop
    if n == 0:
        return np.array([]), np.array([])
    energy = squared[: n * hop].reshape(n, hop).mean(axis=1)
    times = (np.arange(n) + 0.5) * hop_seconds
    return times, energy


def _read_track_lowband(path: str, t0: float, t1: float):
    """Tiefton-Envelope eines Track-Ausschnitts [t0, t1] in TRACK-Zeit."""
    info = sf.info(path)
    sr = info.samplerate
    start = max(0, int(t0 * sr))
    stop = min(info.frames, int(t1 * sr))
    if stop - start < sr * 5:
        return None
    data, _ = sf.read(path, start=start, stop=stop, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    times, energy = lowband_envelope(mono, sr)
    return times + start / sr, energy  # Zeiten in Track-Zeit


def _set_to_track_time(set_t: np.ndarray, match: Dict) -> np.ndarray:
    """Set-Zeit -> Track-Zeit (Tempo-Faktor + Fensterversatz aus dem Match)."""
    stretch = float(match.get("stretch") or 1.0)
    w0 = float(match["start"])
    offset_track = float(match.get("track_offset") or 0.0) / stretch
    return offset_track + (set_t - w0) / stretch


def _median_ratio(set_e: np.ndarray, trk_e: np.ndarray) -> Optional[float]:
    mask = trk_e > ENERGY_FLOOR
    if mask.sum() < MIN_CALIB_POINTS:
        return None
    return float(np.median(set_e[mask] / trk_e[mask]))


def _grid_interp(grid: np.ndarray, times: np.ndarray, values: np.ndarray) -> np.ndarray:
    return np.interp(grid, times, values, left=np.nan, right=np.nan)


def measure_transition_overlap(set_times: np.ndarray, set_energy: np.ndarray,
                               match_a: Dict, match_b: Dict,
                               blend_start: float, blend_end: float) -> Optional[int]:
    """Bass-Overlap-Score 0-100 fuer EINEN Uebergang - oder None."""
    path_a, path_b = match_a.get("path"), match_b.get("path")
    if not path_a or not path_b:
        return None
    if not Path(path_a).exists() or not Path(path_b).exists():
        return None
    if blend_end - blend_start < 4.0:
        return None

    # Solo-Kalibrierfenster in Set-Zeit
    a_solo = (blend_start - CALIB_GAP - CALIB_LEN, blend_start - CALIB_GAP)
    b_solo = (blend_end + CALIB_GAP, blend_end + CALIB_GAP + CALIB_LEN)
    if a_solo[0] < float(match_a["start"]) or b_solo[1] > float(match_b["end"]):
        return None  # keine sauberen Solo-Fenster -> ehrlich: nicht messbar

    span_a = (a_solo[0], blend_end + 2.0)
    span_b = (blend_start - 2.0, b_solo[1])

    try:
        trk_a = _read_track_lowband(path_a, *(_set_to_track_time(np.array(span_a), match_a)))
        trk_b = _read_track_lowband(path_b, *(_set_to_track_time(np.array(span_b), match_b)))
    except Exception:
        return None
    if trk_a is None or trk_b is None:
        return None

    grid = np.arange(a_solo[0], b_solo[1], HOP_SECONDS)
    set_on_grid = _grid_interp(grid, set_times, set_energy)
    a_on_grid = _grid_interp(_set_to_track_time(grid, match_a), *trk_a)
    b_on_grid = _grid_interp(_set_to_track_time(grid, match_b), *trk_b)

    def window_mask(w):
        return (grid >= w[0]) & (grid <= w[1])

    m_a = window_mask(a_solo) & ~np.isnan(set_on_grid) & ~np.isnan(a_on_grid)
    m_b = window_mask(b_solo) & ~np.isnan(set_on_grid) & ~np.isnan(b_on_grid)
    gain_a = _median_ratio(set_on_grid[m_a], a_on_grid[m_a]) if m_a.any() else None
    gain_b = _median_ratio(set_on_grid[m_b], b_on_grid[m_b]) if m_b.any() else None
    if not gain_a or not gain_b or gain_a <= 0 or gain_b <= 0:
        return None

    m_blend = (window_mask((blend_start, blend_end))
               & ~np.isnan(set_on_grid) & ~np.isnan(a_on_grid) & ~np.isnan(b_on_grid))
    if m_blend.sum() < 8:
        return None

    ea = gain_a * a_on_grid[m_blend]
    eb = gain_b * b_on_grid[m_blend]
    single = np.maximum(ea, eb)
    both = ea + eb
    denom = both - single  # = min(ea, eb)
    valid = denom > (0.05 * np.maximum(single, ENERGY_FLOOR))
    if valid.sum() < 8:
        return None  # einer der Baesse ist im Blend praktisch stumm -> kein Overlap messbar

    ratio = (set_on_grid[m_blend][valid] - single[valid]) / denom[valid]
    ratio = np.clip(ratio, 0.0, 1.0)
    return int(round(float(np.median(ratio)) * 100))


def annotate_bass_overlap(transitions_detailed: List[Dict], matches: List[Dict],
                          set_waveform: np.ndarray, sample_rate: int) -> None:
    """Haengt bass_overlap_score an Uebergaenge, die zwischen zwei sicher
    erkannten Tracks liegen. Alle anderen behalten ehrlich None."""
    if len(matches) < 2:
        return
    set_times, set_energy = lowband_envelope(set_waveform, sample_rate)
    if set_times.size == 0:
        return

    pairs = list(zip(matches, matches[1:]))
    for t in transitions_detailed:
        mid = t.get("mid_sec")
        if mid is None:
            continue
        for ma, mb in pairs:
            blend_start = max(float(ma["start"]), float(mb["start"]))
            blend_end = min(float(ma["end"]), float(mb["end"]))
            if blend_end <= blend_start:
                blend_end = blend_start + 8.0
            if not (blend_start - 60 <= mid <= blend_end + 60):
                continue
            score = measure_transition_overlap(
                set_times, set_energy, ma, mb,
                float(t.get("start_sec") or blend_start),
                float(t.get("end_sec") or blend_end),
            )
            if score is None:
                break
            t["bass_overlap_score"] = score
            if score >= OVERLAP_BAD:
                t["feedback"] = (t.get("feedback") or "").rstrip() + (
                    f" Beide Baesse liefen im Blend uebereinander (Overlap {score}/100) - "
                    f"schneide den Bass des alten Tracks frueher raus (EQ/Kill)."
                )
                if t.get("feedback_en") is not None:
                    t["feedback_en"] = t["feedback_en"].rstrip() + (
                        f" Both basslines ran on top of each other during the blend "
                        f"(overlap {score}/100) - cut the outgoing bass earlier (EQ/kill)."
                    )
            break
