# Arbeitsauftrag — Erlebnis-Punkt 3 (Coach) bauen

**Für Claude Code · erstellt 14.08.2026**
**Ersetzt `PROMPT_PUNKT3_COACH_2026-08-13.md`** — zwei Befunde darin waren
falsch, siehe Abschnitt „Was sich seit gestern geändert hat".

Lies zuerst `CLAUDE.md`, dann `BEFUNDSTAND_2026-08-14.md`, dann
`PRODUKTVISION.md` Zielerlebnis Punkt 5 und 6.

---

## Der Auftrag in einem Satz

> Der Report soll je Übergang eine Übung zeigen, die eine Zahl nennt, die im
> selben Report steht — und schweigen, wo es keine gibt.

Punkt 3 steht seit dem 30.07. bei ~30 %. Alle 51 Reports tragen dieselbe
Vorlage:

> „Transition Review — Listen to the detected transition points and check
> whether the phrase timing feels natural."

Die Vision verspricht: *„Mixe Übergang 3 aus deinem Set vom 04.07. noch einmal —
gleiche Tracks, Ziel: unter 4 Beats Abweichung."*

**Der Unterschied zu gestern: Das ist heute baubar.** F1 hat den Korrekturweg
geliefert, der Pegelsprung ist von 50 auf 86 % befüllt, und der Zähltest ist
gefahren. Die Zahlen stehen unten — Job 1 aus dem alten Auftrag entfällt.

---

## Was sich seit gestern geändert hat

**Zwei Befunde aus dem alten Auftrag waren falsch. Beide betreffen die
Grundannahme, deshalb hier ausdrücklich:**

**1 · Der LLM-Coach ist kein toter Code.** Ich hatte geschrieben,
`generateCoachFeedbackFn` werde „an genau einer Stelle aufgerufen:
`analysis-engine.ts:278`" — im Browser-Notpfad. In meinem Suchbefehl war
`CoachFeedbackCard.tsx` ausgeschlossen, und genau dort liegt der zweite
Aufrufer:

```
CoachFeedbackCard.tsx:53    getCoachFeedbackFn        lädt vorhandenes Feedback
CoachFeedbackCard.tsx:90    generateCoachFeedbackFn   Knopf "erzeugen"
app.analyses.$id.tsx:277    <CoachFeedbackCard analysis={legacy} />
```

Richtig ist: Der LLM-Coach ist **über einen Knopf auf der Report-Seite
erreichbar, auch für Engine-Analysen**. Nur die *automatische* Erzeugung nach
der Analyse hängt im Notpfad. Praktisch läuft er trotzdem nicht — **es fehlt
`LOVABLE_API_KEY` in `Frontend/.env`** (heute nachgesehen).

**2 · Die Regelreihenfolge dreht sich.** Der alte Auftrag führte
`beat_alignment_score` als Regel 1. Gemessen am 13.08. gegen Sebastians
Bewertungen, gleiches n:

```
|loudness_jump_db|   Spearman -0,377  (n=146)   Befüllung 86 %
beat_alignment       Spearman +0,315  (n=146)   Befüllung 86 %
composite            Spearman +0,146  (n=146)
quality_score        Spearman +0,018  (n=206)
```

---

## Der Zähltest — bereits gefahren, Ergebnis unten

Vier Kandidatenregeln, Schwellen aus der Verteilung über alle 432 Übergänge
abgeleitet (schlechtestes Quintil bzw. musikalisch begründet):

| Regel | Schwelle | Treffer | als erste Regel |
|---|---|---|---|
| R1 Pegelsprung | `\|loudness_jump_db\| ≥ 3,0 dB` | 109 | 109 |
| R2 Harmonie | Camelot-Abstand ≥ 3 | 189 | 150 |
| R3 Energieloch | `energy_dip_pct ≥ 28 %` | 46 | 20 |
| R4 Bass-Overlap | `bass_overlap_score ≤ 20` | 56 | 13 |

**Breite Deckung (alle vier Regeln): 292 von 432 Übergängen (67,6 %), alle 21
Aufnahmen mit ≥ 3 Übungen.** Das Abbruchkriterium des alten Auftrags (unter
50 %) ist deutlich überschritten.

**Aber — und das ist die eigentliche Erkenntnis des Zähltests:**

```
Spearman gegen human_rating:
  |loudness_jump_db|   -0,377   n=146   <- belegt
  Camelot-Abstand      +0,045   n=206   <- kein Zusammenhang
  energy_dip_pct       +0,062   n=126   <- kein Zusammenhang
  bass_overlap_score      n=2           <- nicht messbar
```

**Von den vier Regeln ist genau eine belegt.** R2 und R3 stellen Tatsachen
fest, aber es gibt keinen Beleg, dass sie den DJ stören. R4 lässt sich mit zwei
zuordenbaren Bewertungen überhaupt nicht prüfen.

**Nur mit der belegten Regel:**

```
Übergänge mit Übung:          109 / 432   (25,2 %)
Aufnahmen mit ≥ 1 Übung:       18 / 21
Aufnahmen mit ≥ 3 Übungen:     13 / 21
ohne jede Übung:               Joris-Voorn-Set, mix.wav, synthetic_mix.wav
```

Zwei der drei leeren sind Testdateien. **Praktisch: 18 von 19 echten Aufnahmen
bekommen einen Coach, 13 davon mit drei Übungen.** Das reicht zum Bauen.

---

## Die Regel, die diesen Auftrag trägt

> **Eine Übung darf nur aus einer Größe entstehen, die (a) gegen Sebastians
> Bewertungen belegt ist und (b) genug Spannweite hat, dass ein Ziel Sinn
> ergibt. Alles andere darf als Beobachtung erscheinen — nie als Aufgabe.**

Beide Bedingungen sind nötig. `beat_alignment_score` erfüllt (a) mit ρ +0,315,
aber nicht (b): σ 2,59 auf einer 0–100-Skala, Spanne 83–98. Ein Ziel „von 91 auf
95" ist keine Übung, die jemand ausführen kann. Der Pegelsprung erfüllt beide:
echte Einheit, Spanne −9,0 bis +9,3 dB, und ein Ziel („unter 1 dB"), das am
Mixer umsetzbar ist.

Wer diese Regel aufweicht, baut die Vorlage von heute in neuer Verpackung.

---

## Die Falle des Tages — bitte zuerst lesen

**Ein Backfill der Übungen erreicht den Browser nicht, solange die
Ersetzungsregel nicht greift.**

F1 hat den Korrekturweg gebaut: `scoring-version.ts:loestAb()` ersetzt eine
gespeicherte Fassung nur bei **echt höherer `scoringVersion`**. Ein
nachträglich mit Übungen versehener Report trägt weiter Version 3 — der Browser
behält seine Kopie, und die neuen Übungen kommen nie an. Das ist derselbe
Befund wie 5a, nur eine Ebene höher.

**Der naheliegende Ausweg ist eine Falle.** `SCORING_VERSION` auf 4 zu erhöhen
würde ersetzen — aber `vergleichbar()` erklärt Reports verschiedener Versionen
für **nicht vergleichbar**. Damit zerfiele der Fortschrittsnachweis über die 13
Aufnahmen (r = −0,622) in zwei unvergleichbare Hälften, sobald nur ein Teil
nachgezogen ist. Der erste belegte Fortschritt des Projekts wäre weg, und zwar
für eine Textänderung.

**Die beiden Größen tun Verschiedenes und gehören getrennt:**

| | Frage | ändert sich bei |
|---|---|---|
| `scoringVersion` | Bedeuten zwei Zahlen dasselbe? | Änderung an einer **Rechenvorschrift** |
| `reportRevision` (neu) | Ist diese Fassung neuer? | **jeder** inhaltlichen Änderung am Report |

`loestAb()` entscheidet künftig nach `reportRevision`; `vergleichbar()` bleibt
bei `scoringVersion`. Übungen sind abgeleiteter Text, keine Messung — sie
erhöhen die Revision, nicht die Scoring-Version.

**Das ist eine Architekturentscheidung. Sie gehört in Job 1, vor allem anderen,
und mit einem Checkpoint.**

---

## Die Regeln, die gelten

- **`app/audio/scoring/*` nicht anfassen.**
- Inhalte von Feldern ändern, die eine Seite bereits rendert (`exercises`,
  `strengths`, `weaknesses`, `feedback`), ist erlaubt. **Eine Seite oder einen
  Endpoint ändern ist ein Checkpoint.**
- Ehrlichkeitslinie: nichts anzeigen, was nicht gemessen wurde.
- Kein verschluckter Fehler. `except Exception: pass` ist in diesem Projekt die
  teuerste Codezeile.
- Deutsch in Kommentaren und Doku.
- Sebastian ist kein Entwickler: alles Bedienbare als `.command`.

---

## Die Jobs

### J0 · Kurzprüfung (30 Minuten, nicht länger)

Der Zähltest ist gefahren, die Befunde stehen oben. Zu prüfen bleibt nur, ob sie
am Code stimmen — mit **Datei:Zeile**:

1. `analysis_mapper.py:128` verdrahtet die eine Vorlage-Übung fest.
2. `coach/profile.py:232` rankt nach `quality_score` (ρ +0,018).
3. `transition_quality.py:_feedback()` baut Sätze aus `beats_off` und
   `bpm_drift` (34 Fundstellen).
4. `CoachFeedbackCard.tsx:90` ruft den LLM-Coach; `LOVABLE_API_KEY` fehlt.
5. `loestAb()` verlangt echt höhere `scoringVersion`.

Widerspricht etwas, sag es und halte an. Sonst weiter ohne Checkpoint.

### J1 · `reportRevision` einführen — **Checkpoint**

Siehe „Falle des Tages". Erwartet:

- `reportRevision` im Mapper, beginnend bei 1, in jeden neuen Report.
- Reports ohne Feld gelten als Revision 0.
- `loestAb()` entscheidet nach `reportRevision`; bei Gleichstand weiter nach
  `scoringVersion` (damit die F1-Tests weiter greifen).
- `vergleichbar()` bleibt unberührt.
- Tests: gleiche Revision → bleibt; höhere → ersetzt; Revision ohne Feld
  gegen Revision 1 → ersetzt; `archived` reist weiter mit.

**Anhalten und vorlegen**, bevor Job 2 beginnt. Wenn du einen besseren Weg
sieht als ein zweites Feld, leg ihn vor statt ihn zu bauen.

### J2 · Der Übungsgenerator

Neues Modul `app/coach/uebungen.py` (nicht in `app/audio/scoring/`, gesperrt).

**Übungen** entstehen ausschließlich aus dem Pegelsprung:

> „Bei **12:47** ({track_out} → {track_in}) kam der neue Track **4,2 dB** lauter
> rein. Mix ihn nochmal, Ziel: unter 1 dB."

Ohne Tracknamen (76 % der Fälle) die Übergangsnummer und die Zeit — nie ein
Platzhalter, der Namen vortäuscht.

**Beobachtungen** dürfen aus Camelot-Abstand und `energy_dip_pct` entstehen,
klar getrennt und **ohne Handlungsaufforderung**:

> „Beobachtung: 8A → 11B, drei Schritte auf dem Camelot-Rad. Ob dich das stört,
> ist an deinen Bewertungen nicht ablesbar."

Getrennte Felder, nicht dieselbe Liste. Die Oberfläche muss beides
unterscheiden können.

Jede Übung trägt: `title`, `description`, `analysisId`, `transitionIndex`,
`atSec` (anspringbar), `metric`, `value`, `target`, `xp`.
**`metric` und `value` sind Pflicht.**

Schwelle 3,0 dB mit der Herleitung als Kommentar: p75 der Verteilung liegt bei
3,5 dB, p80 bei 4,0 — und 3 dB ist die Grenze, an der `fdb1780` den
Fortschritt berichtet hat („Anteil über 3 dB von ~50 % auf ~22 %"). Dieselbe
Grenze für Messung und Coaching, nicht zwei.

### J3 · Backfill und Vorführung

`tools/backfill_uebungen.py`, ohne Audio (alles Nötige steht im JSON),
`--dry-run` als Vorgabe, plus `.command`.

Zieht **B5** gleich mit: `notMeasured` dynamisch aus dem tatsächlichen
Befüllungsstand des Reports bilden, statt der festen Fünferliste in
`analysis_mapper.py:39`.

**Die Abnahme ist die Vorführung, nicht die Testsuite** — das ist die Lehre aus
F1, wo die Tests grün waren und der Weg durch die laufende App trotzdem fehlte:

1. Report im Browser öffnen, Vorlage-Übung sehen.
2. Backfill fahren.
3. Seite neu laden, **ohne Cache zu löschen**.
4. Die belegte Übung steht da, mit Zeit und Zahl.

### J4 · Die Feedback-Sätze säubern

`transition_quality.py:_feedback()` erzeugt weiter Sätze aus `beats_off` und
`bpm_drift`. `coach_summary.py:24/29` hebt sie in `positives`/`improvements`,
der Mapper reicht sie als `strengths`/`weaknesses` ins Frontend. Ergebnis
heute wörtlich in einem Report:

> „Uebergang bei 02:55 sitzt: Timing, Tempo und Energie passen zusammen."

`bpm_drift` ist in 89 % der Übergänge exakt 0,0. Der Satz lobt für nichts.

Beide Größen raus. Was übrig bleibt, ist weniger Text — das ist richtig so.
Wird eine Liste leer, sag es ehrlich („zu diesem Set lässt sich aus den
vorhandenen Messungen nichts Konkretes sagen"), statt sie mit Allgemeinplätzen
zu füllen.

### J5 · Das Profil neu ranken

`coach/profile.py:232` wählt die drei schwächsten Übergänge über
`quality_score` und begründet über `phrase_beats_off` — beide ρ ≈ 0. Ersetzen
durch den Pegelsprung. Die gute Struktur (drei Übungen aus möglichst
verschiedenen Sets, Tracknamen wo vorhanden, `startSec`/`midSec` zum
Anspringen) bleibt; es wechselt nur, wonach sortiert wird.

### J6 · Entscheidungsvorlage LLM-Coach — **nicht bauen, vorlegen**

Der Knopf existiert und ist erreichbar. Was fehlt, ist `LOVABLE_API_KEY` — den
kann nur Sebastian eintragen. Vorzulegen:

- Was der Knopf heute täte, wenn der Schlüssel da wäre (der Prompt ist seit K1
  bereinigt, aber `beat_alignment` und der Pegelsprung kommen darin **nicht
  vor** — das wäre zu ergänzen).
- Ob die automatische Erzeugung aus dem Notpfad in den Engine-Pfad gehoben
  werden soll, oder ob der Knopf reicht.
- Welches der zwei Regelwerke künftig gilt: `app/audio/rule_engine.py` (Python,
  4 Regeln, feuert in 25 von 51 Reports) oder die Supabase-KB. Zwei parallel
  sind der Doppelstamm-Fehler in neuer Form.

### J7 · Das Blind-Instrument (wenn die Zeit reicht)

`MixCoach-Uebungen-Bewerten.command` nach dem Muster von
`MixCoach-Zweitrunde.command`: 20 Übergänge, je zwei Texte — alte Vorlage und
neue belegte Übung —, Reihenfolge gewürfelt, Herkunft nicht sichtbar. Frage:
*„Welcher Hinweis würde dich beim nächsten Mix mehr verändern?"*

Dieselben Blindheits-Prüfungen wie bei der zweiten Labelrunde: kein
Herkunftshinweis im HTML, kein verräterischer Feldname. Test dafür schreiben.

**Ohne diesen Vergleich ist „Punkt 3 auf 60 %" eine Behauptung.**

### J8 · Bericht

`SITZUNG_2026-08-14.md` nach dem Muster von `SITZUNG_2026-08-10.md`. Die beiden
vorigen Aufträge haben ihn verlangt, keiner hat ihn geliefert — die
Begründungen stehen nur in Commit-Meldungen. Genau daraus ist am 10.08. ein
übersehener Arbeitstag entstanden.

---

## Reihenfolge

```
J0  Kurzprüfung            30 min, kein Checkpoint wenn alles stimmt
J1  reportRevision         → CHECKPOINT
J2  Übungsgenerator        ─┐
J3  Backfill + Vorführung   │  das ist der Kern des Tages
J4  Feedback-Sätze          │
J5  Profil neu ranken      ─┘
J6  LLM-Vorlage            → Sebastians Entscheidung
J7  Blind-Instrument       wenn die Zeit reicht
J8  Bericht                immer
```

**Realistisch für heute: J0 bis J5.** Wenn die Zeit knapp wird, ist J2 + J3
allein ein vollständiges, vorführbares Ergebnis — dann bekommen 18 von 19
Aufnahmen zum ersten Mal eine Übung, die eine Zahl nennt.

---

## Akzeptanz

1. Kein Report zeigt mehr „Transition Review" als einzige Übung.
2. **Jede angezeigte Übung nennt eine Zahl, die im selben Report unter demselben
   `transitionIndex` steht.** Ein Test hält das fest und schlägt fehl, sobald
   jemand eine Vorlage einbaut.
3. Wo keine belegte Zahl da ist, steht **keine Übung** — und die Lücke ist
   sichtbar, nicht gefüllt.
4. Beobachtungen sind von Übungen getrennt und tragen keine
   Handlungsaufforderung.
5. Die Vorführung aus J3 ist gelaufen.
6. 235 Backend-Tests und 15 Frontend-Tests bleiben grün, plus die neuen.
7. Der Fortschrittsnachweis über die 13 Aufnahmen bleibt gültig —
   `vergleichbar()` darf durch diesen Auftrag nicht zerfallen.
8. **Committet und gepusht.**

## Was nicht dazugehört

- Keine Änderung an Erkennung, Modell oder Betriebspunkt.
- Kein Anfassen von `app/audio/scoring/*`.
- **Keine Übung ohne Zahl** — auch nicht „als Platzhalter, bis die Messwerte da
  sind". Genau so ist die heutige Vorlage entstanden.
- Kein Entfernen des Browser-Notpfads (gehört zu S3), kein Nutzerbegriff
  (gehört zu F2), kein Hosting.
- `bass_overlap_score` wird **nicht** zur Regel gemacht: 15,5 % befüllt, zu
  90 % exakt 0 oder 100, und mit zwei zuordenbaren Bewertungen nicht prüfbar.
