"""Generiert harte Negativbeispiele fuer den Trackwechsel-Klassifikator -
kostenlos, ohne Audio-Synthese, ohne manuelles Labeln.

Idee: ein einzelner, solo abgespielter Track aus der Library hat per
Definition KEINEN Trackwechsel. Jede Kandidaten-Zone, die der Detektor
darin findet (Drop, Breakdown, Break, Bass-Swap), ist deshalb garantiert
ein Fehlalarm-Beispiel - genau die harten Negativbeispiele, die vielen
Feedback-Sets fehlen (siehe KALIBRIERUNG_STATUS: mehrere Sets haben "0
negative Anker", weil Sebastian eher Treffer bestaetigt als Fehlalarme
explizit abgelehnt hat).

Nutzt build_set_rows() 1:1 wie echte Sets (Train/Serve-Drift ausgeschlossen),
nur mit truth={"positives": [], "negatives": []} - dadurch wird jeder
Kandidat automatisch als negativ gelabelt.

Aufruf (im Projektordner):
    python -m app.calibration.generate_solo_track_negatives
    python -m app.calibration.generate_solo_track_negatives --n-tracks 80 --seed 0
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

MIN_DURATION_SECONDS = 180.0
# Schutz gegen falsch beschriftete Library-Eintraege, die in Wirklichkeit
# ganze Alben/Compilations/Mixe sind (z.B. "The Beatles - Help (Complete
# Album)", 2030s als EIN Track indiziert) - die haben echte interne
# Uebergaenge, die faelschlich als negativ gelabelt wuerden. Einzelne
# Club-Tracks sind praktisch nie laenger als 15 Minuten.
MAX_DURATION_SECONDS = 900.0
OUT_PATH = Path(__file__).parent / "synthetic_negatives_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Harte Negativbeispiele aus Solo-Library-Tracks generieren.")
    parser.add_argument("--library-index", type=Path,
                        default=Path(r"C:\Projekte\Projekte\MixCoach\daten\library\index.json"))
    parser.add_argument("--n-tracks", type=int, default=80)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    from app.calibration.build_features import build_set_rows

    if not args.library_index.exists():
        print(f"FEHLER: {args.library_index} nicht gefunden.")
        return 1

    index = json.loads(args.library_index.read_text(encoding="utf-8"))
    candidates = [
        (tid, meta) for tid, meta in index["tracks"].items()
        if MIN_DURATION_SECONDS <= (meta.get("duration") or 0) <= MAX_DURATION_SECONDS
        and Path(meta.get("path", "")).exists()
    ]
    print(f"{len(candidates)} von {len(index['tracks'])} Tracks liegen im Laengenfenster "
          f"({MIN_DURATION_SECONDS:.0f}-{MAX_DURATION_SECONDS:.0f}s, "
          f"filtert Alben/Compilations raus) und sind auf der Platte auffindbar.")

    rng = random.Random(args.seed)
    sample = rng.sample(candidates, min(args.n_tracks, len(candidates)))

    truth = {"positives": [], "negatives": []}
    all_rows = []
    ok, failed = 0, 0

    for i, (tid, meta) in enumerate(sample, start=1):
        path = meta["path"]
        title = f"{meta.get('artist', '')} - {meta.get('title', '')}".strip(" -") or tid
        print(f"[{i}/{len(sample)}] {title} ({meta.get('duration', 0):.0f}s)...", end=" ", flush=True)
        t0 = time.time()
        try:
            rows = build_set_rows(path, truth, set_name=f"synthneg_{tid}")
        except Exception as e:
            print(f"FEHLER: {e}")
            failed += 1
            continue
        all_rows.extend(rows)
        ok += 1
        print(f"{len(rows)} Kandidaten, alle negativ ({time.time() - t0:.0f}s)")

    args.out.write_text(json.dumps(all_rows), encoding="utf-8")
    print(f"\n{ok} Tracks verarbeitet, {failed} fehlgeschlagen.")
    print(f"{len(all_rows)} harte Negativbeispiele geschrieben -> {args.out}")
    print("\nNaechster Schritt: retrain_model.py laedt diese Datei automatisch mit,")
    print("wenn sie existiert (siehe SYNTHETIC_NEGATIVES in retrain_model.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
