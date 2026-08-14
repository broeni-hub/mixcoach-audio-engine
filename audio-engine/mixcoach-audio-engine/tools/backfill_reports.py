"""Gespeicherte Reports auf die Ehrlichkeitslinie ziehen (F1.3).

Der Mapper setzt beatmatching/timing seit dem 31.07.2026 auf None und
fuehrt die Fuenferliste in notMeasured - aber ein Report, der einmal auf
der Platte liegt, wird davon nicht mehr angefasst. Dieses Skript zieht die
gespeicherten Staende nach. Ohne Audio, ohne Demucs: alles Noetige steht
in den JSON.

    python -m tools.backfill_reports                # nur Bericht
    python -m tools.backfill_reports --write        # schreibt
    python -m tools.backfill_reports --mit-archiv   # auch archived/

Warum es das ein zweites Mal gibt
---------------------------------
tools/backfill_honest_scores.py ist am 13.08.2026 ueber 50 Reports
gelaufen. Danach ist ein 51. dazugekommen, und der traegt weiter
beatmatching 100. Die 16 Reports in archived/ hat der Lauf nie
angefasst - sie stehen alle noch auf 100. Genau dieser Nachlauf ist der
Grund, warum F1 ueberhaupt ein Thema ist: eine Korrektur, die nicht alles
erreicht, sieht aus wie erledigt.

Der Stempel ist die heikle Stelle
---------------------------------
scoringVersion 3 zu setzen heisst zu behaupten: "diese Zahlen sind nach
Rechenvorschrift 3 entstanden". Version 3 ist inhaltlich Version 2 - der
Composite mit den gefitteten Gewichten, in Kraft ab 12.07.2026. Ein
Report ist also nur dann belegbar Version 3, wenn

  * seine Composite-Werte nachgerechnet wurden (compositeBackfilledAt), ODER
  * er ab dem 12.07.2026 analysiert wurde (createdAt).

Alles andere ist Version 1 (Gleichverteilung der fuenf Dimensionen) und
bleibt UNSTAMPED. Einen Stempel zu setzen, der nicht stimmt, waere genau
der Fehler, gegen den scoring_version.py geschrieben wurde: derselbe
Feldname, zwei Rechenvorschriften, 25 Punkte Unterschied - und ein
Fortschritts-Radar, das dem DJ einen Sprung zeigt, den er nie gemacht hat.

Dieses Skript nimmt einen Stempel deshalb auch WIEDER WEG, wenn er nicht
belegt ist. backfill_honest_scores.py hat pauschal gestempelt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.api.analysis_mapper import NOT_YET_MEASURED
from app.audio.pipeline.scoring_version import (
    SCORING_CHANGELOG,
    SCORING_VERSION,
    UNSTAMPED,
    naechste_revision,
    revision_von,
)
from app.paths import RESULTS_DIR

# Ab hier galt der Composite mit den gefitteten Gewichten (= Rechenvorschrift
# 2, inhaltlich identisch mit 3). Siehe SCORING_CHANGELOG.
V2_AB = "2026-07-12"


def _stempel_belegt(report: dict) -> bool:
    """Darf dieser Report scoringVersion 3 tragen?"""
    if report.get("compositeBackfilledAt"):
        return True
    return str(report.get("createdAt") or "")[:10] >= V2_AB


def nachziehen(report: dict) -> tuple[dict, list[str]]:
    """Report auf den ehrlichen Stand bringen. Liefert (neu, was geaendert)."""
    neu = dict(report)
    aenderungen: list[str] = []

    scores = dict(neu.get("scores") or {})
    for feld in ("beatmatching", "timing"):
        if scores.get(feld) is not None:
            aenderungen.append(f"scores.{feld}: {scores[feld]} -> None")
            scores[feld] = None
    if scores != (neu.get("scores") or {}):
        neu["scores"] = scores

    if list(neu.get("notMeasured") or []) != list(NOT_YET_MEASURED):
        aenderungen.append(
            f"notMeasured: {len(neu.get('notMeasured') or [])} -> {len(NOT_YET_MEASURED)} Eintraege")
        neu["notMeasured"] = list(NOT_YET_MEASURED)

    ist = neu.get("scoringVersion")
    soll = SCORING_VERSION if _stempel_belegt(neu) else UNSTAMPED
    if soll == UNSTAMPED:
        if ist is not None:
            # Stempel war nicht belegt - lieber gar keine Angabe als eine
            # falsche. vergleichbar() fuehrt ihn dann als nicht vergleichbar.
            aenderungen.append(f"scoringVersion: {ist} -> ungestempelt (nicht belegt)")
            neu.pop("scoringVersion", None)
            neu.pop("scoringNote", None)
    elif ist != soll:
        aenderungen.append(f"scoringVersion: {ist} -> {soll}")
        neu["scoringVersion"] = soll
        # scoringNote nur mitschreiben, wo ohnehin gestempelt wird. Sie
        # NACHZUTRAGEN, wo die Version schon stimmt, wuerde 44 sachlich
        # richtige Reports anfassen, nur um einen Text zu duplizieren, der
        # aus der Version ableitbar ist (SCORING_CHANGELOG).
        neu["scoringNote"] = SCORING_CHANGELOG[soll]

    # Revision hochzaehlen, sobald etwas berichtigt wurde - sonst bleibt die
    # Korrektur auf der Platte liegen und erreicht keinen Browser, der die
    # Analyse schon kennt (siehe scoring_version.ERSTE_REVISION).
    #
    # Auch wenn SONST nichts zu tun war: ein Report ganz ohne Revision kann
    # nichts weitergeben, denn 0 > 0 ist falsch. Die erste Revision ist
    # deshalb selbst eine Aenderung - einmalig, fuer den ganzen Bestand.
    if aenderungen or revision_von(neu) == 0:
        alt_rev = revision_von(neu)
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(f"reportRevision: {alt_rev or 'fehlt'} -> {neu['reportRevision']}")

    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "schon_gut": 0,
              "gestempelt": 0, "entstempelt": 0, "ungestempelt_geblieben": 0}
    for pfad in sorted(ordner.glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as fehler:
            print(f"  UNLESBAR {pfad.name}: {fehler}")
            continue
        if "setTransitions" not in report and "scores" not in report:
            continue  # keine Analyse (z.B. Hilfsdatei)

        zahlen["gesehen"] += 1
        neu, aenderungen = nachziehen(report)

        # Nach dem Lauf ungestempelt - aus dem BERECHNETEN Stand, nicht aus
        # der Platte. Sonst zaehlt der Trockenlauf den Ist- statt den
        # Soll-Zustand und meldet etwas, das er gerade nicht getan hat.
        # Steht VOR dem Fruehausstieg, sonst fehlen die Reports, die schon
        # richtig und schon ungestempelt sind.
        if neu.get("scoringVersion") is None:
            zahlen["ungestempelt_geblieben"] += 1

        if not aenderungen:
            zahlen["schon_gut"] += 1
            continue

        zahlen["geaendert"] += 1
        for a in aenderungen:
            if "-> ungestempelt" in a:
                zahlen["entstempelt"] += 1
            elif a.startswith("scoringVersion:"):
                zahlen["gestempelt"] += 1
        print(f"  {pfad.name}")
        for a in aenderungen:
            print(f"      {a}")

        if schreiben:
            pfad.write_text(json.dumps(neu, ensure_ascii=False), encoding="utf-8")

    return zahlen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true", help="wirklich schreiben")
    p.add_argument("--mit-archiv", action="store_true",
                   help="auch analysis_results/archived/ nachziehen")
    args = p.parse_args()

    ordner = [RESULTS_DIR]
    if args.mit_archiv:
        ordner.append(RESULTS_DIR / "archived")

    gesamt = {"gesehen": 0, "geaendert": 0, "schon_gut": 0,
              "gestempelt": 0, "entstempelt": 0, "ungestempelt_geblieben": 0}
    for o in ordner:
        if not o.exists():
            continue
        print(f"=== {o} ===")
        z = durchlauf(o, args.write)
        for k in gesamt:
            gesamt[k] += z[k]
        print()

    print(f"Reports gesehen              : {gesamt['gesehen']}")
    print(f"  schon auf dem Stand        : {gesamt['schon_gut']}")
    print(f"  nachgezogen                : {gesamt['geaendert']}")
    print(f"    davon Stempel gesetzt    : {gesamt['gestempelt']}")
    print(f"    davon Stempel entfernt   : {gesamt['entstempelt']}")
    print(f"ungestempelt danach          : {gesamt['ungestempelt_geblieben']}")

    if not args.mit_archiv:
        print("\nHinweis: archived/ wurde NICHT angefasst (--mit-archiv).")
    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
