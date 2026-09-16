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
from app.coach.uebungen import baue as uebungen_bauen, ueberschreitung  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402

SCHWELLE_PEGEL, ZIEL_PEGEL = 3.0, 1.0
SCHWELLE_JIT,  ZIEL_JIT    = 15.0, 10.0
# Referenz: die sechs fremden Profi-Sets im Bestand, gerechnet am 07.09.2026
PROFI_PEGEL_P50, PROFI_JIT_P50 = 1.35, 10.0
PROFI_DICHTE_MIN, PROFI_DICHTE_MAX = 1.83, 2.94   # Be Svendsen .. Joris Voorn

# Die Uebungstexte kommen aus der Engine (app/coach/uebungen.py), nicht aus
# einer eigenen Bibliothek. Bis zum 14.09.2026 hatte dieses Werkzeug eine
# zweite - mit Saetzen wie "bevor ein Doppelschlag hoerbar wird", die die
# Engine-Tests ausdruecklich verbieten. Zwei Kopien, und eine lief davon.


def zusatz_beide(metrik, auch_gelistet, anderer_wert):
    """Seiten-Anmerkung, wenn an derselben Stelle beide Groessen reissen.

    Zwei Faelle: steht die zweite Groesse ebenfalls in der angezeigten Liste,
    kann man darauf verweisen. Wurde sie beim Abschneiden weggelassen, muss
    der Wert genannt werden - sonst behauptet der Satz eine Zeile, die es
    nicht gibt.
    """
    andere = "der Pegelsprung" if metrik == "beat_jitter_ms" else "der Beat-Jitter"
    if auch_gelistet:
        return f" An dieser Stelle reißt auch {andere} — sie steht deshalb zweimal in der Liste."
    return f" An diesem Übergang liegt zusätzlich {andere} über der Schwelle ({anderer_wert})."


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

def z(s):
    if s is None: return "–"
    s = int(s); return f"{s//60}:{s%60:02d}"

def zahl(v, n=1):
    return "–" if v is None else f"{v:.{n}f}".replace(".", ",")

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

def _skala(wert, schwelle, profi, max_x, links, rechts):
    if wert is None: return ""
    farbe = {"gut":"var(--gut)","warnung":"#b07d0a","ernst":"#c05f34",
             "kritisch":"var(--kritisch)"}[stufe(wert, schwelle)]
    return (f'<div class="skala"><div class="spur">'
            f'<div class="band" style="left:0;width:{min(profi/max_x*100,100):.1f}%"></div>'
            f'<div class="fuellung" style="width:{min(wert/max_x*100,100):.1f}%;background:{farbe}"></div>'
            f'<div class="schwelle" style="left:{min(schwelle/max_x*100,100):.1f}%"></div></div>'
            f'<div class="legende"><span>{links}</span><span>{rechts}</span></div></div>')

def baue(report: dict, titel: str, datum: str, quelle: str, urteil=None,
         korrektur=None) -> str:
    """Die Report-Seite als HTML.

    korrektur: optional (datum, einleitung, [aenderungen]). Eine Seite, die ein
    Leser schon in einer frueheren Fassung kennt, sagt offen, was sich
    geaendert hat - sonst widerspricht sie stillschweigend dem, was er
    gelesen hat.
    """
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
                   f"Pegelsprung {zahl(f['pegel'])} dB · Jitter {zahl(f['jit'])} ms")
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
        r = (" lauter" if p > 0 else " leiser" if p < 0 else "") if isinstance(p,(int,float)) else ""
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
    for u in uebungen_bauen(report.get("id") or "", ts)[0]:
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
            txt += zusatz_beide(e["feld"], p in gezeigt, f'{zahl(abs(p["wert"]))} {eh}')
        eh = "ms" if e["feld"] == "beat_jitter_ms" else "dB"
        uebungen.append(
          f'<div class="uebung"><div class="zeit">{e["zeit"]}</div>'
          f'<div class="was">{e["titel"]} '
          f'<span class="mono" style="color:var(--ink-3);font-weight:500">· '
          f'{zahl(abs(e["wert"]))} {eh} → Ziel {zahl(e["ziel"])} {eh}</span></div>'
          f'<div class="wie">{txt}</div></div>')

    lage = ""
    for feld, nm in (("beat_jitter_ms","Jitter-Stellen"), ("loudness_jump_db","Pegel-Stellen")):
        stellen = [e for e in roh if e["feld"] == feld and isinstance(e.get("mid"), (int, float))]
        if len(stellen) < 3: continue
        fehlend = len(stellen) - len([e for e in gezeigt if e["feld"] == feld])
        zus = ("" if fehlend <= 0
               else " über der Schwelle — die hier nicht aufgeführte eingeschlossen —" if fehlend == 1
               else " über der Schwelle — die hier nicht aufgeführten eingeschlossen —")
        if all(e["mid"] >= dur/2 for e in stellen):
            lage = f" Und alle {len(stellen)} {nm}{zus} liegen in der zweiten Hälfte des Sets."
        elif all(e["mid"] < dur/2 for e in stellen):
            lage = f" Und alle {len(stellen)} {nm}{zus} liegen in der ersten Hälfte des Sets."
        if lage: break

    n_j = sum(1 for e in gezeigt if e["feld"] == "beat_jitter_ms")
    teile = ([f"<b>{n_j}×</b> Beat-Jitter"] if n_j else []) + \
            ([f"<b>{len(gezeigt)-n_j}×</b> Pegelsprung"] if len(gezeigt)-n_j else [])
    muster = ""
    if roh:
        ungezeigt = len(roh) - len(gezeigt)
        rest = ("" if ungezeigt <= 0 else " Eine weitere Stelle ist hier nicht aufgeführt."
                if ungezeigt == 1 else f" Weitere {ungezeigt} Stellen sind hier nicht aufgeführt.")
        muster = (f'<div class="muster">{len(roh)} Stellen über der Schwelle: '
                  f'{" und ".join(teile)}.{rest} Die Liste steht nach Schwere, gemessen als '
                  f'Vielfaches der jeweiligen Schwelle — so sind dB und ms vergleichbar.{lage}</div>')
    ue_html = muster + "".join(uebungen) if uebungen else (
      '<div class="uebung"><div class="zeit">–</div><div class="was">Keine Stelle über der '
      'Schwelle.</div><div class="wie">Weder Pegelsprung noch Beat-Jitter überschreiten in '
      'diesem Set ihre belegte Schwelle.</div></div>')

    p50p = statistics.median(pj) if pj else None
    p50j = statistics.median(bj) if bj else None
    dichte = n / (dur/600) if dur else 0
    u1, u2 = urteil or ("", "")
    urteil_html = (f'<section class="urteil" style="margin-top:0"><p>{u1}</p>'
                   f'<p>{u2}</p></section>') if u1 else ""

    korrektur_html = ""
    if korrektur:
        k_datum, k_text, k_liste = korrektur
        punkte = "".join(f"<li>{x}</li>" for x in k_liste)
        korrektur_html = (f'<aside class="korrektur" role="note">'
                          f'<span class="marke">Korrigierte Fassung · {k_datum}</span>'
                          f'<p>{k_text}</p>{"<ul>" + punkte + "</ul>" if punkte else ""}</aside>')

    return f"""<title>{titel}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="blatt">
<header class="kopf">
  <span class="marke">MixCoach · Set-Analyse</span>
  <div class="zeile" style="margin-top:8px"><h1>{titel}</h1>
    <span class="mono" style="color:var(--ink-3);font-size:13px">{datum}</span></div>
  <p class="quelle" style="color:var(--ink-2)">{quelle}</p>
  <dl class="stammdaten">
    <div><dt class="marke">Länge</dt><dd class="mono">{zahl(dur/60)} min</dd></div>
    <div><dt class="marke">Übergänge</dt><dd class="mono">{n}</dd></div>
    <div><dt class="marke">Grundtempo</dt><dd class="mono">{report.get('bpm') or '–'} BPM</dd></div>
  </dl>
</header>
{korrektur_html}{urteil_html}
<section>
  <div class="sektionskopf"><span class="nr">01</span><h2>Die zwei Zahlen, die belegt sind</h2></div>
  <p class="hinweis">MixCoach misst viel und belegt zwei Größen: den Pegelsprung am Übergang
    und den Beat-Jitter im Blend. Nur diese beiden hängen nachweisbar mit dem menschlichen
    Urteil zusammen — alles andere steht weiter unten unter „Was hier nicht drinsteht“.</p>
  <div class="kacheln" style="margin-top:18px">
    <div class="kachel">
      <span class="marke">Pegelsprung · Median</span>
      <div class="wert mono">{zahl(p50p)}<span class="einheit">&nbsp;dB</span></div>
      <div class="unter"><b>{sum(1 for v in pj if v>=SCHWELLE_PEGEL)} von {len(pj)}</b> Übergängen
        ({round(sum(1 for v in pj if v>=SCHWELLE_PEGEL)/len(pj)*100) if pj else 0}&nbsp;%)
        springen um mehr als 3 dB. Größter Sprung: {zahl(max(pj) if pj else None)} dB.</div>
      {_skala(p50p, SCHWELLE_PEGEL, PROFI_PEGEL_P50, 4.0, 'Vergleichs-Sets 1,35 dB', 'Schwelle 3 dB')}
    </div>
    <div class="kachel">
      <span class="marke">Beat-Jitter · Median</span>
      <div class="wert mono">{zahl(p50j)}<span class="einheit">&nbsp;ms</span></div>
      <div class="unter"><b>{sum(1 for v in bj if v>=SCHWELLE_JIT)} von {len(bj)}</b> Übergängen
        ({round(sum(1 for v in bj if v>=SCHWELLE_JIT)/len(bj)*100) if bj else 0}&nbsp;%)
        reißen die 15-ms-Schwelle. Schlechtester Wert: {zahl(max(bj) if bj else None)} ms.</div>
      {_skala(p50j, SCHWELLE_JIT, PROFI_JIT_P50, 20.0, 'Vergleichs-Sets 10,0 ms', 'Schwelle 15 ms')}
    </div>
    <div class="kachel beschreibung">
      <span class="marke">Wechseldichte · keine Bewertung</span>
      <div class="wert mono">{zahl(dichte)}<span class="einheit">&nbsp;/10&nbsp;min</span></div>
      <div class="unter">Ein Trackwechsel etwa alle {zahl(dur/n/60)} Minuten.
        <b>Das ist eine Beschreibung, kein Ziel.</b> Über 23 Aufnahmen gemessen, hängt die
        Dichte nicht mit der Qualität zusammen (ρ&nbsp;=&nbsp;−0,09, p&nbsp;=&nbsp;0,67).
        Die Vergleichs-Sets reichen von {zahl(PROFI_DICHTE_MIN)} (Four Tet, Be Svendsen) bis
        {zahl(PROFI_DICHTE_MAX)} (Joris Voorn) — beide Enden sind Weltklasse.</div>
    </div>
  </div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">02</span><h2>Wo im Set du hinhören musst</h2></div>
  <p class="hinweis">Jeder Balken ist ein Übergang — als <b>Zeitfenster</b>, nicht als Sekundenangabe.
    Das ist Absicht: Die Erkennung trifft den exakten Punkt nur selten, das Fenster von
    110 Sekunden enthält den echten Übergang in 73&nbsp;% der Fälle. Die Kurve dahinter ist der
    Energieverlauf. Farbe und Zahl sagen dasselbe — die Zahl gilt.</p>
  <div class="achse-rahmen" style="margin-top:18px">
    <div class="achse-innen">
      <div class="energie"><svg viewBox="0 0 1000 66" preserveAspectRatio="none"
        aria-label="Energieverlauf über das Set">
        <path d="{flaeche}" fill="var(--akzent-flaeche)"></path>
        <path d="{linie}" fill="none" stroke="var(--akzent)" stroke-width="2"
              vector-effect="non-scaling-stroke" stroke-linejoin="round"></path></svg></div>
      <div class="spuren">{''.join(spuren)}</div>
      <div class="zeitleiste">{marken}</div>
    </div>
    <div class="achse-legende">
      <b><span class="punkt" style="background:var(--gut)"></span>im Rahmen</b>
      <b><span class="punkt" style="background:#b07d0a"></span>knapp über der Schwelle</b>
      <b><span class="punkt" style="background:#c05f34"></span>deutlich drüber</b>
      <b><span class="punkt" style="background:var(--kritisch)"></span>weit drüber</b>
      <span style="color:var(--ink-3)">Zahl im Balken: Nummer des Übergangs</span>
    </div>
  </div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">03</span><h2>Alle Übergänge im Einzelnen</h2></div>
  <div class="tabellen-rahmen" style="margin-top:14px"><table>
    <thead><tr><th>Nr</th><th>Fenster</th><th>Pegelsprung</th><th>Beat-Jitter</th><th>Tonart</th></tr></thead>
    <tbody>{''.join(zeilen)}</tbody></table></div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">04</span><h2>Was sich üben lässt</h2></div>
  <p class="hinweis">Nur Stellen, an denen eine belegte Größe ihre Schwelle reißt.
    Jede Zeile nennt den gemessenen Wert aus <em>diesem</em> Set.</p>
  <div class="uebungen" style="margin-top:18px">{ue_html}</div>
</section>
<section>
  <div class="sektionskopf"><span class="nr">05</span><h2>Was hier nicht drinsteht</h2></div>
  <div class="grenzen" style="margin-top:14px">
    <p style="font-size:14px;color:var(--ink-2)">MixCoach zeigt nichts an, was nicht gemessen
      wurde. Für dieses Set heißt das konkret:</p>
    <ul>
      <li><b>Keine Tracknamen.</b> Die Trackerkennung vergleicht gegen die Sammlung im
        Fingerabdruck-Index. Tracks, die dort nicht liegen, bleiben unbenannt — und Treffer,
        die nur knapp an der Erkennungsschwelle liegen, zeigt diese Seite bewusst nicht an.
        <b>Mit einer Tracklist</b> — eine Zeile je Track, Zeiten wenn vorhanden — stünden
        hier Namen.</li>
      <li><b>Nichts zu EQ, Frequenzbild, Timing oder Kreativität.</b> Ob sich Bässe oder
        Höhen im Blend beißen, wird heute nicht gemessen: Die vorhandene Bass-Messung
        braucht beide Tracks aus der Sammlung und ist fast immer entweder 0 oder 100 —
        ein Schalter, keine Abstufung. Gegen Hörurteile belegt ist sie nicht. Daraus einen
        Rat abzuleiten hieße raten.</li>
      <li><b>Das Fenster ist ein Fenster.</b> Die 110 Sekunden enthalten den echten
        Übergang in 73&nbsp;% der Fälle — nicht in allen. Bei etwa jedem vierten Balken
        liegt der Übergang daneben.</li>
      <li><b>Der Vergleich hat eine Schwäche.</b> Die sechs Referenz-Sets (Dixon, Four Tet,
        Joris Voorn, RÜFÜS DU SOL, Be Svendsen) sind veröffentlichte Festival-Mitschnitte
        und damit gemastert. Mastering drückt Pegelsprünge. Beim <em>Pegel</em> ist der
        Vergleich deshalb zu deinen Ungunsten verzerrt; beim <em>Beat-Jitter</em>
        nicht — den ändert kein Mastering.</li>
    </ul>
  </div>
</section>
<div class="fuss">
  <span>Analyse-ID <span class="mono">{report.get('id','')[:8]}</span> ·
    Scoring-Version {report.get('scoringVersion')}</span>
  <span>{n} Übergänge · {zahl(dur/60)} Minuten</span>
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
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    a = p.parse_args()
    pfad = a.results_dir / f"{a.analysis_id}.json"
    if not pfad.exists():
        print(f"FEHLT: {pfad}"); return 1
    report = json.loads(pfad.read_text(encoding="utf-8"))
    titel = a.titel or (report.get("fileName") or a.analysis_id)
    ziel = a.aus or Path(f"report-{a.analysis_id[:8]}.html")
    ziel.write_text(baue(report, titel, a.datum, a.quelle), encoding="utf-8")
    print(f"{ziel}  ({len(report.get('setTransitions') or [])} Übergänge)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
