"""Baseline-Messung der Uebergangserkennung ueber mehrere Toleranzen.

Warum es dieses Skript zusaetzlich zu retrain_model.loso_metrics gibt:
Die dortige Bewertung gruppiert Positiv-Anker in Cluster und zaehlt einen
Cluster als getroffen, sobald IRGENDEIN Marker im Fenster liegt. Bei
cluster_gap=105s verschmelzen dabei benachbarte, in Wahrheit getrennte
Uebergaenge zu einem einzigen "Treffer" - die Zahl wird dadurch
systematisch zu gut. Fuer eine ehrliche Messung im Sekundenbereich braucht
es eine 1:1-Zuordnung: jeder Marker darf hoechstens einen Anker erklaeren
und jeder Anker hoechstens einmal getroffen werden (greedy nach Abstand).

Zwei Anker-Mengen werden getrennt ausgewiesen:
  ALLE          - alle Positiv-Anker
  UNABHAENGIG   - nur DJ-gesetzte Zeiten (timing_off/correctedSec, missed).
                  Anker aus verdict="correct" tragen die midSec des
                  Engine-Markers; gegen sie bei enger Toleranz zu messen
                  ist zirkulaer (die Engine trifft ihre eigene Ausgabe).
                  Siehe tools/eval/gt_inventory.py.

Aufruf (im Projektordner mixcoach-audio-engine, ohne Argumente lauffaehig):
    python -m tools.eval.eval_detection
Optionen:
    --min-p 0.6 --gap 90        Auswahl-Parameter (Default: aus dem aktiven Modell)
    --holdout-file <pfad>       Sets, die ausgeschlossen bleiben
    --json <pfad>               Ergebnis zusaetzlich als JSON
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from app.calibration import retrain_model as rm  # noqa: E402
from app.calibration.build_features import load_truth  # noqa: E402
from app.paths import GROUND_TRUTH_DIR  # noqa: E402

# Toleranzstufen in Sekunden. "1 Takt" = 4 Beats; bei 120 BPM sind das 2,0 s
# - deshalb faellt diese Stufe hier mit +-2 s zusammen und wird separat
# ausgewiesen, sobald ein set-spezifisches Tempo vorliegt (siehe bar_seconds).
TOLERANCES = [0.5, 1.0, 2.0, 5.0, 10.0, 105.0]
BAR_LABEL_BPM = 120.0

# Anker, die naeher als das beieinander liegen, gelten als derselbe
# Uebergang (identisch zu retrain_model._merge_truth).
ANCHOR_DEDUPE = 3.0


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float, float]:
    """Punktschaetzer + Wilson-Konfidenzintervall fuer eine Rate."""
    if total == 0:
        return 0.0, 0.0, 0.0
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return p, max(0.0, centre - margin), min(1.0, centre + margin)


def dedupe(times: list[float], gap: float = ANCHOR_DEDUPE) -> list[float]:
    out: list[float] = []
    for t in sorted(times):
        if not out or t - out[-1] > gap:
            out.append(t)
    return out


def greedy_match(predicted: list[float], truth: list[float], tol: float) -> int:
    """1:1-Zuordnung: Anzahl Anker, die von genau einem Marker erklaert werden.

    Greedy ueber alle Paare nach Abstand - jeder Marker und jeder Anker wird
    hoechstens einmal verbraucht. Verhindert, dass ein einzelner Marker bei
    grosser Toleranz mehrere Anker 'trifft'.
    """
    pairs = sorted(
        ((abs(p - t), i, j) for i, p in enumerate(predicted) for j, t in enumerate(truth)
         if abs(p - t) <= tol)
    )
    used_p: set[int] = set()
    used_t: set[int] = set()
    hits = 0
    for _, i, j in pairs:
        if i in used_p or j in used_t:
            continue
        used_p.add(i)
        used_t.add(j)
        hits += 1
    return hits


def load_independent_anchors() -> dict[str, list[float]]:
    """Nur DJ-gesetzte Zeiten je analysisId (timing_off + missed)."""
    out: dict[str, list[float]] = {}
    for path in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vals: list[float] = []
        for entry in (data.get("verdicts") or {}).values():
            if entry.get("verdict") == "timing_off" and entry.get("correctedSec") is not None:
                vals.append(float(entry["correctedSec"]))
        vals.extend(float(s) for s in (data.get("missed") or []))
        vals.extend(float(s) for s in (data.get("true_transitions_sec") or []))
        if vals:
            out[path.stem] = sorted(vals)
    return out


def anchors_by_set_name() -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """(alle Anker, unabhaengige Anker) je SET-NAME (Dateiname der Aufnahme).

    Die Ground-Truth-Dateien sind nach analysisId benannt; das Training
    gruppiert nach Dateiname der Aufnahme (mehrere Analysen derselben Datei
    werden zusammengefuehrt). Dieselbe Zuordnung wird hier nachgebaut.
    """
    independent_by_id = load_independent_anchors()
    all_by_name: dict[str, list[float]] = {}
    ind_by_name: dict[str, list[float]] = {}

    for path in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        analysis_id = path.stem
        result, _ = rm._find_result_json(analysis_id)
        if not result:
            continue
        name = result.get("fileName") or result.get("filename")
        if not name:
            continue
        truth = load_truth(path)
        all_by_name.setdefault(name, []).extend(truth["positives"])
        if analysis_id in independent_by_id:
            ind_by_name.setdefault(name, []).extend(independent_by_id[analysis_id])

    return ({k: dedupe(v) for k, v in all_by_name.items()},
            {k: dedupe(v) for k, v in ind_by_name.items()})


def evaluate(predictions: dict[str, list[float]],
             anchors: dict[str, list[float]],
             tol: float) -> dict:
    """Aggregiert ueber alle Sets: Precision/Recall/F1 mit 1:1-Zuordnung."""
    hits = n_pred = n_true = 0
    covered_sets = 0
    for name, preds in predictions.items():
        truth = anchors.get(name)
        if not truth:
            continue          # Set ohne Anker dieser Art -> nicht bewertbar
        covered_sets += 1
        hits += greedy_match(preds, truth, tol)
        n_pred += len(preds)
        n_true += len(truth)

    p, p_lo, p_hi = wilson(hits, n_pred)
    r, r_lo, r_hi = wilson(hits, n_true)
    f1 = 2 * hits / (n_pred + n_true) if (n_pred + n_true) else 0.0
    return {"tolerance": tol, "hits": hits, "n_pred": n_pred, "n_true": n_true,
            "sets": covered_sets,
            "precision": p, "precision_lo": p_lo, "precision_hi": p_hi,
            "recall": r, "recall_lo": r_lo, "recall_hi": r_hi, "f1": f1}


def print_table(title: str, rows: list[dict]) -> None:
    print(f"\n{title}")
    print(f"{'Toleranz':>12} | {'Precision':>22} | {'Recall':>22} | {'F1':>5} | "
          f"{'Treffer':>7} | {'Marker':>6} | {'Anker':>5}")
    print("-" * 104)
    for r in rows:
        tol = r["tolerance"]
        label = f"+-{tol:g} s"
        if abs(tol - 2.0) < 1e-9:
            label = f"+-{tol:g} s (1 Takt)"
        print(f"{label:>12} | "
              f"{r['precision']:.3f} [{r['precision_lo']:.3f}-{r['precision_hi']:.3f}] | "
              f"{r['recall']:.3f} [{r['recall_lo']:.3f}-{r['recall_hi']:.3f}] | "
              f"{r['f1']:.3f} | {r['hits']:7d} | {r['n_pred']:6d} | {r['n_true']:5d}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Baseline-Messung ueber mehrere Toleranzen.")
    ap.add_argument("--min-p", type=float, default=None)
    ap.add_argument("--gap", type=float, default=None)
    ap.add_argument("--holdout-file", type=Path, default=Path("tools/eval/holdout_sets.txt"))
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--include-synthetic", action="store_true")
    args = ap.parse_args()

    t_start = time.time()

    active = rm.load_active_model() if hasattr(rm, "load_active_model") else None
    if active is None:
        try:
            active = json.loads(rm.MODEL_PATH.read_text(encoding="utf-8"))
        except Exception:
            active = {}
    sel = (active or {}).get("selection", {})
    min_p = args.min_p if args.min_p is not None else sel.get("min_probability", 0.6)
    gap = args.gap if args.gap is not None else sel.get("min_gap_seconds", 90.0)

    holdout: set[str] = set()
    if args.holdout_file and args.holdout_file.exists():
        holdout = {ln.strip() for ln in args.holdout_file.read_text(encoding="utf-8").splitlines()
                   if ln.strip() and not ln.startswith("#")}

    print("=" * 104)
    print("BASELINE Uebergangserkennung - aktives Modell, LOSO, mehrere Toleranzen")
    print("=" * 104)
    print(f"Datum:            {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Auswahl:          min_probability={min_p}  min_gap={gap}s")
    print(f"Holdout-Sets:     {len(holdout)} ausgeschlossen")

    print("\nLade Trainingszeilen (Cache, falls vorhanden)...")
    t0 = time.time()
    rows = rm.collect_rows(include_synthetic=args.include_synthetic)
    print(f"  {len(rows)} Zeilen aus {len(set(r['set'] for r in rows))} Sets "
          f"({time.time()-t0:.1f}s)")

    if holdout:
        rows = [r for r in rows if r["set"] not in holdout]
        print(f"  nach Holdout-Ausschluss: {len(set(r['set'] for r in rows))} Sets")

    print("\nLOSO-Wahrscheinlichkeiten (einmal fuer alle Toleranzen)...")
    t0 = time.time()
    preds_raw = rm.loso_predictions(rows, rm.make_model)
    print(f"  {len(preds_raw)} Sets bewertet ({time.time()-t0:.1f}s)")

    predictions = {name: rm.select_markers(test, probs, min_p, gap)
                   for name, (test, probs) in preds_raw.items()}
    total_markers = sum(len(v) for v in predictions.values())
    print(f"  {total_markers} Marker insgesamt "
          f"({total_markers/max(1,len(predictions)):.1f} je Set)")

    print("\nLade Ground-Truth-Anker...")
    all_anchors, ind_anchors = anchors_by_set_name()
    print(f"  Sets mit Ankern: alle={len(all_anchors)}  unabhaengig={len(ind_anchors)}")

    rows_all = [evaluate(predictions, all_anchors, t) for t in TOLERANCES]
    rows_ind = [evaluate(predictions, ind_anchors, t) for t in TOLERANCES]

    print_table("A) ALLE Positiv-Anker (enthaelt zirkulaere 'correct'-Anker)", rows_all)
    print_table("B) NUR UNABHAENGIGE Anker (DJ-gesetzte Zeiten) - die belastbare Messung",
                rows_ind)

    print(f"\n1 Takt = 4 Beats = {4*60/BAR_LABEL_BPM:.1f}s bei {BAR_LABEL_BPM:g} BPM "
          f"-> faellt mit der +-2 s-Stufe zusammen.")
    print(f"+-105 s ist die Altwert-Spalte (retrain_model.CLUSTER_GAP), nur fuer den "
          f"Vergleich mit dd/retrain_log.txt.")
    print(f"\nGesamtlaufzeit: {time.time()-t_start:.1f}s")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "min_p": min_p, "gap": gap,
            "holdout": sorted(holdout),
            "sets_evaluated": len(preds_raw),
            "markers_total": total_markers,
            "all_anchors": rows_all,
            "independent_anchors": rows_ind,
        }, indent=1), encoding="utf-8")
        print(f"JSON geschrieben: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
