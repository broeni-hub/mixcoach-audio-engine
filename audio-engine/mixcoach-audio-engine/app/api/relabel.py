"""Eigene Route fuer die zweite, blinde Labelrunde (K1).

Bewusst als eigener Router mit eigener, sehr schlichter HTML-Seite - nicht
im TanStack-Frontend. Zwei Gruende: bestehende Endpoints und Frontend-Seiten
bleiben unberuehrt (CLAUDE.md), und die Seite laeuft ohne npm-Build, also
auch dann, wenn Frontend/node_modules fehlt.

WAS HIER BLIND SEIN MUSS
------------------------
Gemessen wird die Wiederholgenauigkeit eines Menschen. Jede Spur der ersten
Angabe verfaelscht das. Der Server sendet correctedSec deshalb NIE - die
Aufgabenliste wird serverseitig aus der Ground Truth gebaut und der Wert
dort entfernt, statt ihn im Browser auszublenden.

Der Engine-Marker (mid_sec) WIRD gezeigt, und das ist Absicht: beim ersten
Durchgang sah Sebastian genau diesen Marker und hat ihn verschoben. Wuerde
Runde 2 ohne ihn stattfinden, waere es eine andere Aufgabe (Uebergaenge
finden statt Uebergaenge zeitlich einordnen) und die beiden Runden waeren
nicht vergleichbar. Gleicher Reiz, gleiche Aufgabe - nur ohne die eigene
Antwort von damals.

WAS FASSUNG 1 FALSCH GEMACHT HAT (behoben am 19.08.2026)
--------------------------------------------------------
Der Marker war nicht nur der Reiz, er war die VORBELEGUNG der Antwort: der
Abspielkopf sprang beim Laden auf engineSec, bewegen liess er sich nur in
Spruengen von 8 und 30 s, und abgeschickt wurde die Abspielposition im
Moment des Klicks. Wer zuhoerte und dann uebernahm, gab damit den Marker
plus die verstrichene Hoerzeit an.

Nachgerechnet auf den 16 Antworten vom 11.08.2026: Runde 2 lag im Median
+4,7 s neben dem Marker (sigma 14,7 s), Runde 1 bei -50,1 s (sigma 47,1 s);
15 von 16 Antworten lagen naeher am Marker als in Runde 1. Von echter
Uebereinstimmung ist das nicht zu unterscheiden - und genau deshalb misst
das Instrument in dieser Form nicht, was es behauptet.

Fassung 2 aendert drei Dinge und nur diese drei:

1. Der Abspielkopf startet um einen ZUFAELLIGEN Versatz (+-120 s, aus dem
   Sitzungs-Seed abgeleitet) neben dem Marker. Wer trotzdem beim Marker
   landet, ist dorthin gegangen.
2. Freie Positionierung ueber einen Schieber ueber das ganze Set, statt
   nur Spruenge von 8 und 30 s. Runde 1 hatte die Wellenform, also auch
   freie Positionierung - das stellt die Vergleichbarkeit erst her.
3. Die Antwort ist ein ausdruecklicher Griff ("Hier beginnt der Uebergang"),
   nicht die Abspielposition beim Absenden. Damit verschiebt Weiterhoeren
   die Antwort nicht mehr.

Startpunkt und ein etwaiger Sprung auf den Marker werden mitgeschrieben.
Erst dadurch laesst sich hinterher pruefen, ob die Antworten noch am Anker
kleben - eine Selbstpruefung, die Fassung 1 nicht hatte.

NUR timing_off-Uebergaenge
--------------------------
Aufgenommen werden ausschliesslich Uebergaenge, die in Runde 1 den Verdict
timing_off UND ein correctedSec bekommen haben. Bei verdict="correct" ist
midSec der vom Menschen ANGENOMMENE Wert - der Engine-Marker waere dort
gleich seiner Antwort, und die Anzeige des Markers wuerde die Antwort
verraten. Zugleich sind genau die timing_off-Werte die Grundgesamtheit,
auf der die Referenzmetrik ihr sigma = 52,87 s rechnet; die Messung ist
damit direkt vergleichbar.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.jobs import feedback_store, job_manager, relabel_store

router = APIRouter(prefix="/relabel", tags=["relabel"])


class AntwortPayload(BaseModel):
    index: int
    sec: float
    was: str
    # Anker-Diagnose, siehe Modul-Docstring. Optional, damit ein alter
    # Client keine 422 bekommt - dann fehlt eben die Diagnose.
    startSec: float | None = None
    zumMarker: bool = False


def _aufgaben(analysis_id: str) -> tuple[list[dict], float]:
    """Uebergaenge der zweiten Runde - OHNE die Antwort aus Runde 1.

    Zweiter Rueckgabewert ist die Setlaenge; der Schieber der Seite braucht
    sie, um ueber das ganze Set zu reichen.
    """
    ergebnis = job_manager.get_result(analysis_id)
    if ergebnis is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    runde1 = feedback_store.load_feedback(analysis_id)
    verdicts = runde1.get("verdicts") or {}

    transitions = {str(t.get("index")): t for t in (ergebnis.get("setTransitions") or [])}
    dauer = float(ergebnis.get("totalDurationSec") or 0.0)
    seed = int(relabel_store.sitzung(analysis_id).get("seed") or 1)

    aufgaben = []
    for idx, v in verdicts.items():
        if v.get("verdict") != "timing_off" or v.get("correctedSec") is None:
            continue
        t = transitions.get(str(idx))
        if t is None:
            continue
        engine_sec = float(v.get("midSec") or t.get("mid_sec") or 0.0)
        # Startpunkt: Marker plus zufaelliger Versatz, in die Aufnahme
        # geklemmt. Der Marker selbst bleibt sichtbar - er ist der Reiz,
        # nur nicht mehr die Vorbelegung.
        start = engine_sec + relabel_store.startversatz(seed, int(idx))
        obergrenze = dauer - 1.0 if dauer > 1.0 else engine_sec
        start = max(0.0, min(start, obergrenze))
        aufgaben.append({
            "index": int(idx),
            # Der Engine-Marker, den er auch in Runde 1 gesehen hat.
            "engineSec": engine_sec,
            "startSec": round(start, 2),
            "trackVor": t.get("track_before") or t.get("key_before"),
            "trackNach": t.get("track_after") or t.get("key_after"),
            # correctedSec wird hier NICHT uebernommen. Nicht ausgeblendet,
            # nicht mitgeschickt - gar nicht erst eingesammelt.
        })
    return aufgaben, dauer


@router.get("/{analysis_id}/aufgaben")
def get_aufgaben(analysis_id: str) -> dict:
    aufgaben, dauer = _aufgaben(analysis_id)
    # sitzung() statt laden(): der Seed muss beim ERSTEN Aufruf festgeschrieben
    # werden, sonst mischt ein Neuladen des Browsers die Reihenfolge neu.
    stand = relabel_store.sitzung(analysis_id)
    ordnung = relabel_store.reihenfolge([a["index"] for a in aufgaben], stand["seed"])
    nach_index = {a["index"]: a for a in aufgaben}
    return {
        "analysisId": analysis_id,
        "aufgaben": [nach_index[i] for i in ordnung],
        # Nur Antworten der aktuellen Werkzeug-Fassung gelten als erledigt.
        # Was mit Fassung 1 entstanden ist, wird erneut vorgelegt - sonst
        # bliebe eine Messung stehen, von der belegt ist, dass sie am
        # Engine-Marker klebt.
        "erledigt": relabel_store.erledigt_mit_werkzeug(analysis_id),
        "gesamt": len(aufgaben),
        "dauerSec": dauer,
        "werkzeug": relabel_store.WERKZEUG,
    }


@router.post("/{analysis_id}/antwort")
def post_antwort(analysis_id: str, payload: AntwortPayload) -> dict:
    try:
        stand = relabel_store.speichern_antwort(
            analysis_id, payload.index, payload.sec, payload.was,
            start_sec=payload.startSec, zum_marker=payload.zumMarker)
    except ValueError as fehler:
        raise HTTPException(status_code=422, detail=str(fehler)) from fehler
    return {"erledigt": len(stand["antworten"]), "gespeichert": payload.index,
            # Der Anker-Waechter. Faehrt bei JEDER Antwort mit, damit ein
            # unbrauchbarer Durchgang waehrend des Durchgangs auffaellt und
            # nicht Tage spaeter im Terminal (siehe relabel_store).
            "anker": relabel_store.anker_warnung(analysis_id)}


@router.get("/{analysis_id}", response_class=HTMLResponse)
def get_seite(analysis_id: str) -> HTMLResponse:
    if job_manager.get_result(analysis_id) is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return HTMLResponse(_SEITE.replace("__ANALYSIS_ID__", html.escape(analysis_id)))


# Eine Datei, kein Build, keine Abhaengigkeiten. Die Seite wird ein- oder
# zweimal benutzt - sie darf schlicht sein. Was sie NICHT sein darf: eine
# Eingabe, die eine Antwort vorbelegt. Siehe Modul-Docstring, Fassung 1.
_SEITE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MixCoach - zweite Runde</title>
<style>
 body{font-family:-apple-system,system-ui,sans-serif;max-width:820px;margin:0 auto;
      padding:24px;background:#14141a;color:#e8e8ef;line-height:1.5}
 h1{font-size:20px;margin:0 0 4px} .sub{color:#9a9aab;font-size:14px;margin-bottom:20px}
 .karte{background:#1e1e28;border:1px solid #33333f;border-radius:10px;padding:18px;margin-bottom:16px}
 audio{width:100%;margin:12px 0}
 button{font:inherit;padding:9px 14px;border-radius:8px;border:1px solid #44445a;
        background:#2a2a38;color:#e8e8ef;cursor:pointer}
 button:hover{background:#34344a} button.haupt{background:#5b46c8;border-color:#6f5ae0}
 button.gewaehlt{background:#5b46c8;border-color:#6f5ae0}
 button.griff{background:#2a2a38;border-color:#6f5ae0;font-weight:600}
 button.griff.hat{background:#1f5136;border-color:#2f7d52}
 button:disabled{opacity:.45;cursor:not-allowed}
 .reihe{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
 .zeit{font-variant-numeric:tabular-nums;font-size:26px;font-weight:600}
 .gewaehltzeit{font-variant-numeric:tabular-nums;font-size:20px;color:#7ee08a}
 .hinweis{color:#9a9aab;font-size:13px} .fertig{color:#7ee08a}
 .warnung{background:#3a2318;border:1px solid #a8552a;border-radius:10px;
          padding:14px 16px;margin-bottom:16px;color:#ffd9c2;font-size:14px}
 .warnung b{color:#ffb083}
 .balken{height:6px;background:#33333f;border-radius:3px;overflow:hidden;margin:8px 0 18px}
 .balken>div{height:100%;background:#5b46c8;width:0}
 input[type=range]{width:100%;accent-color:#6f5ae0}
</style></head><body>
<h1>Zweite Runde &mdash; wo beginnt der Übergang?</h1>
<div class="sub">Die Reihenfolge ist gewürfelt und der Einstiegspunkt liegt
zufällig neben dem Engine-Vorschlag. Deine Angaben vom ersten Mal werden
nicht angezeigt &ndash; das ist der Sinn der Sache.</div>
<div class="balken"><div id="balken"></div></div>
<div id="anker"></div>
<div class="karte" id="karte">Lade&hellip;</div>
<div class="hinweis" id="status"></div>
<script>
const AID = "__ANALYSIS_ID__";
let aufgaben = [], pos = 0, erledigt = new Set(), dauer = 0;
let was = null, audio = null, gewaehlt = null, zumMarkerGenutzt = false;

function fmt(s){const m=Math.floor(s/60),r=Math.floor(s%60);return m+":"+String(r).padStart(2,"0");}

async function start(){
  const r = await fetch(`/relabel/${AID}/aufgaben`);
  const d = await r.json();
  aufgaben = d.aufgaben; erledigt = new Set(d.erledigt); dauer = d.dauerSec || 0;
  pos = aufgaben.findIndex(a => !erledigt.has(a.index));
  if (pos < 0) pos = aufgaben.length;
  zeichne();
}

function zeichne(){
  const k = document.getElementById("karte");
  document.getElementById("balken").firstElementChild ||
    (document.getElementById("balken").innerHTML = "<div></div>");
  document.querySelector("#balken>div").style.width =
    (aufgaben.length ? erledigt.size/aufgaben.length*100 : 0) + "%";
  document.getElementById("status").textContent =
    `${erledigt.size} von ${aufgaben.length} erledigt`;

  if (pos >= aufgaben.length){
    k.innerHTML = `<p class="fertig"><b>Fertig.</b> Alle ${aufgaben.length}
      Übergänge sind ein zweites Mal eingeordnet.</p>
      <p class="hinweis">Auswertung im Terminal:<br>
      <code>python -m tools.eval.relabel_agreement</code></p>`;
    return;
  }
  const a = aufgaben[pos];
  was = null; gewaehlt = null; zumMarkerGenutzt = false;
  k.innerHTML = `
    <div class="hinweis">Übergang ${pos+1} von ${aufgaben.length}
      &middot; Engine-Vorschlag bei ${fmt(a.engineSec)}</div>
    <audio id="au" controls preload="none"
           src="/analysis/${AID}/audio"></audio>
    <input type="range" id="schieber" min="0" max="${dauer || 1}" step="0.1" value="0">
    <div class="reihe">
      <button onclick="spring(-30)">&minus;30 s</button>
      <button onclick="spring(-8)">&minus;8 s</button>
      <button onclick="spring(8)">+8 s</button>
      <button onclick="spring(30)">+30 s</button>
      <button onclick="zumMarker()">zum Engine-Vorschlag</button>
    </div>
    <div class="reihe"><span class="zeit" id="jetzt">0:00</span>
      <span class="hinweis">&larr; Abspielposition</span></div>
    <div class="reihe">
      <button class="griff" id="griff" onclick="greife()">
        &#9678; Hier beginnt der Übergang</button>
      <span class="gewaehltzeit" id="gewaehlt">noch nicht gesetzt</span>
    </div>
    <div class="reihe hinweis">Was markierst du gerade?</div>
    <div class="reihe">
      <button id="w_a_raus"  onclick="waehle('a_raus')">A geht raus</button>
      <button id="w_b_rein"  onclick="waehle('b_rein')">B kommt rein</button>
      <button id="w_beides"  onclick="waehle('beides')">beide zusammen</button>
    </div>
    <div class="reihe"><button class="haupt" onclick="sichern()">
      Übernehmen und weiter</button></div>`;
  audio = document.getElementById("au");
  const schieber = document.getElementById("schieber");
  audio.addEventListener("timeupdate", () => {
    document.getElementById("jetzt").textContent = fmt(audio.currentTime);
    schieber.value = audio.currentTime;
  });
  schieber.addEventListener("input", () => {
    audio.currentTime = parseFloat(schieber.value);
    document.getElementById("jetzt").textContent = fmt(audio.currentTime);
  });
  // Startpunkt kommt vom Server und liegt zufaellig neben dem Marker.
  audio.addEventListener("loadedmetadata", () => {
    if (!dauer) schieber.max = audio.duration || 1;
    audio.currentTime = a.startSec;
    schieber.value = a.startSec;
    document.getElementById("jetzt").textContent = fmt(a.startSec);
  }, {once:true});
}

function zeigeAnker(a){
  // Der Waechter rechnet auf dem Server, hier steht nur, was er sagt.
  // Absichtlich deutlich und ohne Beschoenigung: ein Durchgang, der so
  // weiterlaeuft, misst nichts, und dann ist Abbrechen die bessere Wahl.
  const k = document.getElementById("anker");
  if (!a || !a.warnung){ k.innerHTML = ""; return; }
  k.innerHTML = `<div class="warnung">
    <b>Achtung - so misst dieser Durchgang nichts.</b><br>
    Deine letzten ${a.n} Marken lagen im Median nur
    <b>${a.medianAbstandS} s</b> vom Einstiegspunkt entfernt. Der
    Einstiegspunkt ist gewürfelt und liegt 30-120 s <i>neben</i> dem
    Übergang &mdash; wer dort markiert, gibt den Würfel zurück, nicht die
    Stelle.<br><br>
    Geh mit dem Schieber oder den Sprungtasten wirklich zu der Stelle, wo der
    Übergang beginnt. Wenn das gerade nicht geht: lieber abbrechen und später
    weitermachen. Der Stand bleibt gespeichert.</div>`;
}

function spring(d){ if(audio) audio.currentTime = Math.max(0, audio.currentTime + d); }
function zumMarker(){
  if(!audio) return;
  zumMarkerGenutzt = true;          // fuer die Anker-Diagnose
  audio.currentTime = aufgaben[pos].engineSec;
}
function greife(){
  if(!audio) return;
  gewaehlt = audio.currentTime;
  document.getElementById("gewaehlt").textContent = "gesetzt bei " + fmt(gewaehlt);
  document.getElementById("griff").classList.add("hat");
}
function waehle(w){
  was = w;
  for (const o of ["a_raus","b_rein","beides"])
    document.getElementById("w_"+o).classList.toggle("gewaehlt", o===w);
}

async function sichern(){
  if (!audio){ return; }
  if (gewaehlt === null){
    alert("Bitte zuerst auf \u201eHier beginnt der Übergang\u201c drücken.");
    return;
  }
  if (!was){ alert("Bitte zuerst angeben, was du markierst."); return; }
  const a = aufgaben[pos];
  const antwort = await fetch(`/relabel/${AID}/antwort`, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({index:a.index, sec:gewaehlt, was:was,
                          startSec:a.startSec, zumMarker:zumMarkerGenutzt})
  });
  try { zeigeAnker((await antwort.json()).anker); } catch(e) {}
  erledigt.add(a.index);
  pos += 1;
  while (pos < aufgaben.length && erledigt.has(aufgaben[pos].index)) pos += 1;
  zeichne();
}
start();
</script></body></html>"""
