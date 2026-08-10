"""Tragen die 17 Merkmale den Uebergangs-ZEITPUNKT, oder nur das Ja/Nein?

Das ist die zentrale Frage hinter der Live-Schwelle. `build_features.py:37-38`
setzt FAIR_BEFORE = 45 s und FAIR_AFTER = 60 s: ein Kandidat gilt als positiv,
wenn er IRGENDWO in einem 105-s-Fenster liegt. Sekundengenauigkeit war mit
dieser Zieldefinition nie verlangt. Die naheliegende Hoffnung lautet deshalb:
die 161 exakten `correctedSec` schaerfer nutzen und den Versatz direkt lernen.

Dieses Skript misst, ob das gehen KANN. Regressiert wird auf denselben 17
Merkmalen der VERSATZ (Wahrheits-Anker minus Kandidatenzeit), LOSO ueber die
Aufnahmen. Drei Zeilen stehen nebeneinander, und nur der Vergleich traegt:

  1. Ausgangsstreuung  - der Versatz, wie er ohne jede Korrektur dasteht
  2. LOSO-Regression   - was die 17 Merkmale davon wegnehmen
  3. konstanter Offset - was schon ein globaler Median wegnimmt

Zeile 3 ist die eigentliche Messlatte. Ein konstanter Offset gilt in diesem
Projekt definitionsgemaess als KEIN Fortschritt (er laesst sigma unveraendert,
siehe CLAUDE.md). Schlaegt die Regression ihn nicht deutlich, tragen die
Merkmale die Zeit nicht - und dann hilft weder mehr Labeln noch eine andere
Verlustfunktion, weil die Antwort nicht in den Eingangsdaten steht.

Rekonstruktion der Messung vom 30.07.2026 (`ZUKUNFTSWEGE_2026-07-30.md` 1.3,
R^2 = 0,082). Das Originalskript lag im Sitzungs-Scratchpad und ist verloren;
diese Fassung ist unabhaengig nachgebaut, die Zahlen sind daher eine
NACHPRUEFUNG, keine Kopie.

Laeuft ohne Audio (nur auf dem Feature-Cache), braucht numpy und sklearn.

    python -m tools.eval.zeit_regression
    python -m tools.eval.zeit_regression --modell ridge
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.calibration.build_features import (  # noqa: E402
    FAIR_AFTER, FAIR_BEFORE, load_truth,
)
from app.calibration.retrain_model import (  # noqa: E402
    FEATURES, _find_result_json, _merge_truth, collect_rows,
)
from app.paths import GROUND_TRUTH_DIR  # noqa: E402


def anker_je_aufnahme() -> dict[str, list[float]]:
    """fileName -> Wahrheits-Anker in Sekunden.

    Dieselbe Gruppierung wie `collect_feedback_rows()`: nach `fileName`, nicht
    nach Analyse-ID, sonst zaehlt eine mehrfach analysierte Aufnahme mehrfach.
    Braucht kein Audio - nur die Ground Truth und die Ergebnis-JSONs.
    """
    gruppen: dict[str, list[Path]] = defaultdict(list)
    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        result, _ = _find_result_json(gt_file.stem)
        gruppen[(result or {}).get("fileName") or gt_file.stem].append(gt_file)

    out: dict[str, list[float]] = {}
    for file_name, gt_files in gruppen.items():
        truth = _merge_truth([load_truth(p) for p in gt_files])
        if truth["positives"]:
            out[file_name] = truth["positives"]
    return out


def paare(rows: list[dict], anker: dict[str, list[float]]) -> list[dict]:
    """Positive Kandidaten mit ihrem naechsten Wahrheits-Anker verheiraten.

    Nur Kandidaten mit label == 1, und nur solche, deren naechster Anker
    tatsaechlich im fairen Fenster liegt - genau die Menge, auf der das
    Ja/Nein-Modell heute trainiert wird. Der Versatz ist Anker minus
    Kandidatenzeit: positiv heisst, die Wahrheit liegt SPAETER.
    """
    out = []
    for r in rows:
        if r.get("label") != 1:
            continue
        kandidaten = anker.get(r["set"])
        if not kandidaten:
            continue
        t = float(r["t"])
        naechster = min(kandidaten, key=lambda a: abs(a - t))
        if not (-FAIR_BEFORE <= t - naechster <= FAIR_AFTER):
            continue
        out.append({**r, "versatz": naechster - t})
    return out


def _kennzahlen(fehler: list[float]) -> dict:
    fehler = list(fehler)
    absolut = [abs(f) for f in fehler]
    return {
        "n": len(fehler),
        "median": statistics.median(fehler) if fehler else 0.0,
        "sigma": statistics.pstdev(fehler) if len(fehler) > 1 else 0.0,
        "in8": 100.0 * sum(1 for a in absolut if a <= 8.0) / len(absolut) if absolut else 0.0,
        "in16": 100.0 * sum(1 for a in absolut if a <= 16.0) / len(absolut) if absolut else 0.0,
    }


def _modell(art: str):
    if art == "ridge":
        from sklearn.linear_model import Ridge
        return Ridge(alpha=1.0)
    from sklearn.ensemble import GradientBoostingRegressor
    # Dieselbe Modellfamilie wie der aktive Klassifikator (make_model), damit
    # der Befund nicht an einer schwaecheren Lernmaschine haengt.
    return GradientBoostingRegressor(random_state=0)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--modell", choices=["gbm", "ridge"], default="gbm")
    p.add_argument("--json", type=Path, help="Kennzahlen zusaetzlich als JSON ablegen")
    args = p.parse_args()

    rows = collect_rows()
    anker = anker_je_aufnahme()
    daten = paare(rows, anker)
    if not daten:
        print("Keine Kandidatenpaare gefunden - gibt es Ground Truth mit Positiv-Ankern?")
        return 1

    sets = sorted({d["set"] for d in daten})
    print(f"{len(daten)} Kandidatenpaare aus {len(sets)} Aufnahmen, Modell: {args.modell}\n")
    if len(sets) < 3:
        print("Weniger als 3 Aufnahmen - LOSO ist hier nicht aussagekraeftig.")
        return 1

    X = np.array([[d.get(f, 0.0) for f in FEATURES] for d in daten], dtype=float)
    y = np.array([d["versatz"] for d in daten], dtype=float)
    gruppe = np.array([d["set"] for d in daten])

    vorhersage = np.zeros_like(y)
    konstante = np.zeros_like(y)
    for s in sets:
        test = gruppe == s
        train = ~test
        if train.sum() < 20 or len(set(y[train])) < 2:
            vorhersage[test] = 0.0
            konstante[test] = 0.0
            continue
        vorhersage[test] = _modell(args.modell).fit(X[train], y[train]).predict(X[test])
        # Der billige Gegenspieler: ein einziger Wert aus den Trainingssets.
        konstante[test] = float(np.median(y[train]))

    zeilen = [
        ("Ausgangsstreuung des Versatzes", y),
        (f"nach LOSO-Regression ({len(FEATURES)} Merkmale)", y - vorhersage),
        ("globaler konstanter Offset", y - konstante),
    ]
    print(f"{'':<40}{'Median':>10}{'sigma':>10}{'in 8 s':>9}{'in 16 s':>9}")
    for name, fehler in zeilen:
        k = _kennzahlen(list(fehler))
        print(f"{name:<40}{k['median']:>+9.2f}s{k['sigma']:>9.2f}s"
              f"{k['in8']:>8.0f}%{k['in16']:>8.0f}%")

    ss_res = float(np.sum((y - vorhersage) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    print(f"\nerklaerter Varianzanteil R^2 = {r2:.3f}")

    # Die Einordnung gehoert in die Ausgabe, nicht in den Kopf eines Berichts,
    # den beim naechsten Mal niemand daneben legt.
    sigma_reg = statistics.pstdev(list(y - vorhersage))
    sigma_konst = statistics.pstdev(list(y - konstante))
    gewinn = 100.0 * (1.0 - sigma_reg / sigma_konst) if sigma_konst else 0.0
    print(f"sigma gegenueber dem konstanten Offset: {gewinn:+.1f} %")
    if r2 < 0.2:
        print("\n-> Die Merkmale tragen die Zeit NICHT. Was auf diesen 17 Groessen")
        print("   arbeitet, kann das Timing nicht loesen - unabhaengig von der")
        print("   Datenmenge. Ein neuer Eingang muesste her, keine neue Zielgroesse.")

    if args.json:
        args.json.write_text(json.dumps({
            "n_paare": len(daten), "n_sets": len(sets), "modell": args.modell,
            "r2": round(r2, 4),
            "zeilen": {name: _kennzahlen(list(f)) for name, f in zeilen},
        }, indent=2), encoding="utf-8")
        print(f"\nKennzahlen geschrieben: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
