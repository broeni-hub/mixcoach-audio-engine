"""Uebungen und Beobachtungen je Uebergang - aus gemessenen Zahlen.

Die Regel, die dieses Modul traegt:

    Eine UEBUNG darf nur aus einer Groesse entstehen, die (a) gegen
    Sebastians Bewertungen belegt ist und (b) genug Spannweite hat, dass
    ein Ziel Sinn ergibt. Alles andere darf als BEOBACHTUNG erscheinen -
    nie als Aufgabe.

Beide Bedingungen sind noetig. Nachgemessen am 14.08.2026 ueber 230
zugeordnete Bewertungen aus labels_prefilled.csv (Spearman gegen
human_rating):

    |loudness_jump_db|      -0,339   n=170   <- belegt
    beat_alignment_score    +0,325   n=170   <- belegt, aber ohne Spannweite
    composite               +0,162   n=170
    energy_dip_pct          +0,065   n=136   <- kein Zusammenhang
    camelot_abstand         +0,053   n=230   <- kein Zusammenhang
    quality_score           -0,008   n=230   <- kein Zusammenhang
    bass_overlap_score      +0,009   n=8     <- nicht pruefbar

KORREKTUR VOM 20.08.2026 - hier stand bis heute "genau eine Groesse
erfuellt sie". Das war richtig beobachtet und falsch geschlossen.
beat_alignment_score erfuellt (a) und scheiterte an (b): sigma 2,56 auf
einer 0-100-Skala, Spanne 83-98. Der Grund liegt aber in der SKALA, nicht
in der Messung - ihr Nullpunkt entspricht 164 ms Jitter bei 128 BPM,
gemessen werden 2,9 bis 26,2 ms. Dieselbe Messung in Millisekunden
(app/audio/beat_jitter.py) hat p10 8,1 / p50 11,4 / p90 18,8 ms, also
Faktor 2,3, eine echte Einheit und ein Ziel am Pitch-Fader.

Nachgeprueft mit tools/eval/beat_jitter.py ueber 237 bewertete Uebergaenge
aus 24 Aufnahmen:

    beat_jitter_ms          -0,336   n=237   <- belegt, p < 0,0001
       bereinigt um Energieloch     -0,488 -> -0,444
       bereinigt um Fensterlaenge   -0,336 -> -0,260
       bereinigt um Pegelsprung     -0,336 -> -0,314
       gegen den Pegelsprung selbst -0,021  <- sagt etwas ANDERES

Es sind also zwei Groessen, nicht eine. Die dritte Zeile ist der Grund,
warum die zweite ueberhaupt dazugehoert: waere der Jitter nur ein anderer
Ausdruck des Pegelsprungs, brauchte ihn niemand.

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

# Ab hier wird Beat-Jitter zur Uebung.
#
# HERLEITUNG, nach demselben Muster wie oben: ueber alle 390 befuellten
# Uebergaenge liegt p75 bei 14,6 ms und p80 bei 15,4 ms - das schlechteste
# Fuenftel beginnt hier. 15 ms trifft 90 von 390 (23 %), vergleichbar mit den
# 29 % des Pegelsprungs. Ein musikalisch hergeleiteter Wert waere eine
# Behauptung: ab wann Eiern hoerbar wird, ist in diesem Projekt nicht
# gemessen.
SCHWELLE_BEAT_JITTER_MS = 15.0

# Das Ziel. 10 ms erreichen heute 130 von 390 Uebergaengen (33 %) - also
# nachweislich erreichbar und kein Wunschwert. Darunter wird es duenn:
# 8 ms schaffen nur 8 %, 5 ms noch 3 %.
ZIEL_BEAT_JITTER_MS = 10.0

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


def _uebung_beat_jitter(analysis_id: str, t: Dict) -> Optional[Dict]:
    """Die zweite belegte Uebung, seit 20.08.2026. None, wenn nichts zu sagen ist.

    Anders als beim Pegelsprung gibt es keine Richtung ("zu laut"/"zu leise")
    - der Jitter ist eine Streuung, und die hat nur einen Betrag.
    """
    jitter = t.get("beat_jitter_ms")
    if not isinstance(jitter, (int, float)):
        return None
    jitter = float(jitter)
    if jitter < SCHWELLE_BEAT_JITTER_MS:
        return None

    mid = t.get("mid_sec")
    return {
        "title": f"Beats zusammenhalten bei {_zeit(mid)}",
        "description": (
            f"Bei {_zeit(mid)} ({_uebergangsname(t)}) schwankte der "
            f"Beat-Abstand im Blend um {_zahl(jitter)} ms. Mix ihn nochmal "
            f"und halte die Beats zusammen, Ziel: unter "
            f"{_zahl(ZIEL_BEAT_JITTER_MS)} ms."
        ),
        "analysisId": analysis_id,
        "transitionIndex": t.get("index"),
        "atSec": t.get("start_sec") if isinstance(t.get("start_sec"), (int, float)) else mid,
        "metric": "beat_jitter_ms",
        "value": round(jitter, 2),
        "target": ZIEL_BEAT_JITTER_MS,
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


# Welche Schwelle zu welcher Groesse gehoert - gebraucht fuer die
# Reihenfolge, siehe baue().
_SCHWELLEN = {
    "loudness_jump_db": SCHWELLE_PEGELSPRUNG_DB,
    "beat_jitter_ms": SCHWELLE_BEAT_JITTER_MS,
}


def _ueberschreitung(uebung: Dict) -> float:
    """Um welchen Faktor liegt der Wert ueber seiner Schwelle."""
    schwelle = _SCHWELLEN.get(uebung.get("metric"))
    if not schwelle:
        return 0.0
    return abs(float(uebung.get("value") or 0.0)) / schwelle


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
        for bauer in (_uebung_pegelsprung, _uebung_beat_jitter):
            u = bauer(analysis_id, t)
            if u is not None:
                uebungen.append(u)
        beobachtungen.extend(_beobachtungen(analysis_id, t))

    # Die schlimmsten zuerst - wer nur eine Sache uebt, soll die groesste
    # ueben. Seit es zwei Groessen gibt, geht das NICHT mehr ueber den
    # Betrag: 19 ms und 4 dB sind keine vergleichbaren Zahlen, und nach
    # Betrag sortiert stuende jede Jitter-Uebung ueber jeder Pegel-Uebung.
    # Verglichen wird stattdessen, wie weit ein Wert seine eigene Schwelle
    # ueberschreitet - das ist in beiden Einheiten dieselbe Frage.
    uebungen.sort(key=lambda u: -_ueberschreitung(u))
    return uebungen, beobachtungen
