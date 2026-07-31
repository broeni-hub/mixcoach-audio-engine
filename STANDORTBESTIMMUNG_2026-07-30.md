# Standortbestimmung — wo MixCoach gegenüber der Vision steht

Stand 30.07.2026. Grundlage: `PRODUKTVISION.md`, `ROADMAP.md`,
`ZUKUNFTSWEGE_2026-07-30.md` und eine Auszählung des tatsächlichen Bestands.

## Wie die Zahlen zustande kommen

Ausgezählt, nicht geschätzt: 50 Analyse-Reports in `daten/analysis_results/` mit
431 Transitions, 30 Routen unter `Frontend/src/routes/`, 17 Backend-Endpoints,
6113 Tracks im Library-Index. Wo eine Zahl aus einer einzelnen Messung stammt,
steht es dabei.

Die Prozentangaben bewerten **Nähe zum Vision-Text**, nicht geleistete Arbeit.
Eine gebaute Oberfläche ohne tragende Daten zählt anteilig, nicht voll — sonst
misst man Fleiß statt Fortschritt.

---

# 1 · Die fünf Erlebnis-Punkte

| Punkt | Stand | Kurz |
|---|---|---|
| 1 · Erkennung | **55 %** | „welcher Track wann" trägt, „wo beginnt der Übergang" nicht |
| 2 · Report | **65 %** | gebaut und benutzbar, aber halb befüllt und zwei Werte täuschen |
| 3 · Coach | **30 %** | Oberfläche steht, die Personalisierung ist eine Vorlage |
| 4 · Fortschritt | **25 %** | Ansicht steht, die Historie liegt im Browser |
| 5 · Teilen | **10 %** | eine Absicht, kein Feature |

## Punkt 1 — Erkennung · 55 %

*Vision: „Ab dann weiß MixCoach bei jedem Set automatisch, welcher Track wann
lief, wo jeder Übergang beginnt und endet — sekundengenau."*

Der Satz besteht aus zwei Zusagen, und sie stehen sehr unterschiedlich da.

**„Welcher Track wann lief" — weitgehend eingelöst.** 6113 Tracks im
Fingerprint-Index, alle Pfade auf macOS aufgelöst (`f7a9c0e`, 6112/6113). Recall
0,90 bei Precision 1,0. In 34 von 50 Reports steht die Trefferliste mit echten
Titeln, Interpreten und Zeitspannen. Der rekordbox-Import existiert als Endpoint
(`/library/rekordbox`). Offen: die Abdeckung schwankt zwischen 43 und 104 % der
Setlänge (Median ~67 %), und rund 10 % harmonisch statische Tracks bleiben mit
reinem Chroma unerkennbar.

**„Wo jeder Übergang beginnt und endet, sekundengenau" — nicht eingelöst.**
Recall 73 %, Precision 75 %, strikt korrekt 30 %. σ = 52,87 s. Vier unabhängige
Schätzer für den Blend-Onset gescheitert. Die vorhandenen Merkmale erklären 8 %
der Zeitvarianz. Ob der menschliche Bezugspunkt selbst scharf genug ist, um das
Versprechen überhaupt zu tragen, ist ungemessen — das klärt K1.

## Punkt 2 — Report · 65 %

*Vision: „Pro Übergang siehst du die Messwerte, die zählen […] Jeder Wert ist
anklickbar und sofort anhörbar."*

Gebaut und benutzbar: Wellenform, Timeline, Transitions-Explorer, Anhören an der
Stelle, Feedback-Knöpfe, Vergleichsansicht, Metrik-Erklärungen.

Die Messwerte sind allerdings **halb befüllt**:

| Wert | befüllt |
|---|---|
| BPM, Tonart, Camelot | 431/431 |
| `loudness_jump_db` | 214/431 · 50 % |
| `energy_dip_pct` | 217/431 · 50 % |
| `composite_quality_score` | 128/431 · 30 % |
| `bass_overlap_score` | **67/431 · 15 %** |

Bass-Overlap ist in der Vision namentlich als Ausbaustufe genannt und in der
Roadmap unter A3 — er liegt bei 15 %. Das ist der Wert, den sonst niemand
anbietet, und er fehlt in fünf von sechs Übergängen.

Dazu die offene Rechnung: `phrase_alignment_score` wird bedingungslos angezeigt
und in einen Ratschlag übersetzt, obwohl `phrase_beats_off` gleichverteilt ist.
Das ist ein aktiver Verstoß gegen den Markenkern und deshalb hier ein Abzug, kein
Nebensatz.

## Punkt 3 — Coach · 30 %

*Vision: „Der Coach erkennt Muster, die du selbst nicht siehst […] Daraus
entstehen Übungen aus deinem eigenen Material."*

Gebaut: Routen für Coach, Training, Career, DNA; `/coach/profile` als Endpoint;
`CoachProfilePanel`, `CoachInsight`, `ExerciseCard`.

Nicht gebaut ist der Kern. Alle 50 Reports enthalten Übungen, aber sie stammen
aus einer statischen `EXERCISE_LIBRARY`. Eine echte lautet:

> „Transition Review — Listen to the detected transition points and check whether
> the phrase timing feels natural."

Das ist eine allgemeine Aufgabe, kein Bezug auf eigenes Material, und sie schickt
den DJ ausgerechnet zu dem Wert, der nichts misst. Die Vision verspricht
dagegen: *„Mixe Übergang 3 aus deinem Set vom 04.07. noch einmal — gleiche
Tracks, Ziel: unter 4 Beats Abweichung."*

Der Abstand zwischen beidem ist die eigentliche Lücke bei Punkt 3.

## Punkt 4 — Fortschritt · 25 %

*Vision: „Das Skill-Radar entwickelt sich über Wochen […] und die Antwort ist
eine Kurve, keine Vermutung."*

Die Ansicht existiert samt Diagrammen und Skill-Beschriftungen. Aber der Zustand
liegt in `localStorage` (`lib/store.ts:68/76`). Das heißt konkret: Die Historie
überlebt keinen Browserwechsel, kein zweites Gerät, kein geleertes Cache. Für ein
Merkmal, das laut eurem eigenen Geschäftsmodell **der Abo-Grund** ist, ist das zu
wenig.

Zweiter Abzug: Ein Teil der Skills speist sich aus Phrasen-Timing — siehe oben.

## Punkt 5 — Teilen · 10 %

*Vision: „Ein Set-Report ist teilbar (ohne Audio) […] Jeder geteilte Report ist
Marketing."*

Es gibt ein Share-Symbol und eine DNA-Seite mit Ansätzen. Keine Bibliothek für
Bild- oder PDF-Export im Projekt, die Community-Seite trägt Platzhalter. Das ist
der am wenigsten begonnene Punkt — zugleich der billigste, wenn Punkt 2 steht.

---

# 2 · Die drei Burggräben

| Burggraben | Stand | Kurz |
|---|---|---|
| 1 · Daten-Schleife | **30 %** | Mechanik gebaut, Wirkung nicht belegt |
| 2 · Library-Verbindung | **70 %** | trägt, aber der rekordbox-Schatz liegt brach |
| 3 · Ehrlichkeit | **60 %** | Werkzeuge da, zwei aktive Verstöße |

**Erstens, die Daten-Schleife — 30 %.** Die Mechanik ist vollständig: Feedback-
Endpoints, `rematch.py`, `auto_retrain.py` mit Schwelle 10, Gate gegen
Verschlechterung, Fortschrittsanzeige. Aber die Wirkung, auf der das
Wachstumsargument ruht, ist gemessen schwach: **20 zusätzliche Sets bringen
+0,1 pp Precision.** Eine Messung, eine Sitzung — deshalb steht die Nachprüfung
als Job 3 im K1-Prompt. Bis dahin ist dieser Burggraben gebaut, aber unbelegt.

**Zweitens, die Library-Verbindung — 70 %.** Der stärkste Teil des Produkts. 6113
Tracks, Recall 0,90 bei Precision 1,0, echte Tracknamen im Report. Zwei Abzüge:
Der Landmark-Pfad läuft wegen `uint16` bei 25:22 über und hat auf keinem echten
Set je sauber gearbeitet. Und das rekordbox-XML liefert **6673 Beatgrids und 432
Cue-Punkte**, von denen nichts genutzt wird — obwohl die Spec festhält, dass
Beat-Phase aus den eigenen Features prinzipiell nicht messbar ist.

**Drittens, die Ehrlichkeit — 60 %.** Die Werkzeuge sind da: ein
`notMeasured`-Feld in allen 50 Reports, der `≈ Position geschätzt`-Badge, der
Warnbanner für Fallback-Reports. Zwei Abzüge: `notMeasured` enthält in allen 50
Reports dieselben drei Einträge (`eq`, `creativity`, `frequency`) — es ist eine
feste Liste, kein Mechanismus, der auf tatsächlich fehlende Messungen reagiert.
Und `phrase_alignment_score` wird angezeigt, obwohl es nichts misst.

---

# 3 · Die Roadmap-Teile

| | Stand |
|---|---|
| Teil 1 · Audio-Engine | **60 %** |
| Teil 2 · Frontend | **55 %** |
| Teil 3 · Online gehen | **10 %** |

**Teil 1 — 60 %.** A2 Fingerprinting stark. A3 Messwerte gebaut, aber halb
befüllt (Bass-Overlap 15 %, Vocal-Clash über Stem-Trennung seit `c176da4`
abgeschaltet). A4 Coaching verdrahtet, aber generisch. A5 teilweise: Analysezeit
nach dem Abschalten der Stem-Trennung um ~70 % gesenkt, Testsuite 195 grün.
**A1 Präzision ist die offene Kernlücke** — und nach dem Befund vom 30.07. keine
Fleißaufgabe mehr, sondern eine Frage, die vielleicht anders gestellt werden muss.

**Teil 2 — 55 %.** F2 Report-Erlebnis weitgehend fertig. F3 Fortschritt als
Oberfläche da, ohne haltbare Historie. F1 (Demo-Report, Onboarding) fehlt — der
erste Eindruck für jeden, der nicht Sebastian heißt. F4 Politur teilweise, F5
Bezahlschranke bewusst aus (`PAYWALL_DISABLED = true`).

**Teil 3 — 10 %.** Supabase im Frontend angelegt, Auth-Route da,
Pricing- und Premium-Seiten existieren, Stripe an drei Stellen referenziert, aber
nicht angebunden. Kein Hosting, keine Datenschutzerklärung, kein Löschkonzept.
Alles läuft auf einem Rechner.

---

# 4 · Gesamtbild

**Rund 40 % der Vision stehen.** Die Zahl allein täuscht aber, weil die
verbleibenden 60 % nicht gleich schwer sind:

- Ein Teil ist **schlichte Arbeit** — Historie in eine Datenbank, Bass-Overlap
  füllen, Demo-Report, Teilen-Funktion, Hosting. Absehbar, planbar, kein Risiko.
- Ein Teil ist **offene Forschung** — die sekundengenaue Übergangserkennung.
  Vier gescheiterte Ansätze, 8 % erklärte Varianz, und die Möglichkeit, dass der
  Zielwert selbst unscharf ist.

Der entscheidende Satz dieser Standortbestimmung lautet deshalb:

> **Der Forschungsteil steht nicht zwischen dir und dem Livegang. Du hast ihn
> selbst dorthin gestellt.**

Die Roadmap definiert die Schwelle als „Precision 75–80 %". Das war eine
vernünftige Setzung, solange man glaubte, dass mehr Labels dorthin führen. Diese
Annahme ist gemessen widerlegt. Die Schwelle festzuhalten heißt jetzt, den
Livegang an eine Frage zu binden, die niemand terminieren kann.

Und das ist nicht nötig. Was **heute** funktioniert — Trackerkennung mit
Zeitspannen, Lautheitsverlauf, Energiebogen, Pegelsprünge, Tonartabstand,
Bass-Overlap — beantwortet bereits die Frage, die kein anderes Tool beantwortet.
Es beantwortet sie nur nicht sekundengenau.

---

# 5 · Die nächsten Schritte

## Zuerst: die Schwelle neu setzen

Ersetze „Precision 75–80 %" durch eine Bedingung, die in deiner Hand liegt:

> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.**

Das ist strenger als es klingt — es schließt `phrase_alignment_score` in seiner
heutigen Form aus. Und es ist erreichbar, ohne eine einzige Forschungsfrage zu
lösen.

## Dann, in dieser Reihenfolge

**1 · K1-Prompt abarbeiten.** ~1 Woche. Räumt den Ehrlichkeitsverstoß, behebt den
`uint16`-Überlauf, prüft den ersten Burggraben und klärt, ob „sekundengenau"
überhaupt einlösbar ist. Danach weißt du, ob der Vision-Text an dieser Stelle
geändert gehört.

**2 · Historie aus dem Browser holen.** ~1 Woche. Analysen, Bewertungen und
Skill-Verlauf nach Supabase, das im Frontend längst konfiguriert ist. Ohne diesen
Schritt kann Punkt 4 nicht existieren — und Punkt 4 ist laut eurem eigenen
Geschäftsmodell das, wofür bezahlt wird. **Das ist der höchste Hebel im ganzen
Projekt, und es ist reine Handwerksarbeit ohne Forschungsrisiko.**

**3 · Die Messwerte füllen, die den Unterschied machen.** ~1 Woche.
Bass-Overlap von 15 % auf möglichst 100 %, `loudness_jump_db` von 50 % hoch.
Warum sie fehlen, ist zu klären — vermutlich hängen sie an der abgeschalteten
Stem-Trennung. Dann ist die Frage: gezielt für diese eine Messung wieder
einschalten, oder billiger nachbauen. Das sind die Werte, die die Vision als
Alleinstellung nennt.

**4 · Den Coach auf messbaren Boden stellen.** ~1–2 Wochen. Übungen aus dem
eigenen Material erzeugen — aber nur aus Größen, die tragen: „Bei deinem Übergang
von X nach Y kam B 4,2 dB lauter rein. Mix ihn nochmal, Ziel unter 1 dB." Das ist
exakt die Form, die die Vision verspricht, nur auf einer Messung, die es gibt.
Phrasen-Timing bleibt draußen, bis es misst.

**5 · Demo-Report und Teilen.** ~1 Woche. F1 und Punkt 5. Ab hier kann jemand
anderes als du das Produkt verstehen, ohne dass du daneben sitzt. Vorher ist
jeder Beta-Test verschenkt.

**6 · Online gehen.** 3–4 Wochen. Hosting, Konten, DSGVO-Basics, Stripe. Erst
jetzt, weil vorher niemand von außen etwas davon hätte.

**Gesamt: rund 8–10 Wochen bis zu einer geschlossenen Beta**, in der jeder
angezeigte Wert gemessen ist — und ohne dass die Timing-Frage vorher gelöst sein
muss. Sie läuft parallel weiter, aber sie blockiert nichts mehr.

## Das größte Risiko

Es ist nicht technisch. Es ist, dass die Übergangserkennung die interessanteste
Frage im Projekt bleibt und deshalb die Zeit bekommt, die Punkt 2 bis 5 bräuchten.
Vier gescheiterte Ansätze in einer Sitzung sind ein Warnsignal in beide
Richtungen: Das Problem ist hart — und es zieht Aufmerksamkeit an, die anderswo
mehr bewirkt.
