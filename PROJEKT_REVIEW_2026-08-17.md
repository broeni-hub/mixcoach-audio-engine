# MixCoach — Produktprojekt-Review

**Stand: 17.08.2026** · Vorgänger: `PROJEKT_REVIEW_2026-08-13.md`

---

## 0 · Wie dieses Dokument entstand

Alle Zahlen heute am Repo nachgemessen, keine aus `PROJEKTSTAND-CLAUDE.md`,
`ROADMAP.md`, einem Sitzungsbericht oder einer Commit-Meldung übernommen.

**Nachgemessen:** Git-Historie und Push-Stand · Modell-Betriebspunkt ·
Referenzmetrik (`analyze_timing_bias --check`) · Befüllung aller 442 Übergänge
in 52 Reports · `scoringVersion`, `reportRevision`, `userId`, `notMeasured`,
`scores` je Report · Frontend-Schalter und `.env`-Schlüsselnamen ·
Engine-Auth und CORS · Ground-Truth-Stämme · `app/experimental` ·
Library-Index · Testzahlen.

**Übernommen, weil aus der Sandbox nicht ausführbar:** dass die 285
Backend-Tests grün laufen (gezählt, nicht gefahren — das venv ist von hier aus
nicht startbar) · die Spearman-Werte gegen `human_rating` vom 13./15.08. ·
die Vorführung des Korrekturwegs vom 16.08. (im Commit `31bb333` mit
Vorher/Nachher belegt).

---

## 1 · Die kurze Fassung

**Die Ehrlichkeitslinie ist durch.** 52 von 52 Reports tragen
`beatmatching: null`, alle 110 Übungen nennen eine Zahl aus dem eigenen Set,
233 Beobachtungen stehen getrennt daneben — ohne Handlungsaufforderung, weil
für sie kein Zusammenhang mit dem menschlichen Urteil belegt ist. Der
Korrekturweg ist am 16.08. in der laufenden App vorgeführt worden, nicht nur
getestet.

**Und die Arbeit liegt endlich auf GitHub** — 0 ungepushte Commits, nach 26
über vier Tage.

**Was jetzt blockiert, ist eine einzige Bedingung:** Die Historie hat einen
Gerätewechsel noch nie überlebt, weil es niemand vorgeführt hat. Der Versuch
am 16.08. ist an der Google-Anmeldung gescheitert — und dabei kam ein Befund
heraus, der über den Tag hinausreicht: **Google kann lokal grundsätzlich nicht
funktionieren**, und das Supabase-Projekt gehört Lovable (Abschnitt 5a).

**Gegenüber der Vision stehen rund 52 %** (13.08.: 48 %, 30.07.: 40 %).

---

## 2 · Der Maßstab

**Die Vision:** „Andere Tools analysieren deine Musik. MixCoach analysiert dein
DJing." Fünf Erlebnis-Punkte, drei Burggräben.

**Die Live-Schwelle** (seit 30.07., in `CLAUDE.md`):

> Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.

| Bedingung | Stand |
|---|---|
| 1 · Jeder angezeigte Wert ist gemessen | **erfüllt**, bis auf einen Mechanismus (B5) |
| 2 · Historie überlebt Gerätewechsel | **gebaut, nie vorgeführt** — der einzige Blocker |
| 3 · Drei Sets zeigen eine Entwicklung | **erfüllt und sichtbar** seit 15.08. |

---

## 3 · Stand gegen die Vision

### Die fünf Erlebnis-Punkte

| Punkt | 30.07. | 13.08. | **17.08.** | Was sich bewegt hat |
|---|---|---|---|---|
| 1 · Erkennung | 55 % | 58 % | **58 %** | Unberührt. Referenzmetrik Ziffer für Ziffer identisch. |
| 2 · Report | 65 % | 78 % | **80 %** | Das Coach-Fazit ganz oben zeigte bis zum 16.08. weiter Lob aus zwei widerlegten Größen — behoben, 0 Reports betroffen. |
| 3 · Coach | 30 % | 32 % | **50 %** | 110 Übungen, **alle** mit einer Zahl aus dem eigenen Set. 233 Beobachtungen getrennt. Kein Nützlichkeitsnachweis (J7). |
| 4 · Fortschritt | 25 % | 50 % | **55 %** | Die Pegelsprung-Kurve steht im Verlauf, vier leere Achsen sagen „nicht gemessen" statt Null. Bedingung 2 weiter nicht vorgeführt. |
| 5 · Teilen | 10 % | 10 % | **10 %** | Unverändert. |

### Die drei Burggräben

| Burggraben | 30.07. | 13.08. | **17.08.** | Begründung |
|---|---|---|---|---|
| 1 · Daten-Schleife | 30 % | 40 % | **40 %** | Unverändert. Die 9 Bewertungskonflikte sind weiter offen. |
| 2 · Library-Verbindung | 70 % | 72 % | **72 %** | Unverändert. Tracknamen an 20,4 % der Übergänge. 6673 rekordbox-Beatgrids weiter brach. |
| 3 · Ehrlichkeit | 60 % | 90 % | **95 %** | In Code, Daten **und** vorgeführt. Kein „belegt", solange `notMeasured` eine feste Liste ist und nicht auf den tatsächlichen Befüllungsstand reagiert. |

### Die Roadmap-Teile

| | 30.07. | 13.08. | **17.08.** |
|---|---|---|---|
| Teil 1 · Audio-Engine | 60 % | 70 % | **72 %** |
| Teil 2 · Frontend | 55 % | 62 % | **68 %** |
| Teil 3 · Online gehen | 10 % | 15 % | **15 %** |

**Gesamt rund 52 %.** Der Zuwachs kommt vollständig aus Punkt 2, 3 und 4 — die
Erkennung hat sich seit dem 30.07. nicht bewegt, und das hat nichts gekostet.

---

## 4 · Kennzahlen-Tafel

### Erkennung — unverändert seit dem 10.08.

| Größe | Wert |
|---|---|
| Betriebspunkt | `min_p = 0,6`, `gap = 150 s` |
| LOSO-Validierung | R 92,4 % · P 62,8 % · F1 0,748 (25 Sets / 3537 Kandidaten) |
| Referenzmetrik `dedup` | 28 Aufnahmen · 286 bewertete Übergänge · 91 `missed` |
| | Recall **70 %** · Precision **74 %** · strikt korrekt **29 %** |
| Timing | σ **54,58 s** · Median −29,43 s · 85 % zu spät |
| Innerhalb 8 s / 16 s | 5 % / 22 % |

### Report — 442 Übergänge in 52 Reports (21 Aufnahmen)

| Messwert | 13.08. | **17.08.** |
|---|---|---|
| `quality_score`, `phrase_alignment_score` | 100 % | **100 %** (beide messen nichts, ρ ≈ 0) |
| `composite_quality_score` | 86,1 % | **86,4 %** |
| `loudness_jump_db` | 86,1 % | **86,4 %** ← die tragende Größe |
| `beat_alignment_score` | 86,1 % | **86,4 %** |
| `harmonic_clash_score` / `vocal_overlap_score` | 80,6 % | **78,7 %** |
| `exit_quality_score` | 76,4 % | **76,0 %** |
| `energy_dip_pct` | 50,5 % | **50,2 %** |
| `bass_overlap_score` | 15,5 % | **15,8 %** ← unverändert |
| `track_in` / `track_out` | 19,0 % | **20,4 %** |

### Ehrlichkeit und Versionierung

```
scores.beatmatching = null      52 / 52
notMeasured, 5 Einträge         52 / 52   (feste Liste, kein Mechanismus)
scoringVersion 3                45 / 52   (7 ohne Stempel: die ohne loudness_jump_db)
reportRevision                  5: 38   4: 13   1: 1
userId "local-single-user"      51 / 52   (1 ohne Besitzer, siehe 5b)
Übungen                        110, davon mit Zahl: 110
Beobachtungen                  233
```

### Betrieb und Technik

| Größe | Wert |
|---|---|
| Datenstamm | **ein** Ground-Truth-Stamm (45 Dateien), 52 Reports |
| Bewertungskonflikte | **9 offen** (`daten/ground_truth/KONFLIKTE.md`) |
| Library-Index | 6113 Tracks, **1** verbliebener Windows-Pfad |
| Toter Code | `app/experimental/` 39 Dateien, **0 Importe von außen** |
| Tests | **285** Backend (gezählt), 6 Frontend-Testdateien |
| Login | `DEV_BYPASS_AUTH = false` ✅ (am 16.08. kurz an, korrekt zurückgesetzt) |
| Bezahlschranke | `PAYWALL_DISABLED = true` (bewusst) |
| `.env` | Supabase-URL + Publishable Key ✅ · **kein `SERVICE_ROLE_KEY`, kein `LOVABLE_API_KEY`** |
| Engine-Auth | **keine** — 0 `Depends`, `allow_origins=["*"]` (F2 nicht begonnen) |
| Push-Stand | **0 ungepusht** ✅ · `main` 30 Commits hinterher · 1 untracked Analyse |
| Worktrees | 3 alte in `.claude/worktrees/` |

---

## 5 · Befunde, die in keinem Projektdokument stehen

### 5a · Das Anmeldesystem gehört nicht dem Projekt

Beim Versuch, Bedingung 2 vorzuführen, ist die Google-Anmeldung gescheitert.
Die Ursachensuche hat mehr zutage gefördert als einen Fehler — sie hat die
Bauart offengelegt. Nachgemessen an `/auth/v1/settings` und `/auth/v1/authorize`:

```
external.google = true      Google ist im Supabase-Projekt eingeschaltet
authorize       = 400       "Unsupported provider: missing OAuth secret"
/auth              200      die Seite läuft
/~oauth/initiate   404      der Broker fehlt lokal
```

**Eingeschaltet, aber ohne Zugangsdaten — und das ist kein halbfertiger
Zustand, sondern Absicht.** Das Supabase-Projekt gehört Lovable. Lovable
behält die OAuth-Anwendung und liefert nur fertige Tokens; ein eigenes Secret
lässt sich in das Projekt gar nicht eintragen. Der Broker liegt unter
`/~oauth/initiate` auf Lovables Hosting — der lokale Vite-Server kennt die
Route nicht.

**Zwei Folgen, beide über den Tag hinaus:**

1. **Google-Anmeldung ist lokal grundsätzlich unmöglich.** Der Knopf sagt das
   jetzt, statt still nichts zu tun.
2. **Für Teil 3 der Roadmap ist das eine Abhängigkeit, die noch nirgends
   steht.** Ein gehostetes MixCoach erbt Lovables Auth-Infrastruktur oder muss
   sie ablösen. Das gehört in die Planung von Teil 3, bevor Hosting-Kosten
   kalkuliert werden.

**Bedingung 2 ist dadurch nicht blockiert** — Registrierung per E-Mail und
Passwort funktioniert (`auth.tsx:50`). Der Weg führt über einen
Bestätigungslink, und der eingebaute Mailversand ist mengenbegrenzt.

### 5b · Eine Analyse ohne Besitzer

`MixCoach2.WAV`, entstanden am 16.08. um 19:32 — der einzige der 52 Reports
mit `userId: None`. Sie ist während der Vorführung entstanden, als
`DEV_BYPASS_AUTH` kurzzeitig auf `true` stand. Alle anderen 51 tragen
`local-single-user`.

Solange ein Nutzer lokal arbeitet, ist das folgenlos. Sobald F2 greift, ist es
ein Report, der niemandem gehört und in keiner Liste auftaucht. Ein Satz in der
Besitzer-Migration behebt es.

### 5c · Der Fund, den nur die laufende App zeigen konnte

Bei der Vorführung am 16.08. kam heraus: `feedback.worked` ist eine **zweite
Kopie** derselben Sätze, die der Mapper auch in `strengths` schreibt. Der
J4-Backfill hatte nur `strengths` gesäubert. Und genau `feedback.worked`
rendert das „Coach-Fazit" **ganz oben auf der Report-Seite**.

Dort stand also weiter *„Übergang bei 36:43 sitzt: Timing, Tempo und Energie
passen zusammen"* — Lob aus zwei Größen, von denen eine in 89 % der Übergänge
exakt 0,0 ist. An der prominentesten Stelle des Produkts, während `strengths`
darunter schon ehrlich war.

**Das ist zum zweiten Mal dieselbe Lehre:** ein Test belegt die Regel, nicht
den Weg durch die Anwendung. Beim Korrekturweg (F1) war es genauso. Heute
tragen 0 von 52 Reports den alten Satz.

### 5d · `main` ist zur Nebensache geworden

Gepusht wird auf `setup/macos-umzug`. `main` liegt **30 Commits** zurück und
hat seit dem 30.07. nichts mehr gesehen. Der Branch heißt „Umzug" und enthält
seit sechs Wochen die gesamte Hauptentwicklung — F1, den Coach, den
Fortschrittsnachweis.

Das ist heute harmlos und wird unangenehm, sobald jemand anderes das
Repository ansieht oder ein zweiter Rechner dazukommt. Ein Merge nach `main`
kostet Minuten.

### 5e · Die Referenzmetrik misst weiter das alte Modell

Unverändert seit dem 13.08.: Der Betriebspunkt steht seit dem 10.08. auf
`gap=150` (LOSO-Precision 62,8 %), aber die Praxiszahlen (Recall 70 % /
Precision 74 %) stammen aus Ground Truth zu Analysen mit `gap=90`. **Was der
Retrain praktisch gebracht hat, ist bis heute ungemessen** — und es bleibt
ungemessen, bis Sets mit dem neuen Punkt analysiert und bewertet sind.

---

## 6 · Die Korrektur-Schleife

Von den 12 Commits seit dem 15.08. sind **drei** Korrekturen an eigenen
früheren Aussagen:

| Commit | Was korrigiert wurde |
|---|---|
| `31bb333` | „J4 ist erledigt" — `feedback.worked` war eine übersehene zweite Kopie |
| `3ec4ab6` | Nimmt `5519a9b` zurück: „Meine Diagnose war richtig, die Schlussfolgerung falsch" |
| `a063f39` | „Es sind vier Übungen mit widerlegtem Kriterium" — es waren sechs, der Grep hatte zwei übersehen |

**Die Rate ist gefallen** — von 8 aus 25 (13.08.) auf 3 aus 12. Und die Art hat
sich geändert: Es sind keine Zustandsirrtümer mehr („liegt an zwei Orten",
„ist nicht gebaut"), sondern Unvollständigkeiten beim ersten Durchgang. Die
Gegenmaßnahmen greifen.

**Zwei Ursachen wirken weiter:**

- **Ein Test belegt die Regel, nicht den Weg durch die Anwendung.** Zweimal in
  vier Tagen (F1, dann `feedback.worked`) hat erst das Öffnen der Seite den
  Rest gezeigt. Die Gegenmaßnahme ist keine weitere Testschicht, sondern die
  Vorführung als fester Bestandteil jeder Abnahme.
- **Ein Grep ist keine Zählung.** Zweimal (Übungsbibliothek, LLM-Aufrufer) hat
  eine Suche nach Stichwörtern Treffer übersehen.

**Erledigt seit dem 13.08.:** Doppelstamm aufgelöst, gepusht.
**Weiter offen:** `memory.md` führt bis heute `tools/real_mix_labeler/` und
`tools/active_learning/` als implementiert — beide existieren nicht.

---

## 7 · Offene Posten, sortiert nach der Live-Schwelle

### Bedingung 1 — jeder angezeigte Wert ist gemessen · **erfüllt bis auf B5**

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **B5** | `notMeasured` dynamisch aus dem Befüllungsstand bilden statt fester Fünferliste | 1 Tag | offen |
| **B2** | `quality_score` entscheiden — steht in 100 % der Übergänge und misst nichts (ρ +0,018) | **deine Entscheidung** | offen |
| **B3** | `bass_overlap_score` — erst klären, ob er überhaupt abstuft (zu 90 % exakt 0 oder 100) | 1 Tag | offen |
| **B6** | `energy_dip_pct` von 50,2 % hoch | 1 Tag | offen |

### Bedingung 2 — Historie überlebt Gerätewechsel · **der einzige Blocker**

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **H1** | **Vorführen** — per E-Mail registrieren, Analyse anlegen, Browser-Profil wechseln, anmelden, nachsehen. **Nicht über Google** (5a) | ½ Tag | **offen, blockiert die Schwelle** |
| **H2** | `SUPABASE_SERVICE_ROLE_KEY` in `.env` — für die Historie nicht nötig, für Beta-Funktionen schon | 10 min | offen, **nur du** |

### Bedingung 3 — drei Sets zeigen eine Entwicklung · **erfüllt**

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **E3** | Die Vorbehalte prüfen — 13 Aufnahmen über 22 Tage, ein Rater, r = −0,622 bei n = 13 | ½ Tag | offen |

### Parallel

| | Aufgabe | Aufwand | Status |
|---|---|---|---|
| **J7** | **Blind-Test zu den Übungen** — 20 Paare, hebt Punkt 3 über 50 % | **dein Abend** | Instrument steht |
| **P3** | Zweite, blinde Labelrunde | **dein Abend** | Instrument steht |
| **P5** | 9 Bewertungskonflikte entscheiden | ½ h, **nur du** | offen |
| **S6** | `app/experimental/` archivieren, `CLAUDE.md:33` korrigieren | 1 h | offen, 5× verschoben |
| **P7** | `main` nachziehen, 3 alte Worktrees aufräumen, `memory.md` berichtigen | ½ h | **neu** |
| **P1** | `start_sec` vs. `mid_sec` zu Ende messen | 1 Tag | offen |
| **F2** | Nutzerbegriff in der Engine | 1 Woche | nicht begonnen, **vor Teil 3** |

---

## 8 · Ausblick

**Diese Woche — die Schwelle schließen.** H1 ist der einzige Blocker und kostet
einen halben Tag. Dazu P5, S6 und P7 — zusammen zwei Stunden. Danach ist die
Live-Schwelle zum ersten Mal vollständig erfüllt, und zwar nachweislich.

**Danach — den Coach beweisen.** J7. Die Übungen sind belegt; ob sie mehr
bewirken als die alte Vorlage, ist die einzige offene Frage bei Punkt 3. Ein
Abend, und Punkt 3 bewegt sich über 50 % oder es gibt einen Grund, warum nicht.

**Dann — B5, B3, B6 und E3.** Vier eintägige Aufgaben, die Bedingung 1 von
„erfüllt" auf „belegt" heben.

**Dann — Punkt 5 und der erste Eindruck.** Demo-Report, Onboarding, Teilen. Ab
hier kann jemand anderes das Produkt verstehen, ohne dass du daneben sitzt.

**Zuletzt — Teil 3.** F2 zuerst, dann Hosting. Und dort gehört jetzt der Befund
aus 5a hinein: Das Anmeldesystem gehört Lovable. Vor der ersten Kostenrechnung
ist zu klären, ob das so bleiben soll.

---

## 9 · Was nur du tun kannst

1. **Bedingung 2 vorführen** (H1). Per E-Mail registrieren, nicht per Google.
2. **Die 9 Bewertungskonflikte** (P5). In 8 von 9 Fällen ist der `daten/`-Stand
   der spätere (13.07. gegen 06.–08.07.) und sagt `not_a_transition`. Wenn das
   ein bewusster zweiter Durchgang war, heißt die Entscheidung „`daten/` gilt"
   und die Liste kann geleert werden.
3. **`quality_score` entscheiden** (B2).
4. **J7 und die zweite Labelrunde** — je ein Abend.
5. **`SUPABASE_SERVICE_ROLE_KEY` eintragen** (H2).

---

## 10 · Was über die Beta hinaus trägt

**Das Intervall statt des Punktes.** `start_sec` nimmt dem Timing-Fehler den
systematischen Anteil (Median −33 s → −10 s, Trefferquote 4 % → 21 % innerhalb
8 s), nicht die Streuung. Ein Tag Messarbeit klärt, ob es der Ausweg ist.

**Der rekordbox-Schatz.** 6673 Beatgrids und 432 Cue-Punkte liegen ungenutzt —
deine eigene, von Hand kuratierte Wahrheit über Downbeats. Der einzige Weg zu
„sekundengenau", der nicht durch Forschung führt.

**Tracknamen an jedem Übergang.** 20,4 % ist zu wenig für ein Versprechen, das
im Leitsatz steht.

**Ein zweiter Rater.** Alle Bewertungen stammen von `sebro`. Ohne einen zweiten
gibt es keine Obergrenze dafür, was ein Modell erreichen kann.

---

## 11 · Das größte Risiko

Am 13.08. stand hier: Der Fortschrittsnachweis ruht auf **einer** Größe, in
**einer** Stichprobe von 13 Aufnahmen, von **einem** Rater bewertet.

**Das gilt unverändert — und es ist seither gewichtiger geworden**, weil in der
Zwischenzeit der gesamte Coach auf dieselbe Größe gestellt wurde. Alle 110
Übungen ruhen auf `loudness_jump_db`. Die Kurve im Fortschritt ruht darauf.
Der LLM-Prompt priorisiert sie.

Das ist die richtige Entscheidung gewesen — es ist die einzige Größe, die
belegt trägt. Aber es heißt: **Wenn ρ = −0,377 bei n = 146 sich an einer
zweiten Stichprobe nicht bestätigt, fällt Punkt 3 und Punkt 4 gleichzeitig.**

Zwei Dinge senken das Risiko, beide stehen schon auf der Liste und beide kosten
einen Abend: **J7** (bewirken die Übungen mehr als die Vorlage?) und **ein
zweiter Rater** (stimmt das Urteil überhaupt zwischen zwei Menschen überein?).

Solange beides aussteht, ist der Coach gut begründet — aber auf einer einzigen
Säule gebaut.
