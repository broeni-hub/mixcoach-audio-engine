# -*- coding: utf-8 -*-
"""Die sechs fremden Profi-Sets als Vergleichsmassstab - als SPANNE.

WARUM ES DIESES MODUL GIBT
--------------------------
Bis zum 23.09.2026 standen diese Zahlen an genau einer Stelle: als
Konstantenblock in tools/set_report.py, einem Kommandozeilen-Werkzeug. Die
App kannte sie nicht. Damit gab es zwei Report-Erzeuger mit verschiedenen
Massstaeben - und die Seite, die fremde DJs bekommen, war strenger als das
Produkt.

DIE SPANNE, NICHT DER MITTELWERT
--------------------------------
Bis zum 23.09.2026 stand in set_report.py nur der Median (Pegel 1,35 dB,
Jitter 10,0 ms), und die Skala zeichnete ihr Band von 0 bis dorthin. Alles
darueber las sich als Rueckstand.

Ein Test-DJ schrieb zu seinem Report: "maybe I'm not a machine but I believe
10ms is fucking amazing haha". Er hatte recht. Sein Set liegt bei 11,2 ms -
INNERHALB der Spanne, besser als Dixon bei Tomorrowland (11,9).
Nachgerechnet am 23.09.2026:

    Standardfehler des Set-Medians        +-1,8 ms
    angezeigter Rueckstand                 1,2 ms
    Set gegen alle Referenz-Uebergaenge    Mann-Whitney p = 0,49
    Set gegen jedes Referenz-Set einzeln   alle p > 0,09

Gegen kein einziges Referenz-Set war ein Unterschied nachweisbar. Der Report
zeigte eine Groesse an, die er nicht gemessen hatte - genau die
Ehrlichkeitslinie, gegen die das Produkt sonst antritt. Wer hier wieder einen
Mittelwert einsetzt, baut denselben Fehler.

WAS DIESE SETS SIND - UND WAS NICHT
-----------------------------------
Sechs Festival-Mitschnitte, gemastert. Mastering drueckt Pegelspruenge, der
Pegelvergleich gegen sie ist also zu Ungunsten des Nutzers verzerrt. Naeher an
dem, was ein echter Nutzer hochlaedt, liegen die drei ungemasterten Sets von
Fabi - die taugen aber nicht als "Profi"-Referenz. Solange hier die sechs
stehen, gehoert der Vorbehalt dazu.

DIE DICHTE IST BESCHREIBUNG, KEIN ZIEL
--------------------------------------
Uebergaenge je 10 Minuten steht nur hier, damit die Kachel einen Bereich
nennen kann. Ein Zusammenhang mit der Qualitaet ist NICHT belegt: rho -0,094
gegen den Jitter-Median ueber 23 Aufnahmen, p = 0,67 (13.09.2026,
nachgerechnet am 16.09. nach der Ankerregel). Fabi hat am 13.09. genau danach
gefragt - "Ist es empfohlen, schneller Tracks zu wechseln?" - weil die Kachel
gleichrangig neben zwei belegten Groessen stand. Sie ist keine Vorgabe.

NACHRECHENBAR, NICHT ABGETIPPT
------------------------------
`neu_berechnen()` bildet die Spannen aus dem Datenstamm. Ein Test vergleicht
sie gegen die Konstanten unten und schlaegt an, sobald beides auseinanderlaeuft
- etwa weil ein Set neu analysiert wurde. Dieselbe Bauart wie der Selbsttest
der Referenzmetrik: eine Zahl, die sich nicht selbst pruefen kann, ist in
diesem Projekt eine Zahl auf Zeit.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Erkannt am Dateinamen der Aufnahme. Bewusst Teilstrings - die vollen Namen
# tragen Schreibweisen, die sich je Quelle unterscheiden.
PROFI_SETS: Tuple[str, ...] = (
    "Dixon WE2",
    "Dixon at Cercle",
    "Four Tet",
    "Joris Voorn",
    "RÜFÜS DU SOL",
    "Be Svendsen",
)

#: Uebergaenge je 10 Minuten - keine Messgroesse je Uebergang, deshalb
#: getrennt behandelt.
DICHTE = "uebergaenge_je_10min"

#: Je Groesse: (min, max) ueber die Set-Mediane der sechs, und wer die Raender
#: haelt. Gerechnet am 23.09.2026 mit neu_berechnen().
SPANNEN: Dict[str, Dict] = {
    "loudness_jump_db": {
        "min": 0.50, "max": 2.00,
        "einheit": "dB",
        "raender": ("Joris Voorn", "RÜFÜS DU SOL"),
        "belegt": True,
    },
    "beat_jitter_ms": {
        "min": 5.8, "max": 11.9,
        "einheit": "ms",
        "raender": ("Joris Voorn", "Dixon WE2"),
        "belegt": True,
    },
    DICHTE: {
        "min": 1.83, "max": 2.94,
        "einheit": "",
        "raender": ("Be Svendsen", "Joris Voorn"),
        # Kein Zusammenhang mit der Qualitaet - siehe Modulkopf.
        "belegt": False,
    },
}


def vergleich(uebergaenge: Optional[Sequence[Dict]]) -> List[Dict]:
    """Der Vergleich dieses Sets mit den sechs - je BELEGTER Groesse ein Eintrag.

    Das ist die Form, in der die App und die verschickte Seite denselben
    Massstab zeigen koennen: Median des Sets, Spanne der sechs, und die
    Antwort auf die einzige Frage, die sich daraus belegen laesst - liegt der
    Wert innerhalb oder ausserhalb.

    WAS HIER BEWUSST FEHLT
    ----------------------
    Ein Rueckstand. "1,2 ms schlechter als die Profis" war genau der Satz,
    den ein Test-DJ am 23.09.2026 beanstandet hat, und er hatte recht: der
    Standardfehler des Set-Medians ist groesser als der angezeigte Abstand.
    Ein Wert innerhalb der Spanne ist nicht schlechter, er ist dieselbe
    Gegend. Ausserhalb ist eine Feststellung, kein Urteil - das Urteil
    haengt an der Schwelle, und die steht daneben.

    Die DICHTE fehlt ebenfalls. Sie hat keinen belegten Zusammenhang
    (rho -0,094, p 0,67) und gehoert deshalb nicht neben zwei Groessen, die
    einen haben. In der verschickten Seite steht sie als Kachel mit
    ausdruecklichem Hinweis; in der App gibt es diese Kachel nicht, und sie
    kommt auch nicht dazu.

    Leere Liste, wenn nichts gemessen ist. Kein Platzhalter.
    """
    from app.coach.uebungen import GROESSEN, wert_von  # spaet: Zyklus vermeiden

    raus: List[Dict] = []
    for metrik, regel in SPANNEN.items():
        if not regel.get("belegt") or metrik not in GROESSEN:
            continue
        werte = [w for w in (wert_von(t, metrik) for t in (uebergaenge or []))
                 if w is not None]
        if metrik == "loudness_jump_db":
            werte = [abs(w) for w in werte]
        if not werte:
            continue
        median = statistics.median(werte)
        raus.append({
            "metrik": metrik,
            "wert": round(median, 2),
            "einheit": regel["einheit"],
            "min": regel["min"],
            "max": regel["max"],
            "innerhalb": innerhalb(metrik, median),
            "schwelle": GROESSEN[metrik]["schwelle"],
            "uebergaenge": len(werte),
            "referenzSets": len(PROFI_SETS),
        })
    return raus


def spanne(metrik: str) -> Optional[Tuple[float, float]]:
    """(min, max) der sechs Referenz-Sets, oder None."""
    regel = SPANNEN.get(metrik)
    return (regel["min"], regel["max"]) if regel else None


def innerhalb(metrik: str, wert: Optional[float]) -> Optional[bool]:
    """Liegt der Wert in der Spanne der sechs? None, wenn nicht entscheidbar.

    Gedacht fuer den Satz "das liegt zwischen den Profis" - und gegen den
    Satz "du liegst zurueck", solange der Unterschied nicht gemessen ist.
    """
    grenzen = spanne(metrik)
    if grenzen is None or not isinstance(wert, (int, float)):
        return None
    wert = abs(float(wert)) if metrik == "loudness_jump_db" else float(wert)
    return grenzen[0] <= wert <= grenzen[1]


def _ist_profi(dateiname: str) -> Optional[str]:
    name = (dateiname or "").lower()
    return next((p for p in PROFI_SETS if p.lower() in name), None)


def neu_berechnen(results_dir: Path) -> Dict[str, Dict[str, float]]:
    """Die Spannen aus dem Datenstamm bilden - je Set der Median.

    Der Median je Set, dann min/max ueber die sechs. Nicht der Median ueber
    alle Uebergaenge zusammen: ein Set mit 34 Uebergaengen wuerde eines mit
    13 sonst ueberstimmen.
    """
    je_set: Dict[str, Dict[str, float]] = {}
    for pfad in sorted(Path(results_dir).glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = _ist_profi(report.get("fileName") or "")
        if not name:
            continue
        uebergaenge = report.get("setTransitions") or []
        werte: Dict[str, float] = {}
        for metrik in ("loudness_jump_db", "beat_jitter_ms"):
            roh: List[float] = [
                abs(float(t[metrik])) if metrik == "loudness_jump_db" else float(t[metrik])
                for t in uebergaenge
                if isinstance(t.get(metrik), (int, float))
            ]
            if roh:
                werte[metrik] = statistics.median(roh)
        dauer = report.get("totalDurationSec") or 0
        if dauer and uebergaenge:
            werte[DICHTE] = len(uebergaenge) / (float(dauer) / 600.0)
        if werte:
            je_set[name] = werte

    raus: Dict[str, Dict[str, float]] = {}
    for metrik in SPANNEN:
        vorhanden = {s: w[metrik] for s, w in je_set.items() if metrik in w}
        if not vorhanden:
            continue
        raus[metrik] = {
            "min": min(vorhanden.values()),
            "max": max(vorhanden.values()),
            "sets": len(vorhanden),
            "min_set": min(vorhanden, key=vorhanden.get),
            "max_set": max(vorhanden, key=vorhanden.get),
        }
    return raus
