"""Wer erzeugt die riesigen Schein-Peaks? Listet fuer den Boratto-Mix die
Top-Fremd-Tracks nach Peak, mit Pfad, Track-Dauer und Anzahl EINDEUTIGER
Hashes (degenerierte Loop/Sample-Tracks haben wenige eindeutige Hashes)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def _norm(p: str) -> str:
    return str(Path(p)).lower()


def main() -> int:
    import librosa

    from app.audio import landmark_match as lm
    from app.library.manager import load_landmark_fingerprints

    lf = Path("datasets/synthetic/v1/labels/synth_000003.json")
    label = json.loads(lf.read_text(encoding="utf-8"))
    true_paths = {_norm(t["source_file"]) for t in label["tracks"]}
    mix_path = lf.parent.parent / "mixes" / f"{lf.stem}.wav"
    wave, sr = librosa.load(str(mix_path), sr=lm.SR, mono=True)
    mix_fp = lm.prepare_mix(lm.fingerprint(wave, sr))

    idx = load_landmark_fingerprints()
    rows = []
    for tid, tfp in idx.items():
        r = lm.match(mix_fp, tfp)
        n_hashes = len(tfp["hashes"])
        n_uniq = len(np.unique(tfp["hashes"]))
        rows.append((r["peak"], r["dominance"], n_hashes, n_uniq,
                     tfp.get("duration"), _norm(tfp.get("path") or "")))
    rows.sort(key=lambda x: -x[0])
    print(f"{'peak':>8} {'dom':>7} {'#hash':>7} {'#uniq':>7} {'uniq%':>6} {'dur':>6}  track")
    for peak, dom, nh, nu, dur, path in rows[:12]:
        flag = " <-- ECHT" if path in true_paths else ""
        uniqpct = 100.0 * nu / max(1, nh)
        print(f"{peak:>8} {dom:>7.1f} {nh:>7} {nu:>7} {uniqpct:>5.1f}% {str(dur or 0):>6}  "
              f"{Path(path).name[:38]}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
