# Arbeitsauftrag — Coach, zwei Stunden selbstständig

**Für Claude Code · erstellt 15.08.2026 · Sebastian ist nicht da**

Lies zuerst `CLAUDE.md`, dann `SITZUNG_2026-08-14.md` Abschnitt 6 und 6a.

---

## Die Lage

Punkt 3 ist seit dem 14.08. weit gekommen: `app/coach/uebungen.py` steht, 109
Übungen nennen eine belegte Zahl, 286 Beobachtungen sind getrennt und seit
gestern sichtbar, das Profil rankt nach dem Pegelsprung, die Feedback-Sätze
sind von `bpm_drift` und `phrase_beats_off` befreit, das Blind-Instrument
wartet auf einen Abend.

**Was gestern nicht dran war, ist heute der größte offene Hebel — und er ist
ohne Sebastian entscheidbar.**

Heute nachgezählt über alle 51 Reports:

```
Skill-Achse      befüllt
  beatmatching     0 / 51
  eq               0 / 51
  timing           0 / 51
  creativity       0 / 51
  flow            51 / 51
  musicality      51 / 51
```

**Vier der sechs Achsen des Skill-Radars sind in jedem Report leer.** Das
Radar und die Trendkurve in `app.progress.tsx` und `CoachProfilePanel` ruhen
über `progression.ts` und `profile.py:_skill_timeline()` genau auf diesen sechs
Feldern. Für das Merkmal, das laut Geschäftsmodell der Abo-Grund ist, heißt
das: zwei Drittel der Anzeige sind Luft.

Und die eine Größe, die eine Entwicklung **belegt** zeigt, steht nirgends darin:

```
|loudness_jump_db| über 13 eigene Aufnahmen, 06.07. bis 28.07.
  erste drei Sets    Median 2,80 dB     ~50 % der Übergänge über 3 dB
  letzte drei Sets   Median 1,85 dB     ~22 %
  Trend                                 r = −0,622
```

Sie liegt in `profile.py:302` bereits für die Übungen bereit. Sie fehlt nur im
Verlauf.

---

## Der Auftrag

**Das Skill-Radar ehrlich machen und um die Größe erweitern, die trägt.**

Vier Aufgaben, in dieser Reihenfolge, jede für sich committen. Wenn die Zeit
nur für A reicht, ist A allein ein vollständiges Ergebnis.

---

## Weil niemand da ist: die Entscheidungen sind vorweggenommen

Damit du nicht auf Antworten wartest, sind die Fragen, die sonst Checkpoints
wären, hier entschieden. Halte dich daran — oder halte an und begründe, statt
anders zu entscheiden.

1. **Die vier leeren Achsen werden nicht entfernt und nicht mit Ersatz
   gefüllt.** Sie werden als *nicht gemessen* gekennzeichnet, sichtbar, mit dem
   Grund. Dieselbe Linie wie bei `notMeasured` und bei den Beobachtungen.
2. **Die neue Achse heißt nicht „Qualität".** Sie misst den Pegelsprung. Nenn
   sie, was sie ist — z.B. „Pegel-Sauberkeit" —, und schreib die Einheit dazu.
   Ein Composite, der zu 98 % aus einer Dimension besteht, war schon einmal der
   Fehler.
3. **Eine Frontend-Seite darf angefasst werden**, aber nur für diese Anzeige
   und nur als **eigener, rückdrehbarer Commit** — genauso wie gestern die
   Beobachtungs-Karte. Kein Umbau, keine neue Route.
4. **Kleiner ist besser als vollständig.** Lieber eine Achse, die stimmt, als
   sechs, die halb stimmen.

---

## A · Die Zeitreihe, die trägt

**Backend, `app/coach/profile.py`:**

- Eine Zeitreihe je Aufnahme aus `|loudness_jump_db|` — **Median je Aufnahme**,
  nicht Mittelwert (die Verteilung hat einen langen rechten Rand, Maximum
  10,1 dB).
- Dazu, wie bei den bestehenden Skills: aktueller Stand und Trend über die
  letzten drei gegen die drei davor. **Niedriger ist besser** — achte auf das
  Vorzeichen, sonst zeigt die Anzeige Fortschritt als Rückschritt.
- Zusätzlich der Anteil der Übergänge über 3 dB je Aufnahme. Das ist die Zahl,
  in der der Fortschritt am deutlichsten steht (50 % → 22 %), und sie ist
  leichter zu verstehen als ein Median in dB.

**Drei Fallstricke, alle nachprüfbar, alle würden die Kurve verfälschen:**

- **Testdateien gehören nicht in eine Fortschrittskurve.** `mix.wav` und
  `synthetic_mix.wav` stehen mit 0,00 dB im Bestand und würden als perfekte
  Sets ganz rechts landen. Prüf, ob `_load_results()` sie schon ausschließt;
  wenn nicht, schließ sie aus und sag im Bericht, wie viele es waren.
- **Nur vergleichbare Reports.** `scoring_version.py:vergleichbar()` ist dafür
  da. Sieben der 51 Reports sind ungestempelt (genau die ohne
  `loudness_jump_db` — sie fallen ohnehin heraus, aber verlass dich nicht
  darauf, prüf es).
- **Dieselbe Aufnahme liegt mehrfach vor.** Es gibt 51 Reports, aber nur 21
  verschiedene `fileName`. Eine Kurve über Reports statt über Aufnahmen zählt
  REC001 fünfmal. Die Referenzmetrik hat genau diesen Fehler einmal gemacht und
  fährt seitdem `--mode dedup`. Mach es hier von Anfang an richtig und
  dokumentier die Regel, nach der du bei mehreren Läufen derselben Aufnahme
  auswählst.

**Frontend:**

- Die neue Größe in `CoachProfilePanel` anzeigen — Verlauf und Trend, mit
  Einheit, mit der Leserichtung („niedriger ist besser") und mit der Anzahl der
  Aufnahmen, auf der sie ruht.
- **Die Unsicherheit gehört dazu, nicht in die Fußnote:** 13 Aufnahmen über 22
  Tage, ein Rater, r = −0,622 bei n = 13 ist ein deutlicher Hinweis und keine
  Gewissheit. Ein Satz reicht, aber er muss dastehen.

**Tests:** Vorzeichen des Trends, Ausschluss der Testdateien, Entdopplung nach
`fileName`, Verhalten bei weniger als vier Aufnahmen (kein Trend, keine
erfundene Null).

---

## B · Die vier leeren Achsen kennzeichnen

`progression.ts` und `profile.py:_skill_timeline()` führen sechs Achsen, vier
davon sind überall `None`. Heute erscheinen sie als leere oder auf Null
gezogene Punkte im Radar — beides sagt dem DJ etwas Falsches.

- Achsen ohne einen einzigen Wert werden als **„nicht gemessen"** dargestellt,
  nicht als Null und nicht als Lücke.
- Der Grund gehört daneben, kurz: `beatmatching` und `timing` stehen seit dem
  31.07. bewusst auf `None` (K1), `eq` und `creativity` waren nie befüllt.
- Das ist eine Anzeige-Änderung, kein Entfernen. Die Felder bleiben.

---

## C · Der LLM-Prompt kennt die tragende Größe nicht

`coach-feedback.functions.ts` ist seit K1 bereinigt — Tempo-Drift und
Phrasen-Alignment sind ausdrücklich als „nicht gemessen" markiert. Aber
`loudness_jump_db` und `beat_alignment_score`, die beiden Größen mit
nachgewiesenem Zusammenhang, **kommen im Prompt gar nicht vor**.

- Beide in den Transition-Block aufnehmen, mit Einheit und Leserichtung.
- Beim Pegelsprung dazuschreiben, dass er die Größe mit dem stärksten belegten
  Zusammenhang ist — das Modell soll ihn priorisieren, nicht nur erwähnen.
- Das Zod-Schema ist seit dem 13.08. `nullable`; fehlende Werte lässt der
  Prompt weg. Halte dich daran, erfinde keine Pflichtfelder zurück.

**Risikofrei:** Der Aufruf läuft ohnehin nicht, weil `LOVABLE_API_KEY` in
`Frontend/.env` fehlt. Du änderst eine Zeichenkette, die heute niemand
ausführt — aber sie ist dann richtig, wenn Sebastian den Schlüssel einträgt.

---

## D · `EXERCISE_LIBRARY` — vorbereiten, nicht entscheiden

Aus dem Bericht vom 15.08.: 4 der 10 statischen Übungen in `lib/coach.ts` setzen
ihr Erfolgskriterium auf eine Größe, die das Projekt als nicht messend führt
(`phrase-16`, `bass-swap`, `warmup-flow`, `sync-hold`).

**Der Inhalt ist Sebastians Entscheidung.** Deiner ist die Vorarbeit:

- Ein kurzes Dokument `ENTSCHEIDUNG_UEBUNGSBIBLIOTHEK.md`: je Übung das heutige
  Kriterium, warum es nicht trägt, und **ein konkreter Vorschlag**, der auf
  einer belegten Größe ruht. Nicht mehr als eine Seite.
- Der **Mechanismus** darf gebaut werden: ein Feld an `CoachExercise`, das eine
  Übung als „Erfolgskriterium nicht nachprüfbar" markiert, plus die Anzeige
  dazu. Gesetzt wird es erst, wenn Sebastian entschieden hat — **außer** für die
  vier oben, die belegt nicht tragen; die dürfen es sofort bekommen.

---

## Was du heute nicht tust

- **Kein F2.** PyJWT und `cryptography` fehlen im venv; eine Installation ist
  kein Nebenbei-Schritt und gehört in die Sitzung, die F2 wirklich macht.
- **Keine neuen Übungsregeln.** Camelot-Abstand (ρ +0,05) und `energy_dip_pct`
  (ρ +0,07) bleiben Beobachtungen. `bass_overlap_score` bleibt draußen: 15,5 %
  befüllt, zu 90 % exakt 0 oder 100, mit zwei zuordenbaren Bewertungen nicht
  prüfbar.
- **Kein Anfassen von `app/audio/scoring/*`**, keine Änderung an Erkennung,
  Modell oder Betriebspunkt. Dieser Auftrag verschiebt keine Messzahl.
- **Keine Entscheidung über den LLM-Coach**, keine über die
  Übungsbibliothek-Inhalte, keine über die 9 Konflikte in `KONFLIKTE.md`.
- **Keine Migration** über Reports oder Ground Truth.
- **Kein Entfernen des Browser-Notpfads.**

## Wann du anhältst und berichtest, statt weiterzumachen

- Wenn Tests rot werden und die Ursache nicht in deiner eigenen Änderung liegt.
- Wenn die Referenzmetrik sich bewegt (`analyze_timing_bias --check`, `dedup`:
  Recall 70 %, Precision 74 %, σ 54,58 s).
- Wenn eine Aufgabe eine Seite stärker verändern würde als eine hinzugefügte
  Karte.
- Wenn du für etwas einen Schlüssel, einen Zugang oder eine Inhaltsentscheidung
  bräuchtest.
- Wenn du merkst, dass eine der vorweggenommenen Entscheidungen falsch ist —
  dann begründen, nicht umgehen.

## Abnahme

1. Die neue Zeitreihe ist im Backend berechnet, im Frontend sichtbar, und die
   Unsicherheit steht daneben.
2. Testdateien sind draußen, nach `fileName` entdoppelt, nur vergleichbare
   Reports.
3. Die vier leeren Achsen sagen „nicht gemessen" statt Null.
4. 235 Backend-Tests und 15 Frontend-Tests grün, plus die neuen.
   `tsc` bleibt bei 0 Fehlern — das war gestern zum ersten Mal so.
5. Referenzmetrik unverändert.
6. Nach jeder der vier Aufgaben ein eigener Commit, damit ein Teilstand
   brauchbar ist.
7. **Nachtrag in `SITZUNG_2026-08-14.md`** (nicht neue Datei) mit dem, was
   gemessen wurde, was sich geändert hat, was offen blieb — und wo du dich
   selbst korrigiert hast.
8. **Gepusht.**
