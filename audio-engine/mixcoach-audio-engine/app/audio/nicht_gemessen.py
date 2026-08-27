"""Welche Kopfzahlen ein Report NICHT traegt (B5).

WARUM ES DIESES MODUL GIBT
--------------------------
`notMeasured` stand bis zum 27.08.2026 an zwei Stellen und war an beiden
falsch:

1. `app/api/analysis_mapper.py` setzte eine feste Fuenferliste
   `NOT_YET_MEASURED`. Fest heisst: sie kann nicht stimmen, sobald sich
   etwas aendert - und es hat sich etwas geaendert.
2. `tools/backfill_uebungen.py._nicht_gemessen()` bildete sie aus dem
   Ist-Stand - aber aus `scores`. Dort steht `beatmatching: None`, weil diese
   Kopfzahl niemand rechnet. Aus "die Kopfzahl fehlt" wurde "die Groesse ist
   nicht gemessen", und das ist etwas anderes.

Der Schaden war sichtbar: seit dem 20.08. misst `beat_jitter_ms` das
Beatmatching, belegt (Spearman -0,336 ueber 237 Bewertungen) und Grundlage
von 90 Uebungen. Trotzdem sagten **alle 56 Reports** "beatmatching: nicht
gemessen" und zeigten daneben eine Beatmatching-Uebung mit Zahl. Ein Verstoss
gegen die Ehrlichkeitslinie in der selteneren Richtung: nicht zu viel
behauptet, sondern eine echte Messung verleugnet.

DIE UNTERSCHEIDUNG, AUF DIE ES ANKOMMT
--------------------------------------
Befuellt ist nicht gemessen. `phrase_alignment_score` steht in 100 % der
Uebergaenge und sagt ueber die Qualitaet nichts (rho -0,04); `bpm_drift` ist
in 89 % der Uebergaenge exakt 0,0. Eine Zahl, die keinen Zusammenhang mit dem
menschlichen Urteil hat, ist keine Messung im Sinne dieses Feldes - sie ist
eine Zahl.

Deshalb steht unten eine Tabelle mit BEIDEN Bedingungen je Dimension: es
braucht ein Feld, das in diesem Report tatsaechlich befuellt ist, UND einen
Beleg. Fehlt eines von beiden, steht die Dimension in `notMeasured`.

Wer eine Dimension herausnehmen will, traegt den Beleg hier ein - mit Zahl
und Datum. Das ist die einzige Stelle, an der diese Entscheidung faellt.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

# Je Dimension: welches Feld sie messen wuerde, ob dafuer ein Beleg vorliegt,
# und woher der Beleg stammt.
#
# "feld" ist ein Feld JE UEBERGANG in setTransitions. None heisst: es gibt
# gar keinen Messwert, die Dimension kann nur "nicht gemessen" sein.
DIMENSIONEN: Dict[str, Dict] = {
    "beatmatching": {
        "feld": "beat_jitter_ms",
        "belegt": True,
        "beleg": ("Spearman -0,336 gegen 237 eigene Bewertungen, p < 0,0001; "
                  "bereinigt um Energieloch, Fensterlaenge und Pegelsprung "
                  "haelt der Zusammenhang (tools/eval/beat_jitter.py, "
                  "20.08.2026)"),
    },
    "timing": {
        "feld": "phrase_beats_off",
        "belegt": False,
        "beleg": ("befuellt, aber ohne Zusammenhang: rho -0,04 gegen das "
                  "menschliche Urteil, und bpm_drift ist in 89 % der "
                  "Uebergaenge exakt 0,0. Befuellt ist nicht gemessen."),
    },
    "eq": {
        "feld": None,
        "belegt": False,
        "beleg": "kein Messwert vorhanden",
    },
    "creativity": {
        "feld": None,
        "belegt": False,
        "beleg": "kein Messwert vorhanden und keiner in Sicht",
    },
    # frequency steht NICHT in scores, sondern als eigenes Feld auf oberster
    # Ebene. Beim ersten Anlauf ist es genau deshalb aus der Liste gefallen -
    # der Report haette behauptet, das Frequenzbild sei gemessen.
    "frequency": {
        "feld": None,
        "belegt": False,
        "beleg": "eigenes Feld auf oberster Ebene, wird nicht gefuellt",
        "oberste_ebene": "frequency",
    },
}

# Dimensionen, die HEUTE als Note im Report stehen und deren Beleg offen ist.
# Sie bleiben unberuehrt, weil die Frage nicht nebenbei zu entscheiden ist:
# flow und musicality sind Kopfzahlen ueber ein ganzes Set, die vorhandenen
# Bewertungen sind je Uebergang - sie lassen sich nicht direkt gegeneinander
# rechnen. Wer sie prueft, braucht dafuer einen eigenen Eingang.
OFFEN_OHNE_BELEG = ("flow", "musicality")


def bestimmen(uebergaenge: Optional[Sequence[Dict]],
              scores: Optional[Dict] = None,
              frequency: object = None) -> List[str]:
    """Die Dimensionen, die dieser Report nicht traegt - sortiert.

    Eine Dimension faellt nur dann heraus, wenn sie belegt ist UND ihr Feld
    in mindestens einem Uebergang dieses Reports steht. Ein Report ohne
    Uebergaenge traegt nichts.
    """
    uebergaenge = uebergaenge or []
    fehlend: List[str] = []

    for name, regel in DIMENSIONEN.items():
        if regel.get("oberste_ebene") == "frequency" and frequency is not None:
            continue
        feld = regel.get("feld")
        if not regel.get("belegt") or not feld:
            fehlend.append(name)
            continue
        vorhanden = any(isinstance(t, dict) and t.get(feld) is not None
                        for t in uebergaenge)
        if not vorhanden:
            fehlend.append(name)

    # Kopfzahlen, die die Pipeline gar nicht rechnen konnte, sagen das auch
    # dann, wenn sie oben nicht aufgefuehrt sind (flow/musicality koennen
    # None sein, wenn die Analyse sie nicht bilden konnte).
    for name, wert in (scores or {}).items():
        if wert is None and name not in fehlend and name != "overall":
            fehlend.append(name)

    return sorted(set(fehlend))


def aus_report(report: Dict) -> List[str]:
    """Wie bestimmen(), aber aus einem fertigen Report-JSON."""
    return bestimmen(report.get("setTransitions"),
                     report.get("scores"),
                     report.get("frequency"))
