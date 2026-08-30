"""Das Uebergangs-Fenster in die gespeicherten Reports nachtragen (A1/K3).

Ohne Audio: start_sec und mid_sec stehen bereits in jedem Report.

    python -m tools.backfill_uebergangsfenster               # nur Bericht
    python -m tools.backfill_uebergangsfenster --write       # schreibt
    python -m tools.backfill_uebergangsfenster --mit-archiv  # auch archived/

reportRevision zaehlt hoch - sonst bleibt die Aenderung auf der Platte und
erreicht keinen Browser, der die Analyse schon kennt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.pipeline.scoring_version import naechste_revision, revision_von  # noqa: E402
from app.audio.uebergangsfenster import fenster  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402


def nachziehen(report: dict) -> tuple[dict, list[str]]:
    neu = dict(report)
    dauer = report.get("totalDurationSec")
    liste, gesetzt, ohne = [], 0, 0
    for t in report.get("setTransitions") or []:
        t2 = dict(t)
        f = fenster(t2, dauer)
        if f != t2.get("window"):
            t2["window"] = f
            gesetzt += 1
        if f is None:
            ohne += 1
        liste.append(t2)

    aenderungen: list[str] = []
    if gesetzt:
        neu["setTransitions"] = liste
        aenderungen.append(f"window: {gesetzt} gesetzt"
                           + (f", {ohne} ohne Zeitangabe" if ohne else ""))
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(
            f"reportRevision: {revision_von(report) or 'fehlt'} -> {neu['reportRevision']}")
    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "fenster": 0, "ohne": 0}
    for pfad in sorted(ordner.glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as fehler:
            print(f"  UNLESBAR {pfad.name}: {fehler}")
            continue
        if "setTransitions" not in report:
            continue
        zahlen["gesehen"] += 1
        neu, aenderungen = nachziehen(report)
        for t in neu.get("setTransitions") or []:
            zahlen["fenster" if t.get("window") else "ohne"] += 1
        if not aenderungen:
            continue
        zahlen["geaendert"] += 1
        print(f"  {pfad.name}  ({report.get('fileName')})")
        for zeile in aenderungen:
            print(f"      {zeile}")
        if schreiben:
            pfad.write_text(json.dumps(neu, indent=1, ensure_ascii=False),
                            encoding="utf-8")
    return zahlen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true")
    p.add_argument("--mit-archiv", action="store_true")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    print(f"Datenstamm: {args.results_dir}")
    print("PROBELAUF - nichts wird geschrieben.\n" if not args.write else "SCHREIBT.\n")
    zahlen = durchlauf(args.results_dir, args.write)
    if args.mit_archiv and (args.results_dir / "archived").is_dir():
        for k, v in durchlauf(args.results_dir / "archived", args.write).items():
            zahlen[k] += v

    print(f"\n  Reports gesehen     {zahlen['gesehen']}")
    print(f"  davon geaendert     {zahlen['geaendert']}")
    print(f"  Uebergaenge mit Fenster {zahlen['fenster']}")
    print(f"  ohne (keine Zeitangabe) {zahlen['ohne']}")
    if not args.write:
        print("\n  Nichts geschrieben. Mit --write wiederholen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
