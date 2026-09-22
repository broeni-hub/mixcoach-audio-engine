# -*- coding: utf-8 -*-
"""Eine Aufnahme ausdruecklich als eigen oder fremd kennzeichnen.

    python -m tools.aufnahme_markieren <analysisId> --fremd
    python -m tools.aufnahme_markieren <analysisId> --eigen --write

WOFUER
------
Ob eine Aufnahme Sebastians eigene ist, entscheidet sonst die Endung:
.wav gilt als eigen, alles andere als fremd (app/coach/profile.py,
_selbst_aufgenommen). Das ist ein Indiz und steht dort auch so.

Am 22.09.2026 kam ein Set eines befreundeten DJs als .wav. Ungekennzeichnet
waere es in Sebastians Fortschrittskurve gelandet - in die Zahl, die
Bedingung 3 der Live-Schwelle traegt - und in best/worst, Uebungen und
Muster des Coach-Profils. Bei Fabis Sets ging es nur gut, weil sie
zufaellig .mp3 waren.

Dieses Werkzeug setzt das Feld ownRecording. Es gewinnt gegen die Endung.

WAS NICHT PASSIERT
------------------
Die reportRevision wird NICHT hochgezaehlt - genau wie bei
tools/migriere_besitzer.py. Im Report selbst aendert sich nichts, was
jemand liest; Kurve und Coach-Profil werden bei jedem Aufruf neu gerechnet
und lesen das Feld sofort.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paths import RESULTS_DIR  # noqa: E402

FELD = "ownRecording"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("analysis_id")
    gruppe = p.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--eigen", action="store_true", help="Sebastians eigene Aufnahme")
    gruppe.add_argument("--fremd", action="store_true", help="fremdes Set zum Studieren")
    p.add_argument("--write", action="store_true", help="wirklich schreiben")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    a = p.parse_args()

    pfad = a.results_dir / f"{a.analysis_id}.json"
    if not pfad.exists():
        print(f"FEHLT: {pfad}")
        return 1

    report = json.loads(pfad.read_text(encoding="utf-8"))
    neu = bool(a.eigen)
    vorher = report.get(FELD)

    print(f"Aufnahme : {report.get('fileName')}")
    print(f"Endung   : {'.wav -> gaelte als eigen' if str(report.get('fileName','')).lower().endswith('.wav') else 'keine .wav -> gaelte als fremd'}")
    print(f"{FELD}: {vorher if vorher is not None else 'nicht gesetzt'} -> {neu}")

    if vorher == neu:
        print("\nUnveraendert.")
        return 0
    if not a.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
        return 0

    report[FELD] = neu
    pfad.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    print("\nGeschrieben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
