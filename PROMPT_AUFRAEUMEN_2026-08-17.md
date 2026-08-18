# Arbeitsauftrag — Aufräumen, selbstständig

**Für Claude Code · erstellt 17.08.2026 · Sebastian ist nicht da**

Lies zuerst `CLAUDE.md`, dann `BEFUNDSTAND_2026-08-14.md` Abschnitt B (S6).

---

## Worum es geht

Vier Aufräumarbeiten, die keine Entscheidung brauchen und niemanden blockieren.
Zusammen etwa zwei Stunden. **Jede für sich committen** — ein Teilstand ist
brauchbar.

Die erste steht seit dem 13.08. auf jeder Liste und ist sechsmal verschoben
worden. Sie kostet eine Stunde und schickt bis dahin jeden Leser auf eine tote
Datei.

---

## Weil niemand da ist

Es gibt keine Checkpoints. Wenn eine der folgenden Bedingungen eintritt:
**anhalten, committen was fertig ist, im Bericht begründen.**

- Tests werden rot und die Ursache liegt nicht in deiner eigenen Änderung.
- Die Referenzmetrik bewegt sich (`analyze_timing_bias --check`, `dedup`:
  Recall 70 %, Precision 74 %, σ 54,58 s, 91 `missed`).
- Ein Schritt würde mehr Dateien anfassen als angekündigt.
- Du bräuchtest einen Zugang, einen Schlüssel oder eine Inhaltsentscheidung.

---

## A · Der tote Vorfahr und die falsche Karte — 1 Stunde

**Der Befund**, heute nachgemessen: `app/experimental/` enthält 39 Python-
Dateien und wird von **null** Dateien außerhalb importiert — geprüft über
`app/`, `tools/` und `tests/`.

Darin liegt `detection/transition_detector.py` mit `detect_transition_zones()`,
46 Zeilen. Die **lebende** Kandidatensuche ist
`app/audio/set_analyzer_helpers.py:detect_set_transition_zones()`, 351 Zeilen,
mit drei Bewertungsfunktionen für Blend, Drop und Bass-Swap.

`CLAUDE.md` schickt jeden Leser an die falsche Stelle, an **drei** Stellen:

| Zeile | steht dort | richtig |
|---|---|---|
| 33 | `app/experimental/detection/  Kandidatensuche für Übergänge` | `app/audio/set_analyzer_helpers.py` |
| ~113 | „Die Diagnose dazu: `detect_transition_zones()` sucht eine RMS-Delle" | `detect_set_transition_zones()` |
| ~123 | „Keine Grid-Search über die Schwellwerte in `detect_transition_zones()`" | dieselbe Korrektur |

**Wichtig: Der Befund selbst bleibt richtig.** Auch die lebende Fassung sucht
eine RMS-Delle — sie ist nur erheblich differenzierter als der 46-Zeiler, den
das Zitat beschreibt. Korrigiere den **Namen und den Pfad**, nicht die
Aussage. Wenn dir beim Lesen der lebenden Fassung auffällt, dass die
Beschreibung sie unterzeichnet, schreib das dazu — aber ändere die Diagnose
nicht ohne Messung.

**Zu tun:**

1. `app/experimental/` nach `audio-engine/mixcoach-audio-engine/_archiv_2026-08-17/experimental/`
   verschieben, mit einer `LIESMICH.md` nach dem Muster von
   `_archiv_2026-08-13/LIESMICH.md`: warum es hier liegt, seit wann es niemand
   importiert, und dass die lebende Entsprechung
   `set_analyzer_helpers.py:detect_set_transition_zones()` ist.
2. Vorher **noch einmal prüfen**, ob wirklich nichts importiert — auch aus
   `Frontend/`, aus `.command`-Dateien und aus `tools/`. Ein Grep nach
   Stichwörtern hat in diesem Projekt schon zweimal Treffer übersehen; such
   zusätzlich nach dem Ordnernamen selbst.
3. Die drei Stellen in `CLAUDE.md` berichtigen.
4. Tests fahren. Wenn eine rot wird, war der Ordner doch nicht tot — dann
   zurück und melden.

---

## B · `CLAUDE.md` auf den heutigen Stand — 30 Minuten

Es ist die Datei, die jede Claude-Code-Sitzung zuerst liest, und sie steht auf
dem 10.08. Zu berichtigen, jede Zahl vorher selbst nachmessen:

- **Kopfzeile „Stand 10.08.2026"** → heutiger Stand, mit den offenen Punkten:
  Bedingung 2 der Live-Schwelle nicht vorgeführt, J7 wartet auf einen Abend.
- **Referenzmetrik** — dort steht Recall 71 %, 286 Übergänge, 88 `missed`.
  Nach der Stamm-Zusammenführung sind es **Recall 70 %** und **91 `missed`**;
  Precision, σ und Median sind unverändert. `--check` fahren und übernehmen,
  was dort steht.
- **Testzahl** — dort steht 226. Heute sind es **285** im Backend, dazu
  Frontend-Tests.
- **Ground Truth** — der Abschnitt beschreibt zwei Stämme („45 und 24, davon 18
  byteidentisch"). Es ist seit dem 13.08. **ein** Stamm; der zweite liegt
  archiviert. Die neun Bewertungskonflikte sind am 17.08. entschieden
  (`daten/ground_truth/KONFLIKTE.md`, „Offen: 0").
- **Ein Verweis auf `PRODUKTVISION.md`** als maßgebliches Dokument für Ziel und
  Tor — die Vision ist am 17.08. zusammengeführt worden und trägt jetzt beides:
  Fernziel und Live-Schwelle.
- **Zwei Arbeitsregeln ergänzen**, beide teuer gelernt:
  „Ein Test belegt die Regel, nicht den Weg durch die Anwendung — zu jeder
  Abnahme gehört eine Vorführung in der laufenden App." und
  „Jede Information hat genau einen Ort, an dem sie wahr ist."

Was **nicht** angefasst wird: die Live-Schwelle selbst, der Abschnitt „Was
gemessen erledigt ist", die Arbeitsregeln zum Nicht-Anfassen von
`app/audio/scoring/*`.

---

## C · `notMeasured` dynamisch — 1 Stunde

`analysis_mapper.py:40` führt eine feste Liste:

```python
NOT_YET_MEASURED = ["eq", "creativity", "frequency", "beatmatching", "timing"]
```

Sie steht so in allen 52 Reports. Das ist heute zufällig richtig — aber es ist
eine Behauptung, kein Mechanismus: Wird morgen eine Größe befüllt oder fällt
eine aus, sagt der Report weiterhin dasselbe.

**Zu tun:** Die Liste aus dem tatsächlichen Befüllungsstand des jeweiligen
Reports bilden. Ein Wert gilt als nicht gemessen, wenn er im Report `None` ist —
nicht, wenn er in einer Liste steht.

**Die Falle, und sie ist dieselbe wie zweimal zuvor:** Eine Änderung am Mapper
greift nur für **neue** Analysen. Damit die 52 gespeicherten Reports mitkommen,
braucht es einen Backfill **und** eine erhöhte `reportRevision` — sonst löst
`scoring-version.ts:loestAb()` die Browser-Kopie nicht ab und die Änderung
kommt nie an.

**`SCORING_VERSION` dabei NICHT erhöhen.** Sie steht für die Rechenvorschrift
der Messwerte; `notMeasured` ist eine Aussage über Befüllung, keine neue
Rechnung. Eine Erhöhung würde `vergleichbar()` auslösen und den
Fortschrittsnachweis über die 13 Aufnahmen in zwei unvergleichbare Hälften
zerlegen.

Backfill mit `--dry-run` als Vorgabe, plus `.command`.

---

## D · `main` nachziehen und Worktrees aufräumen — 20 Minuten

**`main` liegt 30 Commits zurück** und hat seit dem 30.07. nichts gesehen.
Gearbeitet wird auf `setup/macos-umzug` — ein Branch, dessen Name „Umzug"
sagt und der seit sechs Wochen die gesamte Hauptentwicklung trägt.

- `main` auf den Stand des Arbeitsbranches bringen, **nur als Fast-Forward**.
  Ist es kein Fast-Forward, anhalten und melden — dann liegt auf `main` etwas,
  das hier nicht ist, und das will jemand ansehen.
- Beide Branches pushen.
- **Die drei Worktrees** in `.claude/worktrees/` entfernen
  (`amazing-chatelet-50ec0a`, `clever-gauss-4ba17b`, `kind-goldstine-948804`).
  Heute geprüft: **alle drei tragen 0 Commits, die nicht in HEAD sind.** Prüf
  es vor dem Entfernen noch einmal selbst — am 10.08. lag in genau einem
  dieser Ordner ein ganzer Tag unsichtbarer Arbeit.

---

## E · Bericht

Nachtrag in `SITZUNG_2026-08-14.md` (keine neue Datei): was gemessen wurde, was
sich geändert hat, was offen blieb, und wo du dich selbst korrigiert hast.

---

## Was nicht dazugehört

- **Kein F2** — PyJWT und `cryptography` fehlen im venv, das gehört in die
  Sitzung, die F2 wirklich macht.
- **Keine Änderung an Erkennung, Modell oder Betriebspunkt.** Dieser Auftrag
  verschiebt keine einzige Messzahl. Tut er es doch, ist etwas schiefgegangen.
- **Kein Anfassen von `app/audio/scoring/*`.**
- **Keine neuen Übungsregeln, keine Coach-Änderungen.**
- **Keine Entscheidung** über den LLM-Coach, die Übungsbibliothek oder
  `quality_score`.
- **Nicht `memory.md`** — die liegt in Sebastians Cowork-Projektablage, nicht
  im Repo, und ist von hier aus nicht erreichbar. (Inhalt, damit es nicht
  vergessen wird: Sie führt `tools/real_mix_labeler/` und
  `tools/active_learning/` als implementiert. Beide haben nie existiert.)

## Abnahme

1. `app/experimental/` archiviert, `CLAUDE.md` nennt an allen drei Stellen die
   lebende Funktion.
2. `CLAUDE.md` trägt die heutigen Zahlen, jede selbst nachgemessen.
3. `notMeasured` entsteht aus dem Befüllungsstand; die 52 Reports sind
   nachgezogen und erreichen den Browser (`reportRevision` erhöht,
   `scoringVersion` unverändert).
4. `main` auf Stand, drei Worktrees weg, beides gepusht.
5. 285 Backend-Tests grün, Frontend-Tests grün, `tsc` bei 0 Fehlern.
6. Referenzmetrik in allen drei Sichten unverändert.
7. Nach jedem Block ein eigener Commit.
