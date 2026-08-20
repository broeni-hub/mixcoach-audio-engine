"""Traegt der Beat-Jitter eine zweite Uebungs-Dimension - oder misst er den Beat-Tracker?

HINTERGRUND
-----------
app/coach/uebungen.py laesst eine Uebung nur aus einer Groesse entstehen, die
(a) gegen Sebastians Bewertungen belegt ist und (b) genug Spannweite fuer ein
Ziel hat. Genau eine Groesse erfuellt beides, der Pegelsprung; alle 110
Uebungen ruhen darauf.

beat_alignment_score erfuellt (a) - Spearman +0,325 bei n=170 - und scheitert
an (b): Spanne 83-98, sigma 2,56. Der Grund liegt in der Skala, nicht in der
Messung. Der Score ist

    score = 100 - (cv / 0,35) * 100

und cv = 0,35 entspraeche bei 128 BPM einem Jitter von 164 ms. Gemessen werden
2,9 bis 26,2 ms. Die Skala ist auf das 6,3-fache dessen ausgelegt, was
vorkommt, und drueckt die echte Variation in ihre obersten 15 %.

Dieselbe Messung in Millisekunden hat p10 8,1 und p90 18,8 ms - Faktor 2,3,
eine echte Einheit und ein Ziel, das am Pitch-Fader umsetzbar ist.

DER VORBEHALT, DEN DIESES WERKZEUG PRUEFT
-----------------------------------------
app/audio/scoring/beat_alignment.py misst nicht die Phasenlage zweier Raster,
sondern die REGELMAESSIGKEIT des einen globalen Beat-Trackers im Blend-Fenster
- eine offen dokumentierte Vereinfachung. Damit sind drei Erklaerungen fuer
hohen Jitter moeglich, und nur die erste taugt zum Coachen:

    1. schlecht gebeatmatcht         -> Uebung sinnvoll
    2. Breakdown ohne klaren Puls    -> der Tracker eiert, der DJ kann nichts
    3. kurzes Fenster, wenige Beats  -> Schaetzrauschen, reines Artefakt

Geprueft wird deshalb nicht nur der Zusammenhang mit der Bewertung, sondern ob
er ueberlebt, wenn man Energieloch und Fensterlaenge herausrechnet.

ABBRUCHKRITERIUM
----------------
Faellt die partielle Korrelation gegen einen der Stoerfaktoren unter die
Haelfte der rohen, ist der Weg tot: dann misst der Jitter ueberwiegend den
Stoerfaktor. Ebenso, wenn er nur wiederholt, was der Pegelsprung schon sagt -
eine zweite Achse muss etwas Neues sagen.

    python -m tools.eval.beat_jitter
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.paths import RESULTS_DIR  # noqa: E402

# Aus app/audio/scoring/beat_alignment.py - dort ist es der Nullpunkt der
# Skala. Hier gebraucht, um den Score zurueck in den Variationskoeffizienten
# zu rechnen. Wird die Konstante dort geaendert, ist auch diese Auswertung
# hinfaellig; deshalb wird sie importiert und nicht abgeschrieben.
from app.audio.scoring.beat_alignment import CV_AT_ZERO_SCORE  # noqa: E402

# Der Engine-Zeitpunkt steht bei korrigierten Uebergaengen im Klartext in
# verdict_info: "timing_off (Engine: 481.6s -> korrigiert)". Damit trifft der
# Abgleich den rohen Marker statt der korrigierten Zeit - sonst gehen genau
# die timing_off-Zeilen verloren, die im Median 29 s daneben liegen.
_ENGINE_ZEIT = re.compile(r"Engine:\s*([0-9]+(?:\.[0-9]+)?)\s*s")

TOLERANZ_S = 8.0


def _csv_text(pfad: Path) -> str:
    """Excel schreibt die Datei beim Nachbearbeiten als cp1252 zurueck."""
    roh = pfad.read_bytes()
    for kodierung in ("utf-8-sig", "cp1252"):
        try:
            return roh.decode(kodierung)
        except UnicodeDecodeError:
            continue
    return roh.decode("utf-8", errors="replace")


def _transitions(set_id: str, results_dir: Path) -> List[Dict]:
    for pfad in (results_dir / f"{set_id}.json",
                 results_dir / "archived" / f"{set_id}.json"):
        if pfad.exists():
            try:
                return json.loads(pfad.read_text(encoding="utf-8")).get("setTransitions") or []
            except (OSError, json.JSONDecodeError):
                return []
    return []


def _jitter_ms(t: Dict) -> Optional[float]:
    """Der Score, zurueckgerechnet in Millisekunden Beat-Abstands-Streuung.

    ACHTUNG, Aufloesung: der Score liegt gerundet als ganze Zahl vor, ein
    Punkt entspricht rund 1,6 ms. Fuer eine Rangkorrelation ist das
    konservativ (die Rundung erzeugt Bindungen und schwaecht den
    Zusammenhang eher ab), fuer Einzelwerte zu grob.
    """
    score = t.get("beat_alignment_score")
    if score is None:
        return None
    bpm = t.get("bpm_before") or t.get("bpm_after")
    if not bpm or float(bpm) <= 0:
        return None
    cv = CV_AT_ZERO_SCORE * (100.0 - float(score)) / 100.0
    return cv * (60.0 / float(bpm)) * 1000.0


def _fensterbeats(t: Dict) -> Optional[float]:
    """Wieviele Beats lagen im Fenster - die Stichprobe, aus der cv entsteht."""
    start, ende = t.get("start_sec"), t.get("end_sec")
    bpm = t.get("bpm_before") or t.get("bpm_after")
    if start is None or ende is None or not bpm or float(bpm) <= 0:
        return None
    return (float(ende) - float(start)) / (60.0 / float(bpm))


def sammeln(labels_csv: Path, results_dir: Path) -> tuple[List[Dict], Dict[str, int]]:
    zeilen = csv.DictReader(_csv_text(labels_csv).splitlines(), delimiter=";")
    cache: Dict[str, List[Dict]] = {}
    paare: List[Dict] = []
    verworfen = {"ohne_bewertung": 0, "ohne_json": 0, "kein_treffer": 0, "ohne_jitter": 0}

    for zeile in zeilen:
        roh = (zeile.get("human_rating") or "").strip()
        if not roh:
            verworfen["ohne_bewertung"] += 1
            continue
        try:
            bewertung = float(roh)
        except ValueError:
            verworfen["ohne_bewertung"] += 1
            continue

        set_id = zeile.get("set_id") or ""
        if set_id not in cache:
            cache[set_id] = _transitions(set_id, results_dir)
        if not cache[set_id]:
            verworfen["ohne_json"] += 1
            continue

        treffer = _ENGINE_ZEIT.search(zeile.get("verdict_info") or "")
        if treffer:
            ziel = float(treffer.group(1))
        else:
            try:
                ziel = float(zeile["transition_center_time"])
            except (KeyError, ValueError, TypeError):
                verworfen["kein_treffer"] += 1
                continue

        naechste = min(cache[set_id],
                       key=lambda t: abs((t.get("mid_sec") or 1e9) - ziel))
        if abs((naechste.get("mid_sec") or 1e9) - ziel) > TOLERANZ_S:
            verworfen["kein_treffer"] += 1
            continue

        jitter = _jitter_ms(naechste)
        if jitter is None:
            verworfen["ohne_jitter"] += 1
            continue

        sprung = naechste.get("loudness_jump_db")
        paare.append({
            "set_id": set_id,
            "bewertung": bewertung,
            "jitter_ms": jitter,
            "energieloch": naechste.get("energy_dip_pct"),
            "fensterbeats": _fensterbeats(naechste),
            "pegelsprung": abs(float(sprung)) if sprung is not None else None,
        })
    return paare, verworfen


def _partiell(x: List[float], y: List[float], z: List[float]) -> Optional[float]:
    """Partielle Spearman-Korrelation von x und y bei festgehaltenem z.

    Auf Raengen gerechnet, dann linear herausprojiziert - das ist die
    uebliche Rangvariante und braucht keine Normalverteilung.
    """
    if len(x) < 10:
        return None
    rx, ry, rz = (np.argsort(np.argsort(np.asarray(v, dtype=float))).astype(float)
                  for v in (x, y, z))
    grund = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - grund @ np.linalg.lstsq(grund, rx, rcond=None)[0]
    ey = ry - grund @ np.linalg.lstsq(grund, ry, rcond=None)[0]
    if np.std(ex) == 0 or np.std(ey) == 0:
        return None
    return float(np.corrcoef(ex, ey)[0, 1])


def _zeile(text: str, wert: str) -> str:
    return f"  {text:<38} {wert}"


def bericht(paare: List[Dict], verworfen: Dict[str, int]) -> str:
    z: List[str] = []
    z.append("=" * 72)
    z.append("  Beat-Jitter - traegt er eine zweite Uebungs-Dimension?")
    z.append("=" * 72)

    if len(paare) < 20:
        z.append(f"  Zu wenige Paare ({len(paare)}). Verworfen: {verworfen}")
        return "\n".join(z)

    jitter = [p["jitter_ms"] for p in paare]
    bewertung = [p["bewertung"] for p in paare]

    z.append(_zeile("Bewertete Uebergaenge mit Jitter", f"{len(paare)} aus {len({p['set_id'] for p in paare})} Aufnahmen"))
    z.append(_zeile("verworfen", ", ".join(f"{k} {v}" for k, v in verworfen.items() if v)))
    js = sorted(jitter)
    z.append(_zeile("Jitter p10 / p50 / p90",
                    f"{js[int(.10*(len(js)-1))]:.1f} / {js[int(.50*(len(js)-1))]:.1f} / "
                    f"{js[int(.90*(len(js)-1))]:.1f} ms"))
    z.append("")

    roh, p_roh = spearmanr(jitter, bewertung)
    z.append("DER ZUSAMMENHANG, DEN ES ZU PRUEFEN GILT")
    z.append(_zeile("Jitter gegen Bewertung", f"Spearman {roh:+.3f}   p = {p_roh:.4f}"))
    z.append("  (negativ erwartet: mehr Jitter = schlechter bewertet)")
    z.append("")

    z.append("DIE DREI STOERFAKTOREN")
    z.append("  Korreliert der Jitter mit ihnen - und bleibt vom Zusammenhang")
    z.append("  etwas uebrig, wenn man sie herausrechnet?")
    stoerer = [
        ("energieloch", "Energieloch (Breakdown)"),
        ("fensterbeats", "Beats im Fenster (Stichprobe)"),
        ("pegelsprung", "Pegelsprung (schon belegt)"),
    ]
    ergebnisse = {}
    for feld, name in stoerer:
        teil = [p for p in paare if p.get(feld) is not None]
        if len(teil) < 20:
            z.append(_zeile(name, f"n = {len(teil)} - zu wenig"))
            continue
        tj = [p["jitter_ms"] for p in teil]
        tb = [p["bewertung"] for p in teil]
        tz = [p[feld] for p in teil]
        mit_stoerer, _ = spearmanr(tj, tz)
        roh_teil, _ = spearmanr(tj, tb)
        rest = _partiell(tj, tb, tz)
        ergebnisse[feld] = (roh_teil, rest)
        z.append(_zeile(f"{name}  (n={len(teil)})", f"Jitter dagegen: {mit_stoerer:+.3f}"))
        z.append(_zeile("   Zusammenhang roh -> bereinigt",
                        f"{roh_teil:+.3f} -> {rest:+.3f}" if rest is not None else "nicht rechenbar"))
    z.append("")

    z.append("ERGEBNIS")
    tot = []
    for feld, name in stoerer:
        if feld not in ergebnisse:
            continue
        roh_teil, rest = ergebnisse[feld]
        if rest is None or abs(roh_teil) < 1e-9:
            continue
        if abs(rest) < abs(roh_teil) / 2:
            tot.append(name)
    if p_roh >= 0.05:
        z.append("  Der rohe Zusammenhang ist nicht signifikant (p >= 0,05).")
        z.append("  -> Der Weg ist tot. Keine zweite Achse aus dieser Groesse.")
    elif tot:
        z.append(f"  Der Zusammenhang bricht weg, sobald man herausrechnet: {', '.join(tot)}.")
        z.append("  -> Der Jitter misst ueberwiegend den Stoerfaktor, nicht das")
        z.append("     Beatmatching. Der Weg ist tot.")
    else:
        z.append("  Der Zusammenhang ueberlebt alle drei Stoerfaktoren.")
        z.append("  -> Die Groesse traegt. Naechster Schritt: den Jitter direkt aus")
        z.append("     dem Beat-Raster rechnen statt aus dem gerundeten Score, und")
        z.append("     die Zahlen hier gegen die ungerundeten Werte wiederholen.")
    return "\n".join(z)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--labels-csv", type=Path, default=Path("labels_prefilled.csv"))
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    if not args.labels_csv.exists():
        print(f"FEHLT: {args.labels_csv}")
        return 1
    paare, verworfen = sammeln(args.labels_csv, args.results_dir)
    print(bericht(paare, verworfen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
