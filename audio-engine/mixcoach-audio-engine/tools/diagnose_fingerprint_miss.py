"""Diagnose fuer verpasste Fingerprint-Treffer: WO geht ein Ground-Truth-
Track verloren?

Stufen des Matchings (library_match.py):
  1. Screen-Vorfilter (_prefilter_candidates, nur Libraries > 400 Tracks)
  2. Grobsuche (FFT-Korrelation, PRE_SCORE)
  3. Feinjustierung + gespieltes Fenster (_played_window, PLAY_SIM_THRESHOLD)
  4. Endschwelle (MIN_SCORE)

Fuer jeden findbaren Ground-Truth-Track eines Mixes wird gemeldet, welche
Stufe ihn verwirft - erst damit ist gezieltes Tuning moeglich statt Raten.

Aufruf:
    python -m tools.diagnose_fingerprint_miss --label datasets/synthetic/v1/labels/synth_000003.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def _norm(p: str) -> str:
    return str(Path(p)).lower()


def diagnose(mix_path: Path, label: dict) -> int:
    import librosa

    from app.audio.library_match import (
        MIN_PLAYED_SECONDS,
        MIN_SCORE,
        FP_DECIMATE,
        _prefilter_candidates,
        decimate_chroma,
        match_track,
    )
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    fingerprints = load_fingerprints()
    by_path = {_norm(fp["path"]): fp for fp in fingerprints if fp.get("path")}
    print(f"{len(fingerprints)} Fingerprints im Index.")

    waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    chroma = compute_chroma_matrix(waveform, sr)
    set_coarse = decimate_chroma(chroma)
    fps = sr / (512 * FP_DECIMATE)

    t0 = time.time()
    survivors = {_norm(fp["path"]) for fp in _prefilter_candidates(set_coarse, fingerprints)
                 if fp.get("path")}
    print(f"Vorfilter: {len(survivors)} Kandidaten ({time.time()-t0:.0f}s)")

    for t in label["tracks"]:
        span = float(t["end_in_mix"]) - float(t["start_in_mix"])
        p = _norm(t["source_file"])
        name = p.rsplit("\\", 1)[-1][:55]
        if span < MIN_PLAYED_SECONDS:
            print(f"  [zu kurz gespielt {span:.0f}s] {name}")
            continue
        fp = by_path.get(p)
        if fp is None:
            print(f"  [NICHT IM INDEX] {name}")
            continue

        stage = "1-VORFILTER" if p not in survivors else None
        hit = match_track(set_coarse, np.asarray(fp["chroma"], dtype=np.float64), fps)
        if hit is None:
            stage = stage or "2/3-MATCHING (kein Fenster ueber PLAY_SIM/PRE_SCORE)"
            print(f"  [VERLOREN in {stage}] {name}")
            continue
        ok_time = abs(hit["start"] - t["start_in_mix"]) < 60
        verdict = "OK" if (stage is None and hit["score"] >= MIN_SCORE and ok_time) else "PROBLEM"
        extra = "" if stage is None else f" (waere im Vorfilter rausgeflogen!)"
        print(f"  [{verdict}] {name}: score={hit['score']:.3f} (MIN {MIN_SCORE}), "
              f"erkannt {hit['start']:.0f}-{hit['end']:.0f}s vs. wahr {t['start_in_mix']:.0f}-{t['end_in_mix']:.0f}s, "
              f"stretch={hit['stretch']}{extra}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--mix", type=Path, default=None)
    args = parser.parse_args()
    label = json.loads(args.label.read_text(encoding="utf-8"))
    mix = args.mix or (args.label.parent.parent / "mixes" / f"{args.label.stem}.wav")
    return diagnose(mix, label)


if __name__ == "__main__":
    sys.exit(main())
