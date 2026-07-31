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


def _aufgaben(analysis_id: str) -> list[dict]:
    """Uebergaenge der zweiten Runde - OHNE die Antwort aus Runde 1."""
    ergebnis = job_manager.get_result(analysis_id)
    if ergebnis is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    runde1 = feedback_store.load_feedback(analysis_id)
    verdicts = runde1.get("verdicts") or {}

    transitions = {str(t.get("index")): t for t in (ergebnis.get("setTransitions") or [])}
    aufgaben = []
    for idx, v in verdicts.items():
        if v.get("verdict") != "timing_off" or v.get("correctedSec") is None:
            continue
        t = transitions.get(str(idx))
        if t is None:
            continue
        aufgaben.append({
            "index": int(idx),
            # Der Engine-Marker, den er auch in Runde 1 gesehen hat.
            "engineSec": float(v.get("midSec") or t.get("mid_sec") or 0.0),
            "trackVor": t.get("track_before") or t.get("key_before"),
            "trackNach": t.get("track_after") or t.get("key_after"),
            # correctedSec wird hier NICHT uebernommen. Nicht ausgeblendet,
            # nicht mitgeschickt - gar nicht erst eingesammelt.
        })
    return aufgaben


@router.get("/{analysis_id}/aufgaben")
def get_aufgaben(analysis_id: str) -> dict:
    aufgaben = _aufgaben(analysis_id)
    # sitzung() statt laden(): der Seed muss beim ERSTEN Aufruf festgeschrieben
    # werden, sonst mischt ein Neuladen des Browsers die Reihenfolge neu.
    stand = relabel_store.sitzung(analysis_id)
    ordnung = relabel_store.reihenfolge([a["index"] for a in aufgaben], stand["seed"])
    nach_index = {a["index"]: a for a in aufgaben}
    return {
        "analysisId": analysis_id,
        "aufgaben": [nach_index[i] for i in ordnung],
        "erledigt": sorted(int(k) for k in (stand.get("antworten") or {})),
        "gesamt": len(aufgaben),
    }


@router.post("/{analysis_id}/antwort")
def post_antwort(analysis_id: str, payload: AntwortPayload) -> dict:
    try:
        stand = relabel_store.speichern_antwort(
            analysis_id, payload.index, payload.sec, payload.was)
    except ValueError as fehler:
        raise HTTPException(status_code=422, detail=str(fehler)) from fehler
    return {"erledigt": len(stand["antworten"]), "gespeichert": payload.index}


@router.get("/{analysis_id}", response_class=HTMLResponse)
def get_seite(analysis_id: str) -> HTMLResponse:
    if job_manager.get_result(analysis_id) is None:
        raise HTTPException(status_code=404, detail="Analyse nicht gefunden.")
    return HTMLResponse(_SEITE.replace("__ANALYSIS_ID__", html.escape(analysis_id)))


# Eine Datei, kein Build, keine Abhaengigkeiten. Die Seite wird ein- oder
# zweimal benutzt - sie darf schlicht sein.
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
 .reihe{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
 .zeit{font-variant-numeric:tabular-nums;font-size:26px;font-weight:600}
 .hinweis{color:#9a9aab;font-size:13px} .fertig{color:#7ee08a}
 .balken{height:6px;background:#33333f;border-radius:3px;overflow:hidden;margin:8px 0 18px}
 .balken>div{height:100%;background:#5b46c8;width:0}
</style></head><body>
<h1>Zweite Runde &mdash; wo beginnt der Übergang?</h1>
<div class="sub">Die Reihenfolge ist gewürfelt. Deine Angaben vom ersten Mal
werden nicht angezeigt &ndash; das ist der Sinn der Sache.</div>
<div class="balken"><div id="balken"></div></div>
<div class="karte" id="karte">Lade&hellip;</div>
<div class="hinweis" id="status"></div>
<script>
const AID = "__ANALYSIS_ID__";
let aufgaben = [], pos = 0, erledigt = new Set(), was = null, audio = null;

function fmt(s){const m=Math.floor(s/60),r=Math.floor(s%60);return m+":"+String(r).padStart(2,"0");}

async function start(){
  const r = await fetch(`/relabel/${AID}/aufgaben`);
  const d = await r.json();
  aufgaben = d.aufgaben; erledigt = new Set(d.erledigt);
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
  was = null;
  k.innerHTML = `
    <div class="hinweis">Übergang ${pos+1} von ${aufgaben.length}
      &middot; Engine-Vorschlag bei ${fmt(a.engineSec)}</div>
    <audio id="au" controls preload="none"
           src="/analysis/${AID}/audio"></audio>
    <div class="reihe">
      <button onclick="spring(-30)">&minus;30 s</button>
      <button onclick="spring(-8)">&minus;8 s</button>
      <button onclick="spring(8)">+8 s</button>
      <button onclick="spring(30)">+30 s</button>
      <button onclick="zumMarker()">zum Engine-Vorschlag</button>
    </div>
    <div class="reihe"><span class="zeit" id="jetzt">0:00</span>
      <span class="hinweis">&larr; hier beginnt der Übergang</span></div>
    <div class="reihe hinweis">Was markierst du gerade?</div>
    <div class="reihe">
      <button id="w_a_raus"  onclick="waehle('a_raus')">A geht raus</button>
      <button id="w_b_rein"  onclick="waehle('b_rein')">B kommt rein</button>
      <button id="w_beides"  onclick="waehle('beides')">beide zusammen</button>
    </div>
    <div class="reihe"><button class="haupt" onclick="sichern()">
      Übernehmen und weiter</button></div>`;
  audio = document.getElementById("au");
  audio.addEventListener("timeupdate", () => {
    document.getElementById("jetzt").textContent = fmt(audio.currentTime);
  });
  audio.addEventListener("loadedmetadata", zumMarker, {once:true});
}

function spring(d){ if(audio) audio.currentTime = Math.max(0, audio.currentTime + d); }
function zumMarker(){ if(audio) audio.currentTime = aufgaben[pos].engineSec; }
function waehle(w){
  was = w;
  for (const o of ["a_raus","b_rein","beides"])
    document.getElementById("w_"+o).classList.toggle("gewaehlt", o===w);
}

async function sichern(){
  if (!audio){ return; }
  if (!was){ alert("Bitte zuerst angeben, was du markierst."); return; }
  const a = aufgaben[pos];
  await fetch(`/relabel/${AID}/antwort`, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({index:a.index, sec:audio.currentTime, was:was})
  });
  erledigt.add(a.index);
  pos += 1;
  while (pos < aufgaben.length && erledigt.has(aufgaben[pos].index)) pos += 1;
  zeichne();
}
start();
</script></body></html>"""
