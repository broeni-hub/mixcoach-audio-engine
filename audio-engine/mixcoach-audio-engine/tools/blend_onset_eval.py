"""Blend-Onset-Varianten gegen die Ground Truth messen (Job B, Schritt 2).

Arbeitet ausschliesslich auf dem Cache aus tools/blend_onset_cache.py, ein
Durchlauf ueber alle Varianten dauert Sekunden statt Stunden.

    python -m tools.blend_onset_cache      # einmalig
    python -m tools.blend_onset_eval

Aufteilung
----------
Der Split laeuft auf SET-Ebene, nicht auf Transitions-Ebene. Transitions
desselben Sets teilen Tempo, Genre, Aufnahmekette und oft denselben DJ -
lagen sie auf beiden Seiten, waere die Testhaelfte kein Test mehr. Die
Zuordnung haengt am md5 der analysisId, ist also stabil ueber Laeufe und
unabhaengig von der Dateireihenfolge.

Leitgedanke der neuen Varianten
-------------------------------
Die vorhandene refine_boundary() laeuft IMMER rueckwaerts, bis die Novelty
unter 25 % des Peaks faellt. Bei einem harten Schnitt gibt es aber gar
keinen Blend - Start und Mitte fallen zusammen. Dort erfindet die
Rueckwaertssuche eine Laenge, die es nicht gibt. Das erklaert, warum der
Median sich verbessert, Sigma aber nicht: der Bias verschwindet, die
Streuung bleibt.

Die Varianten hier trennen deshalb zwei Fragen:
  1. GIBT es einen Blend?  (sonst: Start = Mitte)
  2. Wenn ja, wo faengt er an?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))

from app.audio.foote import beat_sync_features, foote_novelty, refine_boundary  # noqa: E402
from tools.blend_onset_cache import CACHE_DIR  # noqa: E402

# Kein Blend-Onset naeher als das an der Mitte - darunter ist es derselbe
# Moment und die Suche wuerde nur Rauschen aufgreifen.
MIN_ABSTAND_S = 3.0
# Weiter zurueck als das wird nicht gesucht (Spec: Fenster bis 120 s).
MAX_ABSTAND_S = 120.0


# ------------------------------------------------------------------ Hilfen


def _zeitachse(n: int, sr: int, hop: int) -> np.ndarray:
    return np.arange(n) * (hop / sr)


def _glaetten(x: np.ndarray, fenster: int) -> np.ndarray:
    if fenster < 2 or x.size < fenster:
        return x
    kern = np.ones(fenster) / fenster
    return np.convolve(x, kern, mode="same")


def _robust_z(x: np.ndarray, basis: slice) -> np.ndarray:
    """z-Wert gegen eine Basisperiode, robust ueber Median/MAD.

    Die Basis ist der Anfang des Fensters - dort laeuft im Regelfall noch
    Track A allein. Median und MAD statt Mittelwert und Sigma, damit ein
    einzelner lauter Moment die Referenz nicht verschiebt.
    """
    ref = x[basis]
    if ref.size < 5:
        return np.zeros_like(x)
    med = float(np.median(ref))
    mad = float(np.median(np.abs(ref - med))) or 1e-6
    return (x - med) / (1.4826 * mad)


def _erste_anhaltende_ueberschreitung(z: np.ndarray, zeit: np.ndarray,
                                      schwelle: float, dauer_s: float,
                                      bis_index: int) -> float | None:
    """Fruehester Zeitpunkt, ab dem z fuer >= dauer_s ueber der Schwelle bleibt.

    "Anhaltend" ist der entscheidende Teil: ein einzelner Ausschlag ist ein
    Crash-Becken, kein einsetzender Track. Verlangt wird ein Niveauwechsel,
    der Bestand hat.
    """
    if bis_index <= 1:
        return None
    dt = float(zeit[1] - zeit[0]) or 1e-6
    noetig = max(1, int(dauer_s / dt))
    ueber = z[:bis_index] > schwelle

    lauf = 0
    for i, b in enumerate(ueber):
        if b:
            lauf += 1
            if lauf >= noetig:
                return float(zeit[i - lauf + 1])
        else:
            lauf = 0
    return None


def _evidenz(d: dict) -> tuple[np.ndarray, np.ndarray]:
    """Belegkurve fuer 'eine zweite Schicht ist dazugekommen'.

    Kombiniert drei voneinander unabhaengige Anzeichen, jedes gegen den
    ruhigen Anfang des Fensters normiert:

      Entropie  - mehr belegte Tonklassen, also mehr Harmonie gleichzeitig
      Hoehen    - DJs blenden haeufig ueber Hats/Percussion von B ein
      Dichte    - Gesamtenergie steigt, wenn zwei Quellen laufen

    Bewusst als Summe von z-Werten und nicht als gelerntes Modell: bei 124
    Labels waere jedes Gewicht auswendig gelernt, nicht gemessen.
    """
    sr, hop = int(d["sr"]), int(d["hop"])
    n = int(d["entropie"].shape[0])
    zeit = _zeitachse(n, sr, hop)

    # Basis: die ersten 30 s des Fensters (~120 s vor der Mitte).
    dt = float(zeit[1] - zeit[0]) if n > 1 else 1.0
    basis = slice(0, max(5, int(30.0 / dt)))

    glatt = max(1, int(2.0 / dt))   # 2 s Glaettung gegen Frame-Zappeln
    ent = _robust_z(_glaetten(d["entropie"], glatt), basis)
    hoch = _robust_z(_glaetten(d["hoehen"], glatt), basis)
    dichte = _robust_z(_glaetten(d["bass"] + d["mitten"] + d["hoehen"], glatt), basis)

    return (ent + hoch + dichte) / 3.0, zeit


# ------------------------------------------------------------------ Varianten
# Jede Variante bekommt den Cache-Eintrag und liefert eine ABSOLUTE Sekunde.


def v_mid(d: dict, meta: dict) -> float:
    """Basislinie: der Kandidatenpunkt selbst."""
    return meta["mid_sec"]


def v_start_alt(d: dict, meta: dict) -> float:
    """Basislinie: das heutige start_sec aus der gespeicherten Analyse."""
    return meta["start_sec_alt"]


def v_foote(d: dict, meta: dict, fenster: float = 60.0) -> float:
    """refine_boundary wie heute, nur mit groesserem Suchfenster."""
    beats = d["beats"].tolist()
    if len(beats) < 140:
        return meta["mid_sec"]
    feat = beat_sync_features(d["chroma"], d["mfcc"], beats, int(d["sr"]), int(d["hop"]))
    nov = foote_novelty(feat)
    r = refine_boundary(float(d["mid_rel"]), beats, nov, window_seconds=fenster)
    if r is None:
        return meta["mid_sec"]
    return float(d["offset"]) + r["start_time"]


def v_evidenz(d: dict, meta: dict, schwelle: float = 3.0,
              dauer_s: float = 8.0) -> float:
    """Neu: Niveauwechsel in der Belegkurve, mit Rueckfall auf die Mitte.

    Findet sich kein anhaltender Anstieg, war es kein Blend, sondern ein
    harter Schnitt - dann bleibt die Mitte stehen. Das ist der Unterschied
    zur heutigen Suche, die immer etwas zurueckgeht.
    """
    z, zeit = _evidenz(d)
    mid_rel = float(d["mid_rel"])
    bis = int(np.searchsorted(zeit, mid_rel - MIN_ABSTAND_S))
    ab = int(np.searchsorted(zeit, max(0.0, mid_rel - MAX_ABSTAND_S)))

    if bis - ab < 5:
        return meta["mid_sec"]

    z_fenster = z.copy()
    z_fenster[:ab] = -np.inf   # vor dem Suchfenster nichts finden
    t = _erste_anhaltende_ueberschreitung(z_fenster, zeit, schwelle, dauer_s, bis)
    if t is None:
        return meta["mid_sec"]
    return float(d["offset"]) + t


def v_evidenz_foote(d: dict, meta: dict) -> float:
    """Beides: Evidenz entscheidet OB, Foote verfeinert WO.

    Die Evidenzkurve sagt zuverlaessig, ob ueberhaupt geblendet wurde; die
    beat-synchrone Novelty sitzt genauer auf dem Takt. Nur wenn beide sich
    einig sind (Foote-Start liegt nicht weiter als 20 s vom Evidenz-Start),
    wird Foote genommen.
    """
    ev = v_evidenz(d, meta)
    if abs(ev - meta["mid_sec"]) < 0.01:
        return ev                      # kein Blend erkannt - dabei bleibt es
    ft = v_foote(d, meta)
    if abs(ft - ev) <= 20.0:
        return ft
    return ev


VARIANTEN = {
    "mid_sec (alt gemessen)": v_mid,
    "start_sec (heute)": v_start_alt,
    "foote w=60": v_foote,
    "evidenz z>3 8s": v_evidenz,
    "evidenz z>2.5 6s": lambda d, m: v_evidenz(d, m, 2.5, 6.0),
    "evidenz z>4 10s": lambda d, m: v_evidenz(d, m, 4.0, 10.0),
    "evidenz+foote": v_evidenz_foote,
}


# ------------------------------------------------------------------ Messung


def _haelfte(aid: str) -> str:
    """Set-Ebene, deterministisch: erste Hex-Ziffer des md5 entscheidet."""
    h = hashlib.md5(aid.encode()).hexdigest()
    return "train" if int(h[0], 16) < 8 else "test"


def _kennzahlen(fehler: list[float]) -> dict:
    if not fehler:
        return {"n": 0}
    a = sorted(abs(x) for x in fehler)
    return {
        "n": len(fehler),
        "median": st.median(fehler),
        "sigma": st.pstdev(fehler) if len(fehler) > 1 else 0.0,
        "in4": sum(1 for x in a if x <= 4) / len(a) * 100,
        "in8": sum(1 for x in a if x <= 8) / len(a) * 100,
        "in16": sum(1 for x in a if x <= 16) / len(a) * 100,
        "p90": a[min(len(a) - 1, int(0.9 * (len(a) - 1)))],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", type=Path, default=CACHE_DIR)
    p.add_argument("--out", type=Path, help="beste Variante als Vorhersage-Datei ablegen")
    p.add_argument("--variante", help="nur diese Variante fuer --out verwenden")
    args = p.parse_args()

    verzeichnis = json.loads((args.cache / "verzeichnis.json").read_text(encoding="utf-8"))
    print(f"Cache-Eintraege: {len(verzeichnis)}")

    geladen: list[tuple[dict, dict]] = []
    for meta in verzeichnis:
        f = args.cache / meta["datei"]
        if not f.exists():
            continue
        geladen.append((dict(np.load(f)), meta))
    print(f"geladen: {len(geladen)}")

    sets = {m["aid"] for _, m in geladen}
    train = {a for a in sets if _haelfte(a) == "train"}
    print(f"Sets: {len(sets)}  (train {len(train)}, test {len(sets) - len(train)})\n")

    # Zielgroesse: die menschliche Korrektur bei timing_off.
    ziel = [(d, m) for d, m in geladen
            if m["verdict"] == "timing_off" and m.get("corrected_sec") is not None]
    # Regressionswaechter: bei correct ist mid_sec der akzeptierte Wert.
    waechter = [(d, m) for d, m in geladen if m["verdict"] == "correct"]
    print(f"timing_off mit correctedSec: {len(ziel)}   correct: {len(waechter)}\n")

    kopf = (f"{'Variante':<24}{'n':>4}{'Median':>9}{'Sigma':>8}"
            f"{'in4':>6}{'in8':>6}{'in16':>7}{'p90':>7}   {'| correct in8':>13}")
    print(kopf)
    print("-" * len(kopf))

    ergebnisse = {}
    for name, fn in VARIANTEN.items():
        for teil, menge in (("train", train), ("test", sets - train)):
            fehler = [m["corrected_sec"] - fn(d, m) for d, m in ziel if m["aid"] in menge]
            k = _kennzahlen(fehler)
            w = _kennzahlen([m["mid_sec"] - fn(d, m) for d, m in waechter if m["aid"] in menge])
            if not k.get("n"):
                continue
            print(f"{name if teil == 'train' else '':<24}"
                  f"{k['n']:>4}{k['median']:>+9.2f}{k['sigma']:>8.2f}"
                  f"{k['in4']:>6.0f}{k['in8']:>6.0f}{k['in16']:>7.0f}{k['p90']:>7.1f}"
                  f"   {w.get('in8', 0):>11.0f} %  [{teil}]")
            ergebnisse.setdefault(name, {})[teil] = k
        print()

    if args.out and args.variante:
        fn = VARIANTEN[args.variante]
        preds: dict[str, dict[str, float]] = {}
        for d, m in geladen:
            preds.setdefault(m["aid"], {})[m["index"]] = round(float(fn(d, m)), 2)
        args.out.write_text(json.dumps(preds, indent=1), encoding="utf-8")
        print(f"Vorhersagen ({args.variante}) geschrieben: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
