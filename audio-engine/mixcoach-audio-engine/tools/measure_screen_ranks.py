"""Misst fuer alle findbaren Ground-Truth-Tracks der Benchmark-Mixes ihren
RANG im Screen-Vorfilter (library_match._screen_score) - beantwortet: wie
gross muss SCREEN_TOP_K sein bzw. wie gut ist der Screen wirklich?

Aufruf:
    python -m tools.measure_screen_ranks --limit 8
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
    parser.add_argument("--labels-dir", type=Path, default=Path("datasets/synthetic/v1/labels"))
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    import librosa

    from app.audio.library_match import (
        MIN_PLAYED_SECONDS,
        SCREEN_POOL,
        _pool,
        _screen_score,
        _whiten,
        decimate_chroma,
    )
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    fingerprints = load_fingerprints()
    print(f"{len(fingerprints)} Fingerprints im Index.")

    all_ranks: list[int] = []
    for lf in sorted(args.labels_dir.glob("*.json"))[: args.limit]:
        mix_path = args.labels_dir.parent / "mixes" / f"{lf.stem}.wav"
        if not mix_path.exists():
            continue
        label = json.loads(lf.read_text(encoding="utf-8"))
        waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
        set_coarse = decimate_chroma(compute_chroma_matrix(waveform, sr))
        set_pooled = _whiten(_pool(set_coarse, SCREEN_POOL))

        scores = []
        for fp in fingerprints:
            s = _screen_score(set_pooled, np.asarray(fp["chroma"], dtype=np.float64))
            scores.append((s if np.isfinite(s) else float("inf"), _norm(fp.get("path") or "")))
        # inf (nicht screenbar) landet bewusst VORN (wird immer behalten)
        scores.sort(key=lambda t: -t[0] if np.isfinite(t[0]) else -1e18)
        rank_by_path = {p: i + 1 for i, (_, p) in enumerate(scores)}

        for t in label["tracks"]:
            span = float(t["end_in_mix"]) - float(t["start_in_mix"])
            if span < MIN_PLAYED_SECONDS:
                continue
            p = _norm(t["source_file"])
            rank = rank_by_path.get(p)
            if rank is None:
                continue
            all_ranks.append(rank)
            marker = " <-- FAELLT RAUS (>250)" if rank > 250 else ""
            print(f"  {lf.stem} rank={rank:5d}  {p.rsplit(chr(92), 1)[-1][:55]}{marker}")

    ranks = np.array(all_ranks)
    print("\n=== RANG-VERTEILUNG der echten Tracks im Screen ===")
    print(f"  n={len(ranks)}  median={np.median(ranks):.0f}  p90={np.percentile(ranks, 90):.0f}  max={ranks.max()}")
    for k in (250, 500, 1000, 2000, 3000):
        kept = (ranks <= k).mean() * 100
        print(f"  SCREEN_TOP_K={k}: {kept:.0f}% der echten Tracks ueberleben")
    return 0


if __name__ == "__main__":
    sys.exit(main())
