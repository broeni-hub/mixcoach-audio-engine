"""Kalibriert LANDMARK_MIN_PEAK/LANDMARK_MIN_DOMINANCE an echten Daten:
fuer jeden der 4 harten Faelle den ECHTEN Track vs. ALLE anderen indizierten
Tracks (peak + dominance). Die Trennlinie zwischen echt und fremd wird
gemessen, nicht geraten.

Aufruf:
    python -m tools.calibrate_landmark
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


def _norm(p: str) -> str:
    return str(Path(p)).lower()


HARD = {
    "synth_000002": "hardhouse", "synth_000003": "pentagram",
    "synth_000004": "void_23", "synth_000005": "orisa",
}


def main() -> int:
    import librosa

    from app.audio import landmark_match as lm
    from app.library.manager import load_landmark_fingerprints

    labels_dir = Path("datasets/synthetic/v1/labels")
    landmark_index = load_landmark_fingerprints()

    for mix_id, needle in HARD.items():
        lf = labels_dir / f"{mix_id}.json"
        label = json.loads(lf.read_text(encoding="utf-8"))
        truth = next((t for t in label["tracks"] if needle in t["source_file"].lower()), None)
        if truth is None:
            continue
        mix_path = labels_dir.parent / "mixes" / f"{mix_id}.wav"
        wave, sr = librosa.load(str(mix_path), sr=lm.SR, mono=True)
        mix_fp = lm.prepare_mix(lm.fingerprint(wave, sr))

        true_path = _norm(truth["source_file"])
        # ALLE Tracks des Mixes sind "echt" - nur wirklich nicht vorkommende
        # Tracks sind fremd (frueherer Bug: die anderen echten Tracks des
        # Mixes wurden als fremd gezaehlt und verfaelschten die Trennlinie).
        mix_track_paths = {_norm(t["source_file"]) for t in label["tracks"]}
        true_row = None
        foreign = []
        for tid, tfp in landmark_index.items():
            r = lm.match(mix_fp, tfp)
            p = _norm(tfp.get("path") or "")
            row = (r["peak"], r["dominance"], p)
            if p == true_path:
                true_row = row
            elif p not in mix_track_paths:
                foreign.append(row)
        if true_row is None:
            print(f"{mix_id}: echter Track nicht indiziert")
            continue
        foreign.sort(key=lambda x: -x[1])  # nach Dominanz
        fmax_dom = foreign[0][1] if foreign else 0
        fmax_peak = max((f[0] for f in foreign), default=0)
        print(f"\n{mix_id} / {Path(truth['source_file']).name[:40]}")
        print(f"  ECHT:  peak={true_row[0]:>7d}  dominance={true_row[1]:.2f}")
        print(f"  FREMD: max_peak={fmax_peak:>7d}  max_dominance={fmax_dom:.2f}")
        print(f"  Top-3 fremde nach Dominanz: " +
              ", ".join(f"{d:.2f}" for _, d, _ in foreign[:3]))
        sep = "TRENNBAR" if true_row[1] > fmax_dom * 1.3 else "grenzwertig/NICHT"
        print(f"  => Dominanz echt {true_row[1]:.2f} vs fremd-max {fmax_dom:.2f}: {sep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
