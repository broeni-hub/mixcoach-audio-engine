"""Uebungen in die gespeicherten Reports nachtragen (J3).

Ohne Audio, ohne Demucs: alles Noetige steht in den JSON. Dauert Sekunden.

    python -m tools.backfill_uebungen               # nur Bericht
    python -m tools.backfill_uebungen --write       # schreibt
    python -m tools.backfill_uebungen --mit-archiv  # auch archived/

Was passiert
------------
1. Die fest verdrahtete Vorlage ("Transition Review") wird durch Uebungen
   ersetzt, die je eine Zahl aus demselben Report nennen (app/coach/
   uebungen.py). Wo es keine belegte Zahl gibt, bleibt die Liste LEER -
   das ist keine Luecke, sondern das Ergebnis.
2. Beobachtungen kommen in ein eigenes Feld, getrennt von den Uebungen.
3. notMeasured wird aus dem tatsaechlichen Befuellungsstand gebildet statt
   aus einer festen Fuenferliste (B5). Ein Report, dem darueber hinaus
   etwas fehlt, sagt das jetzt auch.
4. reportRevision zaehlt hoch - ohne das bleibt alles auf der Platte
   liegen und erreicht keinen Browser, der die Analyse schon kennt
   (siehe app/audio/pipeline/scoring_version.py).

Punkt 4 ist der Grund, warum dieser Backfill ueberhaupt ankommt. Bis zum
13.08.2026 ordnete der Korrekturweg nur nach scoringVersion, und Uebungen
sind abgeleiteter Text - sie duerfen die Rechenvorschrift nicht erhoehen.
Ohne die Revision waere dieser Lauf wirkungslos gewesen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.audio.pipeline.scoring_version import naechste_revision, revision_von
from app.coach.uebungen import baue
from app.paths import RESULTS_DIR


def _nicht_gemessen(report: dict) -> list:
    """Welche Kopfzahlen dieser Report NICHT traegt (B5).

    Frueher stand hier eine feste Fuenferliste in analysis_mapper.py. Die
    stimmte fuer den Regelfall, aber nicht fuer Reports, denen darueber
    hinaus etwas fehlt - und die gab es (flow/musicality sind None, wenn
    die Pipeline sie nicht rechnen konnte). Aus dem Ist-Stand gebildet
    sagt das Feld die Wahrheit ueber DIESEN Report.
    """
    scores = report.get("scores") or {}
    fehlend = {k for k, v in scores.items() if v is None}

    # frequency steht NICHT in scores, sondern als eigenes Feld auf oberster
    # Ebene. Beim ersten Anlauf ist es genau deshalb aus der Liste gefallen -
    # der Report haette behauptet, das Frequenzbild sei gemessen. Wer hier
    # Felder ergaenzt, muss dasselbe pruefen.
    if report.get("frequency") is None:
        fehlend.add("frequency")

    return sorted(fehlend)


def nachziehen(report: dict) -> tuple[dict, list]:
    """Report mit Uebungen versehen. Liefert (neu, was geaendert wurde)."""
    neu = dict(report)
    aenderungen: list = []

    aid = str(report.get("id") or "")
    uebergaenge = report.get("setTransitions") or []
    uebungen, beobachtungen = baue(aid, uebergaenge)

    alt_uebungen = report.get("exercises") or []
    if alt_uebungen != uebungen:
        vorlage = any(not u.get("metric") for u in alt_uebungen)
        aenderungen.append(
            f"exercises: {len(alt_uebungen)}{' (Vorlage)' if vorlage else ''}"
            f" -> {len(uebungen)}")
        neu["exercises"] = uebungen

    if (report.get("observations") or []) != beobachtungen:
        aenderungen.append(f"observations: -> {len(beobachtungen)}")
        neu["observations"] = beobachtungen

    nm = _nicht_gemessen(neu)
    if list(report.get("notMeasured") or []) != nm:
        aenderungen.append(
            f"notMeasured: {len(report.get('notMeasured') or [])} -> {len(nm)} Eintraege")
        neu["notMeasured"] = nm

    if aenderungen:
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(
            f"reportRevision: {revision_von(report) or 'fehlt'} -> {neu['reportRevision']}")

    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool, laut: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "schon_gut": 0,
              "mit_uebung": 0, "ohne_uebung": 0, "uebungen": 0, "beobachtungen": 0}
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

        anzahl = len(neu.get("exercises") or [])
        zahlen["uebungen"] += anzahl
        zahlen["beobachtungen"] += len(neu.get("observations") or [])
        zahlen["mit_uebung" if anzahl else "ohne_uebung"] += 1

        if not aenderungen:
            zahlen["schon_gut"] += 1
            continue
        zahlen["geaendert"] += 1
        if laut:
            print(f"  {pfad.name}  ({neu.get('fileName')})")
            for a in aenderungen:
                print(f"      {a}")
        if schreiben:
            pfad.write_text(json.dumps(neu, ensure_ascii=False), encoding="utf-8")
    return zahlen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true", help="wirklich schreiben")
    p.add_argument("--mit-archiv", action="store_true", help="auch archived/")
    p.add_argument("--leise", action="store_true", help="nur die Zusammenfassung")
    args = p.parse_args()

    ordner = [RESULTS_DIR]
    if args.mit_archiv:
        ordner.append(RESULTS_DIR / "archived")

    gesamt = {k: 0 for k in ("gesehen", "geaendert", "schon_gut", "mit_uebung",
                             "ohne_uebung", "uebungen", "beobachtungen")}
    for o in ordner:
        if not o.exists():
            continue
        print(f"=== {o} ===")
        for k, v in durchlauf(o, args.write, not args.leise).items():
            gesamt[k] += v
        print()

    print(f"Reports gesehen        : {gesamt['gesehen']}")
    print(f"  nachgezogen          : {gesamt['geaendert']}")
    print(f"  schon auf dem Stand  : {gesamt['schon_gut']}")
    print(f"mit mindestens 1 Uebung: {gesamt['mit_uebung']}")
    print(f"ohne jede Uebung       : {gesamt['ohne_uebung']}  (dort ist nichts belegt)")
    print(f"Uebungen gesamt        : {gesamt['uebungen']}")
    print(f"Beobachtungen gesamt   : {gesamt['beobachtungen']}")

    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
