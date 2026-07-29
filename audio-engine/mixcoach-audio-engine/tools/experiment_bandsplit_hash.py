"""EXPERIMENT: Band-Split-Konstellation als Wurzel-Fix fuer das Landmark-
Kostenproblem.

Diagnose nach drei gescheiterten Screen-Varianten (rohe Anzahl, Rare-Hash,
Mini-Match - Boratto-Raenge 2773/2843/1142-2386): das Problem ist das
HASH-DESIGN, nicht der Screen. constellation() pickt die global staerksten
Peaks je Frame - bei bass-lastiger Tanzmusik konzentrieren die sich in den
tiefen Bins, dieselben Hashes wiederholen sich massenhaft (Boratto: nur
4,8% eindeutige Hashes) -> riesige Kollisions-Expansionen machen jeden
Vergleich teuer (~330ms) und jede billige Naeherung rangiert falsch.

Standard-Fix (Shazam-Praxis): Peaks pro Frequenz-BAND picken -> Hashes
verteilen sich ueber das Spektrum, Kollisionen sinken, match() wird fuer
alle billig. Gemessen wird hier ON-THE-FLY (Index bleibt unberuehrt):
  - Hash-Statistik alt vs. neu (Mix: unique%)
  - Kosten pro match() alt vs. neu
  - echte Tracks des Mixes vs. Fremd-Tracks: peak/dominance

Aufruf:
    python -m tools.experiment_bandsplit_hash
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

# Frequenz-Baender (STFT-Bins bei n_fft=2048): grob logarithmisch.
BANDS = ((1, 24), (24, 48), (48, 96), (96, 192), (192, 384), (384, 1025))


def bandsplit_constellation(waveform: np.ndarray, sr: int) -> list[tuple[int, int]]:
    import librosa
    S = np.abs(librosa.stft(waveform, n_fft=2048, hop_length=512))
    logS = np.log1p(S)
    peaks: list[tuple[int, int]] = []
    for f in range(logS.shape[1]):
        col = logS[:, f]
        if col.max() < 1e-3:
            continue
        for lo, hi in BANDS:
            seg = col[lo:hi]
            if len(seg) < 3:
                continue
            local = np.where((seg[1:-1] > seg[:-2]) & (seg[1:-1] > seg[2:]))[0] + 1
            if len(local) == 0:
                continue
            b = lo + int(local[np.argmax(seg[local])])
            peaks.append((f, b))
    return peaks


def fp_from_peaks(peaks: list[tuple[int, int]]) -> dict:
    from app.audio import landmark_match as lm
    hashes, frames = lm._hash_arrays(peaks)
    return {"hashes": hashes, "frames": frames}


def main() -> int:
    import librosa

    from app.audio import landmark_match as lm

    mix_path = "datasets/synthetic/v1/mixes/synth_000003.wav"
    wave, sr = librosa.load(mix_path, sr=lm.SR, mono=True)

    print("=== ALT (global top-3 Peaks/Frame) ===")
    t0 = time.time()
    old_fp = lm.fingerprint(wave, sr)
    n_u = len(np.unique(old_fp["hashes"]))
    print(f"Mix-FP: {time.time()-t0:.0f}s, {len(old_fp['hashes'])} Hashes, "
          f"{n_u} unique ({100*n_u/max(1,len(old_fp['hashes'])):.1f}%)")

    print("\n=== NEU (Band-Split, 1 Peak je 6 Baender) ===")
    t0 = time.time()
    new_fp = fp_from_peaks(bandsplit_constellation(wave, sr))
    n_u = len(np.unique(new_fp["hashes"]))
    print(f"Mix-FP: {time.time()-t0:.0f}s, {len(new_fp['hashes'])} Hashes, "
          f"{n_u} unique ({100*n_u/max(1,len(new_fp['hashes'])):.1f}%)")

    new_prep = lm.prepare_mix(new_fp)
    old_prep = lm.prepare_mix(old_fp)

    label_root = Path(r"C:\Users\Sebro\Music")
    cases: dict[str, str] = {}
    label = json.loads(Path("datasets/synthetic/v1/labels/synth_000003.json").read_text(encoding="utf-8"))
    for t in label["tracks"]:
        cases[f"ECHT {Path(t['source_file']).name[:28]}"] = t["source_file"]

    foreign = [
        r"Electro\Electro Pop\always outnumbered, never outgunned\06 The Prodigy - Wake up call.mp3",
        r"House\Deep House\a1 your rolling hills.mp3",
        r"House\Funky House\Detroit Swindle\Detroit Swindle,Lorenz RhodeHigh Life feat. Lorenz Rhode2.mp3",
        r"House\Melodic House\04-paul_kalkbrenner-salz_amp_pfeffer.mp3",
        r"House\Smooth House\Atjazz\Atjazz,Jullian GomesAwi48The Gift the Curse.mp3",
        r"House\Deep House\12. DJ Koze - XTC.mp3",
    ]
    for rel in foreign:
        cases[f"FREMD {Path(rel).name[:28]}"] = rel

    print(f"\n{'':38s} {'ALT peak/dom/ms':>22s}   {'NEU peak/dom/ms':>22s}")
    for name, rel in cases.items():
        p = Path(rel)
        full = p if p.is_absolute() else label_root / rel
        if not full.exists():
            print(f"{name:38s}  [Datei fehlt: {full}]")
            continue
        tw, _ = librosa.load(str(full), sr=lm.SR, mono=True, duration=300.0)
        t_old = lm.fingerprint(tw, sr)
        t_new = fp_from_peaks(bandsplit_constellation(tw, sr))
        t0 = time.time(); r_old = lm.match(old_prep, t_old); ms_old = (time.time()-t0)*1000
        t0 = time.time(); r_new = lm.match(new_prep, t_new); ms_new = (time.time()-t0)*1000
        print(f"{name:38s} {r_old['peak']:>7d}/{r_old['dominance']:>5.1f}/{ms_old:>5.0f}   "
              f"{r_new['peak']:>7d}/{r_new['dominance']:>5.1f}/{ms_new:>5.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
