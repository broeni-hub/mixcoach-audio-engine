"""EXPERIMENT (kein Produktivcode): Rettet ein LOKALER Fenster-Score die
vier harten Misses (boratto/void_23/orisa/century), die alle NULL Grob-
Kandidaten erzeugen?

Hypothese (aus Messung): der echte Track ist im Set nur ausschnittsweise
und mit lokal starker, global schwacher Aehnlichkeit praesent - der
heutige Grob-Score (Korrelations-MITTEL ueber die ganze Ueberlappung)
verwaescht das unter PRE_SCORE. Ein Score aus dem BESTEN zusammenhaengenden
90s-Fenster sollte den echten Track heben, ohne fremde Tracks
mitzuziehen (die haben nirgends ein starkes Fenster).

Messung je Mix: bester lokaler 90s-Fensterscore des ECHTEN Tracks vs. der
gleiche Score fuer N fremde Tracks. Nur wenn echt >> fremd, lohnt der
Umbau von match_track's Grob-Scoring.

Aufruf:
    python -m tools.experiment_local_window_score --limit 8 --n-foreign 6
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _norm(p: str) -> str:
    return str(Path(p)).lower()


def _best_local_and_mean(set_white: np.ndarray, track_white: np.ndarray,
                         fps: float, win_s: float = 90.0) -> tuple[float, float]:
    """Bester lokaler Fenster-Mittelwert (ueber ALLE Offsets/kein Stretch,
    nur 1.0 hier zur Illustration -> in Produktion pro Stretch) und der
    heutige Voll-Ueberlapp-Mittelwert am jeweils besten Offset.

    Vereinfachte Grobsuche: volle Kreuzkorrelation via FFT, dann fuer den
    besten Offset (a) Voll-Mittel, (b) bestes 90s-Fenster."""
    m = set_white.shape[1]
    n = track_white.shape[1]
    if n < 8 or m < 8:
        return 0.0, 0.0
    nfft = 1 << (m + n - 2).bit_length()
    fa = np.fft.rfft(set_white, nfft, axis=1)
    fb = np.fft.rfft(track_white[:, ::-1], nfft, axis=1)
    corr = np.fft.irfft(fa * fb, nfft, axis=1).sum(axis=0)
    size = m + n - 1
    idx = np.arange(size)
    overlap = np.minimum(np.minimum(idx + 1, size - idx), min(m, n))
    mean_scores = np.where(overlap >= int(0.15 * n), corr[:size] / np.maximum(overlap, 1), -1.0)
    best_off = int(np.argmax(mean_scores))
    full_mean = float(mean_scores[best_off])

    # Bestes lokales Fenster: per-frame Beitrag am besten Offset entlang.
    start = best_off - n + 1
    a = max(0, start)
    b = min(m, start + n)
    if b - a < 8:
        return full_mean, 0.0
    contrib = (set_white[:, a:b] * track_white[:, a - start: b - start]).sum(axis=0)
    win = max(1, int(win_s * fps))
    if len(contrib) <= win:
        local = float(contrib.mean())
    else:
        csum = np.cumsum(np.insert(contrib, 0, 0.0))
        window_means = (csum[win:] - csum[:-win]) / win
        local = float(window_means.max())
    return full_mean, local


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("datasets/synthetic/v1/labels"))
    parser.add_argument("--mixes", default="synth_000002,synth_000003,synth_000004,synth_000005")
    parser.add_argument("--n-foreign", type=int, default=6)
    args = parser.parse_args()

    import librosa

    from app.audio.library_match import _whiten, decimate_chroma
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    fps = 22050 / (512 * 16)
    fingerprints = load_fingerprints()
    fp_by_path = {_norm(fp["path"]): fp for fp in fingerprints if fp.get("path")}

    misses = {
        "synth_000002": "hardhouse", "synth_000003": "pentagram",
        "synth_000004": "void_23", "synth_000005": "orisa",
    }
    rng = np.random.default_rng(0)

    for mix_id in args.mixes.split(","):
        lf = args.labels_dir / f"{mix_id}.json"
        if not lf.exists():
            continue
        label = json.loads(lf.read_text(encoding="utf-8"))
        needle = misses.get(mix_id, "")
        truth = next((t for t in label["tracks"] if needle in t["source_file"].lower()), None)
        if truth is None:
            continue
        mix_path = args.labels_dir.parent / "mixes" / f"{mix_id}.wav"
        waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
        set_white = _whiten(decimate_chroma(compute_chroma_matrix(waveform, sr)))

        fp = fp_by_path.get(_norm(truth["source_file"]))
        if fp is None:
            continue
        true_white = _whiten(decimate_chroma(np.asarray(fp["chroma"], dtype=np.float64)))
        # chroma-FP ist schon dezimiert gespeichert -> nicht nochmal dezimieren
        true_white = _whiten(np.asarray(fp["chroma"], dtype=np.float64))
        full_mean, local = _best_local_and_mean(set_white, true_white, fps)
        print(f"\n{mix_id} / {Path(truth['source_file']).name[:45]}")
        print(f"  ECHT: voll_mittel={full_mean:.3f} (PRE_SCORE 0.10)  bestes_90s_fenster={local:.3f}")

        foreign = [f for f in fingerprints if f.get("path")
                   and needle not in f["path"].lower() and (f.get("duration") or 0) > 200]
        rng.shuffle(foreign)
        best_foreign_local = 0.0
        for f in foreign[: args.n_foreign]:
            fw = _whiten(np.asarray(f["chroma"], dtype=np.float64))
            _, f_local = _best_local_and_mean(set_white, fw, fps)
            best_foreign_local = max(best_foreign_local, f_local)
        print(f"  FREMD (max von {args.n_foreign}): bestes_90s_fenster={best_foreign_local:.3f}")
        verdict = "TRENNBAR" if local > best_foreign_local + 0.05 else "NICHT trennbar"
        print(f"  => lokales Fenster {local:.3f} vs fremd {best_foreign_local:.3f}: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
