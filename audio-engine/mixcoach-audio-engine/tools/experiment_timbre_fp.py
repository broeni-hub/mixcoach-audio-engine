"""EXPERIMENT (kein Produktivcode): Trennt ein Timbre-Fingerprint (MFCC-
Ableitung) die harmonisch statischen Tracks, an denen der Chroma-
Fingerprint scheitert (library_match._whiten liefert bei konstanter
Harmonie ~0, daher kein Korrelations-Peak; z.B. Gui Boratto Pentagram,
Bodzin)?

Vorgehen: fuer einen Fehlfall-Track wird am WAHREN Offset (aus dem Synth-
Mix-Label) die geglaettete Frame-Aehnlichkeit gemessen - einmal mit Chroma
(wie heute), einmal mit MFCC. Zum Vergleich dieselbe MFCC-Messung gegen ein
paar FREMDE Tracks (die dort NICHT laufen). Nur wenn der echte Track klar
ueber den Fremden liegt, lohnt der grosse Schritt (MFCC-Fingerprint fuer
alle 6113 Tracks + Neu-Indexierung).

Aufruf:
    python -m tools.experiment_timbre_fp --label datasets/synthetic/v1/labels/synth_000003.json --track pentagram
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

FP_DECIMATE = 16
N_MFCC = 20


def _coarse_mfcc(waveform: np.ndarray, sr: int) -> np.ndarray:
    """MFCC (ohne 0. Koeff = Lautstaerke) -> grob dezimiert, frame-normalisiert.
    Analog zu library_match.decimate_chroma, aber auf Timbre statt Harmonie."""
    import librosa
    mfcc = librosa.feature.mfcc(y=waveform, sr=sr, n_mfcc=N_MFCC, hop_length=512)[1:]
    n = mfcc.shape[1] // FP_DECIMATE
    if n == 0:
        return np.zeros((mfcc.shape[0], 0))
    coarse = mfcc[:, : n * FP_DECIMATE].reshape(mfcc.shape[0], n, FP_DECIMATE).mean(axis=2)
    coarse = coarse - coarse.mean(axis=1, keepdims=True)
    return coarse / (np.linalg.norm(coarse, axis=0, keepdims=True) + 1e-9)


def _whiten(coarse: np.ndarray) -> np.ndarray:
    d = np.diff(coarse, axis=1)
    return d / (np.linalg.norm(d, axis=0, keepdims=True) + 1e-9)


def _sustained_sim(set_white: np.ndarray, track_white: np.ndarray, start_frame: int, fps: float) -> tuple[float, float]:
    """(geglaetteter Max, laengster Lauf ueber 0.22s) am gegebenen Offset."""
    a = max(0, start_frame)
    b = min(set_white.shape[1], start_frame + track_white.shape[1])
    if b - a < 8:
        return 0.0, 0.0
    contrib = (set_white[:, a:b] * track_white[:, a - start_frame: b - start_frame]).sum(axis=0)
    k = max(3, int(5 * fps))
    smooth = np.convolve(contrib, np.ones(k) / k, mode="same")
    active = smooth >= 0.22
    longest = cur = 0
    for f in active:
        cur = cur + 1 if f else 0
        longest = max(longest, cur)
    return float(smooth.max()), longest / fps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--n-foreign", type=int, default=4)
    args = parser.parse_args()

    import librosa

    from app.audio.library_match import _whiten as chroma_whiten
    from app.audio.library_match import decimate_chroma
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    label = json.loads(args.label.read_text(encoding="utf-8"))
    mix_path = args.label.parent.parent / "mixes" / f"{args.label.stem}.wav"
    truth = next(t for t in label["tracks"] if args.track.lower() in t["source_file"].lower())

    fps = 22050 / (512 * FP_DECIMATE)
    waveform, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    set_chroma_w = chroma_whiten(decimate_chroma(compute_chroma_matrix(waveform, sr)))
    set_mfcc_w = _whiten(_coarse_mfcc(waveform, sr))
    start_frame = int(float(truth["start_in_mix"]) * fps)

    # Echter Track
    true_path = truth["source_file"]
    tw, _ = librosa.load(true_path, sr=22050, mono=True)
    true_chroma_w = chroma_whiten(decimate_chroma(compute_chroma_matrix(tw, sr)))
    true_mfcc_w = _whiten(_coarse_mfcc(tw, sr))

    c_max, c_run = _sustained_sim(set_chroma_w, true_chroma_w, start_frame, fps)
    m_max, m_run = _sustained_sim(set_mfcc_w, true_mfcc_w, start_frame, fps)
    print(f"ECHTER Track: {Path(true_path).name}")
    print(f"  CHROMA (heute): smooth_max={c_max:.3f}  laengster Lauf={c_run:.0f}s")
    print(f"  MFCC   (neu):   smooth_max={m_max:.3f}  laengster Lauf={m_run:.0f}s")

    # Fremde Tracks: MFCC am selben Offset - sollten klar niedriger sein.
    fingerprints = load_fingerprints()
    rng = np.random.default_rng(0)
    foreign = [fp for fp in fingerprints
               if fp.get("path") and args.track.lower() not in fp["path"].lower()
               and (fp.get("duration") or 0) > 200]
    rng.shuffle(foreign)
    print(f"\nFREMDE Tracks (MFCC am selben Offset, sollten niedrig sein):")
    for fp in foreign[: args.n_foreign]:
        fw, _ = librosa.load(fp["path"], sr=22050, mono=True, duration=280)
        f_mfcc_w = _whiten(_coarse_mfcc(fw, sr))
        fm_max, fm_run = _sustained_sim(set_mfcc_w, f_mfcc_w, start_frame, fps)
        print(f"  {Path(fp['path']).name[:45]:45s} smooth_max={fm_max:.3f} Lauf={fm_run:.0f}s")

    print("\n=> Wenn MFCC-Lauf des echten Tracks >> Fremde UND >> Chroma-Lauf, "
          "lohnt der MFCC-Fingerprint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
