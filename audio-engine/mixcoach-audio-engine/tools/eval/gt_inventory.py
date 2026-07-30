"""Herkunft und Praezision der Ground-Truth-Anker aufschluesseln.

Warum das VOR jeder Precision-Messung kommt: Nicht jeder Positiv-Anker ist
gleich viel wert. Ein Anker aus verdict="correct" traegt die midSec des
Engine-Markers - also genau die Position, die bewertet werden soll. Gegen
solche Anker bei enger Toleranz zu messen ist zirkulaer: die Engine trifft
ihre eigene Position per Konstruktion auf 0,00 s.

Unabhaengig sind nur:
  - timing_off -> correctedSec (der DJ hat die Stelle selbst angesteuert)
  - missed     -> vom DJ gesetzte Zeit ohne Engine-Vorlage

Aufruf (im Projektordner mixcoach-audio-engine):
    python -m tools.eval.gt_inventory
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.paths import GROUND_TRUTH_DIR  # noqa: E402


def collect() -> dict:
    stats = Counter()
    per_set: dict[str, Counter] = {}
    independent_per_set: dict[str, int] = {}

    for path in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stats["unlesbar"] += 1
            continue

        c = Counter()
        for entry in (data.get("verdicts") or {}).values():
            v = entry.get("verdict")
            if v == "correct":
                c["correct (Anker = Engine-midSec)"] += 1
            elif v == "timing_off":
                # correctedSec vorhanden? sonst faellt es auf midSec zurueck
                if entry.get("correctedSec") is not None:
                    c["timing_off (Anker = DJ-Korrektur)"] += 1
                else:
                    c["timing_off OHNE correctedSec (faellt auf midSec zurueck)"] += 1
            elif v == "not_a_transition":
                c["not_a_transition (Negativ)"] += 1
            else:
                c[f"unbekanntes verdict: {v}"] += 1

        c["missed (Anker = DJ-Klick)"] += len(data.get("missed") or [])
        c["true_transitions_sec (Chat-Annotation)"] += len(data.get("true_transitions_sec") or [])

        stats.update(c)
        per_set[path.stem] = c
        independent_per_set[path.stem] = (
            c["timing_off (Anker = DJ-Korrektur)"]
            + c["missed (Anker = DJ-Klick)"]
            + c["true_transitions_sec (Chat-Annotation)"]
        )

    return {"total": stats, "per_set": per_set, "independent": independent_per_set}


def main() -> int:
    r = collect()
    stats = r["total"]

    print(f"Ground-Truth-Verzeichnis: {GROUND_TRUTH_DIR}")
    print(f"Dateien: {len(r['per_set'])}\n")

    print("=== Anker nach Herkunft ===")
    for key, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {key}")

    circular = stats["correct (Anker = Engine-midSec)"]
    independent = (stats["timing_off (Anker = DJ-Korrektur)"]
                   + stats["missed (Anker = DJ-Klick)"]
                   + stats["true_transitions_sec (Chat-Annotation)"])
    positives = circular + independent + stats["timing_off OHNE correctedSec (faellt auf midSec zurueck)"]

    print(f"\n=== Bewertbarkeit bei enger Toleranz (z.B. +-2 s) ===")
    print(f"  Positiv-Anker gesamt:                    {positives}")
    print(f"  davon ZIRKULAER (= Engine-Position):     {circular}"
          f"  ({circular/positives*100:.0f}%)" if positives else "")
    print(f"  davon UNABHAENGIG (DJ-gesetzte Zeit):    {independent}"
          f"  ({independent/positives*100:.0f}%)" if positives else "")

    usable = {s: n for s, n in r["independent"].items() if n > 0}
    print(f"\n  Sets mit mindestens 1 unabhaengigem Anker: {len(usable)} von {len(r['per_set'])}")
    if usable:
        vals = sorted(usable.values())
        print(f"  unabhaengige Anker je Set: min={vals[0]} median={vals[len(vals)//2]} max={vals[-1]}")
        print(f"  Sets mit >=5 unabhaengigen Ankern: {sum(1 for v in vals if v >= 5)}")

    print("\nFolgerung: eine Precision-Messung bei +-2 s ist nur gegen die")
    print("UNABHAENGIGEN Anker aussagekraeftig. Gegen 'correct'-Anker misst man")
    print("die Engine an ihrer eigenen Ausgabe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
