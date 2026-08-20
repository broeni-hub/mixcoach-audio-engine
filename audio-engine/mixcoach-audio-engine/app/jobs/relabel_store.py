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

WERKZEUG-FASSUNGEN - warum jede Antwort gestempelt ist
-----------------------------------------------------
Fassung 1 (bis 19.08.2026) hat den Abspielkopf beim Laden auf den
Engine-Marker gesetzt und als Antwort die Position beim Absenden genommen.
Damit war der Marker die VORBELEGUNG der Antwort, nicht nur der Reiz.
Nachgerechnet am 19.08. auf den 16 Antworten aus Set 04804f27:

    Runde 1 (App, freie Wellenform)   Median -50,1 s zum Marker, sigma 47,1 s
    Runde 2 (Fassung 1)               Median  +4,7 s zum Marker, sigma 14,7 s
    15 von 16 Antworten der zweiten Runde lagen naeher am Marker als die
    der ersten.

Das ist das Bild, das eine vorbelegte Eingabe erzeugt, und es laesst sich
nicht von echter Uebereinstimmung unterscheiden. Die daraus gerechnete
Selbst-Uebereinstimmung (sigma 48,72 s) misst darum ueberwiegend die
Streuung von Runde 1 und nicht die Wiederholgenauigkeit.

Fassung 2 setzt den Startpunkt zufaellig gegen den Marker versetzt, laesst
frei positionieren und verlangt einen ausdruecklichen Griff ("Hier"), statt
die Abspielposition beim Absenden zu nehmen. Antworten beider Fassungen
duerfen NIE zusammengerechnet werden - deshalb der Stempel je Antwort.

Dateiformat je Aufnahme (daten/relabel/<analysisId>.json):

    {
      "analysisId": "...",
      "seed": 4711,              # fixiert Reihenfolge UND Startversatz
      "startedAt": 1783...,
      "antworten": {
        "<transition-index>": {
          "sec": 812.4,          # zweite Zeitangabe des Menschen
          "was": "a_raus",       # a_raus | b_rein | beides
          "at": 1783...,         # Klickzeitpunkt, wie in feedback_store
          "werkzeug": 2,         # fehlt = Fassung 1, siehe oben
          "startSec": 700.2,    # wo der Abspielkopf begonnen hat
          "zumMarker": false     # hat er den Marker ausdruecklich angefahren?
        }
      },
      "ersetzt": [ ... ]         # ueberschriebene Antworten, nichts geht weg
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

# Fassung des Messwerkzeugs. Hochzaehlen, sobald sich an der EINGABE etwas
# aendert - nicht bei Anzeige-Kosmetik. Antworten verschiedener Fassungen
# sind nicht vergleichbar; die Begruendung steht im Modul-Docstring.
WERKZEUG = 2

# Streubreite des zufaelligen Startversatzes gegen den Engine-Marker.
# 120 s deckt die Streuung von Runde 1 (sigma 47 s zum Marker) und die der
# Engine (sigma 54 s) mit Abstand ab. Enger gewaehlt bliebe der Marker als
# Anker wirksam, weiter waere es eine andere Aufgabe ("finde den Uebergang"
# statt "ordne ihn zeitlich ein").
VERSATZ_MAX_S = 120.0

# Sperrzone um den Marker. Ohne sie zieht die Gleichverteilung frueher oder
# spaeter einen Versatz nahe null - beim ersten Durchlauf mit 16 echten
# Uebergaengen am 19.08.2026 sofort geschehen. Fuer diesen einen Uebergang
# waere der Startpunkt dann wieder der Marker, also genau der Fehler von
# Fassung 1. 30 s liegt jenseits der laengsten ueblichen Transition
# (64 Takte bei 128 BPM), der Startpunkt ist damit nie eine Antwort, die
# man einfach stehen lassen kann.
VERSATZ_MIN_S = 30.0

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
        "werkzeug": WERKZEUG,
        "antworten": {},
        # Ueberschriebene Antworten. Eine Messung wird hier nie geloescht,
        # auch nicht die aus einer widerlegten Werkzeug-Fassung.
        "ersetzt": [],
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
    daten.setdefault("ersetzt", [])
    # Kein Stempel heisst Fassung 1 - so sind die Antworten vom 11.08.2026
    # entstanden, bevor der Startversatz existierte.
    daten.setdefault("werkzeug", 1)
    for antwort in daten["antworten"].values():
        antwort.setdefault("werkzeug", 1)
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


def speichern_antwort(analysis_id: str, index: int, sec: float, was: str,
                      start_sec: Optional[float] = None,
                      zum_marker: bool = False) -> Dict:
    """Eine Zeitangabe der zweiten Runde ablegen.

    Ueberschreibt eine vorhandene Antwort zum selben Index bewusst - wer
    einen Uebergang noch einmal anfaehrt, korrigiert sich; gemessen wird
    der Stand am Ende des Durchgangs. Die ersetzte Antwort wandert nach
    "ersetzt" und geht nicht verloren: sie ist eine Messung, und eine
    Messung wird in diesem Projekt nicht ueberschrieben, nur abgeloest.

    start_sec und zum_marker sind die Anker-Diagnose. Ohne sie laesst sich
    hinterher nicht pruefen, ob die Antwort am Startpunkt oder am
    Engine-Marker klebt - genau der Fehler, an dem Fassung 1 gescheitert ist.
    """
    if was not in WAS_OPTIONEN:
        raise ValueError(f"unbekannte Option: {was!r}, erlaubt {WAS_OPTIONEN}")
    with _lock:
        daten = laden(analysis_id)
        vorher = daten["antworten"].get(str(index))
        if vorher is not None:
            daten["ersetzt"].append({"index": int(index), **vorher})
        daten["antworten"][str(index)] = {
            "sec": round(float(sec), 2),
            "was": was,
            "at": time.time(),
            "werkzeug": WERKZEUG,
            "startSec": None if start_sec is None else round(float(start_sec), 2),
            "zumMarker": bool(zum_marker),
        }
        daten["werkzeug"] = WERKZEUG
        _schreiben(daten)
    return daten


def startversatz(seed: int, index: int) -> float:
    """Zufaelliger, aber reproduzierbarer Versatz des Startpunkts.

    Aus dem Sitzungs-Seed abgeleitet und nicht bei jedem Aufruf neu
    gezogen - aus demselben Grund wie die Reihenfolge: ein Neuladen des
    Browsers darf den Uebergang nicht an eine andere Stelle setzen, sonst
    ist der Versatz kein Merkmal des Uebergangs mehr, sondern des Klicks.

    Betrag zwischen VERSATZ_MIN_S und VERSATZ_MAX_S, Vorzeichen gewuerfelt:
    ein Startpunkt nahe dem Marker waere wieder ein Anker.
    """
    wuerfel = random.Random(seed * 1_000_003 + index)
    betrag = wuerfel.uniform(VERSATZ_MIN_S, VERSATZ_MAX_S)
    return betrag if wuerfel.random() < 0.5 else -betrag


def erledigt_mit_werkzeug(analysis_id: str, fassung: int = WERKZEUG) -> list[int]:
    """Indizes, die MIT DIESER Werkzeug-Fassung beantwortet sind.

    Antworten aelterer Fassungen zaehlen bewusst nicht als erledigt: sie
    sind mit einem Instrument entstanden, das die Antwort vorbelegt hat.
    Wer den Durchgang wiederholt, soll sie erneut vorgelegt bekommen.
    """
    antworten = laden(analysis_id).get("antworten") or {}
    return sorted(int(i) for i, a in antworten.items()
                  if int(a.get("werkzeug") or 1) >= fassung)


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
