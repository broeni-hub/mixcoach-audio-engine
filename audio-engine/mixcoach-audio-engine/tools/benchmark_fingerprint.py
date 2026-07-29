"""Fingerprint-Benchmark: misst die Library-Matching-Genauigkeit an
synthetischen Mixes mit EXAKTER Ground Truth (tools/synth_mixer-Labels:
welcher Track lief von wann bis wann, inkl. Zeitstreckung/EQ-Blends).

Warum synthetische Mixes: echte Sets mit bekannter Tracklist + exakten
Zeiten existieren (noch) nicht als Labels; die Synth-Mixes stammen aus
denselben Library-Tracks, die auch im Fingerprint-Index stehen, und
enthalten realistische DJ-Artefakte (Time-Stretch, Crossfades, Bass-Swap).
Grenze (ehrlich): keine Live-Fader/Loops/FX - Ergebnisse sind eine OBERE
Schranke fuer echte Sets, kein Ersatz fuer einen Real-Set-Benchmark.

Gemessen wird gegen die MIN_PLAYED_SECONDS-Definition des Matchers selbst:
ein Ground-Truth-Track zaehlt nur als "findbar", wenn er lang genug lief
und im Index steht.

Aufruf (im Projektordner, MIXCOACH_DATA_DIR muss gesetzt sein):
    python -m tools.benchmark_fingerprint --limit 10
    python -m tools.benchmark_fingerprint --labels-dir datasets/synthetic/v1/labels
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


def _acoustic_duplicate(chroma_a: np.ndarray, chroma_b: np.ndarray,
                        max_lag_frames: int = 32) -> bool:
    """True, wenn zwei Library-Fingerprints (fast) dieselbe Aufnahme sind -
    derselbe Song zweimal in der Library (unterschiedliche Datei/Metadaten).
    Der Matcher findet dann den richtigen Song, nur die andere Kopie; das
    ist KEIN Fehlalarm, sondern eine Eigenschaft der Library.

    Vergleich per frame-normalisierter Korrelation ueber die gemeinsame
    Laenge - mit kleiner LAG-SUCHE (±max_lag_frames, ~±6s bei ~5.4fps):
    verschiedene Rips desselben Songs starten oft leicht versetzt
    (Encoder-Padding/Silence-Trim). Ein reiner Null-Versatz-Vergleich hat
    genau die zwei real beobachteten Duplikat-Paare verfehlt (daphni,
    bodzin triton, 2026-07-14)."""
    if min(chroma_a.shape[1], chroma_b.shape[1]) < 50 + max_lag_frames:
        return False

    def _prep(c: np.ndarray) -> np.ndarray:
        c = c - c.mean(axis=0, keepdims=True)
        return c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)

    a_full = _prep(chroma_a)
    b_full = _prep(chroma_b)
    best = -1.0
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        if lag >= 0:
            a, b = a_full[:, lag:], b_full
        else:
            a, b = a_full, b_full[:, -lag:]
        n = min(a.shape[1], b.shape[1])
        score = float((a[:, :n] * b[:, :n]).sum(axis=0).mean())
        best = max(best, score)
    return best > 0.6


def evaluate_mix(mix_path: Path, label: dict, fingerprints: list[dict],
                 index_paths: set[str], min_played: float,
                 fp_by_path: dict[str, np.ndarray]) -> dict:
    import librosa

    from app.audio.library_match import match_library
    from app.audio.track_change_classifier import compute_chroma_matrix

    t0 = time.time()
    waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    chroma = compute_chroma_matrix(waveform, sr)
    t_prep = time.time() - t0

    t0 = time.time()
    matches = match_library(chroma, fingerprints, sr)
    t_match = time.time() - t0

    # Findbare Ground-Truth-Tracks: lang genug gespielt UND im Index.
    truth = []
    for t in label["tracks"]:
        span = float(t["end_in_mix"]) - float(t["start_in_mix"])
        findable = span >= min_played and _norm(t["source_file"]) in index_paths
        truth.append({
            "path": _norm(t["source_file"]),
            "start": float(t["start_in_mix"]),
            "end": float(t["end_in_mix"]),
            "findable": findable,
        })

    hits, boundary_errors = [], []
    matched_truth: set[int] = set()
    correct_matches = 0
    duplicate_matches = 0
    for m in matches:
        m_path = _norm(m.get("path") or "")
        ok = False
        for ti, t in enumerate(truth):
            if ti in matched_truth:
                continue
            overlap = min(m["end"], t["end"]) - max(m["start"], t["start"])
            shorter = min(m["end"] - m["start"], t["end"] - t["start"])
            if shorter <= 0 or overlap < 0.5 * shorter:
                continue
            # Exakter Pfad-Treffer ODER akustisches Duplikat (derselbe Song,
            # andere Datei) am richtigen Zeitfenster - beides zaehlt als
            # korrekt erkannter Song.
            same = t["path"] == m_path
            dup = (not same and m_path in fp_by_path and t["path"] in fp_by_path
                   and _acoustic_duplicate(fp_by_path[m_path], fp_by_path[t["path"]]))
            if same or dup:
                matched_truth.add(ti)
                correct_matches += 1
                if dup:
                    duplicate_matches += 1
                boundary_errors.append(abs(m["start"] - t["start"]))
                boundary_errors.append(abs(m["end"] - t["end"]))
                ok = True
                break
        hits.append({"path": m_path, "ok": ok,
                     "start": round(m["start"], 1), "end": round(m["end"], 1),
                     "score": m["score"]})

    findable = [t for t in truth if t["findable"]]
    found = sum(1 for ti in matched_truth if truth[ti]["findable"])
    return {
        "mix": mix_path.stem,
        "n_truth_findable": len(findable),
        "n_found": found,
        "n_duplicate_matches": duplicate_matches,
        "n_matches": len(matches),
        "n_correct_matches": correct_matches,
        "boundary_errors": boundary_errors,
        "t_prep": round(t_prep, 1),
        "t_match": round(t_match, 1),
        "misses": [t["path"].rsplit("\\", 1)[-1][:60] for i, t in enumerate(truth)
                   if t["findable"] and i not in matched_truth],
        "false_matches": [h["path"].rsplit("\\", 1)[-1][:60] for h in hits if not h["ok"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fingerprint-Genauigkeit an Synth-Mixes messen.")
    parser.add_argument("--labels-dir", type=Path,
                        default=Path("datasets/synthetic/v1/labels"))
    parser.add_argument("--mixes-dir", type=Path, default=None,
                        help="Default: ../mixes neben labels-dir")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("tools/fp_benchmark_results.json"))
    args = parser.parse_args()

    from app.audio.library_match import MIN_PLAYED_SECONDS
    from app.library.manager import load_fingerprints

    mixes_dir = args.mixes_dir or (args.labels_dir.parent / "mixes")
    fingerprints = load_fingerprints()
    if not fingerprints:
        print("FEHLER: kein Fingerprint-Index geladen (MIXCOACH_DATA_DIR gesetzt?).")
        return 1
    index_paths = {_norm(fp["path"]) for fp in fingerprints if fp.get("path")}
    print(f"{len(fingerprints)} Fingerprints im Index.")

    label_files = sorted(args.labels_dir.glob("*.json"))[: args.limit]
    # Chroma fuer den Duplikat-Check LAZY konvertieren (nur wenn wirklich
    # ein Pfad-Mismatch auftritt, das ist selten) - alle 6113 Fingerprints
    # vorab nach float64 zu konvertieren kostete ~600MB RAM und machte den
    # ganzen Benchmark durch Speicherdruck ~3x langsamer (gemessen
    # 2026-07-14: prep 8s -> 116s).
    _raw_by_path = {_norm(fp["path"]): fp for fp in fingerprints if fp.get("path")}

    class _LazyChroma:
        def __init__(self) -> None:
            self._cache: dict[str, np.ndarray] = {}

        def __contains__(self, path: str) -> bool:
            return path in _raw_by_path

        def __getitem__(self, path: str) -> np.ndarray:
            if path not in self._cache:
                self._cache[path] = np.asarray(_raw_by_path[path]["chroma"], dtype=np.float64)
            return self._cache[path]

    fp_by_path = _LazyChroma()

    results = []
    for i, lf in enumerate(label_files, 1):
        mix_path = mixes_dir / f"{lf.stem}.wav"
        if not mix_path.exists():
            continue
        label = json.loads(lf.read_text(encoding="utf-8"))
        r = evaluate_mix(mix_path, label, fingerprints, index_paths, MIN_PLAYED_SECONDS, fp_by_path)
        results.append(r)
        print(f"[{i}/{len(label_files)}] {r['mix']}: {r['n_found']}/{r['n_truth_findable']} Tracks erkannt, "
              f"{r['n_correct_matches']}/{r['n_matches']} Matches korrekt"
              + (f" ({r['n_duplicate_matches']} via Duplikat)" if r["n_duplicate_matches"] else "")
              + f", prep {r['t_prep']}s match {r['t_match']}s"
              + (f", verpasst: {r['misses']}" if r["misses"] else "")
              + (f", falsch: {r['false_matches']}" if r["false_matches"] else ""))

    if not results:
        print("Keine auswertbaren Mixes gefunden.")
        return 1

    n_truth = sum(r["n_truth_findable"] for r in results)
    n_found = sum(r["n_found"] for r in results)
    n_matches = sum(r["n_matches"] for r in results)
    n_correct = sum(r["n_correct_matches"] for r in results)
    n_dup = sum(r["n_duplicate_matches"] for r in results)
    all_errors = [e for r in results for e in r["boundary_errors"]]

    summary = {
        "mixes": len(results),
        "recall": round(n_found / n_truth, 4) if n_truth else None,
        "precision": round(n_correct / n_matches, 4) if n_matches else None,
        "duplicate_matches": n_dup,
        "boundary_error_median_s": round(float(np.median(all_errors)), 2) if all_errors else None,
        "boundary_error_p90_s": round(float(np.percentile(all_errors, 90)), 2) if all_errors else None,
        "avg_match_seconds": round(float(np.mean([r["t_match"] for r in results])), 1),
    }
    print("\n=== ZUSAMMENFASSUNG ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    args.out.write_text(json.dumps({"summary": summary, "results": results}, indent=1),
                        encoding="utf-8")
    print(f"\nDetails -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
