"""Zweite, blinde Labelrunde - Ablage getrennt von der Ground Truth.

Das hier ist eine MESSUNG, kein Label-Zuwachs. Deshalb ein eigener Ordner
(DATA_ROOT/relabel/) und nicht ground_truth/: der Retrain liest
ausschliesslich GROUND_TRUTH_DIR (siehe retrain_model.collect_feedback_rows),
und diese Werte duerfen dort nie hineinlaufen. Sonst trainiert das Modell
auf Daten, die erhoben wurden, um seine Bezugsgroesse zu pruefen.

Wozu das Ganze: Vier unabhaengige Schaetzer verfehlen den menschlichen
Bezugspunkt gleichsinnig um 24-41 s (ZUKUNFTSWEGE_2026-07-30.md, 1.6). Bevor
ein fuenfter gebaut wird, ist zu klaeren, ob der Bezugspunkt selbst
reproduzierbar ist. Das Akzeptanzkriterium aus CLAUDE_CODE_SPEC_2026-07-29.md
("sigma deutlich unter 53 s, innerhalb 8 s >= 50 %") setzt eine menschliche
Wiederholgenauigkeit von deutlich unter 8 s voraus - die ist nie gemessen
worden.

Dateiformat je Aufnahme (daten/relabel/<analysisId>.json):

    {
      "analysisId": "...",
      "seed": 4711,              # fixiert die Reihenfolge ueber Sitzungen
      "startedAt": 1783...,
      "antworten": {
        "<transition-index>": {
          "sec": 812.4,          # zweite Zeitangabe des Menschen
          "was": "a_raus",       # a_raus | b_rein | beides
          "at": 1783...          # Klickzeitpunkt, wie in feedback_store
        }
      }
    }
"""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from app.paths import DATA_ROOT

RELABEL_DIR = DATA_ROOT / "relabel"

# Die drei Antworten auf "was markierst du eigentlich". Absichtlich genau
# diese drei und kein Freitext - die Frage ist, ob sich die Vermutung aus
# ZUKUNFTSWEGE 1.6 bestaetigt (der Mensch markiert nicht den Einsatz von
# Track B, sondern womoeglich, wann A anfaengt zu gehen).
WAS_OPTIONEN = ("a_raus", "b_rein", "beides")

_lock = threading.Lock()


def _pfad(analysis_id: str) -> Path:
    return RELABEL_DIR / f"{analysis_id}.json"


def _leer(analysis_id: str) -> Dict:
    return {
        "analysisId": analysis_id,
        # Seed einmal ziehen und festhalten: die Reihenfolge muss ueber
        # mehrere Sitzungen dieselbe bleiben, sonst bekommt ein Uebergang
        # beim Fortsetzen eine andere Position und die Wuerfelung waere
        # keine Wuerfelung mehr, sondern eine Neumischung je Aufruf.
        "seed": random.randrange(1, 10**9),
        "startedAt": time.time(),
        "antworten": {},
    }


def laden(analysis_id: str) -> Dict:
    pfad = _pfad(analysis_id)
    if not pfad.exists():
        return _leer(analysis_id)
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _leer(analysis_id)
    daten.setdefault("antworten", {})
    daten.setdefault("seed", 1)
    return daten


def sitzung(analysis_id: str) -> Dict:
    """Wie laden(), legt die Datei aber an, falls sie fehlt.

    Noetig, weil _leer() bei jedem Aufruf einen NEUEN Seed zieht. Ohne
    dieses Festschreiben bekaeme man bis zur ersten gespeicherten Antwort
    bei jedem Seitenaufruf eine andere Reihenfolge - ein Neuladen des
    Browsers haette neu gemischt. Die Wuerfelung soll einmal fallen und
    dann liegen bleiben, sonst ist sie keine feste Reihenfolge, gegen die
    sich der Durchgang fortsetzen laesst.
    """
    with _lock:
        pfad = _pfad(analysis_id)
        if pfad.exists():
            return laden(analysis_id)
        daten = _leer(analysis_id)
        _schreiben(daten)
        return daten


def speichern_antwort(analysis_id: str, index: int, sec: float,
                      was: str) -> Dict:
    """Eine Zeitangabe der zweiten Runde ablegen.

    Ueberschreibt eine vorhandene Antwort zum selben Index bewusst - wer
    einen Uebergang noch einmal anfaehrt, korrigiert sich; gemessen wird
    der Stand am Ende des Durchgangs.
    """
    if was not in WAS_OPTIONEN:
        raise ValueError(f"unbekannte Option: {was!r}, erlaubt {WAS_OPTIONEN}")
    with _lock:
        daten = laden(analysis_id)
        daten["antworten"][str(index)] = {
            "sec": round(float(sec), 2),
            "was": was,
            "at": time.time(),
        }
        _schreiben(daten)
    return daten


def _schreiben(daten: Dict) -> None:
    pfad = _pfad(daten["analysisId"])
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, indent=1, ensure_ascii=False),
                    encoding="utf-8")


def reihenfolge(indizes: list[int], seed: int) -> list[int]:
    """Gewuerfelte, aber reproduzierbare Reihenfolge der Uebergaenge.

    Gewuerfelt, damit die Erinnerung an den ersten Durchgang nicht
    mitlaeuft: in zeitlicher Reihenfolge wuerde jeder Uebergang im selben
    Kontext auftauchen wie beim ersten Mal.
    """
    gemischt = list(indizes)
    random.Random(seed).shuffle(gemischt)
    return gemischt


def fortschritt(analysis_id: str, gesamt: int) -> tuple[int, int]:
    return len(laden(analysis_id).get("antworten") or {}), gesamt


def dauer_je_antwort(analysis_id: str) -> Optional[float]:
    """Median-Abstand aufeinanderfolgender Klicks in Sekunden, oder None.

    Beantwortet nebenbei die offene Frage aus ZUKUNFTSWEGE 5 ("wie lange
    dauert ein Label-Durchgang wirklich") fuer die zweite Runde.
    """
    zeiten = sorted(a["at"] for a in (laden(analysis_id).get("antworten") or {}).values()
                    if a.get("at"))
    if len(zeiten) < 2:
        return None
    abstaende = sorted(b - a for a, b in zip(zeiten, zeiten[1:]))
    mitte = len(abstaende) // 2
    if len(abstaende) % 2:
        return abstaende[mitte]
    return (abstaende[mitte - 1] + abstaende[mitte]) / 2
