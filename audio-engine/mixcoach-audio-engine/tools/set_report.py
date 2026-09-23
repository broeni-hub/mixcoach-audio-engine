# -*- coding: utf-8 -*-
"""Aus einer gespeicherten Analyse eine lesbare Report-Seite bauen (HTML).

    python -m tools.set_report <analysisId> [--titel "..."] [--datum "..."] [--aus report.html]

WOFUER
------
Der JSON-Report ist fuer die App. Wer ihn einem fremden DJ schickt, braucht
eine Seite, die ohne Erklaerung lesbar ist. Entstanden am 07.09.2026 fuer die
drei Sets von Fabi - dem ersten fremden DJ, der MixCoach benutzt hat.

DREI REGELN, DIE HIER HAENGEN
-----------------------------
1. Nur belegte Groessen urteilen. Das sind loudness_jump_db (Schwelle 3,0 dB)
   und beat_jitter_ms (15,0 ms). Alles andere ist Beschreibung und muss als
   solche gekennzeichnet sein - siehe DICHTE unten.

2. Der Uebergang ist ein FENSTER (app/audio/uebergangsfenster.py), kein Punkt.

3. Kein Uebungstext zweimal. Eine Vorlage je Groesse erzeugt bei acht
   Uebungen aus zwei Groessen denselben Satz fuenfmal - am 08.09.2026 von
   Sebastian beanstandet. Unterschieden wird nach Richtung und Schwere, der
   Zaehler laeuft ueber ALLE Reports eines Laufs.

KEINE SET-TONART IM KOPF
------------------------
Bis zum 16.09.2026 stand im Kopf eine Tonart fuer das ganze Set. Nach der
Ankerregel wurden Fabis drei Sets neu analysiert: BPM, Laenge und
Energieverlauf blieben gleich, die Tonart kippte in ALLEN drei (2A->3A,
10A->12A, 4A->9A). Sie haengt davon ab, wo Uebergaenge erkannt werden, und
beschreibt ein DJ-Set nicht. Die Tonarten je Uebergang stehen weiter in der
Tabelle - die sind lokal und ueberpruefbar.

DIE DICHTE-KACHEL
-----------------
Am 13.09.2026 fragte Fabi zurueck: "Was genau ist der Vergleichswert der
Dichte? Ist es empfohlen, schneller Tracks zu wechseln?" - Die Kachel stand
gleichrangig neben zwei belegten Groessen und nannte einen Bereich der
Vergleichs-Sets. Das liest sich als Ziel. Gemessen am 13.09. ueber 23
Aufnahmen: Dichte gegen Jitter-Median rho = -0,027, p = 0,90 - nachgerechnet
am 16.09.2026 nach der Ankerregel (Fabis Sets neu analysiert): rho = -0,094,
p = 0,67. Es gibt
keinen Zusammenhang. Die Kachel sagt das jetzt selbst.
"""
from __future__ import annotations

import argparse, json, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.coach.uebungen import (  # noqa: E402
    SCHWELLE_CAMELOT_SCHRITTE,
    SCHWELLE_ENERGIELOCH_PCT,
    _camelot_abstand,
    baue as uebungen_bauen,
    ueberschreitung,
)
from app.paths import RESULTS_DIR  # noqa: E402

SCHWELLE_PEGEL, ZIEL_PEGEL = 3.0, 1.0
SCHWELLE_JIT,  ZIEL_JIT    = 15.0, 10.0
# Referenz: die sechs fremden Profi-Sets im Bestand, gerechnet am 07.09.2026
# Die sechs fremden Profi-Sets als SPANNE, nicht als Mittelwert.
#
# Bis zum 23.09.2026 stand hier nur der Median (Pegel 1,35 dB, Jitter 10,0 ms),
# und die Skala zeichnete ihr Band von 0 bis dorthin. Alles darueber sah nach
# "schlechter als die Profis" aus. Das ist falsch: die sechs Sets streuen beim
# Jitter von 5,8 bis 11,9 ms.
#
# Ein Test-DJ schrieb dazu: "maybe I'm not a machine but I believe 10ms is
# fucking amazing". Er hatte recht. Sein Set liegt bei 11,2 ms - innerhalb der
# Spanne, besser als Dixon bei Tomorrowland (11,9). Nachgerechnet am
# 23.09.2026: der Standardfehler des Set-Medians ist ±1,8 ms, groesser als der
# angezeigte Rueckstand von 1,2 ms, und gegen KEIN einziges Referenz-Set ist
# ein Unterschied nachweisbar (Mann-Whitney, alle p > 0,09; gegen alle
# zusammen p = 0,49). Der Report zeigte also einen Rueckstand, den er nicht
# gemessen hatte.
PROFI_PEGEL_MIN, PROFI_PEGEL_MAX = 0.50, 2.00     # Joris Voorn .. RUEFUES DU SOL
PROFI_JIT_MIN, PROFI_JIT_MAX = 5.8, 11.9          # Joris Voorn .. Dixon WE2
PROFI_DICHTE_MIN, PROFI_DICHTE_MAX = 1.83, 2.94   # Be Svendsen .. Joris Voorn

# Die Uebungstexte kommen aus der Engine (app/coach/uebungen.py), nicht aus
# einer eigenen Bibliothek. Bis zum 14.09.2026 hatte dieses Werkzeug eine
# zweite - mit Saetzen wie "bevor ein Doppelschlag hoerbar wird", die die
# Engine-Tests ausdruecklich verbieten. Zwei Kopien, und eine lief davon.


def zusatz_beide(metrik, auch_gelistet, anderer_wert, sprache="de"):
    """Seiten-Anmerkung, wenn an derselben Stelle beide Groessen reissen.

    Zwei Faelle: steht die zweite Groesse ebenfalls in der angezeigten Liste,
    kann man darauf verweisen. Wurde sie beim Abschneiden weggelassen, muss
    der Wert genannt werden - sonst behauptet der Satz eine Zeile, die es
    nicht gibt.
    """
    T = TEXTE.get(sprache, TEXTE["de"])
    andere = T["a_pegel"] if metrik == "beat_jitter_ms" else T["a_jitter"]
    if auch_gelistet:
        return T["zusatz_gelistet"].format(a=andere)
    return T["zusatz_offen"].format(a=andere, w=anderer_wert)


CSS = """
:root{
  color-scheme: light;
  --grund:#f7f7f5; --blatt:#ffffff; --senke:#eeefec;
  --linie:#e4e6e2; --linie-stark:#d8dbd6;
  --ink:#15181a; --ink-2:#3c4245; --ink-3:#5c6469;
  --akzent:#0f6e6e; --akzent-flaeche:rgba(15,110,110,.13);
  --gut:#0ca30c; --warnung:#fab219; --ernst:#ec835a; --kritisch:#d03b3b;
  --schatten:0 1px 2px rgba(20,30,30,.06), 0 6px 16px -8px rgba(20,30,30,.14);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --grund:#15181a; --blatt:#1c2023; --senke:#22272a;
    --linie:#2c3236; --linie-stark:#3a4145;
    --ink:#f7f7f5; --ink-2:#c9cfd2; --ink-3:#9aa3a8;
    --akzent:#2a9d9d; --akzent-flaeche:rgba(42,157,157,.18);
    --schatten:0 1px 2px rgba(0,0,0,.4), 0 6px 18px -8px rgba(0,0,0,.6);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --grund:#15181a; --blatt:#1c2023; --senke:#22272a;
  --linie:#2c3236; --linie-stark:#3a4145;
  --ink:#f7f7f5; --ink-2:#c9cfd2; --ink-3:#9aa3a8;
  --akzent:#2a9d9d; --akzent-flaeche:rgba(42,157,157,.18);
  --schatten:0 1px 2px rgba(0,0,0,.4), 0 6px 18px -8px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
body{background:var(--grund); color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.6; margin:0; -webkit-font-smoothing:antialiased;}
.blatt{max-width:940px; margin:0 auto; padding:clamp(20px,4vw,52px) clamp(16px,4vw,40px) 72px}
h1,h2{font-family:Archivo,"IBM Plex Sans",sans-serif; text-wrap:balance; margin:0}
h1{font-size:clamp(28px,5.2vw,44px); font-weight:700; letter-spacing:-.022em; line-height:1.08}
h2{font-size:clamp(17px,2.4vw,21px); font-weight:600; letter-spacing:-.01em}
p{margin:0}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums}
.marke{font-family:"IBM Plex Mono",monospace; font-size:10.5px; font-weight:500;
  letter-spacing:.13em; text-transform:uppercase; color:var(--ink-3);}
.kopf{border-bottom:1px solid var(--linie-stark); padding-bottom:24px; margin-bottom:26px}
.kopf .zeile{display:flex; flex-wrap:wrap; gap:10px 18px; align-items:baseline; justify-content:space-between}
.kopf .quelle{margin-top:6px}
.stammdaten{display:flex; flex-wrap:wrap; margin-top:22px;
  border:1px solid var(--linie); border-radius:3px; overflow:hidden;}
.stammdaten div{flex:1 1 100px; padding:10px 14px; background:var(--blatt); border-right:1px solid var(--linie);}
.stammdaten div:last-child{border-right:0}
.stammdaten dt{display:block; margin-bottom:3px}
.stammdaten dd{margin:0; font-size:17px; font-weight:600}
section{margin-top:44px}
.sektionskopf{display:flex; align-items:baseline; gap:12px; margin-bottom:6px}
.sektionskopf .nr{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--akzent);
  font-weight:600; border:1px solid var(--akzent); border-radius:2px; padding:1px 5px; flex:none;}
.hinweis{color:var(--ink-2); max-width:66ch; margin-top:4px}
.urteil{background:var(--blatt); border-left:3px solid var(--akzent);
  border-radius:0 4px 4px 0; padding:20px 24px; box-shadow:var(--schatten); margin-top:0;}
.urteil p{font-size:17px; line-height:1.55; max-width:64ch}
.urteil p + p{margin-top:12px; font-size:15px; color:var(--ink-2)}
.kacheln{display:grid; grid-template-columns:repeat(auto-fit,minmax(238px,1fr)); gap:14px}
.kachel{background:var(--blatt); border:1px solid var(--linie); border-radius:4px;
  padding:18px 18px 16px; box-shadow:var(--schatten);}
/* Beschreibung statt Bewertung: sichtbar anderer Rang als die belegten Groessen */
.kachel.beschreibung{background:transparent; border-style:dashed; box-shadow:none}
.kachel.beschreibung .wert{color:var(--ink-2)}
.kachel .wert{font-size:34px; font-weight:600; line-height:1.05; letter-spacing:-.02em}
.kachel .wert .einheit{font-size:15px; font-weight:500; color:var(--ink-3); margin-left:3px}
.kachel .unter{color:var(--ink-2); font-size:13.5px; margin-top:8px; line-height:1.5}
.kachel .marke{margin-bottom:9px; display:block}
.skala{margin-top:14px}
.skala .spur{position:relative; height:7px; background:var(--senke); border-radius:4px; overflow:hidden;}
.skala .band{position:absolute; top:0; bottom:0; background:var(--akzent-flaeche)}
.skala .fuellung{position:absolute; top:0; bottom:0; left:0; border-radius:4px}
.skala .schwelle{position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--ink)}
.skala .legende{display:flex; justify-content:space-between; gap:8px; margin-top:6px; font-size:11px; color:var(--ink-3);}
.achse-rahmen{background:var(--blatt); border:1px solid var(--linie); border-radius:4px;
  padding:20px 20px 12px; box-shadow:var(--schatten); overflow-x:auto;}
.achse-innen{min-width:520px}
.energie{position:relative; height:66px; margin-bottom:3px}
.energie svg{display:block; width:100%; height:100%}
.spuren{position:relative; display:flex; flex-direction:column; gap:3px}
.spur-reihe{position:relative; height:19px}
.fenster{position:absolute; top:0; height:19px; border-radius:3px;
  display:flex; align-items:center; padding:0 5px; overflow:hidden;
  font-family:"IBM Plex Mono",monospace; font-size:10.5px; font-weight:600;
  color:#fff; cursor:default; min-width:15px;}
.fenster:focus-visible{outline:2px solid var(--akzent); outline-offset:2px}
.f-gut{background:var(--gut)} .f-warnung{background:#b07d0a}
.f-ernst{background:#c05f34} .f-kritisch{background:var(--kritisch)} .f-keine{background:var(--ink-3)}
.zeitleiste{position:relative; height:20px; margin-top:7px; border-top:1px solid var(--linie-stark);}
.zeitleiste span{position:absolute; top:4px; transform:translateX(-50%);
  font-family:"IBM Plex Mono",monospace; font-size:10px; color:var(--ink-3);}
.zeitleiste span::before{content:""; position:absolute; top:-5px; left:50%; width:1px; height:4px; background:var(--linie-stark);}
.achse-legende{display:flex; flex-wrap:wrap; gap:8px 16px; margin-top:16px;
  padding-top:13px; border-top:1px solid var(--linie); font-size:12px; color:var(--ink-2);}
.achse-legende b{display:inline-flex; align-items:center; gap:6px; font-weight:500}
.punkt{width:9px; height:9px; border-radius:2px; flex:none}
.tabellen-rahmen{overflow-x:auto; border:1px solid var(--linie); border-radius:4px; background:var(--blatt)}
table{border-collapse:collapse; width:100%; min-width:560px; font-size:13.5px}
th,td{padding:9px 13px; text-align:left; border-bottom:1px solid var(--linie)}
thead th{background:var(--senke); font-family:"IBM Plex Mono",monospace; font-size:10.5px;
  letter-spacing:.09em; text-transform:uppercase; color:var(--ink-3);
  font-weight:500; white-space:nowrap; position:sticky; top:0;}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap}
.chip{display:inline-flex; align-items:center; gap:5px; white-space:nowrap;
  font-family:"IBM Plex Mono",monospace; font-size:11.5px; font-weight:600;}
.chip .punkt{width:8px; height:8px; border-radius:50%}
.c-gut{color:var(--gut)} .c-warnung{color:#8a6206} .c-ernst{color:#a94f28} .c-kritisch{color:var(--kritisch)}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .c-warnung{color:var(--warnung)}
  :root:not([data-theme="light"]) .c-ernst{color:var(--ernst)}
}
:root[data-theme="dark"] .c-warnung{color:var(--warnung)}
:root[data-theme="dark"] .c-ernst{color:var(--ernst)}
.korrektur{background:var(--blatt); border:1px solid var(--linie-stark);
  border-radius:4px; padding:16px 20px; margin:0 0 22px;}
.korrektur .marke{display:block; margin-bottom:6px; color:var(--akzent)}
.korrektur p{font-size:14px; color:var(--ink-2); line-height:1.55; max-width:70ch}
.korrektur p + p{margin-top:8px}
.korrektur ul{margin:8px 0 0; padding-left:18px; display:flex; flex-direction:column; gap:4px}
.korrektur li{font-size:13.5px; color:var(--ink-2); line-height:1.5}
.korrektur b{color:var(--ink); font-weight:600}
.muster{background:var(--blatt); border:1px solid var(--linie); border-left:3px solid var(--akzent);
  border-radius:0 4px 4px 0; padding:13px 16px; margin-bottom:14px;
  font-size:13.5px; color:var(--ink-2); line-height:1.55;}
.muster b{color:var(--ink)}
.gut{background:var(--blatt); border:1px solid var(--linie); border-left:3px solid var(--gut);
  border-radius:0 4px 4px 0; padding:18px 22px; box-shadow:var(--schatten);}
.gut p{font-size:15px; color:var(--ink-2); line-height:1.55; max-width:68ch}
.gut p b{color:var(--ink)}
.beobachtungen{display:flex; flex-direction:column; gap:1px; border:1px solid var(--linie);
  border-radius:4px; overflow:hidden; background:var(--linie)}
.beob{display:grid; grid-template-columns:auto auto 1fr; gap:14px; align-items:baseline;
  padding:10px 16px; background:var(--blatt); font-size:13.5px; color:var(--ink-2)}
.beob .zeit{color:var(--akzent); font-weight:600; font-size:12.5px; white-space:nowrap}
.uebungen{display:flex; flex-direction:column; gap:11px}
.uebung{background:var(--blatt); border:1px solid var(--linie); border-radius:4px;
  padding:15px 17px; display:grid; grid-template-columns:auto 1fr; gap:3px 15px;
  align-items:baseline; box-shadow:var(--schatten);}
.uebung .zeit{font-family:"IBM Plex Mono",monospace; font-weight:600; font-size:13px;
  color:var(--akzent); grid-row:span 2; align-self:center; white-space:nowrap;}
.uebung .was{font-weight:600}
.uebung .wie{color:var(--ink-2); font-size:13.5px; line-height:1.5}
.grenzen{background:var(--senke); border:1px solid var(--linie); border-radius:4px; padding:20px 22px;}
.grenzen ul{margin:12px 0 0; padding-left:19px; display:flex; flex-direction:column; gap:9px}
.grenzen li{color:var(--ink-2); font-size:13.5px; line-height:1.55; max-width:70ch}
.grenzen li b{color:var(--ink); font-weight:600}
.fuss{margin-top:40px; padding-top:18px; border-top:1px solid var(--linie);
  font-size:12px; color:var(--ink-3); display:flex; flex-wrap:wrap; gap:6px 18px; justify-content:space-between;}
#tip{position:fixed; z-index:20; background:var(--ink); color:var(--grund);
  padding:7px 10px; border-radius:4px; font-size:12px; line-height:1.45;
  pointer-events:none; opacity:0; transition:opacity .12s; max-width:250px;
  font-family:"IBM Plex Mono",monospace; box-shadow:0 4px 14px rgba(0,0,0,.3);}
@media (prefers-reduced-motion:reduce){*{transition:none!important; animation:none!important}}
"""

# --- Seitentexte je Sprache -----------------------------------------------
# Die Uebungstexte kommen aus app/coach/uebungen.py und sind dort zweisprachig.
# Hier stehen nur die Texte der SEITE.
TEXTE = {
 "de": {
  "marke": "MixCoach · Set-Analyse", "laenge": "Länge", "uebergaenge": "Übergänge",
  "tempo": "Grundtempo", "min": "min", "minuten": "Minuten", "je10": "/10&nbsp;min",
  "h1": "Die zwei Zahlen, die belegt sind",
  "hinweis1": ("MixCoach misst viel und belegt zwei Größen: den Pegelsprung am Übergang "
    "und den Beat-Jitter im Blend. Nur diese beiden hängen nachweisbar mit dem menschlichen "
    "Urteil zusammen — alles andere steht weiter unten unter „Was hier nicht drinsteht“."),
  "k_pegel": "Pegelsprung · Median", "k_jitter": "Beat-Jitter · Median",
  "k_dichte": "Wechseldichte · keine Bewertung",
  "u_pegel": "<b>{a} von {b}</b> Übergängen ({p}&nbsp;%) springen um mehr als 3 dB. Größter Sprung: {m} dB.",
  "u_jitter": "<b>{a} von {b}</b> Übergängen ({p}&nbsp;%) reißen die 15-ms-Schwelle. Schlechtester Wert: {m} ms.",
  "u_dichte": ("Ein Trackwechsel etwa alle {t} Minuten. <b>Das ist eine Beschreibung, kein Ziel.</b> "
    "Über 23 Aufnahmen gemessen, hängt die Dichte nicht mit der Qualität zusammen "
    "(ρ&nbsp;=&nbsp;−0,09, p&nbsp;=&nbsp;0,67). Die Vergleichs-Sets reichen von {dmin} "
    "(Four Tet, Be Svendsen) bis {dmax} (Joris Voorn) — beide Enden sind Weltklasse."),
  "skala_pegel_l": "Vergleichs-Sets 0,5–2,0 dB", "skala_pegel_r": "Schwelle 3 dB",
  "skala_jitter_l": "Vergleichs-Sets 5,8–11,9 ms", "skala_jitter_r": "Schwelle 15 ms",
  "h_gut": "Was schon sitzt",
  "gut_satz": ("<b>{a} von {b}</b> Übergängen liegen bei beiden Größen innerhalb ihrer Linie — "
    "kein Pegelsprung über 3&nbsp;dB, kein Jitter über 15&nbsp;ms."),
  "gut_bester": ("Am saubersten ist {name} im Fenster {fenster}: {pegel}&nbsp;dB Pegelunterschied "
    "und {jitter}&nbsp;ms Streuung. Das ist die Stelle, an der du hören kannst, wie es klingt, "
    "wenn es sitzt."),
  "h_beob": "Aufgefallen, aber nicht bewertet",
  "beob_satz": ("Diese Stellen sind gemessen, aber es ist <b>nicht belegt</b>, dass sie stören — "
    "der Zusammenhang mit dem Höreindruck ist zu schwach (ρ&nbsp;=&nbsp;+0,05). Sie stehen hier "
    "als Beobachtung, nicht als Aufgabe."),
  "beob_camelot": "{schritte} Schritte auf dem Camelot-Rad",
  "beob_energie": "Energie fällt um {wert}&nbsp;%",
  "h2": "Wo im Set du hinhören musst",
  "hinweis2": ("Jeder Balken ist ein Übergang — als <b>Zeitfenster</b>, nicht als Sekundenangabe. "
    "Das ist Absicht: Die Erkennung trifft den exakten Punkt nur selten, das Fenster von "
    "110 Sekunden enthält den echten Übergang in 73&nbsp;% der Fälle. Die Kurve dahinter ist der "
    "Energieverlauf. Farbe und Zahl sagen dasselbe — die Zahl gilt."),
  "svg_alt": "Energieverlauf über das Set",
  "l_gut": "im Rahmen", "l_warn": "knapp über der Schwelle", "l_ernst": "deutlich drüber",
  "l_krit": "weit drüber", "l_zahl": "Zahl im Balken: Nummer des Übergangs",
  "h3": "Alle Übergänge im Einzelnen",
  "th": ("Nr", "Fenster", "Pegelsprung", "Beat-Jitter", "Tonart"),
  "lauter": " lauter", "leiser": " leiser",
  "tip_pegel": "Pegelsprung", "tip_jitter": "Jitter",
  "h4": "Was sich üben lässt",
  "hinweis4": ("Nur Stellen, an denen eine belegte Größe ihre Schwelle reißt. "
    "Jede Zeile nennt den gemessenen Wert aus <em>diesem</em> Set."),
  "leer": ("<div class=\"uebung\"><div class=\"zeit\">–</div><div class=\"was\">Keine Stelle über der "
    "Schwelle.</div><div class=\"wie\">Weder Pegelsprung noch Beat-Jitter überschreiten in "
    "diesem Set ihre belegte Schwelle.</div></div>"),
  "m_stellen": "{n} Stellen über der Schwelle: ", "m_jit": "<b>{n}×</b> Beat-Jitter",
  "m_peg": "<b>{n}×</b> Pegelsprung", "m_und": " und ",
  "m_rest1": " Eine weitere Stelle ist hier nicht aufgeführt.",
  "m_restn": " Weitere {n} Stellen sind hier nicht aufgeführt.",
  "m_sortiert": (" Die Liste steht nach Schwere, gemessen als Vielfaches der jeweiligen "
    "Schwelle — so sind dB und ms vergleichbar."),
  "lage": " Und alle {n} {was}{zus} liegen in der {haelfte} Hälfte des Sets.",
  "lage_jit": "Jitter-Stellen", "lage_peg": "Pegel-Stellen",
  "lage_erste": "ersten", "lage_zweite": "zweiten",
  "lage_zus1": " über der Schwelle — die hier nicht aufgeführte eingeschlossen —",
  "lage_zusn": " über der Schwelle — die hier nicht aufgeführten eingeschlossen —",
  "h5": "Was hier nicht drinsteht",
  "grenzen_kopf": "MixCoach zeigt nichts an, was nicht gemessen wurde. Für dieses Set heißt das konkret:",
  "g_namen": ("<b>Keine Tracknamen.</b> Die Trackerkennung vergleicht gegen die Sammlung im "
    "Fingerabdruck-Index. Tracks, die dort nicht liegen, bleiben unbenannt — und Treffer, "
    "die nur knapp an der Erkennungsschwelle liegen, zeigt diese Seite bewusst nicht an. "
    "<b>Mit einer Tracklist</b> — eine Zeile je Track, Zeiten wenn vorhanden — stünden hier Namen."),
  "g_eq": ("<b>Nichts zu EQ, Frequenzbild, Timing oder Kreativität.</b> Ob sich Bässe oder "
    "Höhen im Blend beißen, wird heute nicht gemessen: Die vorhandene Bass-Messung "
    "braucht beide Tracks aus der Sammlung und ist fast immer entweder 0 oder 100 — "
    "ein Schalter, keine Abstufung. Gegen Hörurteile belegt ist sie nicht. "
    "Daraus einen Rat abzuleiten hieße raten."),
  "g_fenster": ("<b>Das Fenster ist ein Fenster.</b> Die 110 Sekunden enthalten den echten "
    "Übergang in 73&nbsp;% der Fälle — nicht in allen. Bei etwa jedem vierten Balken "
    "liegt der Übergang daneben."),
  "g_vergleich": ("<b>Der Vergleich hat eine Schwäche.</b> Die sechs Referenz-Sets (Dixon, Four Tet, "
    "Joris Voorn, RÜFÜS DU SOL, Be Svendsen) sind veröffentlichte Festival-Mitschnitte "
    "und damit gemastert. Mastering drückt Pegelsprünge. Beim <em>Pegel</em> ist der "
    "Vergleich deshalb zu deinen Ungunsten verzerrt; beim <em>Beat-Jitter</em> "
    "nicht — den ändert kein Mastering."),
  "fuss_id": "Analyse-ID", "fuss_ver": "Scoring-Version",
  "korr_marke": "Korrigierte Fassung · {d}",
  "zusatz_gelistet": " An dieser Stelle reißt auch {a} — sie steht deshalb zweimal in der Liste.",
  "zusatz_offen": " An diesem Übergang liegt zusätzlich {a} über der Schwelle ({w}).",
  "a_pegel": "der Pegelsprung", "a_jitter": "der Beat-Jitter",
 },
 "en": {
  "marke": "MixCoach · Set analysis", "laenge": "Length", "uebergaenge": "Transitions",
  "tempo": "Base tempo", "min": "min", "minuten": "minutes", "je10": "/10&nbsp;min",
  "h1": "The two numbers that are backed by evidence",
  "hinweis1": ("MixCoach measures a lot and can back up two of it: the level jump at the "
    "transition and the beat jitter inside the blend. Only these two correlate with human "
    "judgement — everything else is listed below under \u201cWhat is not in here\u201d."),
  "k_pegel": "Level jump · median", "k_jitter": "Beat jitter · median",
  "k_dichte": "Change rate · not a rating",
  "u_pegel": "<b>{a} of {b}</b> transitions ({p}&nbsp;%) jump by more than 3 dB. Largest jump: {m} dB.",
  "u_jitter": "<b>{a} of {b}</b> transitions ({p}&nbsp;%) cross the 15 ms line. Worst value: {m} ms.",
  "u_dichte": ("A track change roughly every {t} minutes. <b>This describes, it does not rate.</b> "
    "Measured across 23 recordings, change rate does not correlate with quality "
    "(ρ&nbsp;=&nbsp;−0.09, p&nbsp;=&nbsp;0.67). The reference sets range from {dmin} "
    "(Four Tet, Be Svendsen) to {dmax} (Joris Voorn) — both ends are world class."),
  "skala_pegel_l": "Reference sets 0.5–2.0 dB", "skala_pegel_r": "Line at 3 dB",
  "skala_jitter_l": "Reference sets 5.8–11.9 ms", "skala_jitter_r": "Line at 15 ms",
  "h_gut": "What already works",
  "gut_satz": ("<b>{a} of {b}</b> transitions sit inside the line on both measures — no level jump "
    "over 3&nbsp;dB, no jitter over 15&nbsp;ms."),
  "gut_bester": ("The cleanest is {name} in the window {fenster}: {pegel}&nbsp;dB of level "
    "difference and {jitter}&nbsp;ms of spread. That is the one to listen back to when you want "
    "to hear what it sounds like when it lands."),
  "h_beob": "Noticed, but not rated",
  "beob_satz": ("These places are measured, but it is <b>not established</b> that they bother "
    "anyone — the link to how a mix is heard is too weak (ρ&nbsp;=&nbsp;+0.05). They are here as "
    "observations, not as tasks."),
  "beob_camelot": "{schritte} steps on the Camelot wheel",
  "beob_energie": "energy drops by {wert}&nbsp;%",
  "h2": "Where in the set to listen",
  "hinweis2": ("Every bar is one transition — shown as a <b>time window</b>, not as a timestamp. "
    "That is deliberate: detection rarely hits the exact point, and this 110-second window "
    "contains the real transition in 73&nbsp;% of cases. The curve behind it is the energy "
    "over the set. Colour and number say the same thing — the number is what counts."),
  "svg_alt": "Energy across the set",
  "l_gut": "within range", "l_warn": "just over the line", "l_ernst": "clearly over",
  "l_krit": "far over", "l_zahl": "Number in the bar: transition number",
  "h3": "Every transition in detail",
  "th": ("No", "Window", "Level jump", "Beat jitter", "Key"),
  "lauter": " louder", "leiser": " quieter",
  "tip_pegel": "Level jump", "tip_jitter": "Jitter",
  "h4": "What to practise",
  "hinweis4": ("Only places where a backed-up measure crosses its line. "
    "Every row quotes the value measured in <em>this</em> set."),
  "leer": ("<div class=\"uebung\"><div class=\"zeit\">–</div><div class=\"was\">Nothing crossed a "
    "line.</div><div class=\"wie\">Neither level jump nor beat jitter crosses its backed-up "
    "threshold anywhere in this set.</div></div>"),
  "m_stellen": "{n} places over the line: ", "m_jit": "<b>{n}×</b> beat jitter",
  "m_peg": "<b>{n}×</b> level jump", "m_und": " and ",
  "m_rest1": " One further place is not listed here.",
  "m_restn": " A further {n} places are not listed here.",
  "m_sortiert": (" The list runs by severity, measured as a multiple of each measure's own "
    "line — that makes dB and ms comparable."),
  "lage": " And all {n} {was}{zus} fall in the {haelfte} half of the set.",
  "lage_jit": "jitter places", "lage_peg": "level places",
  "lage_erste": "first", "lage_zweite": "second",
  "lage_zus1": " over the line — including the one not listed here —",
  "lage_zusn": " over the line — including those not listed here —",
  "h5": "What is not in here",
  "grenzen_kopf": "MixCoach shows nothing it has not measured. For this set that means:",
  "g_namen": ("<b>No track names.</b> Track recognition compares against the collection in the "
    "fingerprint index. Tracks that are not in it stay unnamed — and matches that sit just at "
    "the recognition threshold are deliberately not shown on this page. "
    "<b>With a tracklist</b> — one line per track, times if you have them — names would appear here."),
  "g_eq": ("<b>Nothing on EQ, frequency balance, timing or creativity.</b> Whether bass or highs "
    "clash inside a blend is not measured today: the existing bass measurement needs both "
    "tracks from the collection and is almost always either 0 or 100 — a switch, not a scale. "
    "It has not been validated against listening judgements. "
    "Deriving advice from it would mean guessing."),
  "g_fenster": ("<b>The window is a window.</b> Those 110 seconds contain the real transition in "
    "73&nbsp;% of cases — not in all. For roughly one bar in four the transition sits outside it."),
  "g_vergleich": ("<b>The comparison has a weakness.</b> The six reference sets (Dixon, Four Tet, "
    "Joris Voorn, RÜFÜS DU SOL, Be Svendsen) are released festival recordings and therefore "
    "mastered. Mastering flattens level jumps. On <em>level</em> the comparison is skewed "
    "against you; on <em>beat jitter</em> it is not — mastering does not change that."),
  "fuss_id": "Analysis ID", "fuss_ver": "Scoring version",
  "korr_marke": "Corrected version · {d}",
  "zusatz_gelistet": " {a} crosses its line at this same place — which is why it appears twice in the list.",
  "zusatz_offen": " At this transition {a} is over its line as well ({w}).",
  "a_pegel": "the level jump", "a_jitter": "beat jitter",
 },
}


def z(s):
    if s is None: return "–"
    s = int(s); return f"{s//60}:{s%60:02d}"

def _fmt(v, n=1, sprache="de"):
    """Zahl mit n Nachkommastellen - Komma im Deutschen, Punkt im Englischen."""
    if v is None:
        return "–"
    text = f"{v:.{n}f}"
    return text.replace(".", ",") if sprache == "de" else text


def zahl(v, n=1):
    """Deutsch - fuer Aufrufer ausserhalb von baue()."""
    return _fmt(v, n, "de")

def stufe(wert, schwelle):
    if wert is None: return "keine"
    f = abs(wert) / schwelle
    return "gut" if f < 1.0 else "warnung" if f < 1.35 else "ernst" if f < 1.75 else "kritisch"

def _spuren_verteilen(fenster):
    reihen = []
    for f in sorted(fenster, key=lambda x: x["von"]):
        for r in reihen:
            if f["von"] >= r[-1]["bis"] + 8:
                r.append(f); break
        else:
            reihen.append([f])
    return reihen

def _energie_pfad(d, breite=1000, hoehe=66):
    vals = [p["value"] for p in (d.get("energyCurve") or [])]
    if not vals: return "", ""
    lo, hi = min(vals), max(vals); spanne = (hi - lo) or 1; n = len(vals)
    pts = [(i/(n-1)*breite, hoehe - ((v-lo)/spanne)*(hoehe-6) - 3) for i, v in enumerate(vals)]
    linie = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return linie, linie + f" L{breite},{hoehe} L0,{hoehe} Z"

def _skala(wert, schwelle, ref_min, ref_max, max_x, links, rechts):
    """Der Wert auf einer Skala, mit dem Referenzband der sechs Profi-Sets.

    Das Band ist deren SPANNE, nicht ihr Mittelwert - sonst liest sich jeder
    Wert oberhalb des Mittelwerts als Rueckstand, obwohl er zwischen den
    Profis liegen kann (siehe PROFI_JIT_MIN/MAX).
    """
    if wert is None: return ""
    farbe = {"gut":"var(--gut)","warnung":"#b07d0a","ernst":"#c05f34",
             "kritisch":"var(--kritisch)"}[stufe(wert, schwelle)]
    von, breite = min(ref_min/max_x*100, 100), min((ref_max-ref_min)/max_x*100, 100)
    return (f'<div class="skala"><div class="spur">'
            f'<div class="band" style="left:{von:.1f}%;width:{breite:.1f}%"></div>'
            f'<div class="fuellung" style="width:{min(wert/max_x*100,100):.1f}%;background:{farbe}"></div>'
            f'<div class="schwelle" style="left:{min(schwelle/max_x*100,100):.1f}%"></div></div>'
            f'<div class="legende"><span>{links}</span><span>{rechts}</span></div></div>')

def baue(report: dict, titel: str, datum: str, quelle: str, urteil=None,
         korrektur=None, sprache: str = "de") -> str:
    """Die Report-Seite als HTML.

    korrektur: optional (datum, einleitung, [aenderungen]). Eine Seite, die ein
    Leser schon in einer frueheren Fassung kennt, sagt offen, was sich
    geaendert hat - sonst widerspricht sie stillschweigend dem, was er
    gelesen hat.
    """
    T = TEXTE.get(sprache, TEXTE["de"])
    # Lokal an die Sprache gebunden - alle Aufrufe unten bleiben zahl(...).
    zahl = lambda v, n=1: _fmt(v, n, sprache)  # noqa: E731
    ts = report["setTransitions"]
    dur = report.get("totalDurationSec") or 0
    pj = [abs(t["loudness_jump_db"]) for t in ts if isinstance(t.get("loudness_jump_db"), (int, float))]
    bj = [t["beat_jitter_ms"] for t in ts if isinstance(t.get("beat_jitter_ms"), (int, float))]
    n = len(ts)

    rang = {"gut":0,"warnung":1,"ernst":2,"kritisch":3,"keine":-1}
    fenster = []
    for t in ts:
        w = t.get("window") or {}
        if w.get("vonSec") is None: continue
        sp, sj = stufe(t.get("loudness_jump_db"), SCHWELLE_PEGEL), stufe(t.get("beat_jitter_ms"), SCHWELLE_JIT)
        fenster.append({"i":t.get("index"), "von":w["vonSec"], "bis":w["bisSec"],
                        "stufe": sp if rang[sp] >= rang[sj] else sj,
                        "pegel":t.get("loudness_jump_db"), "jit":t.get("beat_jitter_ms")})
    spuren = []
    for reihe in _spuren_verteilen(fenster):
        st = []
        for f in reihe:
            tip = (f"Übergang {f['i']} · {z(f['von'])}–{z(f['bis'])}\n"
                   f"{T['tip_pegel']} {zahl(f['pegel'])} dB · {T['tip_jitter']} {zahl(f['jit'])} ms")
            st.append(f'<div class="fenster f-{f["stufe"]}" style="left:{f["von"]/dur*100:.2f}%;'
                      f'width:{max((f["bis"]-f["von"])/dur*100,1.1):.2f}%" tabindex="0" '
                      f'data-tip="{tip}">{f["i"]}</div>')
        spuren.append(f'<div class="spur-reihe">{"".join(st)}</div>')
    marken = "".join(f'<span style="left:{m*60/dur*100:.2f}%">{m}′</span>'
                     for m in range(0, int(dur//60)+1, 10))
    linie, flaeche = _energie_pfad(report)

    zeilen = []
    for t in ts:
        w = t.get("window") or {}
        p, j = t.get("loudness_jump_db"), t.get("beat_jitter_ms")
        r = (T["lauter"] if p > 0 else T["leiser"] if p < 0 else "") if isinstance(p,(int,float)) else ""
        zeilen.append(
          f'<tr><td class="num">{t.get("index")}</td>'
          f'<td class="num">{z(w.get("vonSec"))}–{z(w.get("bisSec"))}</td>'
          f'<td class="num"><span class="chip c-{stufe(p,SCHWELLE_PEGEL)}">'
          f'<span class="punkt" style="background:currentColor"></span>'
          f'{zahl(abs(p)) if isinstance(p,(int,float)) else "–"} dB</span>'
          f'<span style="color:var(--ink-3)">{r}</span></td>'
          f'<td class="num"><span class="chip c-{stufe(j,SCHWELLE_JIT)}">'
          f'<span class="punkt" style="background:currentColor"></span>{zahl(j)} ms</span></td>'
          f'<td class="num" style="color:var(--ink-3)">'
          f'{t.get("camelot_before") or "–"} → {t.get("camelot_after") or "–"}</td></tr>')

    # Uebungen aus der Engine - dieselbe Regel, derselbe Wortlaut wie in der App.
    je_index = {t.get("index"): t for t in ts}
    roh = []
    for u in uebungen_bauen(report.get("id") or "", ts, sprache=sprache)[0]:
        t = je_index.get(u.get("transitionIndex")) or {}
        w = t.get("window") or {}
        roh.append({"faktor": ueberschreitung(u["metric"], u["value"]), "wert": u["value"],
                    "feld": u["metric"], "idx": u.get("transitionIndex"),
                    "mid": t.get("mid_sec") or w.get("vonSec"),
                    "zeit": f'{z(w.get("vonSec"))}–{z(w.get("bisSec"))}',
                    "titel": u["title"], "text": u["description"], "ziel": u["target"]})
    gezeigt = roh[:8]   # baue() sortiert bereits nach Ueberschreitung

    def partner(e):
        return next((x for x in roh if x["idx"] == e["idx"] and x["feld"] != e["feld"]), None)

    uebungen = []
    for e in gezeigt:
        txt = e["text"]
        p = partner(e)
        if p is not None:
            eh = "ms" if p["feld"] == "beat_jitter_ms" else "dB"
            txt += zusatz_beide(e["feld"], p in gezeigt, f'{zahl(abs(p["wert"]))} {eh}', sprache)
        eh = "ms" if e["feld"] == "beat_jitter_ms" else "dB"
        uebungen.append(
          f'<div class="uebung"><div class="zeit">{e["zeit"]}</div>'
          f'<div class="was">{e["titel"]} '
          f'<span class="mono" style="color:var(--ink-3);font-weight:500">· '
          f'{zahl(abs(e["wert"]))} {eh} → {"Target" if sprache == "en" else "Ziel"} {zahl(e["ziel"])} {eh}</span></div>'
          f'<div class="wie">{txt}</div></div>')

    # Was schon sitzt - gemessen, und im Report bis zum 23.09.2026 unsichtbar.
    # Ein Test-DJ wuenschte sich "more tips" und einen ermutigenderen Ton; das
    # Gute stand nirgends, obwohl es gemessen ist.
    sauber = [t for t in ts
              if isinstance(t.get("loudness_jump_db"), (int, float))
              and abs(t["loudness_jump_db"]) < SCHWELLE_PEGEL
              and isinstance(t.get("beat_jitter_ms"), (int, float))
              and t["beat_jitter_ms"] < SCHWELLE_JIT]
    gut_html = ""
    if sauber:
        bester = min(sauber, key=lambda t: abs(t["loudness_jump_db"]) + t["beat_jitter_ms"] / 5)
        bw = bester.get("window") or {}
        name = (bester.get("track_in") or bester.get("track_out")
                or f'{"Transition" if sprache == "en" else "Übergang"} {bester.get("index")}')
        bester_text = T["gut_bester"].format(
            name=name, fenster=f'{z(bw.get("vonSec"))}–{z(bw.get("bisSec"))}',
            pegel=zahl(abs(bester["loudness_jump_db"])), jitter=zahl(bester["beat_jitter_ms"]))
        gut_html = (f'<p>{T["gut_satz"].format(a=len(sauber), b=len(ts))}</p>'
                    f'<p style="margin-top:10px">{bester_text}</p>')

    # Beobachtungen: gemessen, aber nicht belegt. Kompakt aus den Rohdaten,
    # nicht aus den Engine-Saetzen - die gibt es nur auf Deutsch.
    beob = []
    for t in ts:
        w = t.get("window") or {}
        fenster = f'{z(w.get("vonSec"))}–{z(w.get("bisSec"))}'
        d_cam = _camelot_abstand(t.get("camelot_before"), t.get("camelot_after"))
        if d_cam is not None and d_cam >= SCHWELLE_CAMELOT_SCHRITTE:
            beob.append((fenster, f'{t.get("camelot_before")} → {t.get("camelot_after")}',
                         T["beob_camelot"].format(schritte=d_cam)))
        loch = t.get("energy_dip_pct")
        if isinstance(loch, (int, float)) and loch >= SCHWELLE_ENERGIELOCH_PCT:
            beob.append((fenster, "", T["beob_energie"].format(wert=zahl(float(loch)))))
    beob_html = ""
    if beob:
        zeilen_b = "".join(
            f'<div class="beob"><span class="zeit mono">{f}</span>'
            f'<span class="mono" style="color:var(--ink-3)">{was}</span>'
            f'<span>{txt}</span></div>' for f, was, txt in beob)
        beob_html = (f'<section><div class="sektionskopf"><span class="nr">06</span>'
                     f'<h2>{T["h_beob"]}</h2></div>'
                     f'<p class="hinweis">{T["beob_satz"]}</p>'
                     f'<div class="beobachtungen" style="margin-top:16px">{zeilen_b}</div></section>')

    lage = ""
    for feld, nm in (("beat_jitter_ms", T["lage_jit"]), ("loudness_jump_db", T["lage_peg"])):
        stellen = [e for e in roh if e["feld"] == feld and isinstance(e.get("mid"), (int, float))]
        if len(stellen) < 3: continue
        fehlend = len(stellen) - len([e for e in gezeigt if e["feld"] == feld])
        zus = ("" if fehlend <= 0 else T["lage_zus1"] if fehlend == 1 else T["lage_zusn"])
        if all(e["mid"] >= dur/2 for e in stellen):
            lage = T["lage"].format(n=len(stellen), was=nm, zus=zus, haelfte=T["lage_zweite"])
        elif all(e["mid"] < dur/2 for e in stellen):
            lage = T["lage"].format(n=len(stellen), was=nm, zus=zus, haelfte=T["lage_erste"])
        if lage: break

    n_j = sum(1 for e in gezeigt if e["feld"] == "beat_jitter_ms")
    teile = ([T["m_jit"].format(n=n_j)] if n_j else []) + \
            ([T["m_peg"].format(n=len(gezeigt)-n_j)] if len(gezeigt)-n_j else [])
    muster = ""
    if roh:
        ungezeigt = len(roh) - len(gezeigt)
        rest = ("" if ungezeigt <= 0 else T["m_rest1"] if ungezeigt == 1
                else T["m_restn"].format(n=ungezeigt))
        muster = (f'<div class="muster">{T["m_stellen"].format(n=len(roh))}'
                  f'{T["m_und"].join(teile)}.{rest}{T["m_sortiert"]}{lage}</div>')
    ue_html = muster + "".join(uebungen) if uebungen else T["leer"]

    p50p = statistics.median(pj) if pj else None
    p50j = statistics.median(bj) if bj else None
    dichte = n / (dur/600) if dur else 0
    u1, u2 = urteil or ("", "")
    urteil_html = (f'<section class="urteil" style="margin-top:0"><p>{u1}</p>'
                   f'<p>{u2}</p></section>') if u1 else ""

    gut_block = (f'<section><div class="sektionskopf"><span class="nr">02</span>'
                 f'<h2>{T["h_gut"]}</h2></div><div class="gut" style="margin-top:14px">'
                 f'{gut_html}</div></section>') if gut_html else ""
    korrektur_html = ""
    if korrektur:
        k_datum, k_text, k_liste = korrektur
        punkte = "".join(f"<li>{x}</li>" for x in k_liste)
        korrektur_html = (f'<aside class="korrektur" role="note">'
                          f'<span class="marke">{T["korr_marke"].format(d=k_datum)}</span>'
                          f'<p>{k_text}</p>{"<ul>" + punkte + "</ul>" if punkte else ""}</aside>')

    return f"""<title>{titel}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="blatt">
<header class="kopf">
  <span class="marke">{T["marke"]}</span>
  <div class="zeile" style="margin-top:8px"><h1>{titel}</h1>
    <span class="mono" style="color:var(--ink-3);font-size:13px">{datum}</span></div>
  <p class="quelle" style="color:var(--ink-2)">{quelle}</p>
  <dl class="stammdaten">
    <div><dt class="marke">{T["laenge"]}</dt><dd class="mono">{zahl(dur/60)} {T["min"]}</dd></div>
    <div><dt class="marke">{T["uebergaenge"]}</dt><dd class="mono">{n}</dd></div>
    <div><dt class="marke">{T["tempo"]}</dt><dd class="mono">{report.get('bpm') or '–'} BPM</dd></div>
  </dl>
</header>
{korrektur_html}{urteil_html}
<section>
  <div class="sektionskopf"><span class="nr">01</span><h2>{T["h1"]}</h2></div>
  <p class="hinweis">{T["hinweis1"]}</p>
  <div class="kacheln" style="margin-top:18px">
    <div class="kachel">
      <span class="marke">{T["k_pegel"]}</span>
      <div class="wert mono">{zahl(p50p)}<span class="einheit">&nbsp;dB</span></div>
      <div class="unter">{T["u_pegel"].format(a=sum(1 for v in pj if v>=SCHWELLE_PEGEL), b=len(pj),
        p=round(sum(1 for v in pj if v>=SCHWELLE_PEGEL)/len(pj)*100) if pj else 0,
        m=zahl(max(pj) if pj else None))}</div>
      {_skala(p50p, SCHWELLE_PEGEL, PROFI_PEGEL_MIN, PROFI_PEGEL_MAX, 4.0, T["skala_pegel_l"], T["skala_pegel_r"])}
    </div>
    <div class="kachel">
      <span class="marke">{T["k_jitter"]}</span>
      <div class="wert mono">{zahl(p50j)}<span class="einheit">&nbsp;ms</span></div>
      <div class="unter">{T["u_jitter"].format(a=sum(1 for v in bj if v>=SCHWELLE_JIT), b=len(bj),
        p=round(sum(1 for v in bj if v>=SCHWELLE_JIT)/len(bj)*100) if bj else 0,
        m=zahl(max(bj) if bj else None))}</div>
      {_skala(p50j, SCHWELLE_JIT, PROFI_JIT_MIN, PROFI_JIT_MAX, 20.0, T["skala_jitter_l"], T["skala_jitter_r"])}
    </div>
    <div class="kachel beschreibung">
      <span class="marke">{T["k_dichte"]}</span>
      <div class="wert mono">{zahl(dichte)}<span class="einheit">&nbsp;{T["je10"]}</span></div>
      <div class="unter">{T["u_dichte"].format(t=zahl(dur/n/60), dmin=zahl(PROFI_DICHTE_MIN),
        dmax=zahl(PROFI_DICHTE_MAX))}</div>
    </div>
  </div>
</section>
{gut_block}<section>
  <div class="sektionskopf"><span class="nr">03</span><h2>{T["h2"]}</h2></div>
  <p class="hinweis">{T["hinweis2"]}</p>
  <div class="achse-rahmen" style="margin-top:18px">
    <div class="achse-innen">
      <div class="energie"><svg viewBox="0 0 1000 66" preserveAspectRatio="none"
        aria-label="{T["svg_alt"]}">
        <path d="{flaeche}" fill="var(--akzent-flaeche)"></path>
        <path d="{linie}" fill="none" stroke="var(--akzent)" stroke-width="2"
              vector-effect="non-scaling-stroke" stroke-linejoin="round"></path></svg></div>
      <div class="spuren">{''.join(spuren)}</div>
      <div class="zeitleiste">{marken}</div>
    </div>
    <div class="achse-legende">
      <b><span class="punkt" style="background:var(--gut)"></span>{T["l_gut"]}</b>
      <b><span class="punkt" style="background:#b07d0a"></span>{T["l_warn"]}</b>
      <b><span class="punkt" style="background:#c05f34"></span>{T["l_ernst"]}</b>
      <b><span class="punkt" style="background:var(--kritisch)"></span>{T["l_krit"]}</b>
      <span style="color:var(--ink-3)">{T["l_zahl"]}</span>
    </div>
  </div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">04</span><h2>{T["h3"]}</h2></div>
  <div class="tabellen-rahmen" style="margin-top:14px"><table>
    <thead><tr>{"".join(f"<th>{h}</th>" for h in T["th"])}</tr></thead>
    <tbody>{''.join(zeilen)}</tbody></table></div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">05</span><h2>{T["h4"]}</h2></div>
  <p class="hinweis">{T["hinweis4"]}</p>
  <div class="uebungen" style="margin-top:18px">{ue_html}</div>
</section>
{beob_html}<section>
  <div class="sektionskopf"><span class="nr">07</span><h2>{T["h5"]}</h2></div>
  <div class="grenzen" style="margin-top:14px">
    <p style="font-size:14px;color:var(--ink-2)">{T["grenzen_kopf"]}</p>
    <ul>
      <li>{T["g_namen"]}</li>
      <li>{T["g_eq"]}</li>
      <li>{T["g_fenster"]}</li>
      <li>{T["g_vergleich"]}</li>
    </ul>
  </div>
</section>
<div class="fuss">
  <span>{T["fuss_id"]} <span class="mono">{report.get('id','')[:8]}</span> ·
    {T["fuss_ver"]} {report.get('scoringVersion')}</span>
  <span>{n} {T["uebergaenge"]} · {zahl(dur/60)} {T["minuten"]}</span>
</div>
</div>
<div id="tip" role="status"></div>
<script>
(function(){{
  var tip = document.getElementById('tip');
  function zeigen(e){{
    var el = e.currentTarget, t = el.getAttribute('data-tip');
    if(!t) return;
    tip.textContent = '';
    t.split('\\n').forEach(function(zeile, i){{
      if(i) tip.appendChild(document.createElement('br'));
      tip.appendChild(document.createTextNode(zeile));
    }});
    var r = el.getBoundingClientRect();
    tip.style.opacity = '1';
    var b = tip.getBoundingClientRect();
    var x = Math.min(Math.max(8, r.left + r.width/2 - b.width/2), innerWidth - b.width - 8);
    tip.style.left = x + 'px';
    tip.style.top = (r.top - b.height - 8 < 8 ? r.bottom + 8 : r.top - b.height - 8) + 'px';
  }}
  function weg(){{ tip.style.opacity = '0'; }}
  document.querySelectorAll('.fenster').forEach(function(el){{
    el.addEventListener('mouseenter', zeigen);
    el.addEventListener('mouseleave', weg);
    el.addEventListener('focus', zeigen);
    el.addEventListener('blur', weg);
  }});
}})();
</script>"""

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("analysis_id")
    p.add_argument("--titel", default=None)
    p.add_argument("--datum", default="")
    p.add_argument("--quelle", default="")
    p.add_argument("--aus", type=Path, default=None)
    p.add_argument("--sprache", choices=sorted(TEXTE), default="de")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    a = p.parse_args()
    pfad = a.results_dir / f"{a.analysis_id}.json"
    if not pfad.exists():
        print(f"FEHLT: {pfad}"); return 1
    report = json.loads(pfad.read_text(encoding="utf-8"))
    titel = a.titel or (report.get("fileName") or a.analysis_id)
    ziel = a.aus or Path(f"report-{a.analysis_id[:8]}.html")
    ziel.write_text(baue(report, titel, a.datum, a.quelle, sprache=a.sprache),
                    encoding="utf-8")
    print(f"{ziel}  ({len(report.get('setTransitions') or [])} Übergänge)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
