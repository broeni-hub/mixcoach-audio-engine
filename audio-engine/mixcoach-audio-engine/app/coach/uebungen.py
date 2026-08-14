"""Uebungen und Beobachtungen je Uebergang - aus gemessenen Zahlen.

Die Regel, die dieses Modul traegt:

    Eine UEBUNG darf nur aus einer Groesse entstehen, die (a) gegen
    Sebastians Bewertungen belegt ist und (b) genug Spannweite hat, dass
    ein Ziel Sinn ergibt. Alles andere darf als BEOBACHTUNG erscheinen -
    nie als Aufgabe.

Beide Bedingungen sind noetig, und genau eine Groesse erfuellt sie.
Nachgemessen am 14.08.2026 ueber 230 zugeordnete Bewertungen aus
labels_prefilled.csv (Spearman gegen human_rating):

    |loudness_jump_db|      -0,339   n=170   <- belegt
    beat_alignment_score    +0,325   n=170   <- belegt, aber ohne Spannweite
    composite               +0,162   n=170
    energy_dip_pct          +0,065   n=136   <- kein Zusammenhang
    camelot_abstand         +0,053   n=230   <- kein Zusammenhang
    quality_score           -0,008   n=230   <- kein Zusammenhang
    bass_overlap_score      +0,009   n=8     <- nicht pruefbar

beat_alignment_score erfuellt (a), aber nicht (b): sigma 2,59 auf einer
0-100-Skala, gemessene Spanne 83-98. Ein Ziel "von 91 auf 95" ist keine
Uebung, die jemand ausfuehren kann. Der Pegelsprung erfuellt beides -
echte Einheit, Spanne 0 bis 10,1 dB, und ein Ziel, das am Mixer
umsetzbar ist.

Wer diese Regel aufweicht, baut die Vorlage von frueher in neuer
Verpackung ("Transition Review - listen to the detected transition
points"), und die stand in allen 51 Reports.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# Ab hier wird ein Pegelsprung zur Uebung.
#
# HERLEITUNG: ueber alle 432 Uebergaenge liegt p75 bei 3,50 dB und p80 bei
# 4,00 dB - das schlechteste Fuenftel beginnt also etwa hier. Ausschlaggebend
# ist aber, dass 3 dB schon die Grenze ist, an der der Fortschritt gemessen
# wird (Commit fdb1780: "Anteil ueber 3 dB von ~50 % auf ~22 %"). Dieselbe
# Grenze fuer Messung und Coaching, nicht zwei - sonst lobt die eine Zahl,
# was die andere anmahnt. Trifft 109 von 372 befuellten Uebergaengen (29 %).
SCHWELLE_PEGELSPRUNG_DB = 3.0

# Das Ziel. Unter 1 dB ist am Mixer hoerbar sauber und mit Gain/Trim
# erreichbar - anders als ein Ziel auf einer 0-100-Skala ohne Einheit.
ZIEL_PEGELSPRUNG_DB = 1.0

# Beobachtungen: festgestellt, nicht bewertet. Die Schwellen sind bewusst
# grob - sie entscheiden nur, ob etwas erwaehnenswert ist, nicht ob es
# schlecht ist. Fuer eine Bewertung fehlt der Beleg (siehe Modul-Docstring).
SCHWELLE_CAMELOT_SCHRITTE = 3
SCHWELLE_ENERGIELOCH_PCT = 28.0

# XP ist Spielmechanik, keine Messung. Fester Wert, damit keine erfundene
# Zahl entsteht ("schwerere Uebung = mehr Punkte" waere geraten).
XP_JE_UEBUNG = 30


def _zeit(sekunden: Optional[float]) -> str:
    """Sekunden als mm:ss - die Form, in der der DJ im Player sucht."""
    if not isinstance(sekunden, (int, float)) or sekunden < 0:
        return "?"
    gesamt = int(round(sekunden))
    return f"{gesamt // 60:d}:{gesamt % 60:02d}"


def _zahl(wert: float) -> str:
    """Deutsche Schreibweise mit einer Nachkommastelle."""
    return f"{wert:.1f}".replace(".", ",")


def _uebergangsname(t: Dict) -> str:
    """Tracknamen, wo vorhanden - sonst die Uebergangsnummer.

    NIE ein Platzhalter, der Namen vortaeuscht: nur 19 % der Uebergaenge
    tragen track_in/track_out, und ein erfundener Name waere genau die Art
    Text, gegen die dieses Modul geschrieben ist.
    """
    raus, rein = t.get("track_out"), t.get("track_in")
    if raus or rein:
        return f"{raus or '?'} → {rein or '?'}"
    index = t.get("index")
    return f"Übergang {index}" if index is not None else "dieser Übergang"


def _camelot_abstand(vorher: Optional[str], nachher: Optional[str]) -> Optional[int]:
    """Abstand auf dem Camelot-Rad: Stunden plus Wechsel Dur/Moll."""
    def zerlege(c):
        if not isinstance(c, str) or len(c) < 2:
            return None
        try:
            return int(c[:-1]), c[-1].upper()
        except ValueError:
            return None

    a, b = zerlege(vorher), zerlege(nachher)
    if a is None or b is None:
        return None
    stunden = abs(a[0] - b[0])
    stunden = min(stunden, 12 - stunden)
    return stunden + (0 if a[1] == b[1] else 1)


def _uebung_pegelsprung(analysis_id: str, t: Dict) -> Optional[Dict]:
    """Die einzige belegte Uebung. None, wenn nichts zu sagen ist."""
    sprung = t.get("loudness_jump_db")
    if not isinstance(sprung, (int, float)):
        return None
    betrag = abs(float(sprung))
    if betrag < SCHWELLE_PEGELSPRUNG_DB:
        return None

    mid = t.get("mid_sec")
    richtung = "lauter" if sprung > 0 else "leiser"
    return {
        "title": f"Pegel angleichen bei {_zeit(mid)}",
        "description": (
            f"Bei {_zeit(mid)} ({_uebergangsname(t)}) kam der neue Track "
            f"{_zahl(betrag)} dB {richtung} rein. Mix ihn nochmal, "
            f"Ziel: unter {_zahl(ZIEL_PEGELSPRUNG_DB)} dB."
        ),
        "analysisId": analysis_id,
        "transitionIndex": t.get("index"),
        "atSec": t.get("start_sec") if isinstance(t.get("start_sec"), (int, float)) else mid,
        # metric/value sind Pflicht: sie sind der Beleg, dass diese Uebung
        # aus einer Messung stammt und nicht aus einer Vorlage.
        "metric": "loudness_jump_db",
        "value": round(float(sprung), 2),
        "target": ZIEL_PEGELSPRUNG_DB,
        "xp": XP_JE_UEBUNG,
    }


def _beobachtungen(analysis_id: str, t: Dict) -> List[Dict]:
    """Feststellungen ohne Handlungsaufforderung.

    Camelot-Abstand und Energieloch sind messbar, aber es gibt KEINEN Beleg,
    dass sie den DJ stoeren (rho +0,05 und +0,07). Sie als Aufgabe zu
    formulieren waere eine Behauptung; sie zu verschweigen waere schade.
    Also: hinstellen und dazusagen, was man nicht weiss.
    """
    raus: List[Dict] = []
    mid = t.get("mid_sec")
    index = t.get("index")

    schritte = _camelot_abstand(t.get("camelot_before"), t.get("camelot_after"))
    if schritte is not None and schritte >= SCHWELLE_CAMELOT_SCHRITTE:
        raus.append({
            "text": (
                f"Bei {_zeit(mid)}: {t.get('camelot_before')} → "
                f"{t.get('camelot_after')}, {schritte} Schritte auf dem "
                f"Camelot-Rad. Ob dich das stört, ist an deinen Bewertungen "
                f"nicht ablesbar."
            ),
            "analysisId": analysis_id,
            "transitionIndex": index,
            "atSec": mid,
            "metric": "camelot_distance",
            "value": schritte,
        })

    loch = t.get("energy_dip_pct")
    if isinstance(loch, (int, float)) and loch >= SCHWELLE_ENERGIELOCH_PCT:
        raus.append({
            "text": (
                f"Bei {_zeit(mid)}: die Energie fällt um {_zahl(float(loch))} % ab. "
                f"Ob das stört, ist an deinen Bewertungen nicht ablesbar."
            ),
            "analysisId": analysis_id,
            "transitionIndex": index,
            "atSec": mid,
            "metric": "energy_dip_pct",
            "value": round(float(loch), 1),
        })

    return raus


def baue(analysis_id: str, transitions: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """(Uebungen, Beobachtungen) fuer einen Report.

    Getrennte Listen, nicht dieselbe: die Oberflaeche muss den Unterschied
    zwischen "tu das" und "das ist so" zeigen koennen.

    Findet sich nichts Belegtes, kommt eine LEERE Uebungsliste zurueck - das
    ist der Kern des Auftrags. Eine allgemeine Uebung waere schlimmer als
    keine, weil sie so aussieht, als haette das Werkzeug etwas gemessen.
    """
    uebungen: List[Dict] = []
    beobachtungen: List[Dict] = []
    for t in transitions or []:
        if not isinstance(t, dict):
            continue
        u = _uebung_pegelsprung(analysis_id, t)
        if u is not None:
            uebungen.append(u)
        beobachtungen.extend(_beobachtungen(analysis_id, t))

    # Die schlimmsten zuerst - wer nur eine Sache uebt, soll die groesste
    # ueben. Sortiert nach Betrag des Sprungs, nicht nach Zeit.
    uebungen.sort(key=lambda u: -abs(u["value"]))
    return uebungen, beobachtungen
