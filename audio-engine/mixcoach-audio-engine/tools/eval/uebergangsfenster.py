"""Worauf gehoert das Uebergangs-Fenster, und wie breit muss es sein?

Erzeugt die zwei Zahlen, auf denen app/audio/uebergangsfenster.py steht:
den Anker (start_sec gegen mid_sec) und die Breite. Laeuft ohne Audio und
ohne numpy.

    python -m tools.eval.uebergangsfenster
    python -m tools.eval.uebergangsfenster --check    # gegen den Stand vom 27.08.

DIE FRAGE
---------
Der Report zeigt einen Punkt, und der ist meistens falsch: von 132
menschlichen Korrekturen liegen 5 % innerhalb von 8 s um mid_sec. Fuer einen
fremden DJ ist das der teuerste Fehler des Produkts - der erste Klick landet
im Nichts, und danach ist die Meinung gemacht.

sigma laesst sich nicht wegoptimieren (K1 zweimal gescheitert). Die Angabe
laesst sich ehrlich machen. Dieses Werkzeug sagt, wie.

GRUNDGESAMTHEIT
---------------
Nur Uebergaenge mit verdict "timing_off" UND correctedSec: dort hat der
Mensch ausdruecklich gesagt, wo die Stelle wirklich liegt. Die mit "correct"
bewerteten sind KEIN Massstab - dort hat er den angezeigten Marker
uebernommen, und das ist eine Zustimmung zur Anzeige, keine unabhaengige
Angabe. Dieselbe Verwechslung hat am 19.08. die K1-Messung wertlos gemacht.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.paths import GROUND_TRUTH_DIR, RESULTS_DIR  # noqa: E402

# Stand 27.08.2026 - die Zahlen, die app/audio/uebergangsfenster.py traegt.
SOLL = {"n": 132, "mid_p50": 34, "start_p50": 32, "abdeckung_gewaehlt": 73}


def _paare() -> list[tuple[float, dict]]:
    tr_von: dict[str, dict] = {}
    for pfad in RESULTS_DIR.glob("*.json"):
        try:
            d = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("id"):
            tr_von[d["id"]] = {str(t.get("index")): t
                               for t in (d.get("setTransitions") or [])}

    raus = []
    for pfad in GROUND_TRUTH_DIR.glob("*.json"):
        try:
            g = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ts = tr_von.get(g.get("analysisId")) or {}
        for idx, v in (g.get("verdicts") or {}).items():
            if v.get("verdict") != "timing_off" or v.get("correctedSec") is None:
                continue
            t = ts.get(str(idx))
            if not t or t.get("start_sec") is None:
                continue
            raus.append((float(v["correctedSec"]), t))
    return raus


def bericht(paare: list, pruefen: bool = False) -> tuple[str, bool]:
    z = ["=" * 72,
         "  Das Uebergangs-Fenster - Anker und Breite",
         "=" * 72]
    if len(paare) < 20:
        return "\n".join(z + [f"  Zu wenige Korrekturen ({len(paare)})."]), False

    z.append(f"  {len(paare)} menschliche Korrekturen (timing_off mit correctedSec)")
    z.append("")
    z.append("DER ANKER")
    werte = {}
    for name, feld in (("mid_sec", "mid_sec"), ("start_sec", "start_sec")):
        d = [w - float(t[feld]) for w, t in paare if t.get(feld) is not None]
        ab = sorted(abs(x) for x in d)
        werte[name] = ab
        z.append(f"  {name:<11} Median {statistics.median(d):+6.1f} s   "
                 f"|Fehler| p50 {ab[len(ab)//2]:>3.0f} s  "
                 f"p75 {ab[int(.75*len(ab))]:>3.0f} s  p90 {ab[int(.90*len(ab))]:>3.0f} s")
    z.append("  -> start_sec ist bei jeder Breite besser. Das passt zur Diagnose:")
    z.append("     die Engine findet das ENDE des Blends, der Mensch markiert den ANFANG.")
    z.append("")

    d = sorted(w - float(t["start_sec"]) for w, t in paare)
    n = len(d)
    z.append("DIE BREITE, um start_sec")
    z.append(f"  {'Fenster':<22} {'Breite':>8} {'enthaelt':>10}")
    for vor, nach in ((30, 30), (60, 50), (100, 130)):
        treffer = sum(1 for x in d if -vor <= x <= nach)
        marke = "   <- gewaehlt" if (vor, nach) == (60, 50) else ""
        z.append(f"  {f'-{vor} s .. +{nach} s':<22} {vor+nach:>6} s "
                 f"{100*treffer/n:>9.0f} %{marke}")

    blend = sum(1 for w, t in paare
                if t.get("end_sec") is not None
                and float(t["start_sec"]) <= w <= float(t["end_sec"]))
    breiten = sorted(float(t["end_sec"]) - float(t["start_sec"])
                     for w, t in paare if t.get("end_sec") is not None)
    z.append(f"  {'(Blend-Fenster heute)':<22} {statistics.median(breiten):>6.0f} s "
             f"{100*blend/n:>9.0f} %")
    z.append("")
    z.append("  90 % waeren ehrlicher, kosten aber 230 s Fenster. In einem")
    z.append("  30-Minuten-Set sagt das nichts mehr. 110 s heisst: einmal Play")
    z.append("  druecken und knapp zwei Minuten zuhoeren.")

    gut = True
    if pruefen:
        z.append("")
        z.append("SELBSTTEST")
        ist = {"n": n,
               "mid_p50": round(werte["mid_sec"][len(werte["mid_sec"])//2]),
               "start_p50": round(werte["start_sec"][len(werte["start_sec"])//2]),
               "abdeckung_gewaehlt": round(100*sum(1 for x in d if -60 <= x <= 50)/n)}
        for k, soll in SOLL.items():
            ok = ist[k] == soll
            gut &= ok
            z.append(f"  {'ok  ' if ok else 'ROT '}       {k}: {ist[k]} (soll {soll})")
        z.append("")
        z.append(f"  ERGEBNIS: {'reproduziert.' if gut else 'ABWEICHUNG - die Fensterwerte in'}"
                 f"{'' if gut else ' app/audio/uebergangsfenster.py gehoeren nachgezogen.'}")
    return "\n".join(z), gut


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    text, gut = bericht(_paare(), args.check)
    print(text)
    return 0 if (gut or not args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
