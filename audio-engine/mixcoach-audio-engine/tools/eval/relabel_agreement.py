"""K1: Wie gut trifft der Mensch seine eigene Zeitangabe ein zweites Mal?

Beantwortet die Frage, an der das Akzeptanzkriterium aus
CLAUDE_CODE_SPEC_2026-07-29.md haengt ("sigma deutlich unter 53 s,
innerhalb 8 s >= 50 %"). Dieses Kriterium setzt voraus, dass der
menschliche Bezugspunkt selbst deutlich genauer als 8 s reproduzierbar
ist - gemessen wurde das nie.

Vergleicht Runde 1 (correctedSec aus ground_truth/) gegen Runde 2
(sec aus relabel/), in denselben Groessen wie die Referenzmetrik. Laeuft
ohne Audio und ohne numpy, wie tools/analyze_timing_bias.py.

    python -m tools.eval.relabel_agreement
    python -m tools.eval.relabel_agreement --set <analysisId>

Vorzeichen: delta = runde2 - runde1. Negativ heisst, beim zweiten Mal
frueher markiert.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.jobs import relabel_store  # noqa: E402
from app.paths import GROUND_TRUTH_DIR  # noqa: E402
from tools.eval.gt_status import GT_DIRS  # noqa: E402

# Engine-sigma aus der Referenzmetrik, --mode spec, Stand 29.07.2026.
# Die Zahl, gegen die sich die menschliche Streuung messen lassen muss.
ENGINE_SIGMA = 52.87
WAS_LABEL = {"a_raus": "A geht raus", "b_rein": "B kommt rein",
             "beides": "beide zusammen"}


def _runde1(analysis_id: str) -> dict[int, float]:
    """index -> correctedSec aus der ersten Runde (beide GT-Staemme)."""
    out: dict[int, float] = {}
    for gt_dir in GT_DIRS + [GROUND_TRUTH_DIR]:
        pfad = gt_dir / f"{analysis_id}.json"
        if not pfad.exists():
            continue
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for idx, v in (daten.get("verdicts") or {}).items():
            if v.get("verdict") == "timing_off" and v.get("correctedSec") is not None:
                out[int(idx)] = float(v["correctedSec"])
    return out


def _marker(analysis_id: str) -> dict[int, float]:
    """index -> midSec, der Engine-Marker, den beide Runden gesehen haben.

    Ohne ihn laesst sich nicht pruefen, ob eine Runde am Marker klebt -
    die Frage, an der Werkzeug-Fassung 1 gescheitert ist.
    """
    out: dict[int, float] = {}
    for gt_dir in GT_DIRS + [GROUND_TRUTH_DIR]:
        pfad = gt_dir / f"{analysis_id}.json"
        if not pfad.exists():
            continue
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for idx, v in (daten.get("verdicts") or {}).items():
            if v.get("midSec") is not None:
                out[int(idx)] = float(v["midSec"])
    return out


def _paare(analysis_id: str) -> list[dict]:
    r1 = _runde1(analysis_id)
    marker = _marker(analysis_id)
    r2 = relabel_store.laden(analysis_id).get("antworten") or {}
    paare = []
    for idx, antwort in r2.items():
        if int(idx) not in r1:
            continue
        paare.append({
            "index": int(idx),
            "runde1": r1[int(idx)],
            "runde2": float(antwort["sec"]),
            "delta": float(antwort["sec"]) - r1[int(idx)],
            "was": antwort.get("was"),
            # Fehlender Stempel heisst Fassung 1, siehe relabel_store.
            "werkzeug": int(antwort.get("werkzeug") or 1),
            "engineSec": marker.get(int(idx)),
            "startSec": antwort.get("startSec"),
            "zumMarker": bool(antwort.get("zumMarker")),
        })
    return sorted(paare, key=lambda p: p["index"])


def anker_diagnose(paare: list[dict]) -> list[str]:
    """Klebt eine der beiden Runden am Engine-Marker oder am Startpunkt?

    Das ist keine Nebenrechnung, sondern die Vorfrage: eine Eingabe, die
    die Antwort vorbelegt, erzeugt Uebereinstimmung, die keine ist.
    """
    mit_marker = [p for p in paare if p["engineSec"] is not None]
    z = ["ANKER-DIAGNOSE"]
    if not mit_marker:
        z.append("  Kein Engine-Marker in der Ground Truth - nicht pruefbar.")
        return z

    d1 = [p["runde1"] - p["engineSec"] for p in mit_marker]
    d2 = [p["runde2"] - p["engineSec"] for p in mit_marker]
    z.append("  Abstand zum Engine-Marker, den beide Runden gesehen haben:")
    z.append(_zeile("Runde 1 (App, Wellenform)",
                    f"Median {statistics.median(d1):+7.1f} s   "
                    f"sigma {statistics.pstdev(d1) if len(d1) > 1 else 0:6.1f} s"))
    z.append(_zeile("Runde 2 (Zweitrunden-Seite)",
                    f"Median {statistics.median(d2):+7.1f} s   "
                    f"sigma {statistics.pstdev(d2) if len(d2) > 1 else 0:6.1f} s"))
    naeher = sum(1 for a, b in zip(d1, d2) if abs(b) < abs(a))
    z.append(_zeile("davon Runde 2 naeher am Marker",
                    f"{naeher} von {len(mit_marker)}"))

    # Fassung 2: der Startpunkt ist bekannt und zufaellig - damit laesst
    # sich das Kleben direkt messen statt nur vermuten.
    mit_start = [p for p in mit_marker if p.get("startSec") is not None]
    if len(mit_start) > 2:
        versatz = [p["startSec"] - p["engineSec"] for p in mit_start]
        antwort = [p["runde2"] - p["engineSec"] for p in mit_start]
        am_start = sum(1 for p in mit_start if abs(p["runde2"] - p["startSec"]) <= 8)
        z.append("")
        z.append("  Startpunkt lag zufaellig neben dem Marker - klebt die Antwort daran?")
        try:
            r = statistics.correlation(versatz, antwort)
            z.append(_zeile("Korrelation Startversatz / Antwort", f"r = {r:+.3f}"))
            if abs(r) > 0.5:
                z.append("  -> Die Antwort folgt dem Startpunkt. Das Instrument ankert")
                z.append("     weiterhin; die Zahlen oben sind nicht zu gebrauchen.")
            else:
                z.append("  -> Die Antwort folgt dem Startpunkt NICHT. Der Anker ist raus.")
        except statistics.StatisticsError:
            z.append(_zeile("Korrelation Startversatz / Antwort", "nicht berechenbar"))
        z.append(_zeile("Antwort innerhalb 8 s des Startpunkts",
                        f"{am_start} von {len(mit_start)}"))
        gesprungen = sum(1 for p in mit_start if p["zumMarker"])
        z.append(_zeile("Marker ausdruecklich angefahren",
                        f"{gesprungen} von {len(mit_start)}"))
    return z


def _stats(deltas: list[float]) -> dict:
    if not deltas:
        return {"n": 0}
    absolut = sorted(abs(d) for d in deltas)

    def perzentil(p: float) -> float:
        if len(absolut) == 1:
            return absolut[0]
        pos = p / 100 * (len(absolut) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(absolut) - 1)
        return absolut[lo] + (absolut[hi] - absolut[lo]) * (pos - lo)

    def innerhalb(s: float) -> float:
        return sum(1 for a in absolut if a <= s) / len(absolut) * 100

    return {
        "n": len(deltas),
        "median": statistics.median(deltas),
        "mittel": statistics.fmean(deltas),
        "sigma": statistics.pstdev(deltas) if len(deltas) > 1 else 0.0,
        "p50": perzentil(50), "p75": perzentil(75),
        "p90": perzentil(90), "p95": perzentil(95),
        "in4": innerhalb(4), "in8": innerhalb(8), "in16": innerhalb(16),
    }


def _zeile(label: str, wert: str) -> str:
    return f"  {label:<34} {wert}"


def bericht(analysis_id: str, paare: list[dict], fassung: int) -> str:
    z = ["=" * 72,
         f"  K1 - Selbst-Uebereinstimmung   [{analysis_id}]   Werkzeug-Fassung {fassung}",
         "=" * 72]
    if fassung < relabel_store.WERKZEUG:
        z.append("!! DIESE ANTWORTEN SIND MIT EINEM WERKZEUG ENTSTANDEN, DAS DIE")
        z.append("!! ANTWORT VORBELEGT HAT. Der Abspielkopf startete auf dem")
        z.append("!! Engine-Marker, abgeschickt wurde die Abspielposition. Die")
        z.append("!! Zahlen unten beschreiben das Instrument mit, nicht nur den")
        z.append("!! Menschen - sie beantworten die K1-Frage NICHT.")
        z.append("!! Begruendung und Messung: app/jobs/relabel_store.py, Docstring.")
        z.append("")
    s = _stats([p["delta"] for p in paare])
    z.append(f"SELBST-UEBEREINSTIMMUNG ueber {s['n']} Uebergaenge")
    z.append("  (delta = zweite minus erste Angabe; negativ = beim zweiten Mal frueher)")
    z.append(_zeile("Sigma", f"{s['sigma']:.2f} s"))
    z.append(_zeile("Median", f"{s['median']:+.2f} s"))
    z.append(_zeile("Mittelwert", f"{s['mittel']:+.2f} s"))
    z.append("")
    z.append(_zeile("Absolutfehler p50 / p75", f"{s['p50']:.1f} s / {s['p75']:.1f} s"))
    z.append(_zeile("Absolutfehler p90 / p95", f"{s['p90']:.1f} s / {s['p95']:.1f} s"))
    z.append("")
    z.append(_zeile("innerhalb 4 s", f"{s['in4']:.0f} %"))
    z.append(_zeile("innerhalb 8 s", f"{s['in8']:.0f} %"))
    z.append(_zeile("innerhalb 16 s", f"{s['in16']:.0f} %"))
    z.append("")

    # Systematischer Versatz: labelt er beim zweiten Mal durchweg frueher?
    z.append("SYSTEMATISCHER VERSATZ")
    frueher = sum(1 for p in paare if p["delta"] < 0)
    z.append(_zeile("beim zweiten Mal frueher",
                    f"{frueher} von {s['n']} ({frueher / s['n'] * 100:.0f} %)"))
    if abs(s["median"]) > s["sigma"] / 2:
        z.append("  -> Der Median liegt deutlich neben 0: die beiden Runden sind")
        z.append("     gegeneinander verschoben, nicht nur verrauscht.")
    else:
        z.append("  -> Kein nennenswerter Versatz; die Streuung ist Rauschen,")
        z.append("     keine Verschiebung.")
    z.append("")

    z.append("AUFGETEILT NACH 'WAS MARKIERST DU'")
    z.append("  Streut eine der drei Gruppen enger, ist das fuer sich eine Antwort.")
    for was, label in WAS_LABEL.items():
        teil = [p["delta"] for p in paare if p["was"] == was]
        if not teil:
            z.append(_zeile(label, "keine"))
            continue
        t = _stats(teil)
        z.append(_zeile(label,
                        f"n={t['n']:>3}  sigma {t['sigma']:>6.2f} s  "
                        f"in 8 s {t['in8']:>3.0f} %  Median {t['median']:+.1f} s"))
    z.append("")

    z.extend(anker_diagnose(paare))
    z.append("")

    z.append("MENSCH GEGEN ENGINE")
    z.append(_zeile("Engine sigma (Referenzmetrik)", f"{ENGINE_SIGMA:.2f} s"))
    z.append(_zeile("Mensch gegen sich selbst", f"{s['sigma']:.2f} s"))
    if s["sigma"] > 0:
        z.append(_zeile("Verhaeltnis", f"Engine streut {ENGINE_SIGMA / s['sigma']:.1f}x so weit"))
    z.append("")
    if fassung < relabel_store.WERKZEUG:
        z.append("  KEINE LESEHILFE fuer diese Fassung: das Instrument hat die")
        z.append("  Antwort vorbelegt (siehe Kopf). Aus diesen Zahlen folgt weder")
        z.append("  etwas fuer das Akzeptanzkriterium noch fuer 'sekundengenau'.")
        z.append("  Was zu tun ist: den Durchgang mit der aktuellen Fassung")
        z.append("  wiederholen - die alten Antworten bleiben unter 'ersetzt'.")
        z.append("")
        dauer = relabel_store.dauer_je_antwort(analysis_id)
        if dauer is not None:
            z.append(_zeile("Median-Dauer je Uebergang", f"{dauer:.0f} s"))
            z.append(_zeile("hochgerechnet auf den Durchgang",
                            f"{dauer * s['n'] / 60:.0f} min"))
            z.append("")
        return "\n".join(z)
    z.append("  Lesehilfe (aus ZUKUNFTSWEGE_2026-07-30.md, Abschnitt 4):")
    if s["sigma"] < 5:
        z.append("  sigma < 5 s  -> Der Zielwert ist scharf. Die bisherigen")
        z.append("  Misserfolge liegen an den Verfahren, nicht am Ziel. K2 ist")
        z.append("  der naechste Schritt.")
    elif s["sigma"] > 15:
        z.append("  sigma > 15 s -> Das Akzeptanzkriterium in")
        z.append("  CLAUDE_CODE_SPEC_2026-07-29.md ist so nicht erreichbar und")
        z.append("  gehoert neu geschrieben - von einem Zeitpunkt auf ein")
        z.append("  Intervall. Auch der Satz 'sekundengenau' in PRODUKTVISION.md")
        z.append("  waere dann eine Zusage, die niemand einloesen kann.")
    else:
        z.append("  5 s <= sigma <= 15 s -> Dazwischen. Der Zielwert traegt eine")
        z.append("  Genauigkeit in dieser Groessenordnung, aber nicht die")
        z.append("  geforderten 8 s bei 50 % der Faelle. Das Kriterium gehoert")
        z.append("  an die gemessene Streuung angepasst.")
    z.append("")

    dauer = relabel_store.dauer_je_antwort(analysis_id)
    if dauer is not None:
        z.append(_zeile("Median-Dauer je Uebergang", f"{dauer:.0f} s"))
        z.append(_zeile("hochgerechnet auf den Durchgang",
                        f"{dauer * s['n'] / 60:.0f} min"))
        z.append("")
    return "\n".join(z)


def _verfuegbare_sets() -> list[str]:
    if not relabel_store.RELABEL_DIR.is_dir():
        return []
    return sorted(p.stem for p in relabel_store.RELABEL_DIR.glob("*.json"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", dest="analysis_id",
                   help="analysisId; ohne Angabe werden alle vorhandenen ausgewertet")
    args = p.parse_args()

    sets = [args.analysis_id] if args.analysis_id else _verfuegbare_sets()

    # Ohne Daten sauber melden statt leere Zahlen ausgeben.
    if not sets:
        print("Noch keine zweite Labelrunde vorhanden.")
        print(f"  Erwartet in: {relabel_store.RELABEL_DIR}")
        print("  Starten mit einem Doppelklick auf MixCoach-Zweitrunde.command")
        print("  im Projektstamm - danach dieses Skript erneut aufrufen.")
        return 0

    leer = True
    for analysis_id in sets:
        paare = _paare(analysis_id)
        if not paare:
            print(f"[{analysis_id}] Datei vorhanden, aber noch keine Antwort, "
                  f"die sich einem correctedSec aus Runde 1 zuordnen laesst.")
            continue
        leer = False
        # Nach Werkzeug-Fassung getrennt. Zusammenrechnen waere ein Fehler:
        # die Fassungen messen nicht dasselbe.
        nach_fassung: dict[int, list[dict]] = {}
        for paar in paare:
            nach_fassung.setdefault(paar["werkzeug"], []).append(paar)
        for fassung in sorted(nach_fassung):
            print(bericht(analysis_id, nach_fassung[fassung], fassung))
    if leer:
        print("Keine auswertbaren Paare - es wurde noch nichts eingeordnet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
