"""Tiefen-Diagnose fuer Tracks, die das VOLL-Matching verlieren (Stufe 2/3):
umgeht alle Schwellen und misst am WAHREN Zeitfenster (aus dem Label),
woran es konkret scheitert:

  - bester Grobsuche-Peak (vs. PRE_SCORE)
  - Frame-Aehnlichkeit im wahren Fenster: Mittel/Max + Anteil ueber
    PLAY_SIM_THRESHOLD (vs. der Anforderung "MIN_PLAYED_SECONDS anhaltend")
  - bestes Stretch

Aufruf:
    python -m tools.deep_diagnose_match_fail --label datasets/synthetic/v1/labels/synth_000003.json --track pentagram
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _norm(p: str) -> str:
    return str(Path(p)).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--track", required=True, help="Substring des Dateinamens")
    args = parser.parse_args()

    import librosa

    from app.audio.library_match import (
        FP_DECIMATE,
        MIN_PLAYED_SECONDS,
        PLAY_SIM_THRESHOLD,
        PRE_SCORE,
        STRETCHES,
        _stretch_time,
        _whiten,
        decimate_chroma,
    )
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    label = json.loads(args.label.read_text(encoding="utf-8"))
    mix_path = args.label.parent.parent / "mixes" / f"{args.label.stem}.wav"

    truth = next(t for t in label["tracks"] if args.track.lower() in t["source_file"].lower())
    fingerprints = load_fingerprints()
    fp = next(f for f in fingerprints if args.track.lower() in (f.get("path") or "").lower())
    track_coarse = np.asarray(fp["chroma"], dtype=np.float64)

    waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    set_coarse = decimate_chroma(compute_chroma_matrix(waveform, sr))
    set_white = _whiten(set_coarse)
    fps = sr / (512 * FP_DECIMATE)

    t_start = float(truth["start_in_mix"])
    t_end = float(truth["end_in_mix"])
    print(f"Track: {Path(truth['source_file']).name}")
    print(f"Wahr im Set: {t_start:.0f}-{t_end:.0f}s ({t_end-t_start:.0f}s), "
          f"Track-FP: {track_coarse.shape[1]} Frames ({track_coarse.shape[1]/fps:.0f}s)")
    print(f"Schwellen: PRE_SCORE={PRE_SCORE}, PLAY_SIM={PLAY_SIM_THRESHOLD}, "
          f"MIN_PLAYED={MIN_PLAYED_SECONDS}s")

    # Am WAHREN Offset (Label) fuer jedes Stretch die Frame-Aehnlichkeit messen.
    print("\nFrame-Aehnlichkeit am WAHREN Offset (Track-Anfang auf t_start gelegt):")
    best = None
    for stretch in STRETCHES:
        tw = _whiten(_stretch_time(track_coarse, stretch))
        start_frame = int(t_start * fps)
        a = max(0, start_frame)
        b = min(set_white.shape[1], start_frame + tw.shape[1])
        if b - a < 8:
            continue
        contrib = (set_white[:, a:b] * tw[:, a - start_frame: b - start_frame]).sum(axis=0)
        k = max(3, int(5 * fps))
        smooth = np.convolve(contrib, np.ones(k) / k, mode="same")
        frac_above = float((smooth >= PLAY_SIM_THRESHOLD).mean())
        # laengster zusammenhaengender Lauf ueber der Schwelle
        active = smooth >= PLAY_SIM_THRESHOLD
        longest = 0
        cur = 0
        for flag in active:
            cur = cur + 1 if flag else 0
            longest = max(longest, cur)
        row = (stretch, float(contrib.mean()), float(smooth.max()), frac_above, longest / fps)
        if best is None or row[2] > best[2]:
            best = row
        print(f"  stretch={stretch}: mean={row[1]:.3f} smooth_max={row[2]:.3f} "
              f"frac>={PLAY_SIM_THRESHOLD}: {row[3]*100:.0f}%  laengster Lauf={row[4]:.0f}s")

    if best is not None:
        s, mean, smax, frac, run = best
        print(f"\nBestes Stretch {s}: laengster Lauf {run:.0f}s (noetig: {MIN_PLAYED_SECONDS:.0f}s), "
              f"smooth_max {smax:.3f} (noetig: >={PLAY_SIM_THRESHOLD})")
        if run < MIN_PLAYED_SECONDS:
            print("=> DIAGNOSE: Aehnlichkeit haelt nicht lange genug an "
                  "(PLAY_SIM_THRESHOLD/MIN_PLAYED-Kombination schlaegt fehl).")
        else:
            print("=> DIAGNOSE: Fenster waere ok - Verlust muss in der Grobsuche liegen (PRE_SCORE).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
