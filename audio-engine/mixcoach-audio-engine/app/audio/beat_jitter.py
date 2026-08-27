"""Beat-Jitter in Millisekunden - dieselbe Messung wie beat_alignment_score,
in einer Einheit, mit der man ueben kann.

WARUM ES DIESES MODUL GIBT
--------------------------
app/audio/scoring/beat_alignment.py rechnet den Variationskoeffizienten der
Beat-Abstaende im Blend-Fenster in einen 0-100-Score:

    score = 100 - (cv / 0,35) * 100

Der Nullpunkt dieser Skala, cv = 0,35, entspraeche bei 128 BPM einem Jitter
von 164 ms. Gemessen werden ueber 390 Uebergaenge 2,9 bis 26,2 ms. Die Skala
ist auf das 6,3-fache dessen ausgelegt, was vorkommt, und presst die ganze
echte Variation in ihre obersten 15 Punkte: Spanne 83-98, sigma 2,56.

Das hat eine Folge, die ueber die Anzeige hinausgeht. app/coach/uebungen.py
laesst eine Uebung nur aus einer Groesse entstehen, die (a) gegen Sebastians
Bewertungen belegt ist und (b) genug Spannweite fuer ein Ziel hat.
beat_alignment_score erfuellt (a) und scheitert an (b) - nicht an der
Messung, sondern an der Skala. Deshalb ruhten bis zum 20.08.2026 alle 110
Uebungen auf einer einzigen Groesse, dem Pegelsprung.

Dieselbe Messung in Millisekunden: p10 8,1 - p50 11,4 - p90 18,8 ms, also
Faktor 2,3 zwischen gut und schlecht, eine echte Einheit und ein Ziel, das am
Pitch-Fader umsetzbar ist.

WAS GEPRUEFT WURDE, BEVOR DAS HIER ENTSTAND
-------------------------------------------
tools/eval/beat_jitter.py, Lauf vom 20.08.2026 ueber 237 bewertete
Uebergaenge aus 24 Aufnahmen:

    Jitter gegen Bewertung              Spearman -0,336   p < 0,0001
    bereinigt um das Energieloch        -0,488 -> -0,444
    bereinigt um die Fensterlaenge      -0,336 -> -0,260
    bereinigt um den Pegelsprung        -0,336 -> -0,314
    Jitter gegen Pegelsprung            -0,021

Die letzte Zeile ist die wichtigste: der Jitter sagt etwas ANDERES als der
Pegelsprung, nicht dasselbe nochmal. Und der Zusammenhang ueberlebt alle drei
Stoerfaktoren - er misst also nicht bloss Breakdowns oder kurze Fenster.

ZWEI STELLEN, EINE MESSUNG
--------------------------
beat_alignment_score und beat_jitter_ms sind zwei Ansichten derselben Groesse.
Das verstoesst der Form nach gegen die Regel "jede Information hat genau einen
Ort" - und ist hier trotzdem richtig: app/audio/scoring/* darf nicht angefasst
werden (Composite-Rebuild), der Score speist den Composite, der Jitter den
Menschen. Damit die beiden nicht auseinanderlaufen, haelt
tests/test_beat_jitter.py fest, dass sie auf denselben Eingaben dieselbe
Messung ergeben. Wer eine Seite aendert, bekommt einen roten Test.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

# Bewusst dieselben Werte wie in app/audio/scoring/beat_alignment.py. Sie
# werden dort nicht importiert, sondern hier gespiegelt und per Test
# gleichgehalten - ein Import aus scoring/ waere eine Abhaengigkeit in ein
# Modul, das nicht angefasst werden darf.
MIN_BEATS_IM_FENSTER = 4
INTERVALL_MIN_S = 0.15   # 400 BPM
INTERVALL_MAX_S = 2.0    # 30 BPM


def _intervalle(beats_im_fenster: List[float]) -> Optional[np.ndarray]:
    if len(beats_im_fenster) < MIN_BEATS_IM_FENSTER:
        return None
    intervalle = np.diff(np.array(beats_im_fenster))
    intervalle = intervalle[(intervalle > INTERVALL_MIN_S) & (intervalle < INTERVALL_MAX_S)]
    if len(intervalle) < MIN_BEATS_IM_FENSTER - 1:
        return None
    return intervalle


def jitter_ms(beats_im_fenster: List[float]) -> Optional[float]:
    """Streuung der Beat-Abstaende in Millisekunden.

    Das ist cv * mittlerer Beat-Abstand, also genau die Groesse, die
    beat_alignment_score auf seine 0-100-Skala legt - nur ohne die Skala.
    """
    intervalle = _intervalle(beats_im_fenster)
    if intervalle is None:
        return None
    return float(np.std(intervalle)) * 1000.0


def annotate_beat_jitter(transitions_detailed: List[Dict], beats: List[float]) -> None:
    """Haengt beat_jitter_ms und beat_jitter_beats an jeden Uebergang.

    beat_jitter_beats ist die Stichprobe, aus der die Streuung entstanden ist.
    Sie wird mitgeschrieben, weil eine Streuung aus wenigen Beats wenig wert
    ist - und weil ohne diese Zahl niemand nachpruefen kann, ob ein hoher
    Wert Beatmatching oder Schaetzrauschen ist. Gemessen liegt das Minimum
    bisher bei 39 Beats; die Untergrenze von 4 ist trotzdem noetig, weil sie
    Set-Raender und sehr kurze Blends abfaengt.
    """
    for t in transitions_detailed:
        start = t.get("start_sec")
        ende = t.get("end_sec")
        if start is None or ende is None:
            t["beat_jitter_ms"] = None
            t["beat_jitter_beats"] = None
            continue

        im_fenster = [b for b in beats if float(start) <= b <= float(ende)]
        wert = jitter_ms(im_fenster)
        t["beat_jitter_ms"] = round(wert, 2) if wert is not None else None
        t["beat_jitter_beats"] = len(im_fenster) if wert is not None else None
        # Woher der Wert stammt. "raster" heisst: aus den Beat-Zeitpunkten
        # selbst gerechnet, volle Aufloesung. Der Backfill fuer aeltere
        # Reports setzt hier "score" - dort ist der Wert aus dem gerundeten
        # 0-100-Score zurueckgerechnet und auf rund 1,6 ms genau. Ohne diese
        # Unterscheidung sieht eine grob geschaetzte Zahl aus wie eine
        # gemessene.
        t["beat_jitter_quelle"] = "raster" if wert is not None else None


# --- Die Kopfzahl fuers Skill-Radar ---------------------------------------
#
# Das Radar braucht 0-100. Der Jitter ist eine Zeit. Die Umrechnung ist eine
# ANZEIGE-Entscheidung und keine Messung, deshalb steht sie hier offen und
# nicht versteckt in einer Formel:
#
#   100 Punkte bei <= 5 ms, 0 Punkte bei >= 25 ms, dazwischen linear.
#
# Woher die beiden Anker: ueber 390 gemessene Uebergaenge liegt das Minimum
# bei 2,9 ms und das Maximum bei 26,2 ms. 5 ms erreichen 3 %, 25 ms
# ueberschreiten unter 1 %. Die Skala deckt also genau den Bereich ab, der
# vorkommt - und zwar mit FESTEN Werten in Millisekunden, nicht mit
# Perzentilen des heutigen Bestands. Sonst hiesse dieselbe Zahl naechstes
# Jahr etwas anderes.
#
# Das ist die Lehre aus beat_alignment_score: dessen Nullpunkt liegt bei
# cv = 0,35, also 164 ms - dem Sechsfachen des groessten je gemessenen
# Werts. Die Folge war eine Spanne von 83 bis 98 Punkten. Hier laufen p10
# bis p90 (8,1 bis 18,8 ms) ueber 31 bis 84 Punkte.
#
# Die Millisekunden bleiben daneben stehen (beat_jitter_ms je Uebergang).
# Wer der Punktzahl nicht traut, kann die Messung selbst nachsehen.
PUNKTE_100_MS = 5.0
PUNKTE_0_MS = 25.0


def radar_punkte(uebergaenge: List[Dict]) -> Optional[int]:
    """0-100 fuer das Skill-Radar aus dem Median-Jitter eines Sets.

    None, wenn kein einziger Uebergang einen Jitter traegt - dann ist die
    Achse fuer dieses Set nicht gemessen, und das soll sie auch sagen.

    Median und nicht Mittelwert, aus demselben Grund wie bei der
    Pegelsprung-Kurve: ein einzelner ausgerissener Uebergang darf die
    Kopfzahl eines ganzen Sets nicht verschieben.
    """
    werte = sorted(float(t["beat_jitter_ms"]) for t in (uebergaenge or [])
                   if isinstance(t, dict)
                   and isinstance(t.get("beat_jitter_ms"), (int, float)))
    if not werte:
        return None
    m = len(werte) // 2
    median = werte[m] if len(werte) % 2 else (werte[m - 1] + werte[m]) / 2

    anteil = (PUNKTE_0_MS - median) / (PUNKTE_0_MS - PUNKTE_100_MS)
    return int(round(max(0.0, min(1.0, anteil)) * 100))
