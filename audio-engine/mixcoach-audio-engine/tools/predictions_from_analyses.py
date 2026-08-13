"""Vorhersage-Datei aus gespeicherten Analysen bauen (Job B, Schritt 2).

`analyze_timing_bias.py --predictions` erwartet analysisId -> {index: sekunde}.
Dieses Skript erzeugt so eine Datei aus den bereits vorliegenden
Analyse-Ergebnissen, ohne Audio anzufassen.

Damit laesst sich die eigentliche Frage von Job B beantworten: wie gut ist
das heutige `start_sec` gegenueber dem menschlichen Referenzpunkt - im
Unterschied zu `mid_sec`, gegen das bisher gemessen wurde.

    python -m tools.predictions_from_analyses --field start_sec --out start.json
    python -m tools.analyze_timing_bias --predictions start.json

Warum ueber die gespeicherten Analysen und nicht ueber einen frischen Lauf?
Weil so der Kandidatengenerator garantiert unveraendert bleibt. Gemessen
wird nur die Zeitangabe, nicht die Erkennung - genau die Trennung, die
Akzeptanzkriterium 5 verlangt (Recall darf nicht schlechter werden).

Zuordnung: GT-Verdict "3" gehoert zu setTransitions mit index == 3. Zur
Sicherheit wird zusaetzlich geprueft, dass mid_sec und der im Verdict
gespeicherte midSec uebereinstimmen - stimmen sie nicht, wurde die Analyse
seit dem Bewerten neu gerechnet und die Zuordnung waere stillschweigend
falsch. Solche Faelle werden ausgelassen und gezaehlt, nicht geraten.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
PROJEKT_ROOT = ENGINE_ROOT.parents[1]

# Der zweite Stamm ist am 13.08.2026 zusammengefuehrt und nach
# _archiv_2026-08-13/ verschoben worden (tools/staemme_zusammenfuehren.py).
# Er wird nur noch gelesen: die Ground Truth dort ist vollstaendig in
# daten/ eingearbeitet, die 67 .wav daneben gibt es nirgends sonst.
ARCHIV = ENGINE_ROOT / "_archiv_2026-08-13"

ANALYSE_DIRS = [
    PROJEKT_ROOT / "daten" / "analysis_results",
    ARCHIV / "analysis_results",
]
GT_DIRS = [
    PROJEKT_ROOT / "daten" / "ground_truth",
    ARCHIV / "ground_truth",
]

# Toleranz beim Abgleich von mid_sec gegen den im Verdict gespeicherten
# midSec. Beide sind auf 2 Nachkommastellen gerundet, mehr als
# Rundungsrauschen darf nicht auseinanderliegen.
MID_TOLERANZ_S = 0.5


def _sammle(dirs: list[Path]) -> dict[str, Path]:
    """id -> Datei. Frueheres Verzeichnis gewinnt bei Namensgleichheit."""
    out: dict[str, Path] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            out.setdefault(f.stem, f)
    return out


def baue(field: str) -> tuple[dict, dict]:
    analysen = _sammle(ANALYSE_DIRS)
    ground_truth = _sammle(GT_DIRS)

    predictions: dict[str, dict[str, float]] = {}
    statistik = {
        "sets_mit_gt": len(ground_truth),
        "sets_mit_gt_und_analyse": 0,
        "sets_ohne_analyse": [],
        "vorhersagen": 0,
        "kein_passender_index": 0,
        "mid_sec_weicht_ab": 0,
        "feld_fehlt": 0,
    }

    for aid, gt_datei in ground_truth.items():
        analyse_datei = analysen.get(aid)
        if analyse_datei is None:
            statistik["sets_ohne_analyse"].append(aid)
            continue
        statistik["sets_mit_gt_und_analyse"] += 1

        analyse = json.loads(analyse_datei.read_text(encoding="utf-8"))
        gt = json.loads(gt_datei.read_text(encoding="utf-8"))
        nach_index = {str(t.get("index")): t for t in (analyse.get("setTransitions") or [])}

        fuer_set: dict[str, float] = {}
        for idx, verdict in (gt.get("verdicts") or {}).items():
            transition = nach_index.get(str(idx))
            if transition is None:
                statistik["kein_passender_index"] += 1
                continue
            mid = transition.get("mid_sec")
            if mid is None or abs(float(mid) - float(verdict.get("midSec", 0))) > MID_TOLERANZ_S:
                statistik["mid_sec_weicht_ab"] += 1
                continue
            wert = transition.get(field)
            if wert is None:
                statistik["feld_fehlt"] += 1
                continue
            fuer_set[str(idx)] = float(wert)

        if fuer_set:
            predictions[aid] = fuer_set
            statistik["vorhersagen"] += len(fuer_set)

    return predictions, statistik


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--field", default="start_sec",
                   help="Feld aus setTransitions, das als Engine-Zeitpunkt gilt "
                        "(start_sec, mid_sec, end_sec). Default: start_sec")
    p.add_argument("--out", type=Path, required=True, help="Zieldatei")
    args = p.parse_args()

    predictions, s = baue(args.field)
    args.out.write_text(json.dumps(predictions, indent=1), encoding="utf-8")

    print(f"Feld:                        {args.field}")
    print(f"Sets mit Ground Truth:       {s['sets_mit_gt']}")
    print(f"  davon mit Analyse:         {s['sets_mit_gt_und_analyse']}")
    print(f"  ohne Analyse:              {len(s['sets_ohne_analyse'])}")
    print(f"Vorhersagen geschrieben:     {s['vorhersagen']}")
    if s["kein_passender_index"]:
        print(f"  ! kein passender Index:    {s['kein_passender_index']}")
    if s["mid_sec_weicht_ab"]:
        print(f"  ! mid_sec weicht ab:       {s['mid_sec_weicht_ab']}"
              f"  (Analyse seit dem Bewerten neu gerechnet)")
    if s["feld_fehlt"]:
        print(f"  ! Feld fehlt:              {s['feld_fehlt']}")
    print(f"\nGeschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
