"""Diagnose: Warum bleiben Zeitbereiche eines Sets ohne Library-Match?

Laesst den ECHTEN Matcher mit stark abgesenkter Endschwelle laufen und
zeigt pro Luecke die besten (auch unterschwelligen) Kandidaten. Damit wird
unterscheidbar:
  - Beinahe-Treffer (Score 0.15-0.30): Schwellen-/Robustheitsproblem ->
    gezielt loesbar (z.B. Segment-basiertes Nachmatchen)
  - gar keine Kandidaten: harte Faelle (harmonisch statisch / Version
    weicht ab) -> anderes Kaliber noetig

Aufruf:
    python -m tools.diagnose_set_matching --analysis d6dca722-2404-4641-9bc2-444a85f465c8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--diag-min-score", type=float, default=0.15)
    args = parser.parse_args()

    import librosa

    from app.audio import library_match as lm
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.jobs.job_manager import RESULTS_DIR
    from app.library.manager import load_fingerprints

    result = json.loads((RESULTS_DIR / f"{args.analysis}.json").read_text(encoding="utf-8"))
    audio_path = next(p for sfx in (".wav", ".mp3") for p in [RESULTS_DIR / f"{args.analysis}{sfx}"] if p.exists())

    accepted = sorted((result.get("library") or {}).get("matches") or [], key=lambda m: m["start"])
    gaps = []
    prev_end = 0.0
    for m in accepted:
        if m["start"] - prev_end > 60:
            gaps.append((prev_end, m["start"]))
        prev_end = max(prev_end, m["end"])

    wave, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    if len(wave) / sr - prev_end > 60:
        gaps.append((prev_end, len(wave) / sr))
    print(f"{len(gaps)} Luecken > 60s: " + ", ".join(f"{int(a)//60}:{int(a)%60:02d}-{int(b)//60}:{int(b)%60:02d}" for a, b in gaps))

    chroma = compute_chroma_matrix(wave, sr)
    fingerprints = load_fingerprints()

    # Endschwelle absenken, damit auch Beinahe-Treffer sichtbar werden.
    # Bewusst NUR fuer diese Diagnose (Prozess-lokal), nie produktiv.
    original_min = lm.MIN_SCORE
    lm.MIN_SCORE = args.diag_min_score
    try:
        fps = sr / (512 * lm.FP_DECIMATE)
        set_coarse = lm.decimate_chroma(chroma)
        prepared = lm._prepare_set(set_coarse)
        pool = lm._prefilter_candidates(set_coarse, fingerprints)
        all_hits = []
        for fp in pool:
            hit = lm.match_track(set_coarse, __import__("numpy").asarray(fp["chroma"], dtype=float), fps, prepared=prepared)
            if hit is not None:
                hit.update({"title": fp.get("title"), "artist": fp.get("artist"), "path": fp.get("path")})
                all_hits.append(hit)
    finally:
        lm.MIN_SCORE = original_min

    for a, b in gaps:
        print(f"\n=== Luecke {int(a)//60}:{int(a)%60:02d} - {int(b)//60}:{int(b)%60:02d} ===")
        in_gap = [h for h in all_hits
                  if min(h["end"], b) - max(h["start"], a) > 30]
        in_gap.sort(key=lambda h: -h["score"])
        if not in_gap:
            print("  KEINE Kandidaten ueber Diagnose-Schwelle - harter Fall.")
            continue
        for h in in_gap[:5]:
            s, e = int(h["start"]), int(h["end"])
            flag = "AKZEPTIERT" if h["score"] >= original_min else f"unter MIN_SCORE {original_min}"
            print(f"  {h['score']:.3f} [{flag}] {s//60}:{s%60:02d}-{e//60}:{e%60:02d} stretch={h.get('stretch')} {h.get('artist')} - {h.get('title')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
