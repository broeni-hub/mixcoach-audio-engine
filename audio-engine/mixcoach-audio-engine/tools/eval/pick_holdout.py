"""Holdout-Sets auswaehlen - deterministisch und geschichtet.

Warum geschichtet statt rein zufaellig: Die Ground-Truth-Sets zerfallen in
zwei Gruppen mit sehr verschiedenem Charakter -
  EIGEN     Sebastians eigene Aufnahmen (REC*, MixCoach*, Dec25, mix.wav)
  REFERENZ  fremde Festival-/Radio-Sets (Dixon, Four Tet, Joris Voorn, ...)
Eine reine Hash-Auswahl zog 3 der 5 MixCoach-Sets ins Holdout - also genau
das Material, auf das das Produkt zielt. Deshalb wird je Gruppe im gleichen
Verhaeltnis gezogen, innerhalb der Gruppe deterministisch per SHA256 des
Namens. Es werden dabei KEINE Metriken angesehen, die Auswahl kann also
nicht guenstig ausfallen.

Aufruf:
    python -m tools.eval.pick_holdout            # nur anzeigen
    python -m tools.eval.pick_holdout --write    # holdout_sets.txt schreiben
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.calibration import retrain_model as rm  # noqa: E402
from app.paths import GROUND_TRUTH_DIR  # noqa: E402

HOLDOUT_TOTAL = 8
OUT_PATH = Path(__file__).parent / "holdout_sets.txt"

OWN_MARKERS = ("REC", "MIXCOACH", "DEC25", "MIX.WAV")


def is_own(name: str) -> bool:
    upper = name.upper()
    return any(upper.startswith(m) or upper == m for m in OWN_MARKERS)


def usable_sets() -> tuple[list[str], list[str]]:
    """(Set-Namen mit Ground Truth UND auffindbarem Report, verwaiste IDs)."""
    names: set[str] = set()
    orphans: list[str] = []
    for path in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        result, _ = rm._find_result_json(path.stem)
        name = (result or {}).get("fileName") or (result or {}).get("filename")
        if name:
            names.add(name)
        else:
            orphans.append(path.stem)
    return sorted(names), orphans


def stable_rank(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def pick(names: list[str], total: int = HOLDOUT_TOTAL) -> list[str]:
    own = sorted([n for n in names if is_own(n)], key=stable_rank)
    ref = sorted([n for n in names if not is_own(n)], key=stable_rank)
    if not names:
        return []
    # Anteilig ziehen, mindestens 1 je Gruppe solange die Gruppe existiert.
    n_own = round(total * len(own) / len(names))
    n_own = max(1, min(len(own), n_own)) if own else 0
    n_ref = total - n_own
    n_ref = max(0, min(len(ref), n_ref))
    # Rest auffuellen, falls eine Gruppe zu klein war
    while n_own + n_ref < total and (n_own < len(own) or n_ref < len(ref)):
        if n_own < len(own):
            n_own += 1
        elif n_ref < len(ref):
            n_ref += 1
    return sorted(own[:n_own] + ref[:n_ref])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    names, orphans = usable_sets()
    own = [n for n in names if is_own(n)]
    ref = [n for n in names if not is_own(n)]

    print(f"Ground-Truth-Dateien:              {len(list(GROUND_TRUTH_DIR.glob('*.json')))}")
    print(f"davon mit auffindbarem Report:     {len(names)} Sets")
    print(f"davon verwaist (kein Report/Audio):{len(orphans)}")
    print(f"  EIGEN:    {len(own)}  {own}")
    print(f"  REFERENZ: {len(ref)}")

    holdout = pick(names)
    dev = [n for n in names if n not in holdout]
    print(f"\nHOLDOUT ({len(holdout)}), bis zum Abschlusslauf gesperrt:")
    for n in holdout:
        print(f"  [{'EIGEN' if is_own(n) else 'REF  '}] {n}")
    print(f"\nENTWICKLUNG ({len(dev)}):")
    for n in dev:
        print(f"  [{'EIGEN' if is_own(n) else 'REF  '}] {n}")

    if args.write:
        lines = [
            "# Holdout-Sets fuer die Precision-90-Arbeit (P0, 30.07.2026).",
            "# Geschichtet nach EIGEN/REFERENZ, innerhalb der Gruppe deterministisch",
            "# per SHA256 des Set-Namens - ohne Blick auf irgendeine Metrik.",
            "# Diese Sets werden bis zum Abschlusslauf NICHT benutzt.",
            "# Erzeugt von: python -m tools.eval.pick_holdout --write",
        ] + holdout
        OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nGeschrieben: {OUT_PATH}")
    else:
        print("\n(--write, um holdout_sets.txt zu schreiben)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
