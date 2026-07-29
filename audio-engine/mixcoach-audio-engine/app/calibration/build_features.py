"""Feature-Aufbereitung fuer das Trackwechsel-Modell.

Verwandelt ein Set (WAV) + Wahrheit (Annotation oder App-Feedback) in
Trainingszeilen. Nutzt EXAKT dieselbe Feature-Extraktion wie die Inferenz
(app.audio.ml_classifier) - Training und Live-Betrieb koennen nicht
auseinanderlaufen.

Zwei Wahrheits-Formate:
1. Chat-Annotation:  {"true_transitions_sec": [176, 320, ...]}
2. App-Feedback:     {"verdicts": {...}, "missed": [...]}
   - correct       -> positiver Anker bei midSec
   - timing_off    -> positiver Anker bei correctedSec (praeziser!)
   - not_a_transition -> erzwungenes Negativ nahe midSec
   - missed        -> positiver Anker; ohne Zone in der Naehe wird ein
                      Pseudo-Kandidat angelegt (Zonen-Features = 0)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.audio.beats import detect_beat_grid
from app.audio.energy import calculate_energy_curve
from app.audio.foote import beat_sync_features, foote_novelty
from app.audio.ml_classifier import (
    compute_hiband_envelope,
    compute_mfcc_matrix,
    extract_zone_features,
    generate_candidates,
)
from app.audio.set_analyzer_helpers import detect_set_transition_zones
from app.audio.track_change_classifier import compute_chroma_matrix

SR = 22050
FAIR_BEFORE = 45.0   # Anker = Blend-Start, Zone = Blend-Zentrum
FAIR_AFTER = 60.0
NEG_WINDOW = 10.0    # not_a_transition wirkt in diesem Umkreis


class _Audio:
    def __init__(self, waveform, filename):
        self.waveform = waveform
        self.sample_rate = SR
        self.duration_seconds = len(waveform) / SR
        self.filename = filename


def load_truth(path: Path) -> Dict:
    """Beide Wahrheits-Formate in Anker-Listen normalisieren."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    positives: List[float] = list(data.get("true_transitions_sec", []))
    negatives: List[float] = []

    for entry in data.get("verdicts", {}).values():
        verdict = entry.get("verdict")
        if verdict == "correct":
            positives.append(float(entry["midSec"]))
        elif verdict == "timing_off":
            positives.append(float(entry.get("correctedSec", entry["midSec"])))
        elif verdict == "not_a_transition":
            negatives.append(float(entry["midSec"]))

    positives.extend(float(s) for s in data.get("missed", []))

    return {"positives": sorted(set(positives)), "negatives": sorted(set(negatives))}


def build_set_rows(wav_path: str, truth: Dict, set_name: str,
                   waveform: Optional[np.ndarray] = None) -> List[Dict]:
    """Alle Trainingszeilen fuer ein Set (Kandidaten + Labels + Features)."""
    import librosa

    if waveform is None:
        waveform, _ = librosa.load(wav_path, sr=SR, mono=True)

    audio = _Audio(waveform, set_name)
    duration = audio.duration_seconds

    energy = calculate_energy_curve(audio, window_seconds=1.0)
    zones = detect_set_transition_zones(energy)

    # EXAKT dieselbe Kandidaten-Erzeugung wie die Live-Inferenz
    # (Energie-Zonen + dichtes 20s-Raster) - kein Train/Serve-Drift.
    candidates = generate_candidates(zones, duration)

    chroma = compute_chroma_matrix(waveform, SR)
    mfcc = compute_mfcc_matrix(waveform, SR)
    env_hi = compute_hiband_envelope(waveform, SR)

    audio.waveform = waveform
    beat_grid = detect_beat_grid(audio)
    beats = beat_grid["beats"]
    beat_novelty = None
    if len(beats) > 130:
        feat_sync = beat_sync_features(chroma, mfcc, beats, SR)
        beat_novelty = foote_novelty(feat_sync)

    vectors = extract_zone_features(
        candidates, chroma, mfcc, env_hi, duration, SR,
        beats=beats, beat_novelty=beat_novelty, energy_points=energy.get("points", []),
    )

    feature_names = ["score", "blend", "drop", "bass_swap", "chroma_75_15",
                     "chroma_45_10", "mfcc_dist", "rhythm_hi", "e_before",
                     "e_current", "e_after", "pos_in_set", "nearest_zone",
                     "edge", "foote", "beat_cv", "exit_rough"]

    rows = []
    for cand, vec in zip(candidates, vectors):
        t = float(cand["time"])
        label = int(any(-FAIR_BEFORE <= t - a <= FAIR_AFTER for a in truth["positives"]))
        # Explizites Nutzer-Nein schlaegt alles:
        if any(abs(t - n) <= NEG_WINDOW for n in truth["negatives"]):
            label = 0
        row = {"set": set_name, "t": t, "label": label,
               "grid": bool(cand.get("grid", False))}
        row.update(dict(zip(feature_names, vec)))
        rows.append(row)

    return rows
