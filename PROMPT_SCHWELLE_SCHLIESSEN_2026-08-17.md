# Arbeitsauftrag — die Live-Schwelle schließen

**Für Claude Code · erstellt 17.08.2026**
**Ersetzt `PROMPT_AUFRAEUMEN_2026-08-17.md`** — dessen Inhalt ist hier
enthalten, plus der Befund unten, der vorher nicht bekannt war.

Lies zuerst `CLAUDE.md`, dann `PROJEKT_REVIEW_2026-08-17.md` Abschnitt 7 und 8.

---

## Worum es geht

Aus dem Review, Abschnitt 8: *„Diese Woche — die Schwelle schließen. H1 ist der
einzige Blocker."*

Von den vier Posten dieser Woche ist einer schon erledigt (**P5**, die neun
Bewertungskonflikte, am 17.08. entschieden — `KONFLIKTE.md` meldet „Offen: 0").
Bleiben **H1**, **S6** und **P7**.

**Und H1 ist nicht das, wofür wir es gehalten haben.**

---

## Der Befund, der diesen Auftrag auslöst

Bedingung 2 der Live-Schwelle lautet: *„die Historie überlebt einen
Gerätewechsel."* Bisher galt als Blocker, dass sich niemand angemeldet hat.
Das war richtig, aber nicht vollständig. Heute am Code nachgemessen:

```
persistAnalysis()  wird an genau EINER Stelle aufgerufen:
    analysis-engine.ts:286   — innerhalb von runPipeline()

runPipeline() setzt zwei Zeilen vorher result.engine = "local".
Es IST der Browser-Notpfad. app.upload.tsx:97 verhindert per Preflight,
dass er je läuft.
```

Der Engine-Pfad — der einzige, der tatsächlich benutzt wird — endet in
`analysis.processing.$jobId.tsx:102` mit `addAnalysis(result)`. Und
`addAnalysis` (`store.ts:110`) schreibt **ausschließlich in `localStorage`**.

**Eine per Engine analysierte Aufnahme erreicht Supabase also nie beim
Entstehen.** Sie kommt nur mit, wenn später `syncAnalysesWithDb()` läuft — und
das hängt in `app.tsx:73` an einem `useEffect` auf `[user]`, feuert also beim
Anmelden bzw. beim Neuladen der App, **nicht nach einer Analyse**.

**Praktische Folge:** Wer angemeldet ist, ein Set analysiert und dann direkt
das Browser-Profil wechselt, findet dort nichts — die Zeile wurde nie
hochgeschoben. Von außen sieht das exakt so aus, als überlebte die Historie den
Gerätewechsel nicht. **Das ist derselbe Bauplan wie schon dreimal: kein
fehlendes Feature, sondern eine Kette, die eine Stelle vor dem Ziel abreißt.**

---

## Die Regeln

- **`app/audio/scoring/*` nicht anfassen.**
- Keine Änderung an Erkennung, Modell oder Betriebspunkt. Dieser Auftrag
  verschiebt keine Messzahl.
- Kein verschluckter Fehler. Wo etwas fehlschlagen kann, muss die Meldung die
  Ursache benennen.
- **Ein Test belegt die Regel, nicht den Weg durch die Anwendung.** Zu jeder
  Abnahme gehört, dass du die Kette einmal wirklich durchläufst.
- Deutsch in Kommentaren und Doku. Bedienbares als `.command`.

**Anhalten und melden**, wenn: Tests rot werden und die Ursache nicht in deiner
Änderung liegt · die Referenzmetrik sich bewegt (`dedup`: Recall 70 %,
Precision 74 %, σ 54,58 s, 91 `missed`) · du einen Zugang oder eine
Inhaltsentscheidung bräuchtest.

---

## J1 · Engine-Analysen erreichen die Cloud beim Entstehen — **der Kern**

**Ziel:** Eine Analyse, die bei angemeldetem Nutzer über die Engine entsteht,
steht danach in `public.analyses` — ohne dass jemand die App neu lädt.

- Die Persistenz an **eine** Stelle hängen, nicht an zwei. `addAnalysis()` ist
  der gemeinsame Punkt beider Pfade; wenn du sie dort ansetzt, entfällt der
  Aufruf in `runPipeline()` — sonst hast du zwei Wege für dieselbe Sache, und
  genau daran ist der LLM-Coach schon einmal hängen geblieben.
- **Nur bei neuen Einträgen** hochschieben, nicht beim Ersetzen durch eine
  höhere `reportRevision`? Prüf das und entscheide begründet: Eine Korrektur
  gehört auch in die Cloud, sonst laufen die beiden Stände auseinander — aber
  sie darf keine Endlosschleife mit dem Sync auslösen.
- **Nicht angemeldet ist kein Fehler.** Ohne Sitzung wird nicht hochgeschoben,
  und die Meldung sagt das (die Vorlage dafür steht in `sync.ts:persistAnalysis`
  und nennt die zwei tatsächlichen Ursachen beim Namen).
- Der Browser-Notpfad darf dadurch nicht doppelt hochschieben.

**Nachweis, und der zählt mehr als die Tests:** Engine starten, anmelden, eine
Aufnahme analysieren, die noch nie analysiert wurde (⚠️ bei einer bekannten
Datei greift der Hash-Cache in `analysis-engine.ts:91` und es entsteht gar
keine neue Analyse), und danach **ohne Neuladen** prüfen, ob die Zeile in
Supabase steht. Wenn du nicht an die Tabelle kommst: über `listAnalysesFn`
gegenprüfen und im Bericht sagen, wie du es geprüft hast.

**Was Sebastian danach noch selbst tun muss** — und nur das: Profil wechseln,
anmelden, nachsehen. Schreib ihm die drei Schritte als kurze Liste in den
Bericht.

---

## J2 · S6 — der tote Vorfahr und die falsche Karte

`app/experimental/` enthält 39 Python-Dateien und wird von **null** Dateien
außerhalb importiert (heute geprüft über `app/`, `tools/`, `tests/`). Darin
liegt `detection/transition_detector.py` mit `detect_transition_zones()`, 46
Zeilen. Die **lebende** Kandidatensuche ist
`app/audio/set_analyzer_helpers.py:detect_set_transition_zones()`, 351 Zeilen,
mit eigenen Bewertungen für Blend, Drop und Bass-Swap.

`CLAUDE.md` schickt jeden Leser an die falsche Stelle:

| Zeile | steht dort | richtig |
|---|---|---|
| 33 | `app/experimental/detection/  Kandidatensuche für Übergänge` | `app/audio/set_analyzer_helpers.py` |
| ~113 | „Die Diagnose dazu: `detect_transition_zones()` …" | `detect_set_transition_zones()` |
| ~123 | „Keine Grid-Search über die Schwellwerte in `detect_transition_zones()`" | dieselbe Korrektur |

**Der Befund selbst bleibt richtig** — auch die lebende Fassung sucht eine
RMS-Delle. Korrigiere **Name und Pfad**, nicht die Aussage.

Zu tun: Ordner nach `_archiv_2026-08-17/experimental/` verschieben, mit
`LIESMICH.md` nach dem Muster von `_archiv_2026-08-13/`. **Vorher noch einmal
selbst prüfen**, ob wirklich nichts importiert — auch aus `Frontend/` und aus
`.command`-Dateien, und such zusätzlich nach dem Ordnernamen, nicht nur nach
Funktionsnamen. Ein Stichwort-Grep hat in diesem Projekt schon zweimal Treffer
übersehen. Dann Tests fahren; wird eine rot, war der Ordner doch nicht tot.

**Dazu `CLAUDE.md` auf den heutigen Stand**, jede Zahl selbst nachgemessen:
Referenzmetrik (dort steht Recall 71 % und 88 `missed`; es sind **70 %** und
**91**) · Testzahl (dort 226, heute **285**) · Ground Truth (dort zwei Stämme,
seit 13.08. **einer**, Konflikte am 17.08. entschieden) · ein Verweis auf
`PRODUKTVISION.md` als maßgebliches Dokument für Fernziel **und** Live-Schwelle.

Unberührt bleiben: die Live-Schwelle selbst, „Was gemessen erledigt ist", die
Sperre auf `app/audio/scoring/*`.

---

## J3 · P7 — `main` nachziehen, Worktrees aufräumen

- `main` liegt **30 Commits** zurück und hat seit dem 30.07. nichts gesehen.
  Auf den Stand des Arbeitsbranches bringen, **nur als Fast-Forward**. Ist es
  keiner: anhalten und melden.
- Beide Branches pushen.
- Die drei Worktrees in `.claude/worktrees/` entfernen
  (`amazing-chatelet-50ec0a`, `clever-gauss-4ba17b`, `kind-goldstine-948804`).
  Heute geprüft: alle drei tragen **0** Commits, die nicht in HEAD sind. **Prüf
  es vor dem Entfernen noch einmal selbst** — am 10.08. lag in genau einem
  dieser Ordner ein ganzer Tag unsichtbarer Arbeit, und das war der teuerste
  Einzelfehler des Projekts.

---

## J4 · Bericht

Nachtrag in `SITZUNG_2026-08-14.md`, keine neue Datei. Darin ausdrücklich:
die drei Schritte, die Sebastian für Bedingung 2 noch selbst tun muss.

---

## Was nicht dazugehört

- Kein F2 (PyJWT fehlt im venv), kein Hosting, keine Bezahlschranke.
- Keine Coach-Änderungen, keine neuen Übungsregeln.
- Keine Entscheidung über LLM-Coach, Übungsbibliothek oder `quality_score`.
- **Nicht `memory.md`** — sie liegt in Sebastians Cowork-Ablage, nicht im Repo.
  (Zur Erinnerung, damit es nicht verlorengeht: Sie führt
  `tools/real_mix_labeler/` und `tools/active_learning/` als implementiert,
  beide haben nie existiert.)
- `notMeasured` dynamisch (B5) ist **nicht** Teil dieser Woche — es steht im
  Review unter Bedingung 1 und hat Zeit.

## Abnahme

1. Eine bei angemeldetem Nutzer über die Engine erzeugte Analyse steht ohne
   Neuladen in der Cloud — durchlaufen, nicht nur getestet.
2. `app/experimental/` archiviert, `CLAUDE.md` an allen drei Stellen richtig
   und mit den heutigen Zahlen.
3. `main` auf Stand, drei Worktrees weg, beides gepusht.
4. 285 Backend-Tests und die Frontend-Tests grün, `tsc` bei 0 Fehlern.
5. Referenzmetrik in allen drei Sichten unverändert.
6. Nach jedem Block ein eigener Commit.
