"""Debug: WARUM fuellt gap_fill die harten Faelle nicht? Zeigt fuer den
echten Track eines Mixes jeden Filterschritt (peak, dominance, in_gap,
Laenge) - damit sichtbar wird, welche Schwelle/Bedingung ihn verwirft.

Aufruf:
    python -m tools.debug_gapfill --label datasets/synthetic/v1/labels/synth_000003.json --track pentagram
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
    parser.add_argument("--track", required=True)
    args = parser.parse_args()

    import librosa

    from app.audio import landmark_match as lm
    from app.audio.library_match import match_library
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints, load_landmark_fingerprints

    label = json.loads(args.label.read_text(encoding="utf-8"))
    truth = next(t for t in label["tracks"] if args.track.lower() in t["source_file"].lower())
    mix_path = args.label.parent.parent / "mixes" / f"{args.label.stem}.wav"

    fingerprints = load_fingerprints()
    landmark_index = load_landmark_fingerprints()

    waveform, sr = librosa.load(str(mix_path), sr=lm.SR, mono=True)
    set_len = len(waveform) / sr
    chroma = compute_chroma_matrix(waveform, sr)
    chroma_matches = match_library(chroma, fingerprints, sr)
    print(f"Set-Laenge {set_len:.0f}s, {len(chroma_matches)} Chroma-Treffer:")
    for m in chroma_matches:
        print(f"  {m['start']:.0f}-{m['end']:.0f}s  {Path(m.get('path') or '?').name[:40]}")

    print(f"\nWahr: {Path(truth['source_file']).name[:45]} @ {truth['start_in_mix']:.0f}-{truth['end_in_mix']:.0f}s")

    mix_fp = lm.prepare_mix(lm.fingerprint(waveform, sr))

    # den echten Track im Landmark-Index finden
    tid = next((k for k, v in landmark_index.items()
                if _norm(v.get("path") or "") == _norm(truth["source_file"])), None)
    if tid is None:
        print("!! Echter Track NICHT im Landmark-Index (nicht indiziert).")
        return 1
    tfp = landmark_index[tid]
    res = lm.match(mix_fp, tfp)
    start = max(0.0, lm.frames_to_seconds(res["offset_frames"]))
    dur = float(tfp.get("duration") or 0)
    end = min(set_len, start + dur)

    covered = [(m["start"], m["end"]) for m in chroma_matches]
    span = max(1.0, end - start)
    max_ov = max((min(end, ce) - max(start, cs) for cs, ce in covered), default=0.0)

    print(f"\n=== Landmark-Match des ECHTEN Tracks ===")
    print(f"  peak={res['peak']} (Schwelle LANDMARK_MIN_PEAK={lm.LANDMARK_MIN_PEAK})")
    print(f"  dominance={res['dominance']:.2f} (Schwelle {lm.LANDMARK_MIN_DOMINANCE})")
    print(f"  n_shared={res['n_shared']}")
    print(f"  offset->start={start:.0f}s dur={dur:.0f}s end={end:.0f}s (Laenge {end-start:.0f}s, min {lm.GAP_MIN_SECONDS})")
    print(f"  groesster Ueberlapp mit Chroma-Treffer: {max_ov:.0f}s "
          f"(erlaubt {lm.GAP_OVERLAP_TOLERANCE*span:.0f}s)")
    fails = []
    if res["peak"] < lm.LANDMARK_MIN_PEAK: fails.append("PEAK zu niedrig")
    if res["dominance"] < lm.LANDMARK_MIN_DOMINANCE: fails.append("DOMINANCE zu niedrig")
    if end - start < lm.GAP_MIN_SECONDS: fails.append("zu kurz")
    if max_ov > lm.GAP_OVERLAP_TOLERANCE * span: fails.append("ueberlappt Chroma-Treffer (in_gap=False)")
    print(f"\n  VERWORFEN wegen: {fails if fails else 'NICHTS - haette akzeptiert werden muessen!'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
