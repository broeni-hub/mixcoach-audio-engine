"""Der Uebergang als FENSTER statt als Sekundenangabe (K3, A1).

WARUM ES DIESES MODUL GIBT
--------------------------
Der Report zeigt heute einen Punkt: "Uebergang bei 14:32". Diese Angabe ist
in den meisten Faellen falsch, und zwar messbar:

    Marker mid_sec gegen die menschliche Korrektur, 132 Faelle:
      innerhalb 4 s     2 %
      innerhalb 8 s     5 %
      |Fehler| p50     34 s      p75  66 s      p90 117 s

Fuer einen fremden DJ ist das der teuerste Fehler des Produkts. Er klickt
"anhoeren bei 14:32", hoert mitten in einen Track, und hat in fuenf Sekunden
entschieden, dass das Werkzeug nicht funktioniert. Er schreibt nicht "euer
Marker ist 51 s daneben" - er schreibt "interessant, danke" und schickt nie
wieder ein Set.

sigma = 54,6 s ist zweimal gemessen und in drei Monaten nicht wegzuoptimieren
(ZUKUNFTSWEGE_2026-07-30.md, K1 zweimal gescheitert). Die MESSUNG bleibt also,
wie sie ist. Was sich aendern laesst, ist die BEHAUPTUNG:

    vorher   "Uebergang bei 14:32"              - falsch, zerstoert Vertrauen
    nachher  "Uebergang zwischen 13:32 und 15:22" - wahr und brauchbar

DIE ZWEI ZAHLEN, DIE HIER DRINSTECKEN
-------------------------------------
Beide am 27.08.2026 ueber 132 menschliche Korrekturen gemessen.

1. DER ANKER IST start_sec, NICHT mid_sec.

       mid_sec     Median -28,3 s   |Fehler| p50 34 s  p75 66 s  p90 117 s
       start_sec   Median  -7,1 s   |Fehler| p50 32 s  p75 61 s  p90  97 s

   start_sec ist bei jeder Fensterbreite besser. Das passt zur Diagnose in
   CLAUDE.md: detect_set_transition_zones() findet die RMS-Delle, also das
   ENDE des Blends; der Mensch markiert den ANFANG.

2. DIE BREITE IST -60 s BIS +50 s um start_sec.

       -30 s .. +30 s    49 %
       -60 s .. +50 s    73 %   <- gewaehlt
      -100 s ..+130 s    90 %

   90 % waeren ehrlicher, kosten aber ein Fenster von 230 s. In einem
   30-Minuten-Set sagt das nichts mehr. 110 s heisst: einmal Play druecken
   und knapp zwei Minuten zuhoeren - ungefaehr das, was ein DJ beim
   Nachhoeren ohnehin tut.

   Zum Vergleich: das vorhandene Blend-Fenster start_sec..end_sec ist im
   Median 34 s breit und enthaelt nur 32 % der Korrekturen. Es als "der
   Uebergang" anzuzeigen waere in zwei von drei Faellen falsch.

WAS DIESES MODUL NICHT TUT
--------------------------
Es aendert keine Messung. loudness_jump_db und beat_jitter_ms werden weiter
ueber das Blend-Fenster gerechnet und behalten ihre Bedeutung. Hier entsteht
nur die Angabe, WO der DJ hinhoeren soll.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Gemessen am 27.08.2026 ueber 132 menschliche Korrekturen. Wer diese Werte
# aendert, misst vorher nach - tools/eval/uebergangsfenster.py.
VOR_S = 60.0
NACH_S = 50.0
ABDECKUNG_PCT = 73


def fenster(t: Dict, gesamtdauer_s: Optional[float] = None) -> Optional[Dict]:
    """Das Fenster, in dem der Uebergang beginnt. None, wenn nicht bestimmbar.

    Anker ist start_sec. Fehlt der, faellt es auf mid_sec zurueck - dann ist
    das Fenster schlechter, aber immer noch ehrlicher als ein Punkt.
    """
    anker = t.get("start_sec")
    grund = "start_sec"
    if not isinstance(anker, (int, float)):
        anker = t.get("mid_sec")
        grund = "mid_sec"
    if not isinstance(anker, (int, float)):
        return None

    von = max(0.0, float(anker) - VOR_S)
    bis = float(anker) + NACH_S
    if gesamtdauer_s:
        bis = min(bis, float(gesamtdauer_s))
    if bis <= von:
        return None
    return {"vonSec": round(von, 1), "bisSec": round(bis, 1),
            "abdeckungPct": ABDECKUNG_PCT, "anker": grund}


def annotate_fenster(transitions: List[Dict],
                     gesamtdauer_s: Optional[float] = None) -> None:
    """Haengt window an jeden Uebergang."""
    for t in transitions or []:
        if isinstance(t, dict):
            t["window"] = fenster(t, gesamtdauer_s)
