"""beat_jitter_ms in die gespeicherten Reports nachtragen.

Ohne Audio: der Wert steckt bereits in beat_alignment_score, nur auf einer
Skala, die ihn unbrauchbar macht (app/audio/beat_jitter.py erklaert, warum).
Zurueckgerechnet wird mit

    cv     = 0,35 * (100 - score) / 100
    jitter = cv * (60 / bpm) * 1000   [ms]

    python -m tools.backfill_beat_jitter               # nur Bericht
    python -m tools.backfill_beat_jitter --write       # schreibt
    python -m tools.backfill_beat_jitter --mit-archiv  # auch archived/

WAS DIESER BACKFILL NICHT KANN
------------------------------
Der Score liegt als ganze Zahl vor. Ein Punkt sind rund 1,6 ms - der
nachgetragene Wert ist also auf etwa +-0,8 ms genau, waehrend eine frische
Analyse den Jitter direkt aus dem Beat-Raster rechnet. Deshalb bekommt jeder
hier erzeugte Wert den Stempel beat_jitter_quelle = "score". Neu analysierte
Uebergaenge tragen "raster".

Die Unterscheidung ist keine Formsache: 1,6 ms Aufloesung liegen weit unter
der Schwelle, ab der eine Uebung entsteht (15 ms), aber wer die Zahl im
Report liest, hat ein Recht darauf zu wissen, ob sie gemessen oder
zurueckgerechnet ist.

reportRevision zaehlt hoch - ohne das bleibt die Aenderung auf der Platte
liegen und erreicht keinen Browser, der die Analyse schon kennt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.pipeline.scoring_version import naechste_revision, revision_von  # noqa: E402
from app.audio.scoring.beat_alignment import CV_AT_ZERO_SCORE  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402


def jitter_aus_score(score, bpm) -> float | None:
    if score is None or not bpm:
        return None
    try:
        bpm = float(bpm)
        if bpm <= 0:
            return None
        cv = CV_AT_ZERO_SCORE * (100.0 - float(score)) / 100.0
    except (TypeError, ValueError):
        return None
    return round(cv * (60.0 / bpm) * 1000.0, 2)


def nachziehen(report: dict) -> tuple[dict, list[str]]:
    neu = dict(report)
    uebergaenge = report.get("setTransitions") or []
    neue_liste, gesetzt, schon = [], 0, 0

    for t in uebergaenge:
        t2 = dict(t)
        if t2.get("beat_jitter_ms") is not None:
            schon += 1
            neue_liste.append(t2)
            continue
        wert = jitter_aus_score(t2.get("beat_alignment_score"),
                                t2.get("bpm_before") or t2.get("bpm_after"))
        if wert is not None:
            t2["beat_jitter_ms"] = wert
            # Die Stichprobe ist aus dem Score nicht rekonstruierbar. None
            # statt einer geschaetzten Zahl - siehe Ehrlichkeitslinie.
            t2["beat_jitter_beats"] = None
            t2["beat_jitter_quelle"] = "score"
            gesetzt += 1
        neue_liste.append(t2)

    aenderungen: list[str] = []
    if gesetzt:
        neu["setTransitions"] = neue_liste
        aenderungen.append(f"beat_jitter_ms: {gesetzt} nachgetragen"
                           f"{f', {schon} schon da' if schon else ''}")
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(
            f"reportRevision: {revision_von(report) or 'fehlt'} -> {neu['reportRevision']}")
    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "werte": 0, "ohne_score": 0}
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
        ohne = sum(1 for t in (neu.get("setTransitions") or [])
                   if t.get("beat_jitter_ms") is None)
        zahlen["ohne_score"] += ohne

        if not aenderungen:
            continue
        zahlen["geaendert"] += 1
        zahlen["werte"] += sum(1 for t in (neu.get("setTransitions") or [])
                               if t.get("beat_jitter_quelle") == "score")
        print(f"  {pfad.name}")
        for zeile in aenderungen:
            print(f"      {zeile}")
        if schreiben:
            pfad.write_text(json.dumps(neu, indent=1, ensure_ascii=False),
                            encoding="utf-8")
    return zahlen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true", help="schreibt wirklich")
    p.add_argument("--mit-archiv", action="store_true")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    print(f"Datenstamm: {args.results_dir}")
    print("PROBELAUF - nichts wird geschrieben.\n" if not args.write else "SCHREIBT.\n")

    zahlen = durchlauf(args.results_dir, args.write)
    if args.mit_archiv and (args.results_dir / "archived").is_dir():
        for k, v in durchlauf(args.results_dir / "archived", args.write).items():
            zahlen[k] += v

    print(f"\n  Reports gesehen        {zahlen['gesehen']}")
    print(f"  davon geaendert        {zahlen['geaendert']}")
    print(f"  Werte nachgetragen     {zahlen['werte']}  (Quelle: score)")
    print(f"  bleiben ohne Wert      {zahlen['ohne_score']}  (kein beat_alignment_score oder keine BPM)")
    if not args.write:
        print("\n  Nichts geschrieben. Mit --write wiederholen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
