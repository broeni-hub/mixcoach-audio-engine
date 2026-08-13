"""Bringt die Ehrlichkeitslinie aus dem Code in die gespeicherten Reports.

Der Befund (PROJEKT_REVIEW_2026-08-13.md, 5a), nachgezaehlt am 13.08.2026:

    scores.beatmatching = None :  0 von 50
    scores.timing       = None :  0 von 50
    notMeasured                :  50 von 50 mit nur ['eq','creativity','frequency']

`analysis_mapper.py` setzt beide seit dem 31.07. auf None und fuehrt fuenf
Eintraege in NOT_YET_MEASURED. Nur wurde seither **keine Analyse neu
gerechnet**. Der Code ist ehrlich, die Historie nicht - und der DJ sieht in
jedem seiner Sets weiter eine Beatmatching-Note von 96-100 aus einem
Tempo-Schaetzer, der in 89 % der Faelle exakt 0,0 Drift meldet.

## Warum nicht einfach neu analysieren

Weil es die Ground Truth entwerten wuerde. Die 45 Label-Dateien haengen an
Analyse-IDs und Uebergangs-Indizes; mit `gap=150` faende die Erkennung andere
Uebergaenge, und Sebastians Klickarbeit zeigte ins Leere. Deshalb wird hier
**nichts an der Erkennung angefasst** - kein Uebergang, kein Zeitpunkt, kein
Index aendert sich. Nur die drei Set-Noten werden auf den heutigen Stand
gebracht.

## Was mit scores.overall passiert

Die alte Kopfzahl entstand aus sechs Teilen, darunter phrase_timing und
beatmatching. Die heutige Formel (pipeline.py) nutzt nur noch harmonic,
energy_shape und flow. Aus dem gespeicherten Report sind davon zwei verfuegbar
(`musicality` = harmonic, `flow`); `energy_shape` wurde nie in den Report
gemappt.

Neu gebildet wird deshalb aus den VERFUEGBAREN - genau so, wie es
`_combined_score` und `composite_score` im Bestand ohnehin halten, wenn eine
Dimension fehlt. Das ist kein neuer Rechenweg, sondern der vorhandene mit einem
fehlenden Eingang.

Der Effekt ist nicht kosmetisch:

    alt   Median 71   Spanne 65-77   sigma  2,6
    neu   Median 62   Spanne 53-90   sigma 12,7

Die alte Zahl spannte ueber 50 Sets zwoelf Punkte - die Pipeline nennt sie
selbst "eine Kopfzahl, die keinen DJ von einem anderen unterscheiden kann".
Die neue streut fuenfmal so weit und kann damit ueberhaupt erst etwas zeigen.

Welche Eingaenge zur Verfuegung standen, wird je Report festgehalten
(`overallInputs`) - ohne diese Angabe waere ein Vergleich mit einer frisch
analysierten Aufnahme (die drei Eingaenge hat) stillschweigend unsauber.

Sicherung: 'git checkout -- daten/analysis_results/' holt alles zurueck.

    python -m tools.backfill_honest_scores --dry-run
    python -m tools.backfill_honest_scores
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.analysis_mapper import NOT_YET_MEASURED  # noqa: E402
from app.audio.pipeline.scoring_version import SCORING_VERSION  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402

# Die Teile, aus denen die heutige Gesamtnote entsteht (pipeline.py), und wie
# sie im gespeicherten Report heissen. energy_shape fehlt dort - deshalb steht
# es hier nicht: was nicht da ist, wird nicht geraten.
OVERALL_TEILE = {"musicality": 0.10, "flow": 0.10}


def _neuer_overall(scores: dict) -> tuple[float | None, list[str]]:
    verfuegbar = [(scores[k], w) for k, w in OVERALL_TEILE.items()
                  if scores.get(k) is not None]
    if not verfuegbar:
        return None, []
    gewicht = sum(w for _, w in verfuegbar)
    wert = round(sum(s * w for s, w in verfuegbar) / gewicht)
    return wert, sorted(k for k in OVERALL_TEILE if scores.get(k) is not None)


def _muss_angefasst(report: dict) -> bool:
    s = report.get("scores") or {}
    return (s.get("beatmatching") is not None
            or s.get("timing") is not None
            or set(report.get("notMeasured") or []) != set(NOT_YET_MEASURED))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    offen = []
    for pfad in sorted(RESULTS_DIR.glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not report.get("setTransitions"):
            continue
        if _muss_angefasst(report):
            offen.append((pfad, report))

    if not offen:
        print("Nichts zu tun - alle Reports tragen bereits den ehrlichen Stand.")
        return 0

    print(f"{len(offen)} Report(s) mit altem, unehrlichem Notenstand.")
    print()
    print(f"{'Aufnahme':<30}{'beatm.':>8}{'timing':>8}{'overall alt':>13}{'neu':>7}")
    alt_werte, neu_werte = [], []
    for pfad, report in offen:
        s = report.get("scores") or {}
        neu, _ = _neuer_overall(s)
        if s.get("overall") is not None:
            alt_werte.append(s["overall"])
        if neu is not None:
            neu_werte.append(neu)
        print(f"{(report.get('fileName') or pfad.stem)[:29]:<30}"
              f"{str(s.get('beatmatching')):>8}{str(s.get('timing')):>8}"
              f"{str(s.get('overall')):>13}{str(neu):>7}")

    if alt_werte and neu_werte:
        print()
        print(f"  alt: Median {statistics.median(alt_werte):.0f}  "
              f"Spanne {min(alt_werte)}-{max(alt_werte)}  "
              f"sigma {statistics.pstdev(alt_werte):.1f}")
        print(f"  neu: Median {statistics.median(neu_werte):.0f}  "
              f"Spanne {min(neu_werte)}-{max(neu_werte)}  "
              f"sigma {statistics.pstdev(neu_werte):.1f}")

    if args.dry_run:
        print("\n--dry-run: nichts geschrieben.")
        return 0

    print()
    for pfad, report in offen:
        s = report.setdefault("scores", {})
        neu, eingaenge = _neuer_overall(s)
        s["beatmatching"] = None
        s["timing"] = None
        s["overall"] = neu
        report["notMeasured"] = list(NOT_YET_MEASURED)
        report["scoringVersion"] = SCORING_VERSION
        # Welche Eingaenge die Gesamtnote tragen konnten. Eine frisch
        # analysierte Aufnahme hat zusaetzlich energy_shape - ohne diese
        # Angabe waere der Vergleich stillschweigend unsauber.
        report["overallInputs"] = eingaenge
        tmp = pfad.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(report), encoding="utf-8")
        os.replace(tmp, pfad)

    print(f"{len(offen)} Report(s) auf den ehrlichen Stand gebracht.")
    print("  beatmatching und timing stehen auf None und in notMeasured,")
    print("  overall neu gebildet aus den verfuegbaren Teilen,")
    print(f"  scoringVersion = {SCORING_VERSION} gestempelt.")
    print()
    print("Die Erkennung wurde NICHT angefasst - kein Uebergang, kein")
    print("Zeitpunkt, kein Index hat sich geaendert. Die Ground Truth gilt weiter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
