"""Blinder Vergleich: alte Vorlage gegen belegte Uebung (J7).

Die Belegpflicht (tests/test_uebungen_belegt.py) beweist, dass keine Zahl
erfunden ist. Sie beweist NICHT, dass die neue Uebung dem DJ mehr nuetzt
als die alte Vorlage. Dafuer gibt es genau einen Weg, und er kostet
Sebastian einen Abend: er liest 20 Paare und sagt, welcher Hinweis ihn
beim naechsten Mix mehr veraendern wuerde.

Ohne diesen Vergleich ist "Punkt 3 auf 50 %" eine Behauptung.

WAS HIER BLIND SEIN MUSS
------------------------
Welcher der beiden Texte der neue ist. Sebastian weiss, dass er an den
Uebungen mitgearbeitet hat - wuesste er zusaetzlich, welcher Text von wem
stammt, bewertete er seine eigene Entscheidung und nicht den Text.

Deshalb: die Zuordnung Position -> Herkunft entsteht EINMAL beim Anlegen
des Laufs, wird serverseitig gespeichert und nie ausgeliefert. Die Seite
bekommt zwei Texte und zwei Knoepfe, sonst nichts. Kein Feldname, keine
Reihenfolge und keine Klasse im HTML verraet, welcher welcher ist -
dieselbe Regel wie bei der zweiten Labelrunde (app/api/relabel.py).

Gewuerfelt wird mit festem Startwert: ein Neuladen der Seite darf die
Zuordnung nicht aendern, sonst zaehlt eine halb beantwortete Runde falsch.
"""

from __future__ import annotations

import html
import json
import random
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.coach.uebungen import baue
from app.paths import DATA_ROOT, RESULTS_DIR

router = APIRouter(prefix="/uebungen-bewertung", tags=["uebungen-bewertung"])

BEWERTUNG_DIR = DATA_ROOT / "uebungen_bewertung"

# Der Text, der bis zum 14.08.2026 in ALLEN 51 Reports stand - als einzige
# Uebung, unabhaengig davon, was gemessen wurde. Er steht hier als
# Konstante, weil er aus den Reports entfernt wurde; ohne ihn gaebe es
# nichts zu vergleichen.
VORLAGE = ("Listen to the detected transition points and check whether the "
           "phrase timing feels natural.")

ANZAHL_PAARE = 20

# Fester Startwert: dieselbe Runde ergibt dieselbe Zuordnung. Wer eine
# zweite, unabhaengige Runde will, nimmt einen anderen Lauf-Namen.
STARTWERT = 20260814


class AntwortPayload(BaseModel):
    index: int
    gewaehlt: str  # "a" oder "b" - die Position, nicht die Herkunft


def _alle_uebungen() -> List[Dict]:
    """Alle belegten Uebungen des Bestands, mit ihrem Set."""
    raus: List[Dict] = []
    for pfad in sorted(RESULTS_DIR.glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uebergaenge = report.get("setTransitions") or []
        if not uebergaenge:
            continue
        uebungen, _ = baue(str(report.get("id") or ""), uebergaenge)
        for u in uebungen:
            raus.append({**u, "fileName": report.get("fileName") or pfad.stem})
    return raus


def _lauf_pfad(lauf: str) -> Path:
    return BEWERTUNG_DIR / f"{lauf}.json"


def _lauf_anlegen(lauf: str) -> Dict:
    """20 Paare ziehen und die Zuordnung festschreiben.

    Gezogen wird ueber moeglichst viele Aufnahmen: erst je Aufnahme die
    staerkste Uebung, dann aufgefuellt. Sonst kaemen 20 Paare aus zwei
    Sets, und die Antwort saegte mehr ueber diese zwei Sets aus als ueber
    die zwei Textsorten.
    """
    alle = _alle_uebungen()
    if not alle:
        raise HTTPException(status_code=404, detail="Keine belegten Uebungen im Bestand.")

    wuerfel = random.Random(STARTWERT)

    je_aufnahme: Dict[str, List[Dict]] = {}
    for u in alle:
        je_aufnahme.setdefault(u["fileName"], []).append(u)
    for liste in je_aufnahme.values():
        liste.sort(key=lambda u: -abs(u["value"]))

    ausgewaehlt: List[Dict] = []
    runde = 0
    while len(ausgewaehlt) < ANZAHL_PAARE:
        zugelegt = False
        for name in sorted(je_aufnahme):
            if runde < len(je_aufnahme[name]):
                ausgewaehlt.append(je_aufnahme[name][runde])
                zugelegt = True
                if len(ausgewaehlt) == ANZAHL_PAARE:
                    break
        if not zugelegt:
            break
        runde += 1

    aufgaben = []
    for i, u in enumerate(ausgewaehlt):
        # Muenzwurf je Paar: mal steht die Vorlage links, mal rechts.
        vorlage_links = wuerfel.random() < 0.5
        aufgaben.append({
            "index": i,
            "fileName": u["fileName"],
            "atSec": u["atSec"],
            "a": VORLAGE if vorlage_links else u["description"],
            "b": u["description"] if vorlage_links else VORLAGE,
            # NUR serverseitig - siehe Modul-Docstring.
            "_vorlage_ist": "a" if vorlage_links else "b",
        })

    lauf_daten = {"lauf": lauf, "startwert": STARTWERT,
                  "aufgaben": aufgaben, "antworten": {}}
    BEWERTUNG_DIR.mkdir(parents=True, exist_ok=True)
    _lauf_pfad(lauf).write_text(
        json.dumps(lauf_daten, ensure_ascii=False, indent=1), encoding="utf-8")
    return lauf_daten


def _lauf_laden(lauf: str) -> Dict:
    pfad = _lauf_pfad(lauf)
    if pfad.exists():
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return _lauf_anlegen(lauf)


def _blind(aufgabe: Dict) -> Dict:
    """Was der Browser sehen darf. Alles mit _ bleibt hier."""
    return {k: v for k, v in aufgabe.items() if not k.startswith("_")}


@router.get("/{lauf}/aufgaben")
def get_aufgaben(lauf: str) -> dict:
    daten = _lauf_laden(lauf)
    return {
        "lauf": lauf,
        "aufgaben": [_blind(a) for a in daten["aufgaben"]],
        "beantwortet": len(daten.get("antworten") or {}),
    }


@router.post("/{lauf}/antwort")
def post_antwort(lauf: str, payload: AntwortPayload) -> dict:
    if payload.gewaehlt not in {"a", "b"}:
        raise HTTPException(status_code=400, detail="gewaehlt muss 'a' oder 'b' sein.")
    daten = _lauf_laden(lauf)
    passend = next((a for a in daten["aufgaben"] if a["index"] == payload.index), None)
    if passend is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden.")

    # Erst hier wird aus einer Position eine Herkunft - im Browser ist sie nie.
    herkunft = "vorlage" if payload.gewaehlt == passend["_vorlage_ist"] else "belegt"
    daten.setdefault("antworten", {})[str(payload.index)] = {
        "gewaehlt": payload.gewaehlt,
        "herkunft": herkunft,
    }
    _lauf_pfad(lauf).write_text(
        json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "beantwortet": len(daten["antworten"])}


def _fuer_script_block(rohes_json: str) -> str:
    """JSON so einbetten, dass ein <script>-Element es zurueckgibt.

    Hier stand bis zum 17.08.2026 html.escape(..., quote=True), und die Seite
    blieb dadurch leer: Der HTML-Parser behandelt den Inhalt eines
    <script>-Elements als ROHTEXT und loest Entitaeten NICHT auf. `textContent`
    lieferte also woertlich `&quot;index&quot;: 0`, JSON.parse warf, die
    Schleife darunter lief nie - sichtbar blieb nur die statische
    Ueberschrift. Der Fehler war unsichtbar, weil die Aufgaben serverseitig
    korrekt gebaut wurden (20 Paare in der Laufdatei) und die Tests genau das
    pruefen: die Regel, nicht den Weg durch die Anwendung.

    Richtig ist das Gegenteil von Escapen: Das JSON bleibt roh, nur `<` wird
    zu `\\u003c`. Damit kann kein `</script>` den Block vorzeitig schliessen,
    und weil `<` in json.dumps-Ausgabe ausschliesslich innerhalb von
    Zeichenketten vorkommt, bleibt das Ergebnis gueltiges JSON.
    """
    return rohes_json.replace("<", "\\u003c")


@router.get("/{lauf}", response_class=HTMLResponse)
def get_seite(lauf: str) -> HTMLResponse:
    daten = _lauf_laden(lauf)
    aufgaben = json.dumps([_blind(a) for a in daten["aufgaben"]], ensure_ascii=False)
    beantwortet = json.dumps(daten.get("antworten") or {}, ensure_ascii=False)
    # Der Laufname steht im Template zwischen Anfuehrungszeichen und ist damit
    # ein JS-String-Literal - dieselbe Rohtext-Regel wie oben. html.escape war
    # auch hier falsch; es fiel nur nicht auf, weil "abend1" keine Sonderzeichen
    # hat. json.dumps liefert die Anfuehrungszeichen gleich mit.
    return HTMLResponse(_SEITE.replace("__AUFGABEN__", _fuer_script_block(aufgaben))
                        .replace("__ANTWORTEN__", _fuer_script_block(beantwortet))
                        .replace('"__LAUF__"', _fuer_script_block(json.dumps(lauf))))


# Zwei Knoepfe, zwei Texte, sonst nichts. Bewusst ohne Reihenfolge-Hinweis
# in Klassennamen oder Beschriftung ("A" und "B" sind reine Positionen).
_SEITE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<title>MixCoach - Welcher Hinweis hilft mehr?</title>
<style>
 body{font-family:-apple-system,system-ui,sans-serif;max-width:760px;margin:2rem auto;
      padding:0 1rem;line-height:1.5;color:#111}
 .karte{border:1px solid #ddd;border-radius:10px;padding:1rem;margin:1rem 0}
 .wahl{display:block;width:100%;text-align:left;border:1px solid #bbb;background:#fff;
       border-radius:8px;padding:.9rem;margin:.5rem 0;font-size:1rem;cursor:pointer}
 .wahl:hover{border-color:#333;background:#fafafa}
 .fertig{opacity:.45}
 .kopf{color:#666;font-size:.85rem;margin-bottom:.4rem}
 #stand{position:sticky;top:0;background:#fff;padding:.6rem 0;font-weight:600}
</style></head><body>
<h1>Welcher Hinweis würde dich beim nächsten Mix mehr verändern?</h1>
<p>20 Übergänge, je zwei Formulierungen. Es gibt kein Richtig — entscheide aus
dem Bauch. Welcher Text von wo stammt, siehst du bewusst nicht.</p>
<div id="stand"></div>
<div id="liste"></div>
<script>const LAUF = "__LAUF__";</script>
<script id="daten" type="application/json">__AUFGABEN__</script>
<script id="stand-daten" type="application/json">__ANTWORTEN__</script>
<script>
const aufgaben = JSON.parse(document.getElementById("daten").textContent);
const antworten = JSON.parse(document.getElementById("stand-daten").textContent);
const liste = document.getElementById("liste");
const stand = document.getElementById("stand");

function zeit(s){ const g=Math.round(s||0); return Math.floor(g/60)+":"+String(g%60).padStart(2,"0"); }
function standZeigen(){
  const n = Object.keys(antworten).length;
  stand.textContent = n + " von " + aufgaben.length + " beantwortet";
}

for (const a of aufgaben) {
  const karte = document.createElement("div");
  karte.className = "karte" + (antworten[a.index] ? " fertig" : "");
  const kopf = document.createElement("div");
  kopf.className = "kopf";
  kopf.textContent = a.fileName + " - bei " + zeit(a.atSec);
  karte.appendChild(kopf);
  for (const pos of ["a","b"]) {
    const b = document.createElement("button");
    b.className = "wahl";
    b.textContent = a[pos];
    b.onclick = async () => {
      await fetch("/uebungen-bewertung/" + LAUF + "/antwort", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({index:a.index, gewaehlt:pos})
      });
      antworten[a.index] = {gewaehlt:pos};
      karte.className = "karte fertig";
      standZeigen();
    };
    karte.appendChild(b);
  }
  liste.appendChild(karte);
}
standZeigen();
</script>
</body></html>"""
