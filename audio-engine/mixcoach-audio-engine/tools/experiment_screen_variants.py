"""EXPERIMENT: Drei billige Screen-Varianten fuer gap_fill, alle basierend
auf dem ECHTEN Offset-Histogramm-Abgleich (der Boratto nachweislich findet),
nur verkleinert - statt einer Zaehl-Heuristik (2x gescheitert: rohe Anzahl
Rang 2773, Rare-Hash Rang 2843 - repetitive Tracks haben kaum seltene
Hashes, genau die Klasse, fuer die Landmark gebaut wurde).

  A) Subsample 10% der Track-Hashes (jeder 10.), voller Mix-Abgleich
  B) Subsample 5%
  C) Track-Hash-Dedupe: nur EINDEUTIGE Track-Hashes (erster Frame je Hash)

Gemessen je Variante an Mix 3: Boratto-Rang unter allen 6113 + ms/Track.

Aufruf:
    python -m tools.experiment_screen_variants
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np


def _mini_match(mix_prep: dict, th: np.ndarray, tf: np.ndarray,
                max_bucket: int, offset_bin: int = 5) -> int:
    """Kern des echten match(), auf gegebene Track-Hash-Teilmenge."""
    mh, mf = mix_prep["hashes"], mix_prep["frames"]
    left = np.searchsorted(mh, th, side="left")
    right = np.searchsorted(mh, th, side="right")
    counts = np.minimum(right - left, max_bucket)
    keep = counts > 0
    if not keep.any():
        return 0
    k = counts[keep]
    starts = left[keep]
    total = int(k.sum())
    within = np.arange(total) - np.repeat(np.cumsum(k) - k, k)
    idx = np.repeat(starts, k) + within
    delta = (mf[idx].astype(np.int64) - np.repeat(tf[keep].astype(np.int64), k)) // offset_bin
    _, bin_counts = np.unique(delta, return_counts=True)
    return int(bin_counts.max())


def main() -> int:
    import librosa

    from app.audio import landmark_match as lm
    from app.library.manager import load_landmark_fingerprints

    wave, sr = librosa.load("datasets/synthetic/v1/mixes/synth_000003.wav", sr=lm.SR, mono=True)
    mix_prep = lm.prepare_mix(lm.fingerprint(wave, sr))
    idx = load_landmark_fingerprints()
    boratto_tid = next(k for k, v in idx.items() if "pentagram" in (v.get("path") or "").lower())
    tracks = [(tid, tfp) for tid, tfp in idx.items()
              if float(tfp.get("duration") or 0) >= lm.GAP_MIN_SECONDS]
    print(f"{len(tracks)} Kandidaten-Tracks")

    def evaluate(name, prep_track):
        t0 = time.time()
        scores = []
        for tid, tfp in tracks:
            th, tf = prep_track(tfp)
            scores.append((_mini_match(mix_prep, th, tf, lm.MAX_BUCKET), tid))
        dt = time.time() - t0
        scores.sort(key=lambda x: -x[0])
        rank = next(i for i, (s, tid) in enumerate(scores) if tid == boratto_tid) + 1
        b = next(s for s, tid in scores if tid == boratto_tid)
        print(f"\n[{name}] {dt/len(tracks)*1000:.1f}ms/Track (gesamt {dt:.0f}s)")
        print(f"  Boratto: Score={b}, RANG {rank}")
        print(f"  Score an Rang 50/100/250/500: {scores[49][0]} {scores[99][0]} {scores[249][0]} {scores[499][0]}")

    def sub10(tfp):
        th = np.asarray(tfp["hashes"])[::10]
        tf = np.asarray(tfp["frames"])[::10]
        return th, tf

    def sub20(tfp):
        th = np.asarray(tfp["hashes"])[::20]
        tf = np.asarray(tfp["frames"])[::20]
        return th, tf

    def dedupe(tfp):
        th = np.asarray(tfp["hashes"])
        tf = np.asarray(tfp["frames"])
        _, first_idx = np.unique(th, return_index=True)
        return th[first_idx], tf[first_idx]

    evaluate("A: Subsample 1/10", sub10)
    evaluate("B: Subsample 1/20", sub20)
    evaluate("C: Dedupe (eindeutige Track-Hashes)", dedupe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
