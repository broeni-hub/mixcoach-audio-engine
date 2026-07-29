# MixCoach: Async-Analyse (2026-07-02)

Für: Basti | Alle 60 Tests bestehen | Backend-Version 0.2.0

## Das Problem

Ein 30-Minuten-Set braucht 2–3 Minuten Analyse. Der bisherige Upload
wartete synchron auf die Antwort — der Browser wäre in einen Timeout
gelaufen, bevor das Ergebnis da ist.

## Der neue Ablauf

1. **Upload** → Backend nimmt die Datei an, antwortet sofort mit einer Job-Nummer
2. **Hintergrund-Analyse** → läuft in einem eigenen Thread; das Frontend
   fragt alle paar Sekunden den Fortschritt ab und zeigt die Pipeline-Schritte
   an (Preprocessing → Beat-Grid → Key → Transition-Analyse → Report)
3. **Fertig** → Ergebnis wird abgeholt, gespeichert und der Report geöffnet

Neue Endpunkte: POST /analysis/jobs, GET /analysis/jobs/{id},
GET /analysis/{id}, POST /analysis/jobs/{id}/retry.
Der alte synchrone /analyze/set bleibt für kurze Dateien und Tests.

Fertige Ergebnisse landen zusätzlich als JSON im Ordner `analysis_results/`
neben dem Backend — sie überleben einen Server-Neustart.

## Frontend

- Die Engine-URL aus den **Developer Settings** aktiviert jetzt automatisch
  den Job-Flow (gleiche URL wie bisher, kein zweites Feld)
- Upload → eleganter Processing-Screen mit Fortschritt statt eingefrorenem Button
- Bugfix: Nach Job-Abschluss wird das Ergebnis jetzt wirklich in die App
  geladen (vorher: "Analysis not found")
- Ohne konfigurierte Engine-URL wie gehabt: Browser-Demo als Fallback

## So testest du es

1. Backend neu starten:
   `python -m uvicorn app.main:app --port 8000`
2. Health-Check: http://127.0.0.1:8000/health → muss `"version": "0.2.0"` zeigen
3. Frontend starten, Developer Settings: `http://127.0.0.1:8000` (falls schon
   eingetragen: nichts zu tun)
4. REC001/002/013 hochladen → Fortschrittsbalken → nach 2–3 Min. der Report

## Grenzen (bewusst)

- Job-Liste ist im Arbeitsspeicher: Server-Neustart vergisst laufende Jobs
  (fertige Ergebnisse bleiben). Für den Validierungs-Betrieb okay.
- Ein Analyse-Worker: mehrere Uploads laufen nacheinander, nicht parallel.
- "Cancel" bricht die laufende Rechnung nicht ab, sondern verwirft nur den Job.

---

# Nachtrag: Audio-Nachhören im Report (gleicher Tag)

**Warum:** Ein DJ glaubt der Bewertung erst, wenn er die Stelle hören kann.

**Backend (Version bleibt 0.2.0):**
- Das hochgeladene Audio wird nach der Analyse aufbewahrt
  (Ordner `analysis_results/`, gleiche ID wie das Ergebnis)
- Neuer Endpunkt `GET /analysis/{id}/audio` mit HTTP-Range-Support —
  der Browser kann an jede Stelle spulen, ohne die ganze Datei zu laden
- Achtung Speicherplatz: Pro Analyse bleibt das komplette WAV liegen
  (~300 MB bei 30-min-Sets). Alte Analysen ggf. manuell aus
  `analysis_results/` löschen.

**Frontend:**
- Die Waveform im Report spielt jetzt automatisch das Original vom
  Backend (vorher: "Track audio not stored locally")
- Klick auf die Waveform = an die Stelle springen; Klick auf einen
  Marker = zum Übergang springen; Shift+Ziehen = Loop (gab es schon,
  funktioniert jetzt mit echtem Audio)
- Jeder Übergang im Transitions-Explorer hat einen **Anhören-Button**
  (Liste und Detail-Panel): springt 10 Sekunden vor den Übergang und
  spielt ab — genau der Kontext, den man zum Nachvollziehen braucht

**Wichtig:** Gilt für neue Analysen (Audio wird beim Job gespeichert).
Alte Reports von vorher haben kein gespeichertes Audio — Set einfach
neu hochladen.
