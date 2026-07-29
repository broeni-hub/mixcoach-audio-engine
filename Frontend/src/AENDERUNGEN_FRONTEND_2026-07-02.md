# MixCoach Frontend: Was wurde geändert (2026-07-02)

Passend zum neuen ehrlichen Backend-Vertrag ("honest-v2").

## 1. Wichtigster Fund: Das Frontend hat das echte Backend nie benutzt

Beim Upload einer einzelnen Datei rief das Frontend `POST /analyze/transition`
auf — diesen Endpunkt gibt es im Python-Backend gar nicht. Ergebnis: Der
Aufruf schlug immer fehl und die App fiel still auf die Browser-Demo-Analyse
zurück. **Jede bisherige "echte" Analyse war in Wahrheit die Demo.**

Behoben: Einzeldatei-Uploads gehen jetzt an `POST /analyze/set` (den
Endpunkt, den die Engine wirklich anbietet). Zwei-Datei-Uploads
(/analyze/transition) bleiben vorbereitet, bis das Backend sie kann.

## 2. Typen an den ehrlichen Vertrag angepasst

`AnalysisScores` und Co. erlauben jetzt `null` = "nicht gemessen".
Neue Felder: `analysisWarnings` (Warnungen der Engine), `notMeasured`
(Liste ungemessener Metriken), `source` ("engine" oder "browser" — damit
man echte Analysen von Demo-Läufen unterscheiden kann).

## 3. Alle Anzeigen und Berechnungen null-sicher gemacht

- Analysen-Liste, Dashboard, Settings: "—" statt leerer Zahl; Badges für
  ungemessene Scores werden ausgeblendet
- Fortschritts-Seite und Dashboard: Durchschnitte werden nur noch über
  wirklich gemessene Werte gebildet (null zählt nicht mehr als 0 — das
  hätte den Schnitt künstlich nach unten gezogen)
- Achievements: "nicht gemessen" zählt nicht mehr als Score 0
- Coach-Empfehlung: ein ungemessener Skill kann nicht mehr fälschlich
  als "schwächster Skill" ausgewählt werden
- Report-Seite: neuer oranger Hinweis-Kasten zeigt die
  `analysisWarnings` der Engine an

## 4. Aufgeräumt

Debug-`console.log`-Blöcke aus dem Engine-Client entfernt.

## Geprüft

TypeScript-Check über das ganze Projekt: 0 Fehler durch diese Änderungen
(verbleibende Meldungen existierten vorher bzw. sind Artefakte der
Prüfumgebung ohne Vite-Konfiguration).

## Offene Punkte (bewusst nicht angefasst)

- Die Browser-Demo-Engine (`buildAnalysisResult`) erzeugt weiter teils
  erfundene Kurven/Scores als Fallback. Sie ist als Demo gekennzeichnet,
  aber die Ergebnisse landen im selben Verlauf wie echte. Mit dem neuen
  `source`-Feld kann die UI sie künftig markieren (z.B. "Demo"-Badge).
- `remoteProvider` erwartet Job-Endpunkte (`/analysis/jobs`), die das
  Backend nicht hat — läuft heute ins Leere, stört aber nicht.
- Die Pipeline-Stages in der Upload-Animation (Key, Phrasen, Beatgrid)
  versprechen mehr, als die Engine heute misst.
