# Befundstand — jeder Befund gegen den Ist-Stand geprüft

**Stand: 14.08.2026, vormittags** · Grundlage: `PROJEKT_REVIEW_2026-08-13.md`,
`ARCHITEKTUR_BEWERTUNG_2026-08-13.md`, `PROMPT_PUNKT3_COACH_2026-08-13.md`

Jede Zeile heute am Repo nachgemessen. Wo etwas nicht am Repo prüfbar ist
(z.B. eine Vorführung im Browser), steht das ausdrücklich dabei.

**Bilanz: von 25 geprüften Befunden sind 8 gelöst, 2 teilweise, 15 offen.**
Der eine, der heute blockierte, ist gelöst.

---

## A · Die zwei fundamentalen Architektur-Änderungen

| | Befund | Stand | Beleg |
|---|---|---|---|
| **F1** | Eine Analyse hat keinen Ort, an dem sie wahr ist | ✅ **gelöst** | `a814117`, `4b2ced8`, `819ee71`, `3002c11` |
| **F2** | Die Engine kennt keinen Nutzer | ❌ **nicht begonnen** | 0 `Depends` in `main.py`, `allow_origins=["*"]`, kein `user_id` |

**F1 im Einzelnen:**

- Ein Ground-Truth-Stamm (45), ein Ergebnis-Stamm (51). Zweiter Stamm in
  `_archiv_2026-08-13/` mit `LIESMICH.md`.
- Drei von Hand gesetzte Labels aus dem zweiten Stamm gerettet, neun Konflikte
  in `KONFLIKTE.md` dokumentiert statt geraten.
- `Frontend/src/lib/scoring-version.ts` — `versionVon`, `loestAb`,
  `mitNutzerstand`. Angewendet an vier Stellen. 15 Frontend-Tests (vorher 7).
- Die Report-Seite holt beim Öffnen nach (`app.analyses.$id.tsx:88–96`).

**F2 ist nicht versäumt** — der Auftrag sah F1 zuerst vor und hielt fest, dass
F1 allein ein vollständiges Ergebnis ist.

---

## B · Die sechs Strukturbefunde aus der Architekturbewertung

| | Befund | Stand |
|---|---|---|
| **S1** | Korrigierter Report erreicht den Nutzer nicht | ✅ **gelöst** |
| **S2** | Backend kennt keinen Nutzer | ❌ offen (= F2) |
| **S3** | Zwei Analysatoren, LLM-Coach im falschen Pfad | ⚠️ **teilweise — und mein Befund war zu scharf**, siehe unten |
| **S4** | Datenstamm ist vier Dinge gleichzeitig | ⚠️ **halb gelöst** |
| **S5** | Track-IDs hängen am Pfad-String | ❌ offen, **ein Teilschritt getan** |
| **S6** | Toter Vorfahr + falsche Karte in `CLAUDE.md` | ❌ **unverändert offen** |

**S3 — Korrektur an meinem eigenen Befund.** Ich hatte geschrieben, der
LLM-Coach sei „vollständig toter Code" und werde „an genau einer Stelle
aufgerufen: `analysis-engine.ts:278`". **Das war falsch.** In meinem
Suchbefehl hatte ich `CoachFeedbackCard.tsx` ausgeschlossen — und genau dort
liegt der zweite Aufrufer:

```
CoachFeedbackCard.tsx:53   getCoachFeedbackFn       (lädt vorhandenes Feedback)
CoachFeedbackCard.tsx:90   generateCoachFeedbackFn  (Knopf: erzeugen)
app.analyses.$id.tsx:277   <CoachFeedbackCard analysis={legacy} />
```

Richtig ist: Der LLM-Coach ist **über einen Knopf auf der Report-Seite
erreichbar**, auch für Engine-Analysen. Nur die **automatische** Erzeugung nach
der Analyse hängt im Browser-Notpfad. Praktisch läuft er trotzdem nicht — es
fehlt `LOVABLE_API_KEY` in `Frontend/.env` (heute nachgesehen: nicht vorhanden).

Unverändert offen: Der Browser-Notpfad existiert weiter (`runPipeline`,
544 Zeilen in `audio-analysis.ts` + `set-analysis.ts`), und die automatische
Coach-Erzeugung hängt dort. Gehört zum Punkt-3-Auftrag, der noch nicht gelaufen
ist.

**S4 — halb gelöst.** Der Doppelstamm ist weg, das war die Hauptschadensquelle.
Unverändert: `daten/analysis_results/` enthält weiter 51 Reports **und** 46
Audiodateien **und** die Trainingsgrundlage nebeneinander.

**S5 — ein Teilschritt in die richtige Richtung.** Die Track-ID ist weiter
`md5(path)[:16]` (`manager.py:57`). Aber der Feature-Cache läuft seit `8deacae`
auf einen **Inhalts-Schlüssel** statt auf Datei-Zeitstempel — dieselbe Denkweise,
angewandt auf einen kleineren Gegenstand. 3070 Zeilen gegen die aktuelle Ground
Truth nachgerechnet, 0 Abweichungen.

**S6 — unverändert.** `app/experimental/` liegt mit 39 Dateien da, von außen
**0 Importe**. `CLAUDE.md:33` nennt den Ordner weiter als „Kandidatensuche für
Übergänge", und `CLAUDE.md:113` hängt die 30-Sekunden-Diagnose an
`detect_transition_zones()` — die tote Frühfassung. Die lebende Suche ist
`app/audio/set_analyzer_helpers.py:detect_set_transition_zones()`.
**Aufwand: eine Stunde. Von allen offenen Punkten der billigste.**

---

## C · Die Befunde aus dem Projekt-Review

| | Befund | Stand |
|---|---|---|
| **5a** | Ehrlichkeitslinie im Code, nicht in den Daten | ✅ **gelöst** — 51/51 `beatmatching: null`, dazu 16 archivierte |
| **5b** | Echte Tracknamen an 19 % der Übergänge | ❌ **unverändert 19,0 %** (82/432) |
| **5c** | `start_sec` schlägt `mid_sec` — Widerspruch ungeklärt | ❌ offen (= P1) |
| **5d** | Die Arbeit liegt nur auf dieser Platte | ❌ **schlechter: `main` 10 Commits hinterher**, drei Dokumente uncommittet |
| **5e** | Referenzmetrik misst noch das alte Modell (`gap=90`) | ❌ offen — keine Aufnahme mit `gap=150` analysiert |
| **5f** | Korrekturweg fehlt | ✅ **gelöst** |

---

## D · Die offenen Posten aus Abschnitt 7

### Bedingung 1 — jeder angezeigte Wert ist gemessen

| | Aufgabe | Stand |
|---|---|---|
| B1 | Ehrlichkeits-Backfill | ✅ **erledigt** |
| B2 | `quality_score` entscheiden | ❌ offen — **deine Entscheidung**, Grundlage hat sich geändert |
| B3 | `bass_overlap_score` | ❌ offen, **unverändert 15,5 %** (67/432) |
| B4 | `loudness_jump_db` | ✅ **erledigt** — 49,7 % → **86,1 %** |
| B5 | `notMeasured` dynamisch machen | ❌ offen — weiter feste Liste (`analysis_mapper.py:39`) |
| B6 | `energy_dip_pct` hochziehen | ❌ offen, **unverändert 50,5 %** (218/432) |

### Bedingung 2 — Historie überlebt einen Gerätewechsel

| | Aufgabe | Stand |
|---|---|---|
| H1 | Einmal vorführen | ❌ offen — **nicht am Repo prüfbar** |
| H2 | `SUPABASE_SERVICE_ROLE_KEY` eintragen | ❌ offen — nicht in `.env` |

### Bedingung 3 — drei Sets zeigen eine Entwicklung

| | Aufgabe | Stand |
|---|---|---|
| — | Nachweis der Entwicklung | ✅ **erbracht** — r = −0,622 über 13 Aufnahmen |
| E2 | Fortschritts-Radar auf den Pegelsprung stellen | ❌ offen — der Wert kommt in keiner Fortschritts-Ansicht vor |
| E3 | Die Vorbehalte prüfen (n = 13, 22 Tage, ein Rater) | ❌ offen |

### Parallel

| | Aufgabe | Stand |
|---|---|---|
| P1 | `start_sec` vs. `mid_sec` zu Ende messen | ❌ offen |
| P2 | Referenzmetrik gegen `gap=150` | ❌ offen |
| P3 | Zweite, blinde Labelrunde | ❌ offen — **dein Abend** |
| P4 | Doppelstamm, Streudateien | ✅ **erledigt** |
| P5 | Neun Bewertungskonflikte entscheiden | ❌ offen — `KONFLIKTE.md` meldet weiter „Offen: **9**" |
| P6 | Pushen | ❌ offen — **10 Commits** |

---

## E · Erlebnis-Punkt 3 (Coach) — der Auftrag ist noch nicht gelaufen

`PROMPT_PUNKT3_COACH_2026-08-13.md` liegt bereit, ist aber nicht abgearbeitet.
Alle vier Befunde daraus bestehen unverändert:

| Befund | Stand |
|---|---|
| Fest verdrahtete Vorlage-Übung im Mapper | ❌ **51 von 51 Reports** tragen ausschließlich „Transition Review" |
| `coach/profile.py` rankt nach `quality_score` (ρ +0,018) | ❌ unverändert |
| `transition_quality._feedback()` baut auf `beats_off` und `bpm_drift` | ❌ unverändert, 34 Fundstellen |
| Zwei Regelwerke (Python + Supabase-KB) | ❌ unverändert |

**Eine Änderung am Auftrag ist fällig, bevor er läuft:** Die Übungstabelle in
Job 1 führt `beat_alignment_score` als Regel 1 und den Pegelsprung als Regel 2.
Nach der Messung vom 13.08. dreht sich das — `|loudness_jump_db|` trägt mit
ρ = −0,377 stärker als `beat_alignment` (+0,315) und ist mit 86 % befüllt.

---

## F · Die Gegenmaßnahmen gegen die Korrektur-Schleife

| Maßnahme | Stand |
|---|---|
| Doppelstamm auflösen | ✅ **erledigt** |
| Selbsttest zur Pflicht am Sitzungsanfang | ⚠️ nicht am Repo prüfbar — das **Werkzeug** ist deutlich ausgebaut (Befüllung, Streuung, Scoring-Versionen) |
| Push nach jeder Sitzung | ❌ **nicht eingehalten** — 10 Commits offen |
| `memory.md` gegen das Repo abgleichen | ❌ offen — `tools/real_mix_labeler/` und `tools/active_learning/` existieren weiterhin nicht |

**Zusätzlich offen:** Beide Aufträge verlangten einen Bericht
`SITZUNG_<datum>.md`. Es gibt keinen. Die Begründungen stehen ausschließlich in
den Commit-Meldungen — die sind ungewöhnlich gut, aber sie sind nicht das
Format, das eine spätere Sitzung liest. Genau daraus ist am 10.08. schon einmal
ein übersehener Arbeitsstand entstanden.

---

## G · Was ich selbst falsch hatte

Der Vollständigkeit halber, und weil es zum Markenkern gehört:

1. **„`beat_alignment_score` ist die einzige Dimension mit Signal"**
   (`ARCHITEKTUR_BEWERTUNG` §3, S3). Widerlegt: `|loudness_jump_db|` trägt mit
   ρ −0,377 stärker als +0,315 bei gleichem n. Am 13.08. unabhängig
   nachgerechnet.
2. **„Der LLM-Coach ist vollständig toter Code, ein einziger Aufrufer"**
   (`PROMPT_PUNKT3_COACH` Befund 1). Falsch — `CoachFeedbackCard` ruft ihn über
   einen Knopf auf der Report-Seite. Mein Suchbefehl hatte die Datei
   ausgeschlossen. Richtig ist: die **automatische** Erzeugung hängt im
   Notpfad.
3. **„Der Korrekturweg wurde nicht gebaut"** (Meldung vom 13.08. abends). Eine
   zu frühe Momentaufnahme — der Commit kam um 21:06, meine Messung lag davor.
4. **„B1 kostet einen halben Tag"** (Review §7, erste Fassung). Der Backfill
   selbst schon, seine Wirkung hing aber an F1.2.

Alle vier sind in den betroffenen Dokumenten korrigiert.

---

## H · Was als Nächstes ansteht

**Heute, zusammen unter zwei Stunden:**

1. **Pushen** (P6, 5 min) — 10 Commits, darunter der Fortschrittsnachweis.
2. **S6 auflösen** (1 h) — `app/experimental/` archivieren, `CLAUDE.md:33`
   und `:113` auf `set_analyzer_helpers.py` umschreiben.
3. **Korrekturweg vorführen** (½ h) — Report öffnen, Backfill fahren, neu laden
   ohne Cache zu löschen.
4. **Die neun Konflikte entscheiden** (P5, ½ h) — **nur du**.

**Danach:** Punkt-3-Auftrag starten, mit der gedrehten Regelreihenfolge.
