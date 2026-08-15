"""Den blinden Uebungs-Vergleich auswerten (J7).

    python -m tools.uebungen_bewertung_auswerten            # alle Laeufe
    python -m tools.uebungen_bewertung_auswerten --lauf abend1

Die Frage war: "Welcher Hinweis wuerde dich beim naechsten Mix mehr
veraendern?" - alte Vorlage oder belegte Uebung, Herkunft nicht sichtbar.

Wie die Zahl zu lesen ist
-------------------------
20 Paare sind eine kleine Stichprobe von EINEM Menschen. Das Ergebnis ist
kein Beweis, sondern ein Anhaltspunkt. Deshalb steht hier neben der
Trefferzahl auch, ab wann sie sich ueberhaupt von Muenzwurf unterscheidet:
bei 20 Antworten braucht es 15 zu 5, damit ein fairer Muenzwurf das in
weniger als 5 % der Faelle zufaellig hinbekommt (zweiseitig).

Faellt es knapper aus, ist die ehrliche Antwort "unentschieden" - und
Punkt 3 bleibt bei 50 %, egal wie viel Arbeit drinsteckt.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import comb
from pathlib import Path

from app.paths import DATA_ROOT

BEWERTUNG_DIR = DATA_ROOT / "uebungen_bewertung"


def _zweiseitig_p(treffer: int, n: int) -> float:
    """Wahrscheinlichkeit, dass ein Muenzwurf mindestens so schief ausfaellt."""
    if n == 0:
        return 1.0
    extrem = max(treffer, n - treffer)
    schwanz = sum(comb(n, k) for k in range(extrem, n + 1))
    return min(1.0, 2 * schwanz / 2 ** n)


def _noetig_fuer_signifikanz(n: int) -> int:
    """Ab wie vielen Treffern waere das Ergebnis nicht mehr Muenzwurf?"""
    for k in range((n // 2) + 1, n + 1):
        if _zweiseitig_p(k, n) < 0.05:
            return k
    return n + 1


def auswerten(pfad: Path) -> dict:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    antworten = (daten.get("antworten") or {}).values()
    belegt = sum(1 for a in antworten if a.get("herkunft") == "belegt")
    vorlage = sum(1 for a in antworten if a.get("herkunft") == "vorlage")
    n = belegt + vorlage
    return {
        "lauf": daten.get("lauf") or pfad.stem,
        "aufgaben": len(daten.get("aufgaben") or []),
        "beantwortet": n,
        "belegt": belegt,
        "vorlage": vorlage,
        "p": _zweiseitig_p(belegt, n),
        "noetig": _noetig_fuer_signifikanz(n),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lauf", help="nur diesen Lauf auswerten")
    args = p.parse_args()

    if not BEWERTUNG_DIR.exists():
        print(f"Noch keine Bewertung unter {BEWERTUNG_DIR}.")
        print("Zuerst MixCoach-Uebungen-Bewerten.command ausfuehren.")
        return 0

    pfade = sorted(BEWERTUNG_DIR.glob("*.json"))
    if args.lauf:
        pfade = [q for q in pfade if q.stem == args.lauf]
    if not pfade:
        print("Kein passender Lauf gefunden.")
        return 0

    for pfad in pfade:
        e = auswerten(pfad)
        print(f"=== Lauf {e['lauf']} ===")
        print(f"  beantwortet          : {e['beantwortet']} von {e['aufgaben']}")
        if e["beantwortet"] == 0:
            print("  (noch nichts entschieden)\n")
            continue
        anteil = 100 * e["belegt"] / e["beantwortet"]
        print(f"  belegte Uebung gewaehlt: {e['belegt']}  ({anteil:.0f} %)")
        print(f"  alte Vorlage gewaehlt  : {e['vorlage']}")
        print(f"  p (zweiseitig)         : {e['p']:.3f}")
        print(f"  noetig fuer < 5 %      : {e['noetig']} von {e['beantwortet']}")
        if e["p"] < 0.05:
            besser = "die belegte Uebung" if e["belegt"] > e["vorlage"] else "die alte Vorlage"
            print(f"  ERGEBNIS: {besser} wirkt staerker.")
        else:
            print("  ERGEBNIS: unentschieden - von Muenzwurf nicht zu unterscheiden.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
