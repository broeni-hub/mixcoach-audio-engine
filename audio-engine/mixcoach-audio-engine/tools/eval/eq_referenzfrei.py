# -*- coding: utf-8 -*-
"""Laesst sich Bass-Overlap OHNE die Library messen - und traegt er ein Urteil?

    python -m tools.eval.eq_referenzfrei

WARUM ES DIESES WERKZEUG GIBT
-----------------------------
Am 13.09.2026 fragte Fabi - der erste fremde DJ, der MixCoach benutzt hat -
nach Feedback zu Hoehen, Mitten und Tiefen. Der Report sagt dazu "nicht
gemessen". Dieses Werkzeug klaert, was dem im Weg steht.

DIE VORHANDENE MESSUNG IST REFERENZBASIERT
------------------------------------------
app/audio/bass_overlap.py vergleicht den Tiefton der Aufnahme mit dem Tiefton
der beteiligten ORIGINAL-Tracks. Das setzt dreierlei voraus: beide Tracks per
Fingerprint sicher erkannt, die Originaldateien lesbar, saubere Solo-Fenster
zur Kalibrierung. Folge: 17 % Befuellung bei Sebastian, 0 % bei einem fremden
DJ - dessen Tracks kennt der Index nicht.

WAS HIER GEMESSEN WURDE (13.09.2026)
------------------------------------
Geprueft wurde ein REFERENZFREIES Mass: die Verschiebung der spektralen
Balance waehrend des Blends gegen die Fenster davor und danach. Anteile statt
Pegel, damit nicht bloss Lautstaerke gemessen wird. Es braucht nur die
Aufnahme.

1. DAS MASS FUNKTIONIERT TECHNISCH.
   Gegen bass_overlap_score, wo beide vorliegen:
       Spearman +0,471   p < 0,0001   n = 71
   Es misst dasselbe wie die referenzbasierte Messung - ohne Library.

2. EIN URTEIL TRAEGT ES NICHT.
   Gegen 298 Bewertungen (labels_prefilled.csv, human_rating 0-5):
       Tiefton-Verschiebung   rho +0,060   p 0,30   traegt nicht
       Hochton-Verschiebung   rho +0,004   p 0,95   traegt nicht
       Tiefton-Anteil roh     rho +0,190   p 0,001  traegt - misst aber
                                                    vermutlich nur, ob
                                                    gerade ein Beat laeuft
   Vier Fensterzuschnitte durchprobiert (Blend 10 s bis 60 s): rho bleibt
   zwischen +0,06 und +0,14. Am Zuschnitt liegt es nicht.

3. DER GRUND IST DIE DATENLAGE, NICHT DIE TECHNIK.
   Unter allen bewerteten Uebergaengen haben genau ZWEI einen gemessenen
   Bass-Overlap >= 60. Bei 54 von 71 steht der Score auf exakt 0. Was nicht
   vorkommt, kann sich im Urteil nicht zeigen - der Nullbefund unter 2. ist
   damit KEIN Beleg dafuer, dass Matsch egal ist. Er sagt nur: mit diesen
   Daten ist die Frage nicht zu beantworten.

WAS ALS NAECHSTES NOETIG WAERE
------------------------------
Stufe 1 - Messung sauber belegen, ohne Menschen:
    tools/synth_mixer kann `bass_swap` und `eq_blend`. Damit lassen sich
    Uebergangspaare mit und ohne Bassueberlappung erzeugen. Trennt das Mass
    die beiden Gruppen, ist es belegt; trennt es sie nicht, ist der Weg tot.

Stufe 2 - Relevanz belegen, mit Ohren:
    Dieselben Paare blind vorspielen ("welcher klingt sauberer?"), Aufbau wie
    J7 in tools/uebungen_bewertung_auswerten.py. Noetig fuer 5 %: 15 von 20.
    Erst diese Zahl entscheidet, ob EQ-Coaching Substanz hat.

Fuer HOEHEN und MITTEN gilt das alles noch nicht einmal: dort gibt es kein
Referenzmass, der Hochton-Kandidat traegt null (rho +0,004), und der
synth_mixer kann nur den Bass trennen.
"""
from __future__ import annotations

import csv, glob, os, sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.paths import RESULTS_DIR  # noqa: E402

ENGINE = Path(__file__).resolve().parents[2]
LABELS = ENGINE / "labels_prefilled.csv"
TIEF_HZ, HOCH_HZ = 120.0, 2000.0
# Der Mensch markiert den ANFANG des Uebergangs (CLAUDE.md), der Blend laeuft danach.
BLEND, VOR, NACH = (0.0, 20.0), (-45.0, -15.0), (35.0, 65.0)


def _anteile(x: np.ndarray, sr: int) -> Optional[Dict[str, float]]:
    x = x.mean(axis=1) if x.ndim > 1 else x
    if x.size < sr // 4:
        return None
    ges = float(np.mean(x * x)) + 1e-12
    tief = sosfilt(butter(4, TIEF_HZ, btype="low", fs=sr, output="sos"), x)
    hoch = sosfilt(butter(4, HOCH_HZ, btype="high", fs=sr, output="sos"), x)
    return {"tief": float(np.mean(tief*tief))/ges,
            "hoch": float(np.mean(hoch*hoch))/ges, "ges": ges}


def _fenster(pfad: str, t: float, spanne, info) -> Optional[Dict[str, float]]:
    a = max(0.0, t + spanne[0])
    b = min(info.frames / info.samplerate, t + spanne[1])
    if b - a < 3.0:
        return None
    x, sr = sf.read(pfad, start=int(a*info.samplerate),
                    frames=int((b-a)*info.samplerate), dtype="float32", always_2d=True)
    return _anteile(x, sr)


def _audio_index() -> Dict[str, str]:
    return {os.path.basename(p).rsplit(".", 1)[0]: p
            for p in glob.glob(str(RESULTS_DIR / "*"))
            if p.lower().endswith((".wav", ".mp3", ".flac", ".m4a"))}


def _labels() -> List[dict]:
    roh = LABELS.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = roh.decode(enc); break
        except UnicodeDecodeError:
            continue
    return [r for r in csv.DictReader(text.splitlines(), delimiter=";")
            if (r.get("human_rating") or "").strip()]


def main() -> int:
    if not LABELS.exists():
        print(f"FEHLT: {LABELS}"); return 1
    try:
        from scipy import stats
    except ImportError:
        print("scipy fehlt"); return 1

    audio, infos = _audio_index(), {}
    paare, verworfen = [], 0
    for r in _labels():
        p = audio.get(r["set_id"])
        if not p:
            verworfen += 1; continue
        if p not in infos:
            try: infos[p] = sf.info(p)
            except Exception: verworfen += 1; continue
        try: t = float(r["transition_center_time"])
        except (TypeError, ValueError): verworfen += 1; continue
        b = _fenster(p, t, BLEND, infos[p])
        v = _fenster(p, t, VOR,   infos[p])
        n = _fenster(p, t, NACH,  infos[p])
        if not (b and v and n):
            verworfen += 1; continue
        paare.append({"rating": float(r["human_rating"]),
                      "tief_delta": b["tief"] - (v["tief"] + n["tief"]) / 2,
                      "hoch_delta": b["hoch"] - (v["hoch"] + n["hoch"]) / 2,
                      "tief_anteil": b["tief"]})

    print(f"Auswertbare Uebergaenge: {len(paare)}   verworfen: {verworfen}\n")
    y = [p["rating"] for p in paare]
    print(f"{'Kandidat':24s} {'Spearman':>9s} {'p':>8s}  Urteil")
    print("-" * 62)
    for feld, name in (("tief_delta", "Tiefton-Verschiebung"),
                       ("hoch_delta", "Hochton-Verschiebung"),
                       ("tief_anteil", "Tiefton-Anteil roh")):
        rr = stats.spearmanr([p[feld] for p in paare], y)
        print(f"{name:24s} {rr.statistic:+9.3f} {rr.pvalue:8.4f}  "
              f"{'traegt' if rr.pvalue < 0.05 else 'traegt nicht'}")
    print("\nZum Vergleich: der belegte Beat-Jitter liegt bei rho = -0,336.")
    print("Der Befund vom 13.09.2026 steht im Modul-Docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
