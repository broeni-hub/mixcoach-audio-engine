"""ML-Klassifikator fuer Trackwechsel (Gradient Boosting, JSON-Export).

Trainiert auf 5 annotierten Sets (34 echte Uebergaenge). Leave-One-Set-Out
validiert: Recall 88%, Precision 83% - gegenueber 91%/53% der
Hand-Kalibrierung eine Verdopplung der Precision.

Die Inferenz laeuft OHNE sklearn: Das Modell liegt als JSON im Repo
(app/models/track_change_gbm.json), die Baum-Traversierung ist pures
numpy. Paritaet mit sklearn wurde beim Export verifiziert (Abweichung 0).

Wichtigste Features laut Modell: Harmonie-Wechsel (chroma_75_15, 46%),
Randlage (10%), Timbre-Wechsel (mfcc, 8%), Rhythmus-Textur (6%).
Die frueher 'zu schwachen' Einzelsignale werden im Verbund nuetzlich.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy import signal as sps

from app.audio.foote import (
    beat_sync_features,
    foote_novelty,
    novelty_zscore_at,
    refine_boundary,
)

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "track_change_gbm.json"

# Dichte Kandidaten: alle GRID_STEP Sekunden ein Pruefpunkt uebers ganze Set.
# Behebt den Kandidaten-Engpass: Vorher konnte das Modell nur Energie-Zonen
# bewerten - ein Uebergang ohne Energie-Signatur war unsichtbar, egal wie
# deutlich Harmonie/Timbre wechselten.
GRID_STEP_SECONDS = 20.0
GRID_DEDUPE_SECONDS = 10.0  # Grid-Punkt entfaellt, wenn eine Zone naeher liegt

# Position von "edge" im Feature-Vektor (siehe extract_zone_features) - fix
# statt x[-1], damit neue, ans Ende angehaengte Features (beat_cv, exit_rough)
# diesen Lookup nicht verschieben.
EDGE_FEATURE_INDEX = 13

_model_cache: Optional[Dict] = None


def generate_candidates(zones: List[Dict], duration: float,
                        grid_step: float = GRID_STEP_SECONDS) -> List[Dict]:
    """Energie-Zonen + dichtes Zeitraster = vollstaendige Kandidatenmenge.

    Grid-Punkte tragen leere Zonen-Features (score=0) - das Modell erkennt
    sie an Harmonie-/Timbre-/Rhythmus-Wechseln. Wird von Training UND
    Inferenz genutzt (app/calibration/build_features.py importiert diese
    Funktion) - Train/Serve-Drift ist damit ausgeschlossen."""
    candidates = list(zones)
    zone_times = [float(z["time"]) for z in zones]

    t = grid_step
    while t < duration - grid_step / 2:
        if all(abs(t - zt) > GRID_DEDUPE_SECONDS for zt in zone_times):
            candidates.append({
                "time": round(t, 2),
                "score": 0.0,
                "signals": {"blend_score": 0.0, "drop_score": 0.0, "bass_swap_score": 0.0},
                "energy_before": 0.0, "energy_current": 0.0, "energy_after": 0.0,
                "type": "grid_probe",
                "confidence": 0.0,
                "grid": True,
            })
        t += grid_step

    return sorted(candidates, key=lambda c: float(c["time"]))


def load_model() -> Optional[Dict]:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        _model_cache = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _model_cache


def predict_probability(model: Dict, x: List[float]) -> float:
    """Raw-Score = init + lr * Summe(Baum-Outputs); Sigmoid -> Wahrscheinlichkeit."""
    raw = model["init"]
    lr = model["learning_rate"]
    for tree in model["trees"]:
        node = 0
        while tree["left"][node] != -1:
            if x[tree["feature"][node]] <= tree["threshold"][node]:
                node = tree["left"][node]
            else:
                node = tree["right"][node]
        raw += lr * tree["value"][node]
    return 1.0 / (1.0 + math.exp(-raw))


# ---------------------------------------------------------------------
# Feature-Extraktion (muss exakt dem Trainings-Code entsprechen!)
# ---------------------------------------------------------------------


def compute_mfcc_matrix(waveform, sample_rate: int, hop_length: int = 512,
                        chunk_seconds: float = 480.0) -> np.ndarray:
    import librosa
    n = len(waveform)
    step = int(chunk_seconds * sample_rate)
    parts = []
    for start in range(0, n, step):
        seg = np.asarray(waveform[start:start + step])
        if len(seg) < sample_rate:
            break
        parts.append(librosa.feature.mfcc(y=seg, sr=sample_rate, n_mfcc=20, hop_length=hop_length))
    if not parts:
        return np.zeros((20, 0))
    return np.concatenate(parts, axis=1)


def compute_hiband_envelope(waveform, sample_rate: int, hop_length: int = 512) -> np.ndarray:
    """RMS-Envelope des Hochband-Signals (>4kHz) - Percussion-Textur."""
    sos = sps.butter(4, 4000, btype="high", fs=sample_rate, output="sos")
    filtered = sps.sosfilt(sos, np.asarray(waveform))
    n = len(filtered) // hop_length * hop_length
    if n == 0:
        return np.zeros(0)
    frames = filtered[:n].reshape(-1, hop_length)
    return np.sqrt(np.mean(frames ** 2, axis=1))


def _wmean_factory(mat: np.ndarray, fps: float):
    if mat.shape[1] == 0:
        return lambda t0, t1: None
    csum = np.cumsum(mat, axis=1)

    def wmean(t0: float, t1: float):
        a = max(0, int(t0 * fps))
        b = min(mat.shape[1], int(t1 * fps))
        if b - a < 10:
            return None
        v = (csum[:, b - 1] - (csum[:, a - 1] if a > 0 else 0)) / (b - a)
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else None

    return wmean


def _dist(wmean, t: float, width: float, gap: float) -> float:
    before = wmean(t - gap - width, t - gap)
    after = wmean(t + gap, t + gap + width)
    if before is None or after is None:
        return 0.0
    return float(1 - np.dot(before, after))


def _rhythm_dist(env: np.ndarray, t: float, fps: float,
                 width: float = 32.0, gap: float = 8.0) -> float:
    def prof(t0: float, t1: float):
        seg = env[max(0, int(t0 * fps)):int(t1 * fps)]
        if len(seg) < int(10 * fps):
            return None
        seg = seg - seg.mean()
        denom = float(np.dot(seg, seg))
        if denom <= 0:
            return None
        lags = np.arange(int(0.1 * fps), int(1.2 * fps))
        p = np.array([float(np.dot(seg[:-l], seg[l:])) / denom for l in lags])
        norm = np.linalg.norm(p)
        return p / norm if norm > 0 else None

    before = prof(t - gap - width, t - gap)
    after = prof(t + gap, t + gap + width)
    if before is None or after is None:
        return 0.0
    return float(1 - np.dot(before, after))


# --- Zusaetzliche Features aus dem Composite-Quality-Score-Umbau
# (app/audio/scoring/beat_alignment.py, exit_quality.py) - dieselbe Idee,
# aber hier fuer JEDEN Kandidaten statt nur bestaetigte Uebergaenge, und
# ohne Demucs (zu teuer fuer hunderte Kandidaten/Set). Rueckgabe 0.0, wenn
# nicht messbar - wie jedes andere Feature hier auch. ---


def _beat_interval_cv(beats: List[float], t: float, half_window: float = 12.0) -> float:
    """Variationskoeffizient der Beat-Abstaende um den Kandidaten. Hohe
    Werte deuten auf einen unregelmaessigen Puls hin (zwei kollidierende
    Tempi) - ein moeglicher Hinweis auf einen echten Trackwechsel, den die
    bestehenden Chroma-/MFCC-Features nicht abdecken."""
    if not beats:
        return 0.0
    window = [b for b in beats if t - half_window <= b <= t + half_window]
    if len(window) < 4:
        return 0.0
    intervals = np.diff(np.array(window))
    intervals = intervals[(intervals > 0.15) & (intervals < 2.0)]  # 30-400 BPM
    if len(intervals) < 3:
        return 0.0
    mean_interval = float(np.mean(intervals))
    if mean_interval <= 0:
        return 0.0
    return float(min(2.0, np.std(intervals) / mean_interval))


def _exit_roughness(energy_points: List[Dict], t: float, window: float = 20.0) -> float:
    """Wie zackig/unruhig war der Energieverlauf UNMITTELBAR VOR dem
    Kandidaten (statt einer glatten Abklingkurve)? 0 = glatt/nicht
    messbar, hoehere Werte = unruhig (moeglicher Hinweis auf einen bereits
    laufenden Uebergang statt einer stabilen Track-Mitte)."""
    if not energy_points:
        return 0.0
    values = [float(p["rms"]) for p in energy_points if t - window <= float(p["time"]) <= t]
    if len(values) < 5:
        return 0.0
    arr = np.array(values)
    span = float(np.max(arr) - np.min(arr))
    if span <= 1e-9:
        return 0.0
    diffs = np.diff(arr)
    positive_jumps = diffs[diffs > 0]
    return float(min(2.0, np.sum(positive_jumps) / span))


def extract_zone_features(
    zones: List[Dict],
    chroma: np.ndarray,
    mfcc: np.ndarray,
    env_hi: np.ndarray,
    duration: float,
    sample_rate: int,
    hop_length: int = 512,
    beats: Optional[List[float]] = None,
    beat_novelty: Optional[np.ndarray] = None,
    energy_points: Optional[List[Dict]] = None,
) -> List[List[float]]:
    """Feature-Vektoren in exakt der Trainings-Reihenfolge (model['features']).

    beat_cv/exit_rough werden AN DAS ENDE angehaengt (Features 16+17) -
    absichtlich append-only, damit die Baum-Feature-Indizes eines bereits
    trainierten Modells (kennt nur Index 0-14) weiter auf dieselben Werte
    zeigen, auch wenn hier ein laengerer Vektor uebergeben wird."""
    fps = sample_rate / hop_length
    wm_chroma = _wmean_factory(chroma, fps)
    wm_mfcc = _wmean_factory(mfcc[1:] if mfcc.shape[0] > 1 else mfcc, fps)
    ztimes = sorted(float(z["time"]) for z in zones)

    # Feature 15: Foote-Novelty (z-Score) am Kandidaten - beat-genaue
    # Selbstaehnlichkeits-Ecke, unabhaengig von Energie.
    times = [float(z["time"]) for z in zones]
    if beats is not None and beat_novelty is not None and len(beat_novelty):
        foote_values = novelty_zscore_at(times, beats, beat_novelty)
    else:
        foote_values = [0.0] * len(zones)

    vectors = []
    for z, foote_z in zip(zones, foote_values):
        t = float(z["time"])
        neighbors = [abs(t - o) for o in ztimes if o != t]
        signals = z.get("signals", {})
        vectors.append([
            float(z.get("score", 0)),
            float(signals.get("blend_score", 0)),
            float(signals.get("drop_score", 0)),
            float(signals.get("bass_swap_score", 0)),
            _dist(wm_chroma, t, 60, 15),
            _dist(wm_chroma, t, 45, 10),
            _dist(wm_mfcc, t, 60, 15),
            _rhythm_dist(env_hi, t, fps),
            float(z.get("energy_before", 0) or 0),
            float(z.get("energy_current", 0) or 0),
            float(z.get("energy_after", 0) or 0),
            t / duration if duration > 0 else 0.0,
            min(neighbors) if neighbors else 999.0,
            1.0 if (t < 90 or t > duration - 60) else 0.0,
            float(foote_z),
            _beat_interval_cv(beats or [], t),
            _exit_roughness(energy_points or [], t),
        ])
    return vectors


def select_track_changes_ml(
    zones: List[Dict],
    chroma: np.ndarray,
    mfcc: np.ndarray,
    env_hi: np.ndarray,
    duration: float,
    sample_rate: int,
    hop_length: int = 512,
    beats: Optional[List[float]] = None,
    energy_points: Optional[List[Dict]] = None,
) -> Optional[List[Dict]]:
    """ML-Auswahl der Trackwechsel. None, wenn kein Modell verfuegbar ist
    (dann greift die heuristische Fusion als Fallback)."""
    model = load_model()
    if model is None:
        return None

    candidates = generate_candidates(zones, duration)
    if not candidates:
        return None

    # Beat-synchrone Foote-Novelty (fuer Feature 15 + Start-Verfeinerung).
    beat_novelty = None
    if beats and len(beats) > 130:
        feat_sync = beat_sync_features(chroma, mfcc, beats, sample_rate, hop_length)
        beat_novelty = foote_novelty(feat_sync)

    vectors = extract_zone_features(
        candidates, chroma, mfcc, env_hi, duration, sample_rate, hop_length,
        beats=beats, beat_novelty=beat_novelty, energy_points=energy_points,
    )
    min_p = model["selection"]["min_probability"]
    min_gap = model["selection"]["min_gap_seconds"]

    scored = []
    for zone, x in zip(candidates, vectors):
        p = predict_probability(model, x)
        # Index 13 = edge-Flag - FIXER Index, nicht x[-1]: seit beat_cv/
        # exit_rough ans Ende angehaengt wurden, ist edge nicht mehr das
        # letzte Element (war ein Bug beim ersten Anhaengen, hier vermieden).
        scored.append((float(zone["time"]), p, zone, x[EDGE_FEATURE_INDEX]))

    selected: List[Dict] = []
    for t, p, zone, edge in sorted(scored, key=lambda s: -s[1]):
        if p < min_p or edge > 0.5:
            continue
        if all(abs(t - b["time"]) >= min_gap for b in selected):
            boundary = {
                **zone,
                "time": round(t, 2),
                "track_change_probability": round(p, 3),
                "detected_by": "ml",
            }
            # Beat-genaue Verfeinerung: Peak = Kern des Wechsels,
            # Anstiegsbeginn = plausibler Blend-START (Nutzerfeedback:
            # "Starts sind nicht erkannt").
            if beats and beat_novelty is not None:
                refined = refine_boundary(t, beats, beat_novelty)
                if refined is not None:
                    boundary["time"] = refined["peak_time"]
                    boundary["blend_start"] = refined["start_time"]
                    boundary["foote_strength"] = refined["strength"]
            selected.append(boundary)

    # Nach Verfeinerung: Duplikate entfernen (zwei Kandidaten koennen auf
    # denselben Peak gesnappt worden sein).
    deduped: List[Dict] = []
    for b in sorted(selected, key=lambda b: -(b.get("track_change_probability") or 0)):
        if all(abs(b["time"] - d["time"]) >= min_gap * 0.5 for d in deduped):
            deduped.append(b)

    return sorted(deduped, key=lambda b: b["time"])
