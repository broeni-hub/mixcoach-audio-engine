"""Welcher Betriebspunkt macht den ersten Eindruck am besten? (A2)

Der aktive Punkt ist min_probability = 0,6 / min_gap = 150 s, gewaehlt auf
F1 - also auf ein Gleichgewicht aus Finden und Treffen. Fuer einen fremden
DJ, der zum ersten Mal einen Report sieht, ist das die falsche Zielgroesse:

    Ein Marker, der auf nichts zeigt, kostet mehr als ein fehlender.

Er klickt, hoert mitten in einen Track und hat entschieden. Ein Uebergang,
den das Werkzeug gar nicht erst zeigt, faellt ihm dagegen selten auf - er
weiss ja nicht, was fehlt. Deshalb wird hier Precision gegen Recall neu
abgewogen, und zwar als MESSUNG, nicht als Behauptung.

    python -m tools.eval.betriebspunkt
    python -m tools.eval.betriebspunkt --gap 150 --tol 105

WAS DAS NICHT IST
-----------------
Keine Grid-Search ueber die Schwellwerte in detect_set_transition_zones() -
die ist in CLAUDE.md ausdruecklich ausgeschlossen, weil sie am falschen
Hebel dreht. Hier geht es um den Betriebspunkt des Modells, also darum, ab
welcher Wahrscheinlichkeit ein Kandidat zum Marker wird. Der ist als Knopf
gedacht und in app/models/track_change_gbm.json hinterlegt.

WIE GEMESSEN WIRD
-----------------
Der teure Teil (LOSO ueber alle Sets) laeuft EINMAL; die Schwelle wird
danach auf dieselben Wahrscheinlichkeiten mehrfach angewendet. Ein Durchlauf
je Schwelle waere derselbe Rechenaufwand mal zehn.

Ausgewiesen wird gegen die UNABHAENGIGEN Anker - nur vom DJ selbst gesetzte
Zeiten (timing_off mit correctedSec, missed). Anker aus verdict="correct"
tragen die midSec des Engine-Markers; gegen sie zu messen hiesse, die Engine
an ihrer eigenen Ausgabe zu messen.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.calibration import retrain_model as rm  # noqa: E402
from tools.eval.eval_detection import (anchors_by_set_name,  # noqa: E402
                                       evaluate)

SCHWELLEN = [0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gap", type=float, default=None,
                    help="min_gap_seconds (Vorgabe: aus dem aktiven Modell)")
    ap.add_argument("--tol", type=float, default=105.0,
                    help="Toleranz in s, in der ein Marker einen Anker erklaert")
    ap.add_argument("--holdout-file", type=Path,
                    default=Path("tools/eval/holdout_sets.txt"))
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    try:
        aktiv = json.loads(rm.MODEL_PATH.read_text(encoding="utf-8"))
    except Exception:
        aktiv = {}
    sel = aktiv.get("selection", {})
    gap = args.gap if args.gap is not None else sel.get("min_gap_seconds", 150.0)
    aktives_p = sel.get("min_probability", 0.6)

    print("=" * 88)
    print("  Betriebspunkt - Precision gegen Recall (A2)")
    print("=" * 88)
    print(f"  aktiver Punkt: min_p = {aktives_p}, gap = {gap} s")
    print(f"  Toleranz:      +-{args.tol:g} s")
    print()

    holdout: set[str] = set()
    if args.holdout_file and args.holdout_file.exists():
        holdout = {ln.strip() for ln in args.holdout_file.read_text(encoding="utf-8").splitlines()
                   if ln.strip() and not ln.startswith("#")}

    t0 = time.time()
    rows = rm.collect_rows(include_synthetic=False)
    if holdout:
        rows = [r for r in rows if r["set"] not in holdout]
    print(f"  {len(rows)} Zeilen aus {len(set(r['set'] for r in rows))} Sets "
          f"({time.time()-t0:.0f}s)")

    t0 = time.time()
    preds_raw = rm.loso_predictions(rows, rm.make_model)
    print(f"  LOSO ueber {len(preds_raw)} Sets ({time.time()-t0:.0f}s) - "
          f"laeuft nur EINMAL fuer alle Schwellen")
    print()

    _, ind_anchors = anchors_by_set_name()

    print(f"  {'min_p':>7} {'Marker':>7} {'je Set':>7} {'Precision':>10} "
          f"{'Recall':>8} {'F1':>6}   {'Marker, die auf nichts zeigen':>30}")
    print("  " + "-" * 84)
    ergebnisse = []
    for p in SCHWELLEN:
        vorhersagen = {name: rm.select_markers(test, probs, p, gap)
                       for name, (test, probs) in preds_raw.items()}
        e = evaluate(vorhersagen, ind_anchors, args.tol)
        n = sum(len(v) for v in vorhersagen.values())
        falsch = e["n_pred"] - e["hits"]
        marke = "  <- aktiv" if abs(p - aktives_p) < 1e-9 else ""
        print(f"  {p:>7.2f} {n:>7} {n/max(1,len(vorhersagen)):>7.1f} "
              f"{e['precision']:>10.3f} {e['recall']:>8.3f} {e['f1']:>6.3f}   "
              f"{falsch:>10} von {e['n_pred']}{marke}")
        ergebnisse.append({"min_p": p, "marker": n, **e})

    print()
    print("  LESEHILFE")
    print("  Precision = Anteil der Marker, die einen echten Uebergang erklaeren.")
    print("  Recall    = Anteil der echten Uebergaenge, die gefunden werden.")
    print("  Fuer den ersten Eindruck zaehlt die linke Spalte: sechs richtige")
    print("  Marker schlagen zehn, von denen zwei auf nichts zeigen.")

    if args.json:
        args.json.write_text(json.dumps(ergebnisse, indent=1), encoding="utf-8")
        print(f"\n  Geschrieben: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
