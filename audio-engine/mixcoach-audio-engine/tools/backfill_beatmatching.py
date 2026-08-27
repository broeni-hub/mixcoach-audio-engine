"""scores.beatmatching und notMeasured in den gespeicherten Reports nachziehen (B5).

Ohne Audio: beat_jitter_ms steht seit dem 20.08.2026 in den Reports, die
Kopfzahl und die Liste leiten sich daraus ab.

    python -m tools.backfill_beatmatching               # nur Bericht
    python -m tools.backfill_beatmatching --write       # schreibt
    python -m tools.backfill_beatmatching --mit-archiv  # auch archived/

WAS HIER GERADEGEZOGEN WIRD
---------------------------
Vom 20. bis zum 27.08.2026 sagten alle 56 Reports "beatmatching: nicht
gemessen" und zeigten daneben eine Beatmatching-Uebung mit gemessener Zahl.
Ursache war eine feste Fuenferliste im Mapper und eine zweite, halbfertige
Fassung in einem Werkzeug. Beide sind durch app/audio/nicht_gemessen.py
ersetzt; dieser Lauf traegt das Ergebnis in den Bestand.

reportRevision zaehlt hoch - sonst bleibt die Korrektur auf der Platte und
erreicht keinen Browser, der die Analyse schon kennt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.beat_jitter import radar_punkte  # noqa: E402
from app.audio.nicht_gemessen import aus_report  # noqa: E402
from app.audio.pipeline.scoring_version import naechste_revision, revision_von  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402


def nachziehen(report: dict) -> tuple[dict, list[str]]:
    neu = dict(report)
    aenderungen: list[str] = []

    scores = dict(neu.get("scores") or {})
    punkte = radar_punkte(neu.get("setTransitions") or [])
    if scores.get("beatmatching") != punkte:
        aenderungen.append(
            f"scores.beatmatching: {scores.get('beatmatching')} -> {punkte}")
        scores["beatmatching"] = punkte
        neu["scores"] = scores

    nm = aus_report(neu)
    if sorted(neu.get("notMeasured") or []) != nm:
        alt = sorted(neu.get("notMeasured") or [])
        aenderungen.append(f"notMeasured: {alt} -> {nm}")
        neu["notMeasured"] = nm

    if aenderungen:
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(
            f"reportRevision: {revision_von(report) or 'fehlt'} -> {neu['reportRevision']}")
    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "mit_punktzahl": 0, "ohne_punktzahl": 0}
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
        if (neu.get("scores") or {}).get("beatmatching") is None:
            zahlen["ohne_punktzahl"] += 1
        else:
            zahlen["mit_punktzahl"] += 1
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

    print(f"\n  Reports gesehen           {zahlen['gesehen']}")
    print(f"  davon geaendert           {zahlen['geaendert']}")
    print(f"  mit Beatmatching-Punkten  {zahlen['mit_punktzahl']}")
    print(f"  ohne (kein Jitter)        {zahlen['ohne_punktzahl']}")
    if not args.write:
        print("\n  Nichts geschrieben. Mit --write wiederholen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
