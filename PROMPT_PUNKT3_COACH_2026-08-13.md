# Arbeitsauftrag — Erlebnis-Punkt 3 (Coach) fertigstellen

**Für Claude Code · erstellt 13.08.2026 · Grundlage: `PROJEKT_REVIEW_2026-08-13.md`**

Lies zuerst `CLAUDE.md`, dann `PRODUKTVISION.md` Abschnitt „Zielerlebnis" Punkt 5
und 6, dann `PROJEKT_REVIEW_2026-08-13.md` Abschnitt 3 und 7.

---

## Warum dieser Auftrag

Erlebnis-Punkt 3 steht seit dem 30.07. unverändert bei **30 %** — er ist die
größte Einzellücke zur Vision. Die Vision verspricht:

> „Mixe Übergang 3 aus deinem Set vom 04.07. noch einmal — gleiche Tracks,
> Ziel: unter 4 Beats Abweichung."

Was in allen 50 Reports tatsächlich steht:

> „Transition Review — Listen to the detected transition points and check
> whether the phrase timing feels natural."

Das ist eine allgemeine Aufgabe ohne Bezug zum eigenen Material, und sie schickt
den DJ ausgerechnet zu dem Wert, den K1 als nicht messend belegt hat.

**Der Auftrag lautet nicht „bau einen Coach".** Er lautet: **die drei
Coach-Systeme, die es bereits gibt, auf einen tragenden Boden stellen und auf
einen Weg zusammenführen.** Es fehlt weniger Code, als es aussieht.

---

## Was ich am 13.08. gemessen habe — bitte nachprüfen, nicht glauben

Die folgenden fünf Befunde sind die Grundlage des Auftrags. **Job 0 besteht
darin, sie zu widerlegen oder zu bestätigen.** Wenn einer falsch ist, sag es und
halte an, bevor du darauf baust — genau diese Reihenfolge ist in den letzten
zwei Wochen mehrfach übersprungen worden und hat jedes Mal Arbeit gekostet.

### Befund 1 — Es gibt vier Coach-Systeme, und das beste läuft nie

| System | Ort | Läuft im Normalbetrieb? |
|---|---|---|
| **A · Fest verdrahtete Übung** | `app/api/analysis_mapper.py:128` | **ja, immer** — steht in allen 50 Reports |
| **B · Set-übergreifendes Profil** | `app/coach/profile.py:232` `_highlights_and_exercises()` | ja, über `/coach/profile` |
| **C · Regelwerk + LLM** | `Frontend/src/lib/coaching.ts` + `coach-feedback.functions.ts` | **nein — toter Code** |
| **D · Statische Übungsbibliothek** | `Frontend/src/lib/coach.ts` `EXERCISE_LIBRARY` (10 Übungen) | ja, in `app.training.tsx` |

**System C ist der wichtigste Befund.** `generateCoachFeedbackFn` wird an genau
einer Stelle aufgerufen: `Frontend/src/lib/analysis-engine.ts:278`, innerhalb
von `runPipeline()`. Diese Funktion setzt zwei Zeilen vorher
`result.engine = "local"` — sie **ist** der Browser-Notpfad. Und
`app.upload.tsx:97` verhindert mit dem Upload-Preflight (`engineReachable()`)
genau, dass dieser Pfad jemals läuft.

Das heißt: Ein vollständig gebauter LLM-Coach mit sauberem Prompt, Retry-Logik,
Zod-Schema, Fehlerprotokoll und deterministischem Fallback (396 Zeilen) liegt
hinter einem Weg, den ein anderer Fix bewusst zugemauert hat. Dasselbe gilt für
das Supabase-Regelwerk (`evaluateRules`, `persistFindings`).

Prüfe das nach:
```bash
grep -rn "generateCoachFeedbackFn\|persistFindings\|evaluateRules" Frontend/src
```
Erwartung: nur Treffer in `analysis-engine.ts` (Notpfad) und in den Modulen
selbst. Kein Treffer in `remoteProvider.ts`, `audioEngineClient.ts`,
`app.upload.tsx`, `analysis.processing.$jobId.tsx`.

### Befund 2 — Der Coach-Text ruht auf den widerlegten Größen

K1 hat `scores.beatmatching` und `scores.timing` auf `None` gesetzt. Die
**Feedback-Sätze je Übergang** wurden dabei nicht angefasst.
`app/audio/transition_quality.py:_feedback()` baut sie weiter aus `beats_off`
und `bpm_drift`; `app/audio/coach_summary.py:24/29` hebt sie in
`positives`/`improvements`, und `analysis_mapper.py` reicht sie als
`strengths`/`weaknesses`/`feedback` ins Frontend.

Wörtlich aus einem echten Report:
> „Uebergang bei 02:55 sitzt: Timing, Tempo und Energie passen zusammen."

`bpm_drift` ist in 89 % der Übergänge exakt 0,0, `phrase_beats_off` erklärt
nichts (ρ = 0,014). Der Satz lobt den DJ für zwei Zahlen, die nichts sagen.

### Befund 3 — Welche Messwerte tragen

Gemessen am 11.08. an 146–170 bewerteten Übergängen (`SITZUNG_2026-08-10.md`,
Nachtrag 11.08.), Befüllung heute an 431 Übergängen nachgezählt:

| Messwert | Spearman gegen dein Urteil | befüllt |
|---|---|---|
| `beat_alignment_score` | **+0,315** | 86,3 % |
| `exit_quality_score` | +0,100 | 76,6 % |
| `vocal_overlap_score` | +0,047 (Median 100 — feuert nie) | 80,7 % |
| `phrase_alignment_score` | −0,037 | 100 % |
| `harmonic_clash_score` | −0,137 | 80,7 % |
| `quality_score` (Kopfzahl) | +0,014 | 100 % |
| `loudness_jump_db` | nicht geprüft, physikalisch eindeutig | 49,7 % |
| `energy_dip_pct` | nicht geprüft | 50,3 % |
| `bass_overlap_score` | nicht geprüft | **15,5 %** |
| Tonart / Camelot-Abstand | — | 100 % |
| `track_in` / `track_out` | — | **19,0 %** |

**Genau eine Dimension trägt messbar: `beat_alignment_score`.** Alles andere ist
entweder unbefüllt, ungeprüft oder gemessen wirkungslos.

### Befund 4 — Zwei Regelwerke, die nichts voneinander wissen

`app/audio/rule_engine.py` (Python, 4 set-weite Regeln, feuert in 25 von 50
Reports) und die Supabase-Tabelle `coaching_rules` (`coaching.ts`, nur im
Notpfad). Die Python-Regeln liefern in `findings` teils identischen Text für
`diagnosis` und `fix` — prüfe das an einem Report.

### Befund 5 — Ein Backfill ohne Audio ist möglich

Alles, was für Übungen gebraucht wird, steht bereits in
`daten/analysis_results/*.json` unter `setTransitions`: `index`, `mid_sec`,
`start_sec`, `beat_alignment_score`, `loudness_jump_db`, `camelot_before/after`,
`track_in`/`track_out`. **Kein Audio, kein Demucs, keine GPU.** Der Composite-
Backfill vom 11.08. brauchte 78 Minuten, weil er Stems trennte — dieser hier
läuft in Sekunden.

---

## Die Regeln, die für diesen Auftrag gelten

Aus `CLAUDE.md`, unverändert:

- **`app/audio/scoring/*` nicht anfassen.**
- **Bestehende API-Endpoints und Frontend-Seiten nicht verändern.** Für diesen
  Auftrag heißt das: Du darfst den **Inhalt** von Feldern ändern, die eine Seite
  bereits rendert (`exercises`, `strengths`, `weaknesses`, `feedback`). Willst du
  eine Seite oder einen Endpoint ändern, ist das ein **Checkpoint** — halte an
  und frag.
- **Ehrlichkeitslinie:** nichts anzeigen, was nicht gemessen wurde.
- **Kein Feature still im Live-Pfad**, das langsam ist oder unsichere Ergebnisse
  liefert.
- Kommentare und Doku auf Deutsch.
- Sebastian ist kein Entwickler: alles Bedienbare als `.command`.

Und eine Regel speziell für diesen Auftrag:

> **Jede erzeugte Übung muss mindestens eine Zahl nennen, die im selben Report
> steht.** Findet sich für einen Übergang keine solche Zahl, wird **keine Übung
> erzeugt** — und die Lücke wird sichtbar gemacht, nicht mit einer Vorlage
> gefüllt. Eine allgemeine Übung ist schlimmer als keine, weil sie so aussieht,
> als hätte das Tool etwas gemessen.

---

## Der Ausgang, der diesen Auftrag widerlegt

Bau das zuerst, nicht zuletzt. **Job 1 ist ein Zähltest, kein Feature.**

Wenn sich zeigt, dass für **weniger als die Hälfte** der 431 Übergänge
überhaupt eine belegbare, konkrete Übung erzeugbar ist — weil
`loudness_jump_db` bei 50 %, `bass_overlap_score` bei 15 % und Tracknamen bei
19 % stehen — dann ist die ehrliche Antwort **nicht** „bau den Coach trotzdem",
sondern:

> **Punkt 3 ist heute nicht baubar. Zuerst B3 und B4 aus dem Review (Messwerte
> füllen), dann wieder hierher.**

Melde das dann als Ergebnis und halte an. Ein Coach, der in der Hälfte der Fälle
schweigen muss, ist kein fertiger Punkt 3 — aber es ist ein sauberes Ergebnis,
und es ist in zwei Stunden zu haben statt in zwei Wochen.

---

## Die Jobs

### Job 0 · Befunde prüfen — vor allem anderen

Prüfe die fünf Befunde oben am Code und an den Daten. Belege jede Bestätigung
mit **Datei:Zeile** oder einer ausgezählten Zahl. Widerlege, was falsch ist.

**Checkpoint:** Bericht in den Chat, dann warten. Wenn Befund 1 falsch ist —
wenn der LLM-Coach doch im Engine-Pfad läuft — ändert das den ganzen Auftrag.

---

### Job 1 · Der Zähltest: wie viele Übungen sind überhaupt belegbar?

Ein Skript, das **ohne Audio** über `daten/analysis_results/*.json` läuft und je
Übergang beantwortet: *Welche konkrete, mit einer Zahl belegte Übung ließe sich
hier erzeugen?*

Kandidaten-Regeln, absteigend nach Belastbarkeit — nimm die erste, die greift:

| # | Bedingung | Übungstext (Muster) | Deckung erwartet |
|---|---|---|---|
| 1 | `beat_alignment_score` < Schwelle | „Bei **{zeit}** ({track_out} → {track_in}) liegt die Puls-Regelmäßigkeit im Übergangsfenster bei **{wert}/100**. Mix ihn nochmal, Ziel über {ziel}." | 86 % |
| 2 | `loudness_jump_db` > Schwelle | „Bei **{zeit}** kam der neue Track **{wert} dB** lauter rein. Ziel: unter 1 dB." | 50 % |
| 3 | Camelot-Abstand groß | „Bei **{zeit}** liegen {key_a} und {key_b} **{n} Schritte** auseinander." | 100 % |
| 4 | `bass_overlap_score` < Schwelle | „Bei **{zeit}** lagen zwei Bässe {n} s übereinander." | 15 % |

Die Schwellen **nicht raten**: leite sie aus der Verteilung über alle 431
Übergänge ab (z.B. schlechtestes Quintil) und schreib die Herleitung als
Kommentar daneben.

**Was das Skript ausgeben muss:**

```
Übergänge gesamt:                431
  mit mindestens einer belegten Übung:   ___  (__%)
  davon mit echten Tracknamen:           ___  (__%)
  ohne jede belegbare Übung:             ___  (__%)

Verteilung nach Regel:  R1 ___  R2 ___  R3 ___  R4 ___
Aufnahmen mit ≥3 belegten Übungen:  ___ von 21
```

**Checkpoint — hier hängt alles dran.** Liegt die Deckung unter 50 %, gilt der
Abschnitt „Der Ausgang, der diesen Auftrag widerlegt". Halte an und melde.

---

### Job 2 · Die erzeugten Übungen in die Reports bringen

Erst wenn Job 1 grün ist.

**2a — Erzeugung im Live-Pfad.** `app/api/analysis_mapper.py:128` ersetzt die
fest verdrahtete Übung durch die in Job 1 entwickelte Logik. Neues Modul
`app/coach/uebungen.py` (nicht in `app/audio/scoring/`, das ist gesperrt).

Jede Übung trägt:
```
{ "title", "description", "analysisId", "transitionIndex",
  "atSec",                       # anspringbar im Player
  "metric", "value", "target",   # die Zahl, auf der sie ruht
  "xp" }
```
`metric`/`value` sind **Pflicht**. Keine Übung ohne Zahl.

**2b — Ein Backfill über die 50 vorhandenen Reports**, ohne Audio.
`tools/backfill_uebungen.py`, mit `--dry-run` als Vorgabe.

**Zieh die offene Aufgabe B1 aus dem Review hier mit rein** — es ist derselbe
Durchlauf über dieselben Dateien:
- `scores.beatmatching` und `scores.timing` auf `None` (der Mapper tut das seit
  dem 31.07., die 50 gespeicherten Reports tragen weiter 100 bzw. 61)
- `notMeasured` auf die Fünfer-Liste aus `analysis_mapper.py:39`

Danach muss gelten: `beatmatching = None` in **50 von 50** Reports.

**2c — Die Feedback-Sätze je Übergang** (`transition_quality.py:_feedback()`,
Befund 2) von `beats_off` und `bpm_drift` befreien. Was übrig bleibt, ist
weniger Text — das ist richtig so. Prüfe danach, was `coach_summary.py`
`positives`/`improvements` noch liefert; wenn eine Liste leer wird, sag es
ehrlich („zu diesem Set lässt sich aus den vorhandenen Messungen nichts
Konkretes sagen") statt sie mit Allgemeinplätzen zu füllen.

**Akzeptanz, maschinell prüfbar:** Über alle Reports nach dem Backfill gilt für
**jede** angezeigte Übung und **jeden** Feedback-Satz: die genannte Zahl steht
im selben Report unter demselben `transitionIndex`. Schreib den Test
(`tests/test_uebungen_belegt.py`), er muss fehlschlagen, wenn jemand später eine
Vorlage einbaut.

---

### Job 3 · Das Profil neu ranken

`app/coach/profile.py:232` wählt die drei schwächsten Übergänge über
`quality_score` (ρ = 0,014) und begründet über `phrase_beats_off` (ρ = 0,014).
Beide ersetzen durch die tragende Größe aus Job 1.

Die gute Struktur dort — drei Übungen aus **möglichst verschiedenen Sets**,
Tracknamen wo vorhanden, `startSec`/`midSec` zum Anspringen — bleibt. Es
wechselt nur, wonach sortiert wird.

---

### Job 4 · Die Entscheidung zum LLM-Coach vorbereiten

**Nicht bauen. Vorlegen.** Das ist eine Produktentscheidung, und die trifft
Sebastian.

Leg drei Wege hin, jeden mit Aufwand, Risiko und dem, was er dem DJ bringt:

- **A · Stilllegen.** System C aus `analysis-engine.ts` entfernen, den Ordner
  als unbenutzt kennzeichnen. Ehrlich, kostet nichts, nimmt eine Möglichkeit weg.
- **B · In den Engine-Pfad heben.** `generateCoachFeedbackFn` nach der
  Engine-Analyse aufrufen (dort, wo der Report ankommt), gespeist aus den
  Werten, die Job 1 als tragend identifiziert hat. Braucht: angemeldeten Nutzer
  (steht seit 13.08.), `LOVABLE_API_KEY` in `Frontend/.env`, und für das
  Fehlerprotokoll (`coach_feedback_failures`, Zeile 332) den
  `SUPABASE_SERVICE_ROLE_KEY`. **Beides kann nur Sebastian eintragen.**
- **C · Regelwerk ja, LLM nein.** Nur `evaluateRules` + `persistFindings` in den
  Engine-Pfad, LLM bleibt aus. Deterministisch, kein Halluzinationsrisiko,
  keine API-Kosten, keine Schlüssel.

Nenne dazu, welche der zwei Regelwerke aus Befund 4 künftig gelten soll — zwei
parallel sind der Doppelstamm-Fehler in neuer Form.

Prüf außerdem, ob der Prompt in `coach-feedback.functions.ts` noch stimmt: Er
nennt heute `bass_clash_score` und schreibt dem Modell vor, Tempo-Drift und
Phrasen-Alignment **nicht** zu kommentieren (K1, Zeile 135). `beat_alignment` —
die einzige tragende Dimension — kommt darin **nicht vor**. Das wäre bei Weg B
zu ergänzen.

---

### Job 5 · Dieselbe Übung über Sets hinweg

Der kleinste Schritt, der Punkt 3 mit Punkt 4 verbindet und auf **Bedingung 3
der Live-Schwelle** einzahlt („drei Sets desselben DJs zeigen eine Entwicklung").

Wenn dieselbe Übung — gleiche `metric`, ähnlicher Übergangstyp — in mehreren
Sets auftaucht, zeig die Entwicklung des Werts über die Zeit statt einer
isolierten Aufgabe.

**Zwei harte Bedingungen, sonst lügt die Kurve:**
1. Nur Reports mit **gleicher `scoringVersion`** vergleichen
   (`app/audio/pipeline/scoring_version.py:vergleichbar()`). Heute ist **kein
   einziger** der 50 Reports gestempelt — die Funktion gibt für alle `False`
   zurück. Das ist richtig so und darf nicht umgangen werden.
2. Deshalb ist Job 5 **erst nach F1 aus dem Review** (drei Sets neu analysieren)
   wirklich vorführbar. Bau die Logik, aber zeig sie nur, wenn sie greift — und
   sag im UI ehrlich, warum sie schweigt.

---

### Job 6 · Der Test, der zählt

Maschinelle Belegpflicht (Job 2) beweist, dass keine Zahl erfunden ist. Sie
beweist nicht, dass das Coaching **nützlich** ist. Dafür gibt es genau einen
Weg, und er kostet Sebastian einen Abend:

Bau ein kleines Blind-Instrument nach dem Muster von
`MixCoach-Zweitrunde.command` — **`MixCoach-Uebungen-Bewerten.command`**:

- 20 Übergänge, je zwei Übungstexte: der alte (Vorlage) und der neue (belegt),
  Reihenfolge gewürfelt, Herkunft **nicht sichtbar**
- Frage: *„Welcher Hinweis würde dich beim nächsten Mix mehr verändern?"*
- Ergebnis nach `daten/uebungen_bewertung/`, Auswertung als Skript

Dasselbe Blindheits-Prinzip wie bei der zweiten Labelrunde, dieselben Prüfungen:
kein Herkunftshinweis im HTML, kein Feldname, der ihn verrät. Schreib den Test
dafür.

**Ohne diesen Vergleich ist „Punkt 3 auf 60 %" eine Behauptung.**

---

## Reihenfolge und Checkpoints

```
Job 0  Befunde prüfen            → CHECKPOINT (warten)
Job 1  Zähltest                  → CHECKPOINT (warten, Abbruchkriterium!)
Job 2  Übungen + Backfill + B1   → Tests grün, dann weiter
Job 3  Profil neu ranken
Job 4  Entscheidungsvorlage LLM  → CHECKPOINT (Sebastians Entscheidung)
Job 5  Übung über Sets           → nur bauen, nicht vorführen (braucht F1)
Job 6  Blind-Instrument
```

**Nicht am Stück durchlaufen.** Bei Job 0 und Job 1 wirklich anhalten. Der
Fehler der letzten zwei Wochen war nicht schlechte Arbeit, sondern Arbeit, die
auf einer ungeprüften Annahme aufsetzte.

---

## Was am Ende dastehen muss

1. `beatmatching = None` in **50 von 50** Reports (B1 aus dem Review erledigt).
2. Jede angezeigte Übung nennt eine Zahl, die im selben Report steht — und ein
   Test verhindert den Rückfall.
3. Wo keine Zahl da ist, steht **keine Übung** — und die Lücke ist sichtbar.
4. 226 Tests weiter grün, plus die neuen.
5. Ein Bericht `SITZUNG_<datum>.md` nach dem Muster von `SITZUNG_2026-08-10.md`:
   was gemessen wurde, was sich geändert hat, was offen bleibt — und wo du dich
   im Lauf der Sitzung selbst korrigiert hast.
6. **Alles committet und gepusht.** Beim Schreiben dieses Auftrags lagen 7
   Commits ungepusht auf der Platte.

## Was ausdrücklich nicht Teil dieses Auftrags ist

- Kein Anfassen von `app/audio/scoring/*`.
- Keine neue Erkennung, kein Retrain, keine Grid-Search.
- Kein fünfter Blend-Onset-Schätzer.
- Kein Ausbau des Fortschritts-Radars über Job 5 hinaus.
- Keine Bezahlschranke, kein Hosting.
- **Keine Übung, die keine Zahl nennt** — auch nicht „nur als Platzhalter, bis
  die Messwerte da sind". Genau so ist die heutige Vorlage entstanden.
