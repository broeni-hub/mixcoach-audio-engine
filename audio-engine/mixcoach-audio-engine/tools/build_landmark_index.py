"""Landmark-Fingerprint-Index bauen (Shazam-Ergaenzung).

Voller Lauf ueber die ganze Library dauert Stunden - daher separat vom
schnellen Chroma-Reindex und ueber Nacht laufbar. Fuer einen schnellen
Test/Benchmark kann eine Teilmenge indiziert werden:

    # alle Ground-Truth-Tracks der Benchmark-Mixes + N zufaellige Fremde:
    python -m tools.build_landmark_index --from-labels datasets/synthetic/v1/labels --limit-mixes 8 --extra-foreign 300

    # ganze Library (Stunden):
    python -m tools.build_landmark_index --all
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _norm(p: str) -> str:
    return str(Path(p)).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="ganze Library (Stunden)")
    parser.add_argument("--from-labels", type=Path, default=None,
                        help="Synth-Label-Ordner: alle darin vorkommenden Ground-Truth-Tracks indizieren")
    parser.add_argument("--limit-mixes", type=int, default=8)
    parser.add_argument("--extra-foreign", type=int, default=0,
                        help="zusaetzlich N zufaellige Fremd-Tracks (Precision-Test)")
    parser.add_argument("--track-cap", type=float, default=360.0)
    args = parser.parse_args()

    from app.library.manager import _load_index, _track_id, build_landmark_index

    tids = None
    if not args.all:
        index = _load_index()
        path_to_tid = {_norm(m["path"]): t for t, m in index["tracks"].items() if m.get("path")}
        wanted: set[str] = set()

        if args.from_labels:
            for lf in sorted(args.from_labels.glob("*.json"))[: args.limit_mixes]:
                for t in json.loads(lf.read_text(encoding="utf-8"))["tracks"]:
                    tid = path_to_tid.get(_norm(t["source_file"]))
                    if tid:
                        wanted.add(tid)
            print(f"{len(wanted)} Ground-Truth-Tracks aus Labels.")

        if args.extra_foreign > 0:
            import random
            rng = random.Random(0)
            others = [t for t in index["tracks"] if t not in wanted]
            rng.shuffle(others)
            wanted.update(others[: args.extra_foreign])
            print(f"+ {args.extra_foreign} Fremd-Tracks -> {len(wanted)} gesamt.")

        tids = sorted(wanted)
        if not tids:
            print("Keine Tracks ausgewaehlt (Index leer? Pfade passen nicht?).")
            return 1

    t0 = time.time()
    stats = build_landmark_index(tids, track_cap_seconds=args.track_cap)
    print(f"\nFertig in {time.time()-t0:.0f}s: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
