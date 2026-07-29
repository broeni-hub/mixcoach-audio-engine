"""EXPERIMENT: Rare-Hash-Offset-Screen als Vorfilter fuer gap_fill.

Der verworfene Screen (rohe Anzahl gemeinsamer Hashes) scheiterte, weil
haeufige Hashes (Zufalls-Kollisionen im 27-bit-Raum) dichte Fremd-Tracks
nach oben spuelten (Boratto: Rang 2773/6113). Dieser Screen misst
stattdessen dasselbe wie der volle Abgleich - OFFSET-KOHAERENZ - aber nur
ueber die SELTENEN Hashes des Mixes (Bucket-Groesse <= RARE_MAX): dort
gibt es kaum Kollisionen, die Expansion ist winzig (billig), und ein
echter Treffer zeigt trotzdem einen kohaerenten Offset-Peak.

Gemessen wird fuer Mix 3 (Boratto-Fall): Rang des echten Tracks unter
allen 6113, Screen-Kosten pro Track, Score-Verteilung.

Aufruf:
    python -m tools.experiment_rare_hash_screen
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

RARE_MAX = 2  # Mix-Hashes mit hoechstens so vielen Vorkommen zaehlen als "selten"


def rare_screen_prepare(mix_fp: dict) -> dict:
    """Seltene Mix-Hashes (sortiert) + zugehoerige Frames vorbereiten."""
    hashes = np.asarray(mix_fp["hashes"])
    frames = np.asarray(mix_fp["frames"])
    order = np.argsort(hashes, kind="stable")
    h, f = hashes[order], frames[order]
    uniq, starts, counts = np.unique(h, return_index=True, return_counts=True)
    keep_mask = counts <= RARE_MAX
    keep_idx = np.concatenate([np.arange(s, s + c) for s, c in
                               zip(starts[keep_mask], counts[keep_mask])]) if keep_mask.any() else np.array([], dtype=int)
    return {"hashes": h[keep_idx], "frames": f[keep_idx],
            "unique": uniq[keep_mask]}


def rare_screen_score(prep: dict, track_fp: dict, offset_bin: int = 5) -> int:
    """Offset-Histogramm-Peak NUR ueber seltene Mix-Hashes."""
    mh, mf = prep["hashes"], prep["frames"]
    if len(mh) == 0:
        return 0
    th = np.asarray(track_fp["hashes"])
    tf = np.asarray(track_fp["frames"])
    left = np.searchsorted(mh, th, side="left")
    right = np.searchsorted(mh, th, side="right")
    counts = right - left
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
    mix_fp = lm.fingerprint(wave, sr)
    prep = rare_screen_prepare(mix_fp)
    print(f"Mix-Hashes gesamt: {len(mix_fp['hashes'])}, davon selten (<= {RARE_MAX}x): {len(prep['hashes'])}")

    idx = load_landmark_fingerprints()
    boratto_tid = next(k for k, v in idx.items() if "pentagram" in (v.get("path") or "").lower())

    t0 = time.time()
    scores = []
    for tid, tfp in idx.items():
        if float(tfp.get("duration") or 0) < lm.GAP_MIN_SECONDS:
            continue
        scores.append((rare_screen_score(prep, tfp), tid))
    dt = time.time() - t0
    scores.sort(key=lambda x: -x[0])
    rank = next(i for i, (s, tid) in enumerate(scores) if tid == boratto_tid) + 1
    b_score = next(s for s, tid in scores if tid == boratto_tid)

    print(f"Screen-Kosten: {dt:.1f}s fuer {len(scores)} Tracks ({dt/len(scores)*1000:.1f}ms/Track)")
    print(f"Boratto: Score={b_score}, RANG {rank} von {len(scores)}")
    print("Top-10 Scores:", [s for s, _ in scores[:10]])
    print("Score an Rang 50/100/250/500:",
          scores[49][0], scores[99][0], scores[249][0], scores[499][0])
    for i, (s, tid) in enumerate(scores[:5]):
        print(f"  Top{i+1}: {Path(idx[tid].get('path') or '?').name[:50]} score={s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
