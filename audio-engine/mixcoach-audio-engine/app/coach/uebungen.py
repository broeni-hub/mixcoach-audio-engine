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

import zlib
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


# --- Wortlaut: Fassungen statt einer Vorlage ------------------------------
#
# Bis zum 14.09.2026 erzeugte jede Groesse genau einen Satz, in den Zeit und
# Wert eingesetzt wurden. Rechnet man Zeiten, Werte und Klammern heraus,
# blieben fuer 32 Uebungen aus drei Analysen VIER Formulierungen, die
# haeufigste 17-mal. Ein Report mit zehn Uebungen zeigte zehnmal denselben
# Satz - er las sich als Serienbrief, und die Messung dahinter wirkte mit.
#
# Unterschieden wird an dem, was in den Daten verschieden ist: der Richtung
# des Pegelsprungs (zu laut und zu leise brauchen entgegengesetzte
# Handgriffe) und der Schwere als Vielfaches der Schwelle. Innerhalb eines
# Falls werden gleichwertige Fassungen reihum vergeben.
#
# WAS KEINE FASSUNG DARF: etwas behaupten, das nicht gemessen ist. Keine
# Wahrnehmung ("hoerbar", "klingt", "der Raum"), keine Wirkung ("kostet
# mehr"), beim Jitter keine Richtung. Jede Fassung nennt den Wert, beim
# Pegel die Richtung, und einen Handgriff. Geprueft fuer ALLE Fassungen in
# tests/test_uebungen_wortlaut.py - nicht nur fuer die gerade ausgewaehlten.
#
# Die Stufen sind Textauswahl, keine Messgrenzen: sie aendern weder, ob eine
# Uebung entsteht, noch ihre Reihenfolge. Das entscheidet GROESSEN unten.
STUFE_WEIT = 1.75
STUFE_DEUTLICH = 1.35

# Hoechste Anzahl Uebungen DESSELBEN Falls in einem Report, gezaehlt am
# 14.09.2026 ueber 59 Reports. Jede Liste unten ist laenger - der Test haelt
# das fest. Waechst der Bestand darueber, wiederholt sich eine Fassung erst
# nach allen anderen.
GEMESSENES_MAXIMUM = {
    ("beat_jitter_ms", "knapp"): 6, ("beat_jitter_ms", "deutlich"): 5,
    ("beat_jitter_ms", "weit"): 0,
    ("lauter", "knapp"): 4, ("lauter", "deutlich"): 2, ("lauter", "weit"): 2,
    ("leiser", "knapp"): 2, ("leiser", "deutlich"): 3, ("leiser", "weit"): 3,
}

TITEL = {
    ("loudness_jump_db", "weit"): "Pegel vorab setzen",
    ("loudness_jump_db", "deutlich"): "Pegel angleichen",
    ("loudness_jump_db", "knapp"): "Pegel nachjustieren",
    ("beat_jitter_ms", "weit"): "Übergang neu ansetzen",
    ("beat_jitter_ms", "deutlich"): "Beats früher nachziehen",
    ("beat_jitter_ms", "knapp"): "Beats kurz nachfassen",
}

# {w} = Wert mit Einheit, {r} = "lauter"/"leiser". Jede Fassung setzt den
# Satz fort, der mit "Bei mm:ss (Uebergang)" beginnt.
FASSUNGEN = {
    ("lauter", "weit"): [
        "kam der neue Track {w} {r} rein. Den Gain des einkommenden Kanals schon "
        "vor dem Einblenden zurücknehmen, nicht erst während des Blends.",
        "war der einsetzende Track {w} {r} als der laufende. Am Kopfhörer "
        "vorhören und den Trim zurückdrehen, bis beide Anzeigen gleich stehen.",
        "lag der Einstieg {w} {r}. Den Übergang mit abgesenktem Gain neu "
        "ansetzen, statt ihn mit dem Fader auszugleichen.",
    ],
    ("lauter", "deutlich"): [
        "sprang der Pegel beim Einsetzen um {w}, der neue Track lief {r}. Vor dem "
        "Blend am Trim angleichen.",
        "zeigte die Pegelanzeige beim Wechsel {w} Unterschied, der neue Track war "
        "{r}. Beide Anzeigen vor dem Öffnen des Faders vergleichen und den Gain zurücknehmen.",
        "öffnete der neue Kanal {w} {r} als der alte. Den Gain vorab "
        "zurücknehmen, dann erst einblenden.",
    ],
    ("lauter", "knapp"): [
        "stand der neue Kanal beim Einsetzen {w} {r}. Ein kleiner Dreh am Gain vor dem Blend reicht.",
        "legte der Pegel beim Wechsel um {w} zu — der neue Track kam {r}. Eine "
        "kleine Rücknahme am Trim vor dem Einblenden reicht.",
        "hob sich der neue Track um {w} ab, er war {r}. Knapp über der Schwelle — "
        "beim Vorhören am Trim angleichen.",
        "startete der neue Track {w} {r}. Vor dem Einblenden die Pegelanzeige "
        "des Cue-Kanals prüfen.",
        "fiel der Einstieg mit {w} {r} aus. Den Gain vor dem Blend eine Spur zurücknehmen genügt.",
    ],
    ("leiser", "weit"): [
        "fehlten dem neuen Track {w} — er kam {r} als der laufende. Die Lücke "
        "gehört vor dem Einblenden an den Gain, nicht an den Kanalfader.",
        "sackte der Pegel beim Einsetzen um {w} ab, der neue Track lief {r}. "
        "Vor dem nächsten Versuch am Cue-Kanal den Trim hochdrehen.",
        "blieb der einsetzende Track {w} {r} als sein Vorgänger. Den Wechsel "
        "noch einmal üben, diesmal mit dem Gain vorab auf Höhe des laufenden Tracks.",
        "startete der neue Track {w} {r}. Den einkommenden Kanal vorab anheben "
        "und erst dann öffnen.",
    ],
    ("leiser", "deutlich"): [
        "verlor der Mix beim Wechsel {w}, der neue Track war {r}. Vor dem Öffnen "
        "des Faders am Gain nachregeln.",
        "lief der neue Kanal {w} {r} an. Die Anzeige des Cue-Kanals zeigt das "
        "schon vor dem Einblenden — dann den Trim nach oben.",
        "lag der Einstieg {w} {r}. Am Gain angleichen, bevor der Fader aufgeht.",
        "ging der Pegel beim Wechsel um {w} zurück, der neue Track kam {r}. Beim "
        "Vorhören am Cue-Kanal den Trim nachziehen.",
    ],
    ("leiser", "knapp"): [
        "kam der neue Track {w} {r} rein. Am Gain in Sekunden behoben.",
        "setzte der Track {w} {r} ein. Eine kleine Korrektur am Gain nach oben genügt.",
        "blieb der neue Track {w} {r} als sein Vorgänger, knapp über der Schwelle. "
        "Vor dem Blend den Trim eine Spur hochdrehen.",
    ],
    ("beat_jitter_ms", "weit"): [
        "schwankte der Beat-Abstand im Blend um {w}. Den Übergang neu ansetzen: "
        "Tempo beider Decks vorher angleichen und erst dann einblenden.",
        "wich der Abstand der Beats im Blend um {w} ab. Pitch vor dem Blend "
        "feiner angleichen und im Blend nur kleine Jog-Korrekturen setzen.",
        "hielt das Beatraster im Blend nicht: {w} Streuung. Früher in den Blend "
        "einsteigen, damit Zeit zum Nachregeln bleibt.",
    ],
    ("beat_jitter_ms", "deutlich"): [
        "streute der Beat-Abstand im Blend um {w}. Die Korrektur gehört in die "
        "erste Phrase, nicht ans Ende des Blends.",
        "maß MixCoach im Blend {w} Streuung zwischen den Beats. Pitch-Bend früh "
        "und in kleinen Schritten setzen statt einmal groß.",
        "war das Beatraster im Blend um {w} unregelmäßig. Tempo beider Decks vor "
        "dem Einblenden genauer angleichen.",
        "variierte der Abstand zwischen den Kicks um {w}. Zwei Takte früher "
        "einsteigen gibt Zeit zum Nachregeln.",
        "lag die Streuung des Beat-Abstands im Blend bei {w}. Während des Blends "
        "die Beatanzeige beider Decks im Blick behalten.",
        "blieb der Beat-Abstand nicht stabil, die Streuung betrug {w}. Vor dem "
        "Blend das Tempo am Pitch-Fader nachführen, dann erst den Fader öffnen.",
    ],
    ("beat_jitter_ms", "knapp"): [
        "zeigte der Beat-Abstand im Blend {w} Streuung. Meist reicht ein kurzer "
        "Nudge am Jog.",
        "kam das Beatraster auf {w} Streuung, knapp über der Schwelle. Ein "
        "einzelner Schubs am Jog genügt.",
        "betrug die Schwankung zwischen den Beats {w}. In der ersten Phrase "
        "kurz nachkorrigieren.",
        "stand die Streuung im Blend bei {w}. Ein Antippen des Jogs früh im "
        "Blend reicht.",
        "liefen die Kicks mit {w} Streuung übereinander. Beim Einblenden auf die "
        "Beatanzeige schauen und leicht nachführen.",
        "ergab die Messung {w} Unregelmäßigkeit im Beatraster. Kleine Korrektur "
        "am Pitch-Fader vor dem Einblenden.",
        "wackelte der Beat-Abstand um {w}. In den ersten acht Takten des Blends "
        "einmal nachregeln.",
        "summierte sich die Abweichung der Beats auf {w}. Die Tempos beider Decks "
        "vorab eine Nachkommastelle genauer angleichen.",
    ],
}


# --- Englisch. Dieselben Faelle, dieselben Regeln, eigener Wortlaut. -------
#
# Das Muster steht schon in app/coach/profile.py (TEXTS mit de/en) und je
# Uebergang in feedback/feedback_en. Uebersetzt wird NICHT im Report-
# Generator: dort entstuende eine zweite Textbibliothek, und genau die war
# am 14.09.2026 das Problem. Fuer beide Sprachen gelten dieselben Tests -
# Wert im Text, Richtung nur beim Pegel, keine Wahrnehmung, eigener
# Satzanfang je Gruppe, Aehnlichkeit unter 0,80.
TITEL_EN = {
    ("loudness_jump_db", "weit"): "Set the gain beforehand",
    ("loudness_jump_db", "deutlich"): "Match the levels",
    ("loudness_jump_db", "knapp"): "Trim the level",
    ("beat_jitter_ms", "weit"): "Rebuild this transition",
    ("beat_jitter_ms", "deutlich"): "Correct the beats earlier",
    ("beat_jitter_ms", "knapp"): "Nudge the beats",
}

FASSUNGEN_EN = {
    ("lauter", "weit"): [
        "the incoming track came in {w} {r} than the one playing. Pull its gain "
        "down before you open the fader, not while the blend is running.",
        "the level rose by {w} as the new track entered, it played {r}. Cue it up "
        "and turn the trim back until both meters sit level.",
        "the new channel opened {w} {r} than the old one. Rebuild the transition "
        "with the gain lowered instead of riding it out on the fader.",
    ],
    ("lauter", "deutlich"): [
        "the level jumped by {w} on entry, the new track ran {r}. Match it on the "
        "trim before the blend.",
        "the meter showed {w} difference at the switch, the new track was {r}. "
        "Compare both meters before the fader opens and take the gain back.",
        "the second deck came up {w} {r} than the first. Lower its gain first, "
        "then start blending.",
    ],
    ("lauter", "knapp"): [
        "the channel came up {w} {r} on entry. A small turn of the gain before "
        "the blend is enough.",
        "the level gained {w} at the switch, the incoming track was {r}. A light "
        "trim correction before you blend covers it.",
        "the track lifted {w} above the one playing, so {r}. Just over the line — "
        "match it while cueing.",
        "the entry started {w} {r}. Check the cue channel meter before opening "
        "the fader.",
        "the incoming level landed {w} {r}. Taking the gain down a notch before "
        "the blend is enough.",
    ],
    ("leiser", "weit"): [
        "the incoming track was missing {w} — it came in {r} than the one "
        "playing. That gap belongs on the gain before the blend, not on the fader.",
        "this switch gave up {w} of level, the second track playing {r}. Cue it "
        "next time and bring the trim up before the fader moves.",
        "the second deck stayed {w} {r} than its predecessor. Run the switch again "
        "with the gain already at the level of the track playing.",
        "the entry lost {w} at once, the new track was {r}. Raise the incoming "
        "channel first and only then open it.",
    ],
    ("leiser", "deutlich"): [
        "the mix lost {w} at the switch, the new track was {r}. Correct on the "
        "gain before the fader opens.",
        "the new channel started {w} {r} than the one playing. The cue meter shows "
        "that before the blend — trim it up.",
        "the entry sat {w} {r}. Match it on the gain before the fader moves.",
        "the new deck ran {w} {r} than its predecessor. Raise the trim while "
        "cueing.",
    ],
    ("leiser", "knapp"): [
        "the new track entered {w} {r}. A few seconds on the gain fixes it.",
        "the track came up {w} {r} than what was playing. A small upward "
        "correction on the gain is enough.",
        "the incoming level stayed {w} {r} than its predecessor, just over the "
        "line. Turn the trim up a notch before the blend.",
    ],
    ("beat_jitter_ms", "weit"): [
        "the beat spacing moved by {w} through the blend. Rebuild the transition: "
        "match the tempo of both decks first, then start blending.",
        "the gap between the beats varied by {w}. Align the pitch more finely "
        "before the blend and keep jog corrections small inside it.",
        "the grid did not hold through the blend: {w} of spread. Start the blend "
        "earlier so there is room to correct.",
    ],
    ("beat_jitter_ms", "deutlich"): [
        "beat spacing scattered by {w} inside the blend. The correction belongs in "
        "the first phrase, not at the end of it.",
        "MixCoach measured {w} of spread between the beats. Use pitch bend early "
        "and in small steps instead of one large push.",
        "the grid ran {w} off through the blend. Match the tempo of both decks "
        "more precisely before you open the fader.",
        "the distance between the kicks varied by {w}. Coming in two bars earlier "
        "leaves time to correct.",
        "spread of the beat spacing reached {w} in the blend. Keep an eye on the "
        "beat display of both decks while it runs.",
        "the spacing would not settle, at {w} of spread. Trim the tempo on the "
        "pitch fader first, then open the fader.",
    ],
    ("beat_jitter_ms", "knapp"): [
        "beat spacing showed {w} of spread. A short nudge on the jog usually does it.",
        "the grid came to {w} of spread, just past the line. One push on the jog "
        "is enough.",
        "variation between the beats measured {w}. Correct briefly in the first "
        "phrase.",
        "spread inside the blend stood at {w}. A tap on the jog early in the blend "
        "covers it.",
        "the kicks sat {w} apart in spread. Watch the beat display as you blend "
        "and follow gently.",
        "measurement returned {w} of irregularity in the grid. A small pitch "
        "correction before the blend fixes it.",
        "beat spacing wobbled by {w}. Correct once within the first eight bars of "
        "the blend.",
        "deviation across the beats added up to {w}. Match both tempos one decimal "
        "place more precisely beforehand.",
    ],
}

ZIELSATZ = {"de": " Ziel: unter {z} {e}.", "en": " Target: under {z} {e}."}
BIBLIOTHEK = {"de": (FASSUNGEN, TITEL), "en": (FASSUNGEN_EN, TITEL_EN)}


def _stufe(faktor: float) -> str:
    """Textstufe aus dem Vielfachen der Schwelle - keine Messgrenze."""
    if faktor >= STUFE_WEIT:
        return "weit"
    if faktor >= STUFE_DEUTLICH:
        return "deutlich"
    return "knapp"


def _fall(metrik: str, wert: float) -> Tuple[str, str]:
    """Schluessel in FASSUNGEN: (Richtung oder Groesse, Stufe)."""
    faktor = ueberschreitung(metrik, wert)
    if metrik == "loudness_jump_db":
        return ("lauter" if wert > 0 else "leiser", _stufe(faktor))
    return (metrik, _stufe(faktor))


def _versatz(analysis_id: str) -> int:
    """Stabiler Startpunkt je Report - zlib statt hash(), das je Prozess wuerfelt.

    Damit beginnen zwei Reports nicht mit derselben Fassung, und derselbe
    Report bekommt bei jedem Backfill denselben Wortlaut.
    """
    return zlib.crc32((analysis_id or "").encode("utf-8"))


def _zeit(sekunden: Optional[float]) -> str:
    """Sekunden als mm:ss - die Form, in der der DJ im Player sucht."""
    if not isinstance(sekunden, (int, float)) or sekunden < 0:
        return "?"
    gesamt = int(round(sekunden))
    return f"{gesamt // 60:d}:{gesamt % 60:02d}"


def _zahl(wert: float, sprache: str = "de") -> str:
    """Eine Nachkommastelle - Komma im Deutschen, Punkt im Englischen."""
    text = f"{wert:.1f}"
    return text.replace(".", ",") if sprache == "de" else text


def _uebergangsname(t: Dict, sprache: str = "de") -> str:
    """Tracknamen, wo vorhanden - sonst die Uebergangsnummer.

    NIE ein Platzhalter, der Namen vortaeuscht: nur 19 % der Uebergaenge
    tragen track_in/track_out, und ein erfundener Name waere genau die Art
    Text, gegen die dieses Modul geschrieben ist.
    """
    raus, rein = t.get("track_out"), t.get("track_in")
    if raus or rein:
        return f"{raus or '?'} → {rein or '?'}"
    index = t.get("index")
    if sprache == "en":
        return f"Transition {index}" if index is not None else "this transition"
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


def _uebung_pegelsprung(analysis_id: str, t: Dict, fassung: int = 0,
                        sprache: str = "de") -> Optional[Dict]:
    """Die erste belegte Uebung. None, wenn nichts zu sagen ist.

    `fassung` waehlt den Wortlaut innerhalb des Falls - baue() vergibt sie
    reihum, damit derselbe Satz in einem Report nicht zweimal steht.
    """
    sprung = t.get("loudness_jump_db")
    if not isinstance(sprung, (int, float)):
        return None
    betrag = abs(float(sprung))
    if betrag < SCHWELLE_PEGELSPRUNG_DB:
        return None

    mid = t.get("mid_sec")
    richtung, stufe = _fall("loudness_jump_db", float(sprung))
    fassungen, titel = BIBLIOTHEK.get(sprache, BIBLIOTHEK["de"])
    liste = fassungen[(richtung, stufe)]
    wort = "louder" if sprung > 0 else "quieter"
    satz = liste[fassung % len(liste)].format(
        w=f"{_zahl(betrag, sprache)} dB", r=wort if sprache == "en" else richtung)
    kopf = "At" if sprache == "en" else "Bei"
    return {
        "title": (f"{titel[('loudness_jump_db', stufe)]} "
                  f"{'at' if sprache == 'en' else 'bei'} {_zeit(mid)}"),
        "description": (
            f"{kopf} {_zeit(mid)} ({_uebergangsname(t, sprache)}) {satz}"
            + ZIELSATZ[sprache].format(z=_zahl(ZIEL_PEGELSPRUNG_DB, sprache), e="dB")
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


def _uebung_beat_jitter(analysis_id: str, t: Dict, fassung: int = 0,
                        sprache: str = "de") -> Optional[Dict]:
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
    _, stufe = _fall("beat_jitter_ms", jitter)
    fassungen, titel = BIBLIOTHEK.get(sprache, BIBLIOTHEK["de"])
    liste = fassungen[("beat_jitter_ms", stufe)]
    satz = liste[fassung % len(liste)].format(w=f"{_zahl(jitter, sprache)} ms")
    kopf = "At" if sprache == "en" else "Bei"
    return {
        "title": (f"{titel[('beat_jitter_ms', stufe)]} "
                  f"{'at' if sprache == 'en' else 'bei'} {_zeit(mid)}"),
        "description": (
            f"{kopf} {_zeit(mid)} ({_uebergangsname(t, sprache)}) {satz}"
            + ZIELSATZ[sprache].format(z=_zahl(ZIEL_BEAT_JITTER_MS, sprache), e="ms")
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


# --- Die gemeinsame Auswahl- und Reihenfolge-Regel -------------------------
#
# Uebungen entstehen an ZWEI Stellen: hier je Report und in
# app/coach/profile.py ueber alle Sets, mit eigenem DE/EN-Text. Die TEXTE
# duerfen verschieden sein - "Pegel angleichen bei 17:30" und "Mixe diesen
# Uebergang neu: A -> B" sagen dasselbe an verschiedene Leser.
#
# Was NICHT zweimal existieren darf, ist die Regel: welche Groesse zaehlt, ab
# wann, mit welchem Ziel, und in welcher Reihenfolge. Am 20.08.2026 stand sie
# zweimal da, und die zweite Groesse waere fast nur im Report gelandet und im
# Coach-Panel - dem, was der Nutzer sieht - unsichtbar geblieben. Ab hier
# steht sie einmal, und beide Seiten lesen sie.
GROESSEN: Dict[str, Dict] = {
    "loudness_jump_db": {
        "schwelle": SCHWELLE_PEGELSPRUNG_DB,
        "ziel": ZIEL_PEGELSPRUNG_DB,
        # Der Pegelsprung hat eine Richtung (lauter/leiser), gemessen wird
        # der Betrag. Der Jitter ist eine Streuung und hat keine.
        "betrag": True,
    },
    "beat_jitter_ms": {
        "schwelle": SCHWELLE_BEAT_JITTER_MS,
        "ziel": ZIEL_BEAT_JITTER_MS,
        "betrag": False,
    },
}


def wert_von(t: Dict, metrik: str) -> Optional[float]:
    """Der Messwert eines Uebergangs, oder None."""
    wert = (t or {}).get(metrik)
    return float(wert) if isinstance(wert, (int, float)) else None


def ueber_der_schwelle(t: Dict, metrik: str) -> bool:
    wert = wert_von(t, metrik)
    if wert is None:
        return False
    regel = GROESSEN[metrik]
    return (abs(wert) if regel["betrag"] else wert) >= regel["schwelle"]


def unter_allen_schwellen(t: Dict) -> bool:
    """Sitzt diese Stelle - alle belegten Groessen gemessen UND unter Schwelle.

    Aufgenommen am 23.09.2026 aus tools/set_report.py. "Gemessen" ist Teil der
    Bedingung, nicht nur "unter der Schwelle": ein Uebergang ohne Pegelwert
    ist nicht sauber, sondern unbekannt, und darf nicht als Lob auftauchen.
    """
    return all(wert_von(t, m) is not None and not ueber_der_schwelle(t, m)
               for m in GROESSEN)


def sauberkeit(t: Dict) -> float:
    """Wie weit diese Stelle insgesamt von ihren Schwellen weg ist.

    Kleiner ist sauberer. Summe der Ueberschreitungen ueber alle Groessen -
    also derselbe einheitenfreie Vergleich, den ueberschreitung() begruendet.

    Bis zum 23.09.2026 rechnete set_report.py hierfuer
    `abs(pegel) + jitter / 5`. Die 5 stand nirgends begruendet; sie machte dB
    und ms per Dekret vergleichbar - genau das, wogegen ueberschreitung()
    geschrieben wurde. Eine vierte Art, dieselben zwei Zahlen zu verrechnen.
    """
    return sum(ueberschreitung(m, wert_von(t, m) or 0.0) for m in GROESSEN)


#: Ab welcher Ueberschreitung eine Stelle wie stark benannt wird.
#: Die Grenzen sind Vielfache der EIGENEN Schwelle, nicht absolute Werte -
#: nur so laesst sich 19 ms mit 4 dB vergleichen (siehe ueberschreitung).
STUFEN = ((1.00, "warnung"), (1.35, "ernst"), (1.75, "kritisch"))


def stufe(metrik: str, wert: Optional[float]) -> str:
    """Wie schwer ist diese Stelle - "gut", "warnung", "ernst", "kritisch".

    Aufgenommen am 23.09.2026. Bis dahin stand diese Einteilung in
    tools/set_report.py und rechnete dort `abs(wert) / schwelle` selbst aus -
    die DRITTE Fassung derselben Rechnung, neben ueber_der_schwelle() und
    ueberschreitung(). Sie hatte ihre eigene Schwelle als Parameter, also auch
    ihre eigene Quelle fuer 3,0 dB und 15,0 ms.

    Das ist die Bauart, an der dieses Projekt wiederholt verloren hat: eine
    Regel an zwei Stellen, und eine davon laeuft davon. Wer eine dritte
    Groesse aufnimmt, traegt sie in GROESSEN ein - und diese Funktion kann
    sie sofort einstufen, ohne dass jemand daran denken muss.
    """
    f = ueberschreitung(metrik, wert) if isinstance(wert, (int, float)) else None
    if f is None:
        return "keine"
    name = "gut"
    for grenze, benennung in STUFEN:
        if f >= grenze:
            name = benennung
    return name


def ueberschreitung(metrik: str, wert: float) -> float:
    """Um welchen Faktor liegt der Wert ueber seiner eigenen Schwelle.

    Der einzige Vergleich, der ueber Einheiten hinweg etwas heisst: 19 ms
    und 4 dB sind keine vergleichbaren Zahlen, "1,3-fach ueber der Schwelle"
    und "1,3-fach" schon.
    """
    regel = GROESSEN.get(metrik)
    if not regel or not regel["schwelle"]:
        return 0.0
    return abs(float(wert)) / regel["schwelle"]


def sortieren(eintraege: List, metrik_von, wert_von_eintrag,
              vielfalt_zuerst: bool = False) -> List:
    """Die schlimmsten zuerst, ueber Einheiten hinweg vergleichbar.

    vielfalt_zuerst=True stellt zusaetzlich die schlimmste Stelle JE GROESSE
    nach vorn. Das braucht nur, wer am Ende abschneidet: im Profil sind es
    drei Plaetze, und der Pegelsprung reicht ueber alle Aufnahmen bis zum
    3,4-fachen seiner Schwelle, der Jitter nur bis zum 1,75-fachen - ohne
    diese Regel belegte der Pegelsprung alle drei. Wer die ganze Liste zeigt
    (der Report), braucht sie nicht und faehrt besser mit "schlimmste zuerst".
    """
    geordnet = sorted(
        eintraege,
        key=lambda e: -ueberschreitung(metrik_von(e), wert_von_eintrag(e)))
    if not vielfalt_zuerst:
        return geordnet

    zuerst, danach, gesehen = [], [], set()
    for e in geordnet:
        m = metrik_von(e)
        (danach if m in gesehen else zuerst).append(e)
        gesehen.add(m)
    return zuerst + danach


def _ueberschreitung(uebung: Dict) -> float:
    """Wie ueberschreitung(), aber fuer eine fertige Uebung."""
    return ueberschreitung(uebung.get("metric") or "", uebung.get("value") or 0.0)


def baue(analysis_id: str, transitions: List[Dict],
         sprache: str = "de") -> Tuple[List[Dict], List[Dict]]:
    """(Uebungen, Beobachtungen) fuer einen Report.

    Getrennte Listen, nicht dieselbe: die Oberflaeche muss den Unterschied
    zwischen "tu das" und "das ist so" zeigen koennen.

    Findet sich nichts Belegtes, kommt eine LEERE Uebungsliste zurueck - das
    ist der Kern des Auftrags. Eine allgemeine Uebung waere schlimmer als
    keine, weil sie so aussieht, als haette das Werkzeug etwas gemessen.
    """
    uebungen: List[Dict] = []
    beobachtungen: List[Dict] = []
    versatz = _versatz(analysis_id)
    vergeben: Dict[Tuple[str, str], int] = {}
    for t in transitions or []:
        if not isinstance(t, dict):
            continue
        for metrik, bauer in (("loudness_jump_db", _uebung_pegelsprung),
                              ("beat_jitter_ms", _uebung_beat_jitter)):
            wert = wert_von(t, metrik)
            if wert is None or not ueber_der_schwelle(t, metrik):
                continue
            fall = _fall(metrik, wert)
            u = bauer(analysis_id, t, fassung=versatz + vergeben.get(fall, 0),
                      sprache=sprache)
            if u is not None:
                vergeben[fall] = vergeben.get(fall, 0) + 1
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
