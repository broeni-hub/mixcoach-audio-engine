"""Energiebogen ueber das ganze Set - beschreiben, nicht benoten.

Erlebnis-Punkt 2/3 der Produktvision. Der Bogen ist gegen Zeitfehler
unempfindlich: ob ein Uebergang bei 14:32 oder 15:02 lag, aendert den
Energieverlauf eines 90-Minuten-Sets nicht. Genau darum ist das hier
lieferbar, waehrend die Uebergangszeit noch offen ist (K1).

WARUM HIER KEINE NOTE STEHT
---------------------------
Am 31.07.2026 sind beatmatching und timing aus der Anzeige genommen
worden, weil sie Noten aus Groessen bildeten, die nichts messen. Damit
das hier nicht derselbe Fehler mit anderem Namen wird, gilt eine Regel:
dieses Modul liefert BESCHREIBUNGEN und keine Bewertung. Kein Score,
kein "gut/schlecht", keine Handlungsanweisung.

Der Grund ist nicht Vorsicht, sondern Messbarkeit. Nachgemessen an 19
echten Aufnahmen (31.07.2026):

  - Der Bogen ist deterministisch: zwei Analysen derselben Aufnahme
    liefern identische Kurven (Median-Abstand 0,000 ueber 66 Paare).
    Das unterscheidet ihn von phrase_alignment_score, dessen Raster am
    erkannten Segmentanfang haengt und mit sigma = 52,87 s wandert.
  - Er unterscheidet die Aufnahmen deutlich (Median-Abstand 0,237
    zwischen verschiedenen Aufnahmen, auf 0-1 normiert).
  - Die Lage des Hoehepunkts ist ueber die Sets nahezu gleichverteilt
    (sigma 0,310; Gleichverteilung waere 0,289).

Der letzte Punkt ist der Grund gegen eine Note. Gleichverteilung heisst
hier NICHT, dass die Groesse nichts misst - anders als bei
phrase_beats_off, wo ein Haeufen bei 0 zu erwarten waere, weil DJs auf
Phrase mischen. Wo der Hoehepunkt eines Sets zu liegen hat, sagt keine
Theorie. Es gibt also keinen belegten Sollwert, gegen den benotet werden
koennte - wohl aber etwas zu zeigen.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional

# Glaettungsfenster in Stuetzpunkten. Bei 240 Punkten ueber ein 90-min-Set
# ist ein Punkt rund 22 s; +-12 Punkte glaetten also ueber gut 9 min. Das
# ist bewusst grob: gesucht ist der Bogen ueber das Set, nicht die
# Schwankung einzelner Tracks.
GLAETTUNG = 12

# Ab welchem Unterschied zweier Drittel von einer Bewegung gesprochen wird.
# 5 Punkte auf der 0-100-Skala der Kurve - darunter liegt der Unterschied
# in der Groessenordnung, die zwischen zwei benachbarten Aufnahmen ohnehin
# auftritt (Median-Abstand zwischen Aufnahmen: 6,7 bis 10,1 je Drittel).
MERKLICH = 5.0


def _werte(kurve: Optional[List[dict]]) -> Optional[List[float]]:
    """[{t, value}, ...] -> [value, ...]. None, wenn unbrauchbar."""
    if not kurve:
        return None
    try:
        werte = [float(p["value"]) for p in kurve]
    except (KeyError, TypeError, ValueError):
        return None
    return werte if len(werte) >= 12 else None


def _glaetten(werte: List[float], fenster: int = GLAETTUNG) -> List[float]:
    return [statistics.fmean(werte[max(0, i - fenster):min(len(werte), i + fenster + 1)])
            for i in range(len(werte))]


def bogen(energie_kurve: Optional[List[dict]],
          dauer_sec: Optional[float] = None) -> Optional[Dict]:
    """Beschreibung des Energieverlaufs. None, wenn keine Kurve vorliegt.

    Bewusst None statt Nullwerten: eine Aufnahme ohne Kurve hat keinen
    gemessenen Bogen, und das gehoert so angezeigt.
    """
    werte = _werte(energie_kurve)
    if werte is None:
        return None

    geglaettet = _glaetten(werte)
    n = len(geglaettet)
    drittel = [statistics.fmean(geglaettet[i * n // 3:(i + 1) * n // 3])
               for i in range(3)]

    # Laengster Abschnitt, der nicht faellt UND dabei merklich an Hoehe
    # gewinnt. Die zweite Bedingung ist noetig: mit >= allein zaehlt eine
    # voellig flache Kurve als ein durchgehender Aufbau ueber das ganze Set.
    # Ein Plateau ist kein Aufbau.
    laengster, laufend, start, bester_start = 0, 0, 0, 0
    for i in range(1, n):
        if geglaettet[i] >= geglaettet[i - 1]:
            if laufend == 0:
                start = i - 1
            laufend += 1
            if (laufend > laengster
                    and geglaettet[i] - geglaettet[start] >= MERKLICH):
                laengster, bester_start = laufend, start
        else:
            laufend = 0

    peak_i = max(range(n), key=lambda i: geglaettet[i])

    def in_sekunden(anteil: float) -> Optional[float]:
        return round(anteil * dauer_sec, 1) if dauer_sec else None

    return {
        "punkte": n,
        "dynamikumfang": round(max(werte) - min(werte), 1),
        "drittel": [round(d, 1) for d in drittel],
        "anstieg_gesamt": round(drittel[2] - drittel[0], 1),
        "peak_anteil": round(peak_i / n, 3),
        "peak_sec": in_sekunden(peak_i / n),
        "laengster_aufbau_anteil": round(laengster / n, 3),
        "laengster_aufbau_sec": in_sekunden(laengster / n),
        "laengster_aufbau_start_sec": in_sekunden(bester_start / n),
        "form": _form(drittel),
        # Ausdruecklich KEIN Score und keine Empfehlung - siehe Modul-Docstring.
    }


def _form(drittel: List[float]) -> str:
    """Grobform des Bogens als Wort. Rein beschreibend.

    Die Schwelle MERKLICH verhindert, dass Rauschen zu einer Aussage wird:
    liegen alle drei Drittel innerhalb von 5 Punkten, heisst das Ergebnis
    'gleichbleibend' und nicht die zufaellige Richtung des groessten
    Unterschieds.
    """
    a, m, e = drittel
    hoch_am_ende = e - a > MERKLICH
    tief_am_ende = a - e > MERKLICH
    mitte_hoch = m - max(a, e) > MERKLICH
    mitte_tief = min(a, e) - m > MERKLICH

    if mitte_hoch:
        return "Bogen mit Hoehepunkt in der Mitte"
    if mitte_tief:
        return "Einbruch in der Mitte"
    if hoch_am_ende:
        return "durchgehender Aufbau"
    if tief_am_ende:
        return "Ausklang zum Ende"
    return "gleichbleibend"


def beschreibung(b: Optional[Dict]) -> List[str]:
    """Saetze fuer die Anzeige. Beschreibend, ohne Urteil und ohne Rat.

    Kein Satz enthaelt "gut", "schlecht", "solltest du" oder eine Note -
    was der Bogen fuer die Qualitaet eines Sets bedeutet, ist nicht
    gemessen und wird darum auch nicht behauptet.
    """
    if b is None:
        return []
    saetze = [f"Energieverlauf: {b['form']}."]

    if abs(b["anstieg_gesamt"]) >= MERKLICH:
        richtung = "hoeher" if b["anstieg_gesamt"] > 0 else "niedriger"
        saetze.append(f"Das letzte Drittel liegt {abs(b['anstieg_gesamt']):.0f} Punkte "
                      f"{richtung} als das erste.")
    else:
        saetze.append("Erstes und letztes Drittel liegen auf gleicher Hoehe.")

    if b["laengster_aufbau_sec"] and b["laengster_aufbau_anteil"] >= 0.15:
        minuten = b["laengster_aufbau_sec"] / 60
        saetze.append(f"Laengster durchgehender Aufbau: {minuten:.0f} Minuten "
                      f"({b['laengster_aufbau_anteil'] * 100:.0f} % des Sets).")

    if b["peak_sec"] is not None:
        m, s = divmod(int(b["peak_sec"]), 60)
        saetze.append(f"Hoechste Energie bei {m}:{s:02d} "
                      f"({b['peak_anteil'] * 100:.0f} % der Setlaenge).")
    return saetze
