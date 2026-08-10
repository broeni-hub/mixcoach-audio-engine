"""Was holt die Marker-Entdopplung heraus - und wo ist die Decke?

Die Auswahl arbeitet zweistufig (`retrain_model.select_markers`): erst eine
Mindest-Wahrscheinlichkeit `min_p`, dann eine Nicht-Maximum-Unterdrueckung, die
jeden Marker verwirft, der naeher als `min_gap` an einem bereits gewaehlten
liegt. Beide Zahlen stehen im Modell (`selection`) und werden beim Retrain
mitgewaehlt - sie sind der BETRIEBSPUNKT, und sie kosten kein einziges neues
Label.

Das Skript beantwortet zwei Fragen, die gern vermengt werden:

  1. Wie viel bewegt der Betriebspunkt bei UNVERAENDERTER Datenmenge?
     Ein LOSO-Durchgang, danach beliebig viele Schwellen gratis bewertet.
     Mit Streuung ueber die Aufnahmen (Bootstrap), denn ohne die ist eine
     Differenz von ein paar Prozentpunkten keine Aussage.

  2. Wo ist die Orakel-Schranke?
     Die hoechste Precision, die bei GLEICHER Markerzahl ueberhaupt
     erreichbar waere - wenn die Auswahl die Wahrheit schon kennt. Sie ist
     nicht erreichbar. Sie steht hier, weil die Vorsitzung sich an genau
     dieser Stelle selbst getaeuscht hat: ein Verfahren, das kaum etwas
     auswaehlt, holt sich eine hohe Precision mit einer Handvoll sicherer
     Treffer. Wer eine gemessene Precision nicht gegen ihre Schranke haelt,
     haelt einen Rueckzug fuer einen Fortschritt.

LESEREGEL: Precision allein ist hier nie eine Aussage. Recall daneben, und
F1 ist die Spalte, die zaehlt.

Rekonstruktion aus `ZUKUNFTSWEGE_2026-07-30.md` 1.2; das Originalskript lag im
Sitzungs-Scratchpad und ist verloren. Diese Fassung ist unabhaengig nachgebaut.

Laeuft ohne Audio (nur auf dem Feature-Cache), braucht numpy und sklearn.

    python -m tools.eval.nms2
    python -m tools.eval.nms2 --ziehungen 500
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.audio.ml_classifier import MODEL_PATH  # noqa: E402
from app.calibration.retrain_model import (  # noqa: E402
    CLUSTER_GAP, _aggregate, _score_selection, collect_rows, loso_predictions,
    make_model,
)

# Der Betriebspunkt, den das ausgelieferte Modell faehrt. Wird beim Start aus
# dem Modell gelesen; die Werte hier sind nur der Rueckfall.
AKTIV_MIN_P, AKTIV_GAP = 0.6, 90.0


def _aktiver_betriebspunkt() -> tuple[float, float]:
    try:
        sel = json.loads(MODEL_PATH.read_text(encoding="utf-8"))["selection"]
        return float(sel["min_probability"]), float(sel["min_gap_seconds"])
    except Exception:
        return AKTIV_MIN_P, AKTIV_GAP


def _zaehlungen(loso: dict, min_p: float, gap: float) -> dict[str, tuple]:
    """set -> (Treffer, Wahrheits-Cluster, Auswahl) beim gegebenen Betriebspunkt."""
    return {s: _score_selection(rows, probs, min_p, gap)
            for s, (rows, probs) in loso.items()}


def _bootstrap_sigma(zaehlungen: dict[str, tuple], ziehungen: int, seed: int = 4711) -> tuple:
    """Streuung von Recall/Precision, wenn man die AUFNAHMEN neu zieht.

    Die Unsicherheit sitzt zwischen den Aufnahmen, nicht zwischen einzelnen
    Kandidaten: zwei Sets desselben DJs aehneln sich mehr als zwei zufaellige
    Kandidaten. Deshalb wird ueber Sets gezogen, mit Zuruecklegen.
    """
    namen = list(zaehlungen)
    if len(namen) < 3:
        return 0.0, 0.0
    rng = random.Random(seed)
    recalls, precisions = [], []
    for _ in range(ziehungen):
        zug = [zaehlungen[rng.choice(namen)] for _ in namen]
        r, p, _ = _aggregate(zug)
        recalls.append(r)
        precisions.append(p)
    return statistics.pstdev(recalls), statistics.pstdev(precisions)


def _orakel(zaehlungen: dict[str, tuple]) -> tuple[float, float]:
    """Die Decke bei gleicher Markerzahl.

    Kein Verfahren kann mehr Wahrheits-Cluster treffen, als es Marker setzt,
    und keines mehr, als es Cluster gibt. min(Auswahl, Cluster) ist damit die
    hoechste erreichbare Trefferzahl - erreichbar nur, wenn jeder gesetzte
    Marker auf einem eigenen echten Uebergang landet.
    """
    best = [(min(auswahl, wahrheit), wahrheit, auswahl)
            for _, wahrheit, auswahl in zaehlungen.values()]
    r, p, _ = _aggregate(best)
    return r, p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ziehungen", type=int, default=300,
                    help="Bootstrap-Ziehungen fuer die Streuung (Vorgabe 300)")
    ap.add_argument("--json", type=Path, help="Ergebnis zusaetzlich als JSON ablegen")
    args = ap.parse_args()

    aktiv_p, aktiv_gap = _aktiver_betriebspunkt()
    rows = collect_rows()
    sets = sorted({r["set"] for r in rows})
    print(f"{len(rows)} Kandidaten aus {len(sets)} Aufnahmen. "
          f"Aktiver Betriebspunkt: min_p={aktiv_p}, gap={aktiv_gap:.0f}s")
    print(f"Wahrheits-Cluster ab {CLUSTER_GAP:.0f}s Abstand getrennt.\n")
    if len(sets) < 3:
        print("Weniger als 3 Aufnahmen - LOSO ist hier nicht aussagekraeftig.")
        return 1

    print("LOSO laeuft (einmal, danach sind alle Schwellen gratis)...")
    loso = loso_predictions(rows, make_model)
    print()

    print("=" * 78)
    print("  1. BETRIEBSPUNKT - dieselben Daten, andere Schwellen")
    print("=" * 78)
    print("  Precision allein sagt nichts. F1 ist die Spalte, die zaehlt.")
    print("  'Decke' ist die Orakel-Precision bei DIESER Markerzahl, 'Ausschoepfung'")
    print("  der Anteil davon, den die Auswahl tatsaechlich holt. Steigt die")
    print("  Precision nur, weil die Decke steigt, ist nichts besser geworden -")
    print("  dann wurden bloss weniger Marker gesetzt.\n")
    print(f"  {'min_p':>6} {'gap':>5} | {'Recall':>15} {'Precision':>17} {'F1':>7} "
          f"{'Marker':>7} {'Decke':>7} {'Aussch.':>8}")

    ergebnisse = []
    gitter = [(mp, g) for mp in (0.5, 0.6, 0.7)
              for g in (60.0, 90.0, 120.0, 150.0, 180.0)]
    if (aktiv_p, aktiv_gap) not in gitter:
        gitter.append((aktiv_p, aktiv_gap))
    for min_p, gap in sorted(gitter):
        z = _zaehlungen(loso, min_p, gap)
        r, p, f1 = _aggregate(list(z.values()))
        sr, sp = _bootstrap_sigma(z, args.ziehungen)
        _, decke = _orakel(z)
        marker = sum(a for _, _, a in z.values())
        aussch = p / decke if decke else 0.0
        marke = "  <- aktiv" if (min_p, gap) == (aktiv_p, aktiv_gap) else ""
        print(f"  {min_p:>6} {gap:>5.0f} | {r*100:7.1f}% +-{sr*100:4.1f} "
              f"{p*100:9.1f}% +-{sp*100:4.1f} {f1:>7.3f} "
              f"{marker:>7} {decke*100:>6.1f}% {aussch*100:>7.1f}%{marke}")
        ergebnisse.append({"min_p": min_p, "gap": gap, "recall": r, "precision": p,
                           "f1": f1, "sigma_recall": sr, "sigma_precision": sp,
                           "marker": marker, "decke": decke, "ausschoepfung": aussch})

    aktiv = next(e for e in ergebnisse
                 if e["min_p"] == aktiv_p and e["gap"] == aktiv_gap)
    bestes_f1 = max(ergebnisse, key=lambda e: e["f1"])
    print()
    if bestes_f1 is not aktiv:
        d_f1 = bestes_f1["f1"] - aktiv["f1"]
        d_p = (bestes_f1["precision"] - aktiv["precision"]) * 100
        d_r = (bestes_f1["recall"] - aktiv["recall"]) * 100
        d_decke = (bestes_f1["decke"] - aktiv["decke"]) * 100
        d_aussch = (bestes_f1["ausschoepfung"] - aktiv["ausschoepfung"]) * 100
        print(f"  Bestes F1 bei min_p={bestes_f1['min_p']}, "
              f"gap={bestes_f1['gap']:.0f}s: F1 {d_f1:+.3f} "
              f"(Precision {d_p:+.1f} pp, Recall {d_r:+.1f} pp) gegenueber aktiv.")
        print(f"  Davon kommen {d_decke:+.1f} pp allein aus der hoeheren Decke "
              f"({aktiv['marker']} -> {bestes_f1['marker']} Marker),")
        print(f"  die Ausschoepfung aendert sich um {d_aussch:+.1f} pp.")
        if abs(d_decke) >= 0.8 * abs(d_p):
            print("  -> Das ist im Kern KEINE bessere Erkennung, sondern die")
            print("     Entdopplung mehrfach gesetzter Marker. Der Gewinn ist echt,")
            print("     aber er heisst 'weniger Doubletten', nicht 'trennt besser'.")
        if abs(d_p) <= 2 * aktiv["sigma_precision"] * 100:
            print("  ACHTUNG: der Precision-Unterschied liegt innerhalb der doppelten")
            print("  Streuung zwischen den Aufnahmen - er ist nicht belegt.")
    else:
        print("  Der aktive Betriebspunkt hat bereits das beste F1 im Gitter.")

    print()
    print("=" * 78)
    print("  2. ORAKEL-SCHRANKE - was waere bei gleicher Markerzahl hoechstens drin?")
    print("=" * 78)
    z_aktiv = _zaehlungen(loso, aktiv_p, aktiv_gap)
    o_r, o_p = _orakel(z_aktiv)
    marker = sum(a for _, _, a in z_aktiv.values())
    cluster = sum(w for _, w, _ in z_aktiv.values())
    print(f"  Das Modell setzt {marker} Marker auf {cluster} echte Uebergaenge.")
    print(f"  {'erreicht':<28} Recall {aktiv['recall']*100:5.1f}%   "
          f"Precision {aktiv['precision']*100:5.1f}%")
    print(f"  {'Orakel (nicht erreichbar)':<28} Recall {o_r*100:5.1f}%   "
          f"Precision {o_p*100:5.1f}%")
    luecke = (o_p - aktiv["precision"]) * 100
    print(f"\n  Abstand zur Decke: {luecke:.1f} pp Precision.")
    print("  Alles darueber ist keine bessere Auswahl, sondern ein Rechenfehler")
    print("  oder eine Auswahl, die weniger Marker setzt - das ist Rueckzug,")
    print("  kein Fortschritt, und faellt am Recall auf.")

    if args.json:
        args.json.write_text(json.dumps({
            "aktiv": {"min_p": aktiv_p, "gap": aktiv_gap},
            "gitter": ergebnisse,
            "orakel": {"recall": o_r, "precision": o_p,
                       "marker": marker, "cluster": cluster},
        }, indent=2), encoding="utf-8")
        print(f"\nErgebnis geschrieben: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
