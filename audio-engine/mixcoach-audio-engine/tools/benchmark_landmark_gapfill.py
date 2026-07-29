"""End-to-End-Benchmark der Landmark-Lueckenfuellung: misst, ob das
Shazam-artige Verfahren (app/audio/landmark_match.gap_fill) die 4 harmonisch
statischen Chroma-Misses fuellt, OHNE neue Fehlalarme zu erzeugen.

Chroma laeuft primaer (wie in Produktion), danach fuellt Landmark die
Zeitluecken. Bewertung wie tools/benchmark_fingerprint.py (duplikat-bewusst),
plus getrennte Ausweisung, welche Treffer von Chroma und welche von Landmark
kamen.

Voraussetzung: Landmark-Teilindex existiert
(tools/build_landmark_index.py --from-labels ...).

Aufruf:
    python -m tools.benchmark_landmark_gapfill --limit 8
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("datasets/synthetic/v1/labels"))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("tools/fp_landmark_results.json"))
    args = parser.parse_args()

    import librosa

    from app.audio import landmark_match as lm
    from app.audio.library_match import MIN_PLAYED_SECONDS, match_library
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints, load_landmark_fingerprints
    from tools.benchmark_fingerprint import _acoustic_duplicate

    fingerprints = load_fingerprints()
    landmark_index = load_landmark_fingerprints()
    if not landmark_index:
        print("FEHLER: kein Landmark-Index. Erst tools/build_landmark_index.py laufen lassen.")
        return 1
    index_paths = {_norm(fp["path"]) for fp in fingerprints if fp.get("path")}
    fp_chroma_by_path = {_norm(fp["path"]): np.asarray(fp["chroma"], dtype=np.float64)
                         for fp in fingerprints if fp.get("path")}
    print(f"{len(fingerprints)} Chroma-FPs, {len(landmark_index)} Landmark-FPs.")

    mixes_dir = args.labels_dir.parent / "mixes"
    results = []
    for i, lf in enumerate(sorted(args.labels_dir.glob("*.json"))[: args.limit], 1):
        mix_path = mixes_dir / f"{lf.stem}.wav"
        if not mix_path.exists():
            continue
        label = json.loads(lf.read_text(encoding="utf-8"))
        waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
        set_len = len(waveform) / sr

        t0 = time.time()
        chroma = compute_chroma_matrix(waveform, sr)
        chroma_matches = match_library(chroma, fingerprints, sr)
        t_chroma = time.time() - t0

        t0 = time.time()
        mix_fp = lm.fingerprint(waveform, sr)
        landmark_matches = lm.gap_fill(mix_fp, landmark_index, chroma_matches, set_len)
        t_lm = time.time() - t0

        all_matches = chroma_matches + landmark_matches

        # Ground truth (findbar = lang genug + im Chroma-Index).
        truth = []
        for t in label["tracks"]:
            span = float(t["end_in_mix"]) - float(t["start_in_mix"])
            truth.append({"path": _norm(t["source_file"]),
                          "start": float(t["start_in_mix"]), "end": float(t["end_in_mix"]),
                          "findable": span >= MIN_PLAYED_SECONDS and _norm(t["source_file"]) in index_paths})

        matched: set[int] = set()
        correct = 0
        lm_correct = 0
        false = []
        for m in sorted(all_matches, key=lambda x: -x.get("score", 0)):
            mp = _norm(m.get("path") or "")
            ok = False
            for ti, t in enumerate(truth):
                if ti in matched:
                    continue
                ov = min(m["end"], t["end"]) - max(m["start"], t["start"])
                shorter = min(m["end"] - m["start"], t["end"] - t["start"])
                if shorter <= 0 or ov < 0.5 * shorter:
                    continue
                same = t["path"] == mp
                dup = (not same and mp in fp_chroma_by_path and t["path"] in fp_chroma_by_path
                       and _acoustic_duplicate(fp_chroma_by_path[mp], fp_chroma_by_path[t["path"]]))
                if same or dup:
                    matched.add(ti)
                    correct += 1
                    if m.get("source") == "landmark":
                        lm_correct += 1
                    ok = True
                    break
            if not ok:
                false.append(f"{mp.rsplit(chr(92),1)[-1][:40]}[{m.get('source','chroma')}]")

        findable = [t for t in truth if t["findable"]]
        found = sum(1 for ti in matched if truth[ti]["findable"])
        results.append({"mix": lf.stem, "findable": len(findable), "found": found,
                        "n_matches": len(all_matches), "correct": correct,
                        "lm_correct": lm_correct, "false": false,
                        "t_chroma": round(t_chroma, 1), "t_lm": round(t_lm, 1)})
        print(f"[{i}] {lf.stem}: {found}/{len(findable)} erkannt "
              f"(+{lm_correct} via Landmark), {correct}/{len(all_matches)} korrekt"
              + (f", FALSCH: {false}" if false else "")
              + f"  [chroma {t_chroma:.0f}s + landmark {t_lm:.0f}s]")

    n_truth = sum(r["findable"] for r in results)
    n_found = sum(r["found"] for r in results)
    n_match = sum(r["n_matches"] for r in results)
    n_corr = sum(r["correct"] for r in results)
    n_lm = sum(r["lm_correct"] for r in results)
    print("\n=== ZUSAMMENFASSUNG (Chroma + Landmark-Gapfill) ===")
    print(f"  recall:    {n_found/n_truth:.4f}  (Baseline Chroma-only: 0.90)")
    print(f"  precision: {n_corr/n_match:.4f}")
    print(f"  davon via Landmark neu gefunden: {n_lm}")
    args.out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nDetails -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
