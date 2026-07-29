"""Instrumentierte Stage-B-Diagnose: repliziert match_track()s eigene
Grobsuche und zeigt fuer einen Track die Top-Kandidaten (Offset/Stretch/
Roh-Score), deren Feinjustierung und das _played_window-Ergebnis - also
exakt, welche Schwelle den Track verwirft (keine Anker-Annahmen wie in
deep_diagnose_match_fail, die bei Intro-Skip-Mixes irrefuehren).

Aufruf:
    python -m tools.trace_match_candidates --label datasets/synthetic/v1/labels/synth_000001.json --track "joe love"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--track", required=True)
    args = parser.parse_args()

    import librosa

    from app.audio.library_match import (
        FP_DECIMATE,
        MIN_OVERLAP_SECONDS,
        MIN_OVERLAP_SHARE,
        MIN_SCORE,
        PRE_SCORE,
        PEAK_MIN_DISTANCE_SECONDS,
        STRETCHES,
        TOP_OFFSETS,
        _played_window,
        _prepare_set,
        _refine_match,
        _set_fft,
        _stretch_time,
        _whiten,
        decimate_chroma,
    )
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    label = json.loads(args.label.read_text(encoding="utf-8"))
    mix_path = args.label.parent.parent / "mixes" / f"{args.label.stem}.wav"
    truth = next(t for t in label["tracks"] if args.track.lower() in t["source_file"].lower())
    fp = next(f for f in load_fingerprints()
              if args.track.lower() in (f.get("path") or "").lower())
    track_coarse = np.asarray(fp["chroma"], dtype=np.float64)

    waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    set_coarse = decimate_chroma(compute_chroma_matrix(waveform, sr))
    fps = sr / (512 * FP_DECIMATE)
    prepared = _prepare_set(set_coarse)
    m = prepared["white"].shape[1]

    print(f"Track: {Path(truth['source_file']).name}")
    print(f"Wahr im Set: {truth['start_in_mix']:.0f}-{truth['end_in_mix']:.0f}s | "
          f"Schwellen: PRE={PRE_SCORE} MIN_SCORE={MIN_SCORE}")

    # === Grobsuche exakt wie match_track ===
    min_overlap = int(MIN_OVERLAP_SECONDS * fps)
    variants = [_whiten(_stretch_time(track_coarse, s))[:, ::-1] for s in STRETCHES]
    lengths = [v.shape[1] for v in variants]
    n_max = max(lengths)
    nfft = 1 << (m + n_max - 2).bit_length()
    stack = np.zeros((len(variants), 12, n_max))
    for i, v in enumerate(variants):
        stack[i, :, : v.shape[1]] = v
    fa = _set_fft(prepared, nfft)
    fb = np.fft.rfft(stack, nfft, axis=2)
    corr = np.fft.irfft(fa[None] * fb, nfft, axis=2).sum(axis=1)

    candidates = []
    for v_idx, (stretch, n) in enumerate(zip(STRETCHES, lengths)):
        size = m + n - 1
        idx = np.arange(size)
        overlap = np.minimum(np.minimum(idx + 1, size - idx), min(m, n))
        required = max(min_overlap, int(MIN_OVERLAP_SHARE * n))
        valid = overlap >= required
        if not valid.any():
            continue
        scores = np.where(valid, corr[v_idx, :size] / np.maximum(overlap, 1), -1.0)
        work = scores.copy()
        min_dist = max(1, int(PEAK_MIN_DISTANCE_SECONDS * fps))
        for _ in range(3):
            j = int(np.argmax(work))
            peak = float(work[j])
            if peak <= PRE_SCORE:
                break
            candidates.append((peak, stretch, j - n + 1))
            work[max(0, j - min_dist): j + min_dist] = -1.0

    print(f"\nGrobsuche: {len(candidates)} Kandidaten ueber PRE_SCORE={PRE_SCORE}")
    candidates.sort(key=lambda c: -c[0])
    for coarse_score, stretch, start_frame in candidates[:TOP_OFFSETS]:
        refined = _refine_match(prepared["white"], track_coarse, stretch, start_frame,
                                min_overlap)
        use_stretch, use_start = ((refined["stretch"], refined["start_frame"])
                                  if refined is not None and refined["score"] >= coarse_score
                                  else (stretch, start_frame))
        tw = _whiten(_stretch_time(track_coarse, use_stretch))
        window = _played_window(prepared["white"], tw, use_start, fps)
        wtxt = "KEIN Fenster" if window is None else (
            f"Fenster {window[0]/fps:.0f}-{window[1]/fps:.0f}s score={window[2]:.3f}"
            + (" (< MIN_SCORE!)" if window[2] < MIN_SCORE else " => TREFFER"))
        print(f"  grob={coarse_score:.3f} stretch={stretch} offset={start_frame/fps:.0f}s"
              f" | fein={refined['score'] if refined else None} -> {wtxt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
