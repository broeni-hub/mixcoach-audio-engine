# -*- coding: utf-8 -*-
"""Traegt die Harmonik ein Urteil - oder beschreibt sie nur?

WARUM ES DIESES WERKZEUG GIBT
-----------------------------
Am 23.09.2026 ausgezaehlt: von 509 gespeicherten Uebergaengen tragen 313 einen
Feedback-Satz, und 311 davon (99 %) urteilen ueber Harmonik - fast immer so:

    "Uebergang bei 11:28 wechselt harmonisch weit (F Minor -> A Minor,
     Camelot 4A -> 8A) - waehle einen Track im Nachbarfeld des Camelot-Rads."

Das ist eine Empfehlung, also eine Behauptung ueber Qualitaet. Sie stand nie
in app/audio/nicht_gemessen.py, weil Harmonik dort gar keine Dimension ist -
sie war nie eine Note im Kopf des Reports. Die Ehrlichkeitslinie deckte die
Kacheln ab und die Saetze nicht.

DIE FRAGE, DIE HIER BEANTWORTET WIRD
------------------------------------
Haengt der Camelot-Abstand - die Groesse, auf der die Empfehlung beruht - mit
dem menschlichen Urteil zusammen? Gerechnet wird gegen dieselben Bewertungen
und mit derselben Verknuepfung wie in tools/eval/beat_jitter.py.

DIE KONTROLLE, OHNE DIE DIE ZAHL NICHTS WERT WAERE
--------------------------------------------------
Mitgerechnet wird beat_jitter_ms. Kommt dort nicht die dokumentierte Zahl
heraus (Spearman -0,336, p < 0,0001, n = 237), ist die Verknuepfung kaputt und
keine andere Zahl aus diesem Lauf zu gebrauchen. Das Werkzeug sagt das selbst.

ERGEBNIS AM 23.09.2026
----------------------
    Camelot-Abstand        n=297   rho +0,063   p 0,28     <- kein Zusammenhang
    harmonic_clash_score   n=237   rho -0,138   p 0,034
    beat_jitter_ms         n=237   rho -0,336   p <0,0001  (Kontrolle: ok)

    kompatibel (Abstand <=1, n=121)   Median 4,0
    inkompatibel          (n=176)     Median 4,0   Mann-Whitney p = 0,355

Das Vorzeichen des Camelot-Abstands ist sogar positiv. Und es liegt nicht an
einer wackligen Tonarterkennung: ueber Wiederholungsanalysen derselben
Aufnahme behalten 89 von 96 Uebergaengen ihre Tonart (93 %, --stabilitaet).
Die Tonart wird zuverlaessig gemessen. Sie sagt nur nichts ueber die Qualitaet
des Uebergangs - genau der Fall, den nicht_gemessen.py als "Befuellt ist nicht
gemessen" beschreibt.

    python -m tools.eval.harmonik
    python -m tools.eval.harmonik --stabilitaet
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.paths import RESULTS_DIR  # noqa: E402
from tools.eval.beat_jitter import (  # noqa: E402
    _ENGINE_ZEIT,
    TOLERANZ_S,
    _csv_text,
    _transitions,
)

# Die Kontrollzahl aus tools/eval/beat_jitter.py, 20.08.2026.
KONTROLLE_RHO, KONTROLLE_TOLERANZ = -0.336, 0.03


def camelot_abstand(a: object, b: object) -> Optional[int]:
    """Schritte auf dem Camelot-Rad; Dur/Moll-Wechsel zaehlt einen dazu."""
    m = re.match(r"^(\d{1,2})([AB])$", str(a or ""))
    n = re.match(r"^(\d{1,2})([AB])$", str(b or ""))
    if not m or not n:
        return None
    za, la = int(m.group(1)), m.group(2)
    zb, lb = int(n.group(1)), n.group(2)
    d = min((za - zb) % 12, (zb - za) % 12)
    return d + (0 if la == lb or d == 0 else 1)


def sammeln(labels_csv: Path, results_dir: Path) -> List[Dict]:
    """Bewertung + Harmonik je Uebergang - Verknuepfung wie beat_jitter.py."""
    cache: Dict[str, List[Dict]] = {}
    rows: List[Dict] = []
    for zeile in csv.DictReader(_csv_text(labels_csv).splitlines(), delimiter=";"):
        roh = (zeile.get("human_rating") or "").strip()
        if not roh:
            continue
        try:
            bewertung = float(roh)
        except ValueError:
            continue

        set_id = zeile.get("set_id") or ""
        if set_id not in cache:
            cache[set_id] = _transitions(set_id, results_dir)
        if not cache[set_id]:
            continue

        treffer = _ENGINE_ZEIT.search(zeile.get("verdict_info") or "")
        if treffer:
            ziel = float(treffer.group(1))
        else:
            try:
                ziel = float(zeile["transition_center_time"])
            except (KeyError, ValueError, TypeError):
                continue

        naechste = min(cache[set_id],
                       key=lambda t: abs((t.get("mid_sec") or 1e9) - ziel))
        if abs((naechste.get("mid_sec") or 1e9) - ziel) > TOLERANZ_S:
            continue

        rows.append({
            "bewertung": bewertung,
            "clash": naechste.get("harmonic_clash_score"),
            "abstand": camelot_abstand(naechste.get("camelot_before"),
                                       naechste.get("camelot_after")),
            "jitter": naechste.get("beat_jitter_ms"),
            "pegel": naechste.get("loudness_jump_db"),
        })
    return rows


def _spearman(rows: List[Dict], feld: str) -> Optional[tuple]:
    paare = [(r["bewertung"], r[feld]) for r in rows if r.get(feld) is not None]
    if len(paare) < 10:
        return None
    rho, p = spearmanr([b for _, b in paare], [a for a, _ in paare])
    return len(paare), float(rho), float(p)


def bericht(rows: List[Dict]) -> str:
    z = ["=" * 68,
         "  Traegt die Harmonik ein Urteil?",
         "=" * 68,
         f"  {len(rows)} verknuepfte Bewertungen", ""]

    kontrolle = _spearman(rows, "jitter")
    z.append("KONTROLLE  (muss die dokumentierte Jitter-Zahl reproduzieren)")
    if kontrolle is None:
        z.append("  KAPUTT: keine Jitter-Paare - kein Wert aus diesem Lauf gilt.")
        return "\n".join(z)
    n_k, rho_k, p_k = kontrolle
    ok = abs(rho_k - KONTROLLE_RHO) <= KONTROLLE_TOLERANZ
    z.append(f"  beat_jitter_ms   n={n_k:4d}  rho {rho_k:+.3f}  p {p_k:.4f}"
             f"   (soll {KONTROLLE_RHO:+.3f})")
    z.append("  ok - die Verknuepfung stimmt." if ok else
             "  ABWEICHUNG: die Verknuepfung stimmt nicht. Abbruch der Deutung.")
    z.append("")

    z.append("GEGEN DAS MENSCHLICHE URTEIL")
    for feld, label in (("abstand", "Camelot-Abstand (traegt den Satz)"),
                        ("clash", "harmonic_clash_score"),
                        ("pegel", "loudness_jump_db (Kontrolle)")):
        erg = _spearman(rows, feld)
        if erg is None:
            z.append(f"  {label:36s} zu wenig Daten")
            continue
        n, rho, p = erg
        z.append(f"  {label:36s} n={n:4d}  rho {rho:+.3f}  p {p:.4f}")
    z.append("")

    komp = [r["bewertung"] for r in rows
            if r["abstand"] is not None and r["abstand"] <= 1]
    inko = [r["bewertung"] for r in rows
            if r["abstand"] is not None and r["abstand"] > 1]
    if len(komp) >= 5 and len(inko) >= 5:
        _, p = mannwhitneyu(komp, inko)
        z.append("KOMPATIBEL GEGEN INKOMPATIBEL")
        z.append(f"  Abstand <=1   n={len(komp):4d}  Median {np.median(komp):.1f}")
        z.append(f"  Abstand  >1   n={len(inko):4d}  Median {np.median(inko):.1f}")
        z.append(f"  Mann-Whitney  p = {p:.3f}")
        z.append("")
        z.append("  Kein Unterschied." if p >= 0.05 else "  Unterschied nachweisbar.")
    return "\n".join(z)


def stabilitaet(results_dir: Path) -> str:
    """Behaelt derselbe Uebergang seine Tonart, wenn neu analysiert wird?"""
    nach_datei: Dict[str, List[Dict]] = {}
    for pfad in glob.glob(os.path.join(str(results_dir), "*.json")):
        with open(pfad, encoding="utf-8") as fh:
            d = json.load(fh)
        nach_datei.setdefault(d.get("fileName") or "?", []).append(d)

    z = ["=" * 68,
         "  Stabilitaet der Tonart ueber Wiederholungsanalysen",
         "  (gleicher Uebergang = mid_sec innerhalb 5 s)",
         "=" * 68, ""]
    ges = stab = 0
    for name, reports in sorted(nach_datei.items()):
        if len(reports) < 2:
            continue
        basis = max(reports, key=lambda d: len(d.get("setTransitions") or []))
        bt = [t for t in (basis.get("setTransitions") or []) if t.get("camelot_after")]
        if not bt:
            continue
        treffer = paare = 0
        for d in reports:
            if d is basis:
                continue
            for t in (d.get("setTransitions") or []):
                if not t.get("camelot_after") or t.get("mid_sec") is None:
                    continue
                p = min(bt, key=lambda b: abs((b.get("mid_sec") or 1e9) - t["mid_sec"]))
                if abs((p.get("mid_sec") or 1e9) - t["mid_sec"]) > 5:
                    continue
                paare += 1
                if (p.get("camelot_after") == t.get("camelot_after")
                        and p.get("camelot_before") == t.get("camelot_before")):
                    treffer += 1
        if paare:
            ges += paare
            stab += treffer
            z.append(f"  {name[:44]:44s} {len(reports):2d} Analysen"
                     f"  {treffer:3d}/{paare:3d}  ({100 * treffer / paare:3.0f} %)")
    if ges:
        z.append("")
        z.append(f"  GESAMT {stab} von {ges} behalten ihre Tonart"
                 f" ({100 * stab / ges:.0f} %)")
    return "\n".join(z)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--labels-csv", type=Path, default=Path("labels_prefilled.csv"))
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--stabilitaet", action="store_true",
                   help="statt der Korrelation: bleibt die Tonart gleich?")
    args = p.parse_args()

    if args.stabilitaet:
        print(stabilitaet(args.results_dir))
        return 0
    if not args.labels_csv.exists():
        print(f"FEHLT: {args.labels_csv}")
        return 1
    print(bericht(sammeln(args.labels_csv, args.results_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
