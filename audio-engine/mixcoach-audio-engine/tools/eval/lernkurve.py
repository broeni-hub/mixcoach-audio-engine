"""Traegt der erste Burggraben? Was bringt ein zusaetzlich gelabeltes Set?

Die Produktvision begruendet das Wachstum mit der Daten-Schleife: "Jeder
Nutzer bestaetigt oder korrigiert erkannte Uebergaenge mit einem Klick - und
trainiert damit das Erkennungsmodell weiter. [...] Jeder neue Nutzer macht das
Produkt fuer alle besser." Diese Behauptung ist messbar, und zwar hier.

Das Skript beantwortet drei Fragen getrennt, weil sie oft vermengt werden:

  1. Lernkurve   - wie aendern sich Recall/Precision mit der Zahl der
                   Trainings-Sets? Gemessen auf ZURUECKGEHALTENEN Sets, nicht
                   per LOSO: bei LOSO waechst mit k auch die Testmenge, das
                   vermischt zwei Effekte.
  2. Betriebspunkt - wie viel bewegt stattdessen eine andere Schwelle
                   (min_p) oder ein anderer Mindestabstand (min_gap) bei
                   UNVERAENDERTER Datenmenge?
  3. Merkmale    - wie weit kommt man mit einer Teilmenge der 17 Merkmale?
                   Bleibt die Kurve auch dann flach, liegt es nicht an der
                   Datenmenge.

Laeuft ohne Audio (nur auf dem Feature-Cache), braucht numpy und sklearn.

    python -m tools.eval.lernkurve
    python -m tools.eval.lernkurve --ziehungen 10
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.calibration.retrain_model import (  # noqa: E402
    FEATURES, _aggregate, _score_selection, collect_rows, make_model,
)

# Betriebspunkt des aktiven Modells, siehe retrain_model.
AKTIV_MIN_P, AKTIV_GAP = 0.6, 90.0


def _vektor(row: dict, merkmale: list[str]) -> list:
    return [row.get(f, 0.0) for f in merkmale]


def _bewerte(train_rows, test_rows_je_set, min_p, gap, merkmale):
    """Ein Modell auf train_rows, bewertet auf jedem zurueckgehaltenen Set."""
    X = np.array([_vektor(r, merkmale) for r in train_rows])
    y = np.array([r["label"] for r in train_rows])
    if y.sum() == 0 or y.sum() == len(y):
        return None
    modell = make_model().fit(X, y)
    counts = []
    for rows in test_rows_je_set:
        probs = modell.predict_proba(
            np.array([_vektor(r, merkmale) for r in rows]))[:, 1]
        counts.append(_score_selection(rows, list(probs), min_p, gap))
    return _aggregate(counts)


def lernkurve(rows, ks, ziehungen, min_p, gap, merkmale=None):
    merkmale = merkmale or FEATURES
    sets = sorted({r["set"] for r in rows})
    je_set = {s: [r for r in rows if r["set"] == s] for s in sets}
    ergebnis = []
    for k in ks:
        if k >= len(sets):
            continue
        werte = []
        for zug in range(ziehungen):
            rng = random.Random(1000 * k + zug)
            train_sets = rng.sample(sets, k)
            test_sets = [s for s in sets if s not in train_sets]
            train_rows = [r for s in train_sets for r in je_set[s]]
            aus = _bewerte(train_rows, [je_set[s] for s in test_sets],
                           min_p, gap, merkmale)
            if aus:
                werte.append(aus)
        if werte:
            ergebnis.append({
                "k": k, "n": len(werte),
                "recall": statistics.fmean(w[0] for w in werte),
                "precision": statistics.fmean(w[1] for w in werte),
                "f1": statistics.fmean(w[2] for w in werte),
                "sigma_p": (statistics.pstdev([w[1] for w in werte])
                            if len(werte) > 1 else 0.0),
            })
    return ergebnis


def _tabelle(zeilen, titel):
    aus = [titel, "  k Trainings-Sets |  Recall  Precision      F1   sigma(P)"]
    for z in zeilen:
        aus.append(f"  {z['k']:>14} |  {z['recall']*100:5.1f}%     {z['precision']*100:5.1f}%"
                   f"   {z['f1']:.3f}   +-{z['sigma_p']*100:.1f} pp")
    return "\n".join(aus)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ziehungen", type=int, default=6,
                   help="Wiederholungen je k (Default 6)")
    args = p.parse_args()

    rows = collect_rows(include_synthetic=False)
    sets = sorted({r["set"] for r in rows})
    print(f"Datenbasis: {len(rows)} Zeilen aus {len(sets)} Sets "
          f"({sum(r['label'] for r in rows)} positiv)\n")

    ks = [k for k in (4, 8, 12, 16, 20, 24) if k < len(sets)]

    print("=" * 72)
    print("  1. LERNKURVE - was bringt ein zusaetzliches Set?")
    print("=" * 72)
    zeilen = lernkurve(rows, ks, args.ziehungen, AKTIV_MIN_P, 120.0)
    print(_tabelle(zeilen, f"  Betriebspunkt min_p={AKTIV_MIN_P} / gap=120"))
    if len(zeilen) >= 2:
        dp = (zeilen[-1]["precision"] - zeilen[0]["precision"]) * 100
        dr = (zeilen[-1]["recall"] - zeilen[0]["recall"]) * 100
        print(f"\n  Von k={zeilen[0]['k']} auf k={zeilen[-1]['k']}: "
              f"Precision {dp:+.1f} pp, Recall {dr:+.1f} pp")
        print(f"  Streuung zwischen den Ziehungen bei k={zeilen[0]['k']}: "
              f"+-{zeilen[0]['sigma_p']*100:.1f} pp")
        if abs(dp) <= 2 * zeilen[0]["sigma_p"] * 100:
            print("  -> Der Zuwachs liegt INNERHALB der Ziehungs-Streuung.")
            print("     Mehr Sets sind auf dieser Kurve nicht unterscheidbar von Rauschen.")
    print()

    print("=" * 72)
    print("  2. BETRIEBSPUNKT - was bewegt dieselbe Datenmenge?")
    print("=" * 72)
    je_set = {s: [r for r in rows if r["set"] == s] for s in sets}
    print("  min_p   gap |  Recall  Precision      F1")
    for min_p, gap in [(0.5, 60.0), (0.5, 120.0), (0.6, 60.0), (0.6, 90.0),
                       (0.6, 120.0), (0.6, 150.0), (0.7, 120.0), (0.8, 120.0)]:
        werte = []
        for zug in range(3):
            rng = random.Random(7000 + zug)
            train_sets = rng.sample(sets, max(2, int(len(sets) * 0.7)))
            test_sets = [s for s in sets if s not in train_sets]
            aus = _bewerte([r for s in train_sets for r in je_set[s]],
                           [je_set[s] for s in test_sets], min_p, gap, FEATURES)
            if aus:
                werte.append(aus)
        if werte:
            r_, p_, f_ = (statistics.fmean(w[i] for w in werte) for i in range(3))
            aktiv = "  <- aktiv" if (min_p, gap) == (AKTIV_MIN_P, AKTIV_GAP) else ""
            print(f"  {min_p:>5} {gap:>5.0f} |  {r_*100:5.1f}%     {p_*100:5.1f}%   {f_:.3f}{aktiv}")
    print()

    print("=" * 72)
    print("  3. MERKMALE - tragen die 17 ueberhaupt etwas bei?")
    print("=" * 72)
    print("  ACHTUNG beim Lesen: Precision allein sagt hier nichts. Ein")
    print("  Merkmalssatz, der fast nichts auswaehlt, holt sich eine hohe")
    print("  Precision mit einer Handvoll sicherer Treffer und faellt beim")
    print("  Recall auseinander. Gemessen am 31.07.2026 kommt 'nur")
    print("  score/blend/drop' auf 94 % Precision - bei 34 % Recall. F1 ist")
    print("  die Spalte, die zaehlt.\n")
    teilmengen = {
        "alle 17": FEATURES,
        "nur score/blend/drop": ["score", "blend", "drop"],
        "ohne Chroma": [f for f in FEATURES if not f.startswith("chroma")],
        "nur Energie": ["e_before", "e_current", "e_after", "pos_in_set"],
    }
    # Precision ALLEIN waere hier irrefuehrend: ein Merkmalssatz, der fast
    # nichts auswaehlt, gewinnt sie mit ein paar sicheren Treffern. Recall
    # und F1 stehen deshalb daneben - erst zusammen sind sie eine Aussage.
    print(f"  {'Merkmalssatz':<22} {'n':>2}  {'Recall':>7} {'Precision':>10} {'F1':>7}  (k={ks[-1]})")
    for name, merkmale in teilmengen.items():
        z = lernkurve(rows, [4, ks[-1]], args.ziehungen, AKTIV_MIN_P, 120.0, merkmale)
        if len(z) == 2:
            a, b = z
            print(f"  {name:<22} {len(merkmale):>2}  {b['recall']*100:6.1f}% "
                  f"{b['precision']*100:9.1f}% {b['f1']:6.3f}"
                  f"   (k=4: R {a['recall']*100:.0f}% P {a['precision']*100:.0f}% F {a['f1']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
