"""EXPERIMENT (kein Produktivcode): Knackt Spektral-Peak-/Landmark-Hashing
(Shazam-Prinzip) die harmonisch statischen Tracks, an denen der Chroma-
Fingerprint UND die zwei bereits verworfenen Alternativen (MFCC, lokales
Fenster) scheitern?

Warum das hier anwendbar ist: die Synth-Mixes strecken nur das TEMPO
(pitch-preserving), die Tonhoehe bleibt - also bleiben die Frequenz-Bins
der Peaks stabil, nur die Zeit-Deltas skalieren leicht (+-8%). Genau die
Bedingung, unter der Landmark-Hashing funktioniert.

Verfahren (kompakt): STFT-Magnitude -> lokale Peaks (Konstellation) ->
Hashes aus Anker-Ziel-Paaren (f1_bin, f2_bin, dt) -> pro Match das Offset
(t_mix - t_track) sammeln. Der ECHTE Track erzeugt einen scharfen Peak im
Offset-Histogramm (viele Hashes bei GLEICHEM Offset); Fremd-Tracks nur
diffuses Rauschen. Gemessen wird die Hoehe dieses Peaks: echt vs. fremd.

Aufruf:
    python -m tools.experiment_landmark_fp --label datasets/synthetic/v1/labels/synth_000003.json --track pentagram --n-foreign 6
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

N_FFT = 2048
HOP = 512
PEAKS_PER_FRAME = 3          # dichteste Peaks je Zeitschritt
FANOUT = 5                   # Ziel-Peaks je Anker
TARGET_DT_MIN, TARGET_DT_MAX = 1, 30   # Frames Abstand Anker->Ziel
OFFSET_BIN = 5               # Frames pro Offset-Histogramm-Bin (Toleranz gg. Stretch)


def _constellation(waveform: np.ndarray, sr: int) -> list[tuple[int, int]]:
    """(frame, freq_bin) der lokalen Spektral-Peaks."""
    import librosa
    S = np.abs(librosa.stft(waveform, n_fft=N_FFT, hop_length=HOP))
    logS = np.log1p(S)
    peaks = []
    n_frames = logS.shape[1]
    for f in range(n_frames):
        col = logS[:, f]
        if col.max() < 1e-3:
            continue
        # lokale Maxima ueber Frequenz, dann die staerksten PEAKS_PER_FRAME
        idx = np.where((col[1:-1] > col[:-2]) & (col[1:-1] > col[2:]))[0] + 1
        if len(idx) == 0:
            continue
        strongest = idx[np.argsort(col[idx])[-PEAKS_PER_FRAME:]]
        for b in strongest:
            peaks.append((f, int(b)))
    return peaks


def _hashes(peaks: list[tuple[int, int]]) -> dict[tuple[int, int, int], list[int]]:
    """hash (f1_bin, f2_bin, dt) -> Liste der Anker-Frames."""
    by_frame = defaultdict(list)
    for fr, b in peaks:
        by_frame[fr].append(b)
    frames = sorted(by_frame)
    table: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for fr in frames:
        for b1 in by_frame[fr]:
            targets = 0
            for dt in range(TARGET_DT_MIN, TARGET_DT_MAX + 1):
                if targets >= FANOUT:
                    break
                for b2 in by_frame.get(fr + dt, []):
                    table[(b1, b2, dt)].append(fr)
                    targets += 1
                    if targets >= FANOUT:
                        break
    return table


def _match_peak(mix_hashes, track_peaks) -> int:
    """Hoehe des staerksten Offset-Bins zwischen Mix und einem Track."""
    track_hashes = _hashes(track_peaks)
    offsets = defaultdict(int)
    for h, track_frames in track_hashes.items():
        mix_frames = mix_hashes.get(h)
        if not mix_frames:
            continue
        for tf in track_frames:
            for mf in mix_frames:
                offsets[(mf - tf) // OFFSET_BIN] += 1
    return max(offsets.values()) if offsets else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--n-foreign", type=int, default=6)
    parser.add_argument("--track-cap", type=float, default=300.0)
    args = parser.parse_args()

    import librosa

    from app.library.manager import load_fingerprints

    label = json.loads(args.label.read_text(encoding="utf-8"))
    mix_path = args.label.parent.parent / "mixes" / f"{args.label.stem}.wav"
    truth = next(t for t in label["tracks"] if args.track.lower() in t["source_file"].lower())

    print("Baue Mix-Konstellation ...")
    mix_wave, sr = librosa.load(str(mix_path), sr=22050, mono=True)
    mix_hashes = _hashes(_constellation(mix_wave, sr))
    print(f"  {len(mix_hashes)} Mix-Hashes")

    true_wave, _ = librosa.load(truth["source_file"], sr=22050, mono=True, duration=args.track_cap)
    true_peak = _match_peak(mix_hashes, _constellation(true_wave, sr))
    print(f"\nECHT: {Path(truth['source_file']).name[:50]}  Offset-Peak={true_peak}")

    fingerprints = load_fingerprints()
    rng = np.random.default_rng(0)
    foreign = [f for f in fingerprints if f.get("path")
               and args.track.lower() not in f["path"].lower()
               and Path(f["path"]).exists() and (f.get("duration") or 0) > 200]
    rng.shuffle(foreign)
    print("FREMD (Offset-Peaks, sollten klar niedriger sein):")
    best_foreign = 0
    for f in foreign[: args.n_foreign]:
        fw, _ = librosa.load(f["path"], sr=22050, mono=True, duration=args.track_cap)
        pk = _match_peak(mix_hashes, _constellation(fw, sr))
        best_foreign = max(best_foreign, pk)
        print(f"  {Path(f['path']).name[:50]:50s} Offset-Peak={pk}")

    ratio = true_peak / max(best_foreign, 1)
    verdict = "TRENNBAR" if true_peak > best_foreign * 1.5 and true_peak >= 8 else "NICHT trennbar"
    print(f"\n=> ECHT {true_peak} vs FREMD-max {best_foreign} (Faktor {ratio:.1f}): {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
