# Wege aus dem Label-Nadelöhr — Befund und Vorschläge

Stand: 30.07.2026 · Erstellt aus dem Prompt `PROMPT_SKALIERUNG_2026-07-30.md`.
Alle Zahlen in diesem Dokument sind an den Daten im Repo nachgemessen, nicht
übernommen. Die Skripte dazu liegen im Sitzungs-Scratchpad; die wichtigen sind
am Ende aufgeführt, damit sie bei Bedarf ins Repo wandern können.

**Die kurze Fassung:** „Mehr Labels" ist nicht mehr der bindende Engpass — das
ist gemessen. Der bindende Engpass ist, dass die vorhandenen Merkmale die
gesuchte Zeitinformation nicht enthalten (R² = 0,082) und dass unklar ist, ob
der menschliche Bezugspunkt überhaupt reproduzierbar ist. Bevor irgendetwas
gebaut wird, sollte diese zweite Frage beantwortet werden. Sie kostet einen
halben Abend.

---

## Vorbemerkung: eine Angabe im Prompt ist überholt

Der Prompt und `BEFUND_BLEND_ONSET.md` gehen davon aus, dass Job A offen ist.
Er ist seit Commit `f7a9c0e` (30.07.) abgeschlossen: von 6113 Pfaden in
`daten/library/index.json` sind **6112 auflösbar**. Die Musik liegt auf dem
Rechner. Alles, was der Blend-Onset-Befund als blockiert markiert hat, war für
diese Untersuchung offen — und wurde entsprechend gemessen (Abschnitt 1.6).

Die Ankerwerte reproduzieren exakt: `--mode spec` liefert Recall 73 %,
Precision 75 %, strikt korrekt 30 %, n = 287, 86 % zu spät, Median −29,85 s,
σ = 52,87 s. `--mode dedup`: 45 Sets, n = 161, Median −29,08 s, σ = 51,12 s.

---

# 1 · Befund aus Runde 1

## 1.1 Was ein Set kostet

| | |
|---|---|
| Ground-Truth-Dateien | 45 |
| bewertete Transitions | 358 |
| zusätzlich `missed` markiert | 98 |
| **Handgriffe gesamt** | **456** |
| Handgriffe je Set | Median 10, Mittel 10,1, Maximum 41 |
| gelabelte Audiodauer | 26,7 h (36 Sets mit bekannter Länge, Median 33 min) |

Die Analysezeit ist gemessen und in `c176da4` dokumentiert: 10,5 min für ein
70-Minuten-Set, davon 7,1 min Demucs-Stem-Trennung — die ist seit dem Commit
standardmäßig aus. Bleiben **rund 3,4 min je Set**. Rechenzeit ist nicht der
Engpass.

Realistische Schreibtischzeit je Set: 3 min Analyse plus 10 Übergänge à 1–3 min
Nachhören ≈ **15–35 min**, dazu die Aufnahme in Echtzeit. Der Weg von 20 auf 40
Aufnahmen kostet damit 8–12 h Klickarbeit plus 20 Gigs. Was diese Investition
bringt, steht in 1.2.

## 1.2 „Mehr Labels" ist nicht mehr der bindende Engpass

Drei unabhängige Belege.

**a) Ein Timing-Fix ändert die Precision um exakt null Punkte.**
`tools/analyze_timing_bias.py:229` rechnet
`precision = (correct + timing_off) / bewertet`. `timing_off` zählt bereits als
Treffer. Die Größe, die das Timing bewegt, heißt „strikt korrekt": 27 % heute,
Deckel bei 72 % (= Precision). Die Live-Schwelle „75–80 % Precision" und die
Timing-Baustelle sind **zwei verschiedene Zahlen** und wurden bisher als eine
behandelt.

**b) Die Lernkurve ist flach.** LOSO auf dem vorhandenen Feature-Cache
(3537 Zeilen, 25 Sets, läuft ohne Audio), je 6 Ziehungen, Betriebspunkt
`min_p = 0,6 / gap = 120`:

```
k Trainings-Sets |  Recall  Precision      F1   sigma(P)
        4        |   87,7%      55,6%   0,680   ±1,9 pp
        8        |   87,7%      55,4%   0,679   ±1,3 pp
       12        |   89,9%      56,1%   0,690   ±1,6 pp
       16        |   91,5%      56,7%   0,700   ±0,8 pp
       20        |   93,6%      56,2%   0,702   ±0,7 pp
       24        |   94,1%      55,7%   0,700   ±0,0 pp
```

Zwanzig zusätzliche Sets: **+0,1 pp Precision**, +6,4 pp Recall. Am
Precision-Betriebspunkt (`min_p = 0,7`) steigt die Precision von 63,6 auf
70,0 % — 20 Sets für 6 pp, bei 20 pp Recall-Verlust, und ab k = 12 auch dort
flach. Auf dieser Kurve kostet 75 % Precision über den Labelweg dreistellig
viele Sets.

**c) Der Betriebspunkt ist der stärkere Hebel als die Datenmenge.** Derselbe
Sweep, dieselben Labels:

```
min_p=0,6 gap= 60 → R 94,1%  P 39,9%
min_p=0,6 gap=120 → R 94,1%  P 55,7%    nur der Mindestabstand geändert
min_p=0,7 gap=120 → R 45,3%  P 70,0%
```

+15,8 pp Precision bei unverändertem Recall, allein über `min_gap`. Das aktive
Modell fährt `gap = 90`. Der Retrain vom 28.07. hatte eine Konfiguration mit
R 80,4 / P 71,1 bereits gefunden und verworfen — `auto_retrain_state.json`:
`"exported": false, "reason": "worse_on_new_sets"`. Der Recall-Vorrang-Gate
(`retrain_model.py:37`, `MIN_RECALL = 0.80`) blockiert genau den Tausch, den
das Projekt sucht.

## 1.3 Der eigentliche Engpass: die Merkmale tragen die Zeit nicht

Das ist die wichtigste Messung dieser Untersuchung.

`build_features.py:37-38` setzt `FAIR_BEFORE = 45.0`, `FAIR_AFTER = 60.0`: ein
Kandidat gilt als positiv, wenn er *irgendwo* in einem 105-s-Fenster liegt. Der
Kommentar in `retrain_model.py:74` sagt es selbst — Sekundengenauigkeit war nie
Ziel und ist mit dieser Definition nicht erreichbar. Naheliegender Schluss: die
161 exakten `correctedSec` schärfer nutzen.

Ich habe geprüft, ob das etwas bringen kann. Statt „ja/nein im 105-s-Fenster"
wurde auf denselben 17 Merkmalen der **Versatz** regressiert (Wahrheit minus
Kandidatenzeit), LOSO über 19 Aufnahmen, 1321 Kandidatenpaare:

```
Ausgangsstreuung des Versatzes        Median  +7,40 s   sigma 29,76 s   in 8 s 16 %
nach LOSO-Regression (17 Merkmale)    Median  +0,16 s   sigma 28,52 s   in 8 s 19 %
globaler konstanter Offset            Median  +0,00 s   sigma 29,76 s   in 8 s 15 %

erklärter Varianzanteil R² = 0,082
```

**Die Merkmale erklären 8 % der Zeitvarianz.** σ sinkt um 4 % gegenüber dem
konstanten Offset — und ein konstanter Offset gilt in diesem Projekt
definitionsgemäß als kein Fortschritt.

Damit ist eine ganze Klasse von Vorschlägen erledigt: schärfere Labels, andere
Verlustfunktionen, Ranking statt Zeitstempel, mehr Sets — alles, was auf den
heutigen 17 Merkmalen arbeitet, kann das Timing nicht lösen. Nicht weil zu
wenig Daten da sind, sondern weil die Antwort nicht in den Eingangsdaten steht.

## 1.4 Das Label-Material ist dünner, als 45 Dateien klingen

**45 Dateien sind 28 Aufnahmen, davon 20 verwertbar.**

```
REC001.WAV        11 GT-Dateien  →  11 bewertete Marker insgesamt (8 davon je genau einer)
ohne Ergebnis-JSON  8 Gruppen, 68 Marker — kein Audio auffindbar, für Training unbrauchbar
Dec25 / REC010     je 3 GT-Dateien derselben Aufnahme
```

14 der 45 Dateien haben ≤ 2 Handgriffe; zehn haben genau einen, obwohl die
Engine 6–9 Marker gesetzt hatte — abgebrochene Label-Sitzungen. Ihr Beitrag zur
Metrik: 18 bewertete Transitions mit **11 % Precision**. Ohne sie steigt die
gemessene Precision von 72,1 auf 75,3 %.

**Zwei Stämme:** 24 gemeinsame IDs, 18 byteidentisch, 6 abweichend — in allen
sechs Fällen ist `daten/` der jüngere Stand. `--mode spec` zählt die 24 doppelt,
daher die Differenz 638 zu 358.

**43 % der Fehlalarme sind Doubletten.** Von 100 `not_a_transition` liegen 43
näher als 105 s an einem echten Übergang, 21 weitere stammen aus Sets ganz ohne
echten Übergang.

Hier muss ich eine eigene Zwischenaussage korrigieren: die naheliegende Rechnung
„ohne die 43 Doubletten wäre die Precision 81,9 %" ist eine **Orakel-Schranke**,
kein erreichbarer Wert. Nachgemessen mit echten Auswahlregeln (Marker im Cluster
nach Konfidenz / frühester / spätester), bewertet auf derselben Ground Truth:

```
Regel        gap | Precision  Recall  strikt     F1
heute          - |     72,1%   72,5%   27,1%   72,3
Konfidenz    120 |     74,6%   66,9%   27,3%   70,5
frühester    120 |     75,1%   66,9%   28,1%   70,7
spätester    120 |     73,8%   66,3%   26,6%   69,8
Orakel       120 |     77,0%   68,5%   28,7%   72,5
Orakel       150 |     79,0%   61,2%   28,6%   69,0
```

Selbst das Orakel kommt nicht auf 82 %. Nachträgliches Entdoppeln bringt real
**+3 pp Precision für −5,6 pp Recall** — nützlich, aber kein Durchbruch.

Die 1–5-Bewertungen liegen in `labels_prefilled.csv`: 358 ausgefüllt über 31
Sets, Verteilung `0:31 · 1:0 · 2:43 · 3:61 · 4:60 · 5:163`. Keine einzige 1,
46 % Fünfen. Betrifft die Composite-Anpassung, also die Sperrzone
`app/audio/scoring/*` — hier nur zur Kenntnis.

## 1.5 Wo die Ausbeute je Handgriff am kleinsten ist

- **21 % der Klickarbeit ist fürs Training wertlos**: 95 der 456 Handgriffe
  stecken in den 8 Gruppen ohne Ergebnis-JSON. Sie zählen in der Referenzmetrik,
  aber `collect_feedback_rows()` überspringt sie („kein Audio gefunden").
- **11 GT-Dateien für REC001 werden zu einem Trainings-Set.** Beim Training
  korrekt zusammengeführt, in der Referenzmetrik nicht — dort zählt REC001 elfmal.
- **97 `correct`-Klicks bestätigen, was die Engine schon hat.** Nicht wertlos
  (unbewertete Marker werden im Training stillschweigend zu Negativen), aber der
  informationsärmste Teil.
- **`missed` ist der teuerste und wertvollste Handgriff** — 98 Stück, jeder
  verlangt das Finden einer Stelle, die die Engine gar nicht angeboten hat.

## 1.6 Vier Versuche, den Übergangszeitpunkt zu messen — alle negativ

Da die Library jetzt vorliegt, war der von `BEFUND_BLEND_ONSET.md` empfohlene
Weg offen: den Blend-Onset messen, statt ihn zu erschließen. Der Suchraum ist
dabei kein Problem, weil das Chroma-Matching bereits sagt, **welcher** Track
läuft — gesucht ist nur noch **wann**. Vier Schätzer, jeweils gegen dieselbe
Ground Truth (`timing_off` mit `correctedSec`, Zuordnung über die Engine-Zeit,
Fenster ± 90 s), 12 Sets:

```
                                              n    Median    sigma   in 8 s
Engine mid_sec (Basislinie)                  56   −24,28    29,92      5 %
Engine start_sec (heute aktiv)               56    +1,84    79,68      9 %

Chroma, Dominanzbeginn (_played_window)      44   −32,23    35,22      9 %
Chroma, Beitragskurve ab 15 % des Plateaus   44   −30,56    34,75     11 %
Landmark, kohärente Treffer ab 20 %          36   −33,40    47,34      6 %
Landmark, Ende des Laufs (A ist weg)         31   −30,47    56,65      6 %
Landmark, Verlassen des Plateaus (A geht)    30   −41,15    58,03     20 %
```

**Kein Schätzer schlägt `mid_sec`.** σ steigt bei allen. Zwei Beobachtungen sind
wichtiger als die Zahlen selbst:

1. **Die Chroma-Beitragskurve steigt sprunghaft, nicht allmählich.** Zwischen
   „ab 15 % des Plateaus" und „Dominanzbeginn" liegen 1,7 s. Der Grund steht in
   `library_match.py:86-96`: `_whiten()` nimmt die *zeitliche Ableitung* des
   Chroma. Während eines Blends ist das die Ableitung des Gemischs; die
   Korrelation mit der Solo-Ableitung von Track B rastet erst ein, wenn A weg
   ist. Chroma kann den Blend-Onset prinzipiell nicht sehen.

2. **Auch Landmark-Hashes finden Track B nicht früher.** Sie überleben
   Überlagerung — das war die Hoffnung — und liefern trotzdem einen Onset, der
   im Median 33 s **nach** dem menschlichen Bezugspunkt liegt. Alle 100
   Track-Treffer waren dominant (keiner verworfen), die Erkennung selbst
   funktioniert also einwandfrei.

Wenn drei unabhängige Verfahren übereinstimmend sagen „Track B ist zu diesem
Zeitpunkt noch nicht da", dann markiert der Mensch **nicht** den Einsatz von
Track B. Der einzige Schätzer, der beim 8-s-Kriterium über der Basislinie liegt,
ist ausgerechnet „Track A verlässt sein Plateau" (20 % gegen 5 %) — bei kleinem
n und großem σ, also nur ein Hinweis. Er passt aber zur Vermutung: der Mensch
markiert womöglich, wann **A anfängt zu gehen** (Filter, Bass-Kill), nicht wann
B kommt.

## 1.7 Nebenbefunde, die unabhängig von allem anderen gelten

**Ein Überlauf im Landmark-Fingerprint.** `landmark_match.py:72` und `:93` legen
`frames` als `uint16` ab. Der größte darstellbare Frame ist 65535, das sind bei
`HOP = 512` und `SR = 22050` genau **1521,7 s = 25 min 22 s**. Für Library-Tracks
reicht das; für Mixe nicht — jede aufgenommene Aufnahme hier ist 28 bis 120 min
lang. Unter numpy 2 wirft die Umwandlung (so ist sie mir aufgefallen), unter
numpy 1 lief sie mit stillem Modulo-Überlauf durch. Die Tests
(`tests/test_landmark_match.py`) arbeiten mit 40–80 s, die synthetischen Mixe
mit ~4 min — die Grenze wird von keinem Test berührt. Konsequenz: **der
Landmark-Pfad ist auf echten, vollständigen Sets nie sauber gelaufen.** Das
entwertet die gemessene Laufzeit (~2000–2400 s je Lücke) nicht, wohl aber die
Qualitätsaussagen über die Vorfilter-Versuche. Ein Fix ist eine Zeile je Stelle.

**Zwei angezeigte Messwerte messen heute nichts.**

- `bpm_drift` ist in **90 % von 431 Transitions exakt 0,0**, der Median des
  Betrags ist 0. Vor und nach dem Übergang steht praktisch immer dieselbe Zahl.
- `phrase_beats_off` ist über 0–16 Beats nahezu gleichverteilt (Median 7,01,
  nur 3 % unter 0,5 Beats, 81 % über 2 Beats). Bei einem DJ, der auf Phrase
  mischt, müsste sich das bei 0 häufen.

Beide gehen ins Frontend (`SetTimeline.tsx:102-103`) und in Textbausteine
(`SetTransitionsExplorer.tsx:233`: „Off-phrase: cue point misses the 16-bar
grid"). Das verletzt die Ehrlichkeitslinie **heute**, unabhängig von jedem
Zukunftsweg.

**Die offene Frage der Spec zu `beat_alignment.py` ist beantwortet.** Das Modul
arbeitet nicht auf dezimiertem Chroma, sondern auf der Beat-Liste des globalen
Trackers aus dem Audio, und misst ehrlich dokumentiert die *Regelmäßigkeit* der
Beat-Abstände, keine Phase. Es bewertet also kein Rauschen — aber es misst über
das Fenster `[start_sec, end_sec]`, und genau dieses Fenster ist das, was die
Engine falsch legt.

**Die engine-eigene Tempo-Erkennung liegt für die halbe Library daneben.** Gegen
die rekordbox-Beatgrids gemessen: von 421 `*.analysis.v2.json` liegen 48 %
innerhalb 1 BPM, von 2045 `*.analysis.json` nur 27 %. Der Index-BPM stimmt
dagegen mit rekordbox überein (σ 0,06) — er stammt aus den Tags.

## 1.8 Antwort auf die Leitfrage

**Nein, „mehr Labels" ist nicht mehr der bindende Engpass.** Die Lernkurve ist
bei 4–6 Sets gesättigt. Bindend sind heute drei andere Dinge:

1. **Die Merkmale tragen die Zeitinformation nicht** (R² = 0,082). Das ist die
   harte Grenze; sie lässt sich weder durch Labels noch durch Umlabeln überwinden.
2. **Der menschliche Bezugspunkt ist mit keinem der vier geprüften Verfahren
   reproduzierbar.** Ob er überhaupt reproduzierbar ist — auch für den Menschen
   selbst — ist ungeprüft.
3. **Die Buchhaltung der Metrik** (Doubletten, leere Sets, Doppelzählung über
   zwei Stämme) drückt die gemessene Precision um rund 3 pp unter den
   tatsächlichen Stand und die Set-Zahl um 17 Dateien über den tatsächlichen.

Damit ist auch die Live-Schwelle neu zu lesen: 28 Aufnahmen statt 45 Dateien,
Precision 75,3 % statt 72,1 %, sobald leere Sets nicht mehr mitzählen. Die
Schwelle „15–20 Sets, 75–80 % Precision" ist der Sache nach **erreicht**. Was
fehlt, ist das Timing — und das hängt an keiner der beiden Zahlen.

---

# 2 · Runde 2 — die Vorschläge, nach Familien

Kurz gehalten. Was nach Runde 1 bereits als widerlegt gelten muss, ist als
solches gekennzeichnet — das ist der Sinn der Reihenfolge.

## A · Labels ohne Handarbeit gewinnen

**A1 · rekordbox-Beatgrid als Phrasenraster im Mix.** Das XML bildet **6112 von
6113** Library-Tracks ab (nach derselben Pfadersetzung wie in Job A), 6673
Beatgrids, davon 3170 mit mehreren TEMPO-Marken. Ist ein Track im Set erkannt
und ausgerichtet, folgt daraus das exakte Downbeat- und Phrasenraster des Mixes
an dieser Stelle — ohne Beat-Tracking auf dem Mix. Ersetzt die Größe, die laut
Spec aus Chroma prinzipiell nicht messbar ist.

**A2 · Cue-Punkte als schwache Mix-In/Mix-Out-Labels.** 432 Cues auf 196 Tracks.
**92 % liegen exakt auf einem Beat, 64 % auf einer 16-Beat-Phrase.** Die Lage im
Track ist klar zweigipflig: 179 Cues in den ersten 20 %, 134 zwischen 70 und
90 %. Das ist die Signatur von Mix-In und Mix-Out.

**A3 · Playlists als Kandidatenliste.** Von 128 in den eigenen Sets erkannten
Track-Instanzen liegen **118 (92 %) in irgendeiner rekordbox-Playlist** — 835
verschiedene Tracks, 14 % der Library. Eine einzelne Playlist deckt je Set 3/6
bis 11/11 der Tracks ab. Der Suchraum schrumpft global um Faktor 7, mit einer
Playlist-Auswahl um Faktor 100–250. Genau an dieser Größe ist der
Landmark-Ansatz gescheitert. **Wert nach Runde 1 gesunken:** die Erkennung
funktioniert bereits, und der Zeitpunkt wird dadurch nicht besser (1.6).

**A4 · rekordbox-History als Tracklist mit Uhrzeit.** In diesem Export nicht
enthalten. Für künftige Sets könnte rekordbox die gespielte Reihenfolge samt
Zeitpunkt mitschreiben — dann ist der Trackwechsel nicht mehr zu erkennen,
sondern abzulesen. Ungeprüft, weil kein History-Knoten im vorliegenden XML.

## B · Andere Form von Supervision

**B1 · Übergänge als Intervall labeln und bewerten.** Die Spec-Diagnose lautet:
die Engine gibt einen Punkt aus, wo ein Intervall hingehört. Konsequent wäre,
auch das Label als Intervall zu erheben und die Metrik auf Überlappung (IoU)
umzustellen. Ein großer Teil der 287 `timing_off` ist dann kein Fehler, sondern
eine Definitionslücke.

**B2 · Label-Definition schärfen (`FAIR_BEFORE`/`FAIR_AFTER`).**
**In Runde 1 gemessen widerlegt** — R² = 0,082. Auf den heutigen Merkmalen
bringt eine schärfere Definition nichts.

**B3 · Paarvergleich statt Zeitstempel** („welcher der beiden Marker liegt
näher?"). Billig je Urteil, kein Scrubben. **Schwach**: erzeugt eine Ordnung,
keine absolute Zeit — und die Ordnung müsste aus denselben Merkmalen gelernt
werden, die die Zeit nicht tragen.

**B4 · Selbstüberwachtes Vortraining** auf ungelabeltem Mix-Material, Aufgabe
„stammen diese beiden Ausschnitte aus demselben Track?". Adressiert genau die
Unterscheidung, an der der Blend-Onset-Versuch gescheitert ist. **Schwach für
dieses Projekt**: kein GPU-Stack, Wochen Aufwand, kein billiger Killer-Test.

**B5 · Rauschmodell für die vorhandenen Labels** (asymmetrischer Verlust, „zu
spät" härter bestrafen). **Schwach**: verschiebt den Median, nicht σ — genau
das, was die Spec als keinen Fortschritt definiert.

## C · Andere Zielgröße

**C1 · Nicht „wann", sondern „wie lang".** Die Transitionslänge (8–64 Takte) ist
die eigentliche Streuungsquelle. Start und Ende auszugeben macht die Länge zur
Messgröße und ist für den DJ direkt nützlich („24 Beats Blend").

**C2 · Trackwechsel statt Übergang.** Der Segmentwechsel ist eine harte Tatsache,
der Blend-Verlauf eine Schätzung. „Track A → Track B, Wechsel im Fenster
12:03–12:47" ist heute schon lieferbar; die Fingerprint-Abdeckung liegt bei
43–104 % der Setlänge, Median rund 67 %.

**C3 · Die Bewertung vom Zeitpunkt entkoppeln.** Pegelsprung, LUFS-Verlauf,
Bass-Overlap brauchen ein *Fenster*, keinen Punkt. Ein Übergangs-Score über 60 s
ist robust gegen ± 30 s Zeitfehler.

## D · Fremde Datenquellen

**D1 · EDM-CUE (ETH-DISCO).** 4710 EDM-Tracks, **21 461 von Profi-DJs von Hand
gesetzte Cue-Punkte**, aus vier privaten rekordbox-Bibliotheken. Code MIT,
Datensatz auf Hugging Face, **ohne Audio** — nur Metadaten, Beat/Downbeat und
Referenzen. Dieselbe Datenstruktur wie Sebastians eigene 432 Cues, nur 50-mal
so groß. Die genaue Datensatz-Lizenz habe ich nicht verifiziert (siehe
Abschnitt 5).

**D2 · UnmixDB und verwandte CC-lizenzierte Mix-Datensätze.** Automatisch
erzeugte Mixe mit exakter Ground Truth. Als Trainingsdaten laut Befund vom
28.07. schädlich — als **Prüfstand** für eine Timing-Änderung aber tauglich,
weil dort die Wahrheit definitionsgemäß stimmt. Dasselbe gilt für die 162
eigenen synthetischen Mixe: der Unterschied zwischen „Training" und „Prüfstand"
trägt, weil ein Prüfstand nur eine *notwendige* Bedingung testet — wer auf
synthetischen Mixen mit bekanntem Crossfade das Timing nicht trifft, trifft es
auf echten erst recht nicht.

**D3 · Öffentliche Tracklists mit Zeitstempeln.** Sechs der gelabelten
Aufnahmen sind bereits fremde DJ-Sets (Dixon ×2, Four Tet, RÜFÜS DU SOL, Joris
Voorn, Be Svendsen) und tragen **140 von 323 bewerteten Markern, also 43 %**.
Für viele solcher Sets existieren von Hand erstellte Tracklists.
**Schwach, und zwar aus zwei Gründen:** die Lizenzlage ist ungeklärt — es gibt
nur inoffizielle Scraper, keine offizielle Schnittstelle mit
Nutzungsbedingungen, und die Seite blockt automatisierte Zugriffe aktiv; und
die Zeitangaben sind minutengenau. Für ein Ziel von σ < 8 s ist das unbrauchbar.

## E · Produkt und Nutzer

**E1 · Korrigieren mit sofortigem Eigennutzen.** `rematch.py` und der Knopf „Mit
meinen Korrekturen neu erkennen" existieren bereits. Heute ist die Korrektur
überwiegend Wohltat fürs Modell; sie müsste unmittelbar einen sichtbar besseren
Report erzeugen.

**E2 · Beta-DJs liefern ihre rekordbox-XML statt Klicks.** Der wertvollste
Import ist nicht das Audio, sondern das XML: Beatgrid, Cues, Playlists. Ein
Nutzer liefert damit Supervision, ohne einen einzigen Klick zu machen — und
`app/library/manager.py` hat mit `parse_rekordbox_xml()` bereits einen Einleser.

**E3 · Der Übungs-Loop als Labelquelle.** Wer denselben Übergang zweimal mixt,
liefert ein Paar mit bekannter Beziehung. Ordinale Supervision ohne Zeitstempel.
Setzt voraus, dass das Übungsfeature existiert — tut es nicht.

## F · Umgehen statt lösen

**F1 · Tracklist-Produkt.** Fingerprinting liefert echte Tracknamen mit
Zeitspannen. Das ist für sich genommen ein Produkt und hängt nicht an der
Übergangserkennung.

**F2 · Set-Dramaturgie statt Übergangsurteil.** LUFS- und Energieverlauf über
das ganze Set: 50 Reports haben `volumeCurve`, 31 `loudness`. Zeitfehler von
± 30 s sind hier ohne Belang.

**F3 · Die A1-Lücke sichtbar stehen lassen.** Der `≈ Position geschätzt`-Badge
existiert. Konsequent wäre, *jeden* Übergang mit einem Unsicherheitsband statt
einer Zeitangabe anzuzeigen — die Streuung ist ja gemessen.

**F4 · Die beiden Schein-Messwerte entfernen oder reparieren.** `bpm_drift`
(90 % exakt 0) und `phrase_beats_off` (gleichverteilt) verletzen die
Ehrlichkeitslinie heute. Kein Zukunftsweg, sondern eine offene Rechnung.

---

# 3 · Runde 3 — die drei Kandidaten

Ausgewählt nach dem Verhältnis aus möglichem Gewinn zu Aufwand bis zur
Widerlegung. Kandidat 1 ist bewusst kein Bauvorhaben.

## K1 · Prüfen, ob der Zielwert überhaupt reproduzierbar ist

| | |
|---|---|
| **Was genau** | Sebastian labelt ein bereits gelabeltes Set ein zweites Mal, blind gegenüber seinen früheren Zeitangaben — dieselben 20–25 Übergänge, gleiche Oberfläche. Danach wird die Streuung zwischen erster und zweiter Angabe gemessen, in denselben Größen wie die Referenzmetrik. |
| **Warum plausibel** | Vier unabhängige Schätzer verfehlen den menschlichen Bezugspunkt gleichsinnig um 24–41 s (Abschnitt 1.6), und die vorhandenen Merkmale erklären 8 % der Zeitvarianz (Abschnitt 1.3, `build_features.py:37-38`). Wenn Verfahren, die nachweislich messen *können*, alle danebenliegen, ist zu prüfen, ob der Zielwert selbst stabil ist. Das Akzeptanzkriterium aus `CLAUDE_CODE_SPEC_2026-07-29.md` („σ deutlich unter 53 s, innerhalb 8 s ≥ 50 %") setzt eine menschliche Wiederholgenauigkeit von deutlich unter 8 s voraus — die ist nie gemessen worden. |
| **Killer-Test** | Das Experiment *ist* der Killer-Test. Ein Abend, rund 30–45 min Arbeit, kein Code. Widerlegt wird die Sorge, wenn die Selbst-Übereinstimmung σ < 5 s ergibt: dann ist der Zielwert scharf und alle bisherigen Misserfolge liegen an den Verfahren. |
| **Messgröße** | σ und „innerhalb 8 s" zwischen erster und zweiter Labelrunde derselben Übergänge. |
| **Aufwand** | ½ Tag, davon der größere Teil nicht Entwicklung, sondern Sebastians Zeit. Ein kleines Skript für den Vergleich der beiden Stände: ~2 h. |
| **Was es kaputtmachen kann** | Nichts am Code. Das Risiko ist ein unbequemes Ergebnis: Liegt die Selbst-Streuung bei ± 20 s, dann ist das Akzeptanzkriterium von Job B unerreichbar und muss neu geschrieben werden. Das ist kein Schaden, sondern der Punkt. Für die Ehrlichkeitslinie ist es sogar Voraussetzung — eine Sekundenangabe anzuzeigen, deren Referenz um ± 20 s schwankt, wäre ein Verstoß. |

**Wichtiger Nebeneffekt:** Wenn die zweite Runde auf demselben Set stattfindet,
lässt sich zugleich prüfen, *was* Sebastian eigentlich markiert. Ein Zusatzfeld
mit drei Optionen („A geht raus" / „B kommt rein" / „beide zusammen") kostet
nichts und beantwortet die Frage aus 1.6, die drei Messungen aufgeworfen haben.

## K2 · rekordbox-Beatgrid und Cue-Punkte als externe Zeitreferenz

| | |
|---|---|
| **Was genau** | Das rekordbox-XML einlesen (Pfadersetzung wie in Job A) und Beatgrid, Taktart und Cue-Punkte je Track an den Library-Index hängen. Sobald ein Track im Set erkannt und ausgerichtet ist, ist damit das exakte Downbeat- und Phrasenraster des Mixes an dieser Stelle bekannt — ohne Beat-Tracking auf dem Mix und ohne einen einzigen neuen Klick. |
| **Warum plausibel** | Nachgemessen: **6112 von 6113** Library-Tracks haben einen XML-Eintrag, 6673 Beatgrids liegen vor, 92 % der 432 Cue-Punkte liegen exakt auf einem Beat und 64 % auf einer 16-Beat-Phrase. Zugleich ist belegt, dass die Engine diese Größe heute nicht hat: `phrase_beats_off` ist über 0–16 Beats gleichverteilt (Median 7,01, nur 3 % unter 0,5) und `bpm_drift` in 90 % der Fälle exakt 0. `CLAUDE_CODE_SPEC_2026-07-29.md` hält fest, dass Beat-Phase aus den Chroma-Features mit Hop 372 ms prinzipiell nicht messbar ist — hier liegt genau diese Größe extern vor. |
| **Killer-Test** | Für die 12 Sets mit Fingerprint-Treffern das rekordbox-Raster über die bekannte Ausrichtung in die Set-Zeitachse projizieren und prüfen, wie die 161 `correctedSec` relativ zu den 16- und 32-Beat-Grenzen liegen. Bleibt die Phasenlage gleichverteilt, trägt das Raster nichts — dann ist auch der ganze Weg tot. Läuft ohne neues Audio auf der Ausrichtungs-Maschinerie, die für Abschnitt 1.6 bereits geschrieben ist; Laufzeit unter einer Stunde. |
| **Messgröße** | Primär: Anteil der `correctedSec` innerhalb ± 1 Beat einer 16- bzw. 32-Beat-Grenze, gegen die Nullhypothese Gleichverteilung (Erwartung 12,5 % bzw. 6,25 %). Sekundär, erst danach: „innerhalb 8 s" nach Einrasten der Marker auf das Raster. |
| **Aufwand** | Killer-Test 1 Tag. Vollständige Anbindung ans Produkt (XML-Import, Index-Erweiterung, Projektion in `transition_quality.py`) 3–5 Tage. |
| **Was es kaputtmachen kann** | `phrase_beats_off` und `phrase_alignment_score` würden sich ändern — das ist beabsichtigt, weil sie heute nichts messen. Berührt `app/audio/scoring/*` nicht, solange nur das Raster ersetzt wird. Für die Ehrlichkeitslinie ein Gewinn: aus einer erfundenen Zahl wird eine gemessene, und wo kein Beatgrid vorliegt, bleibt das Feld leer. Ein Risiko: 3170 Tracks haben *mehrere* TEMPO-Marken (variables Grid) — die einfache Annahme „erster Downbeat plus konstantes Tempo" gilt dort nicht und muss behandelt werden. |

## K3 · Ausliefern, was gemessen ist — und aufhören anzuzeigen, was es nicht ist

| | |
|---|---|
| **Was genau** | Den Report auf die Größen umstellen, die heute belastbar sind: benannte Tracks mit Zeitspannen (Fingerprint), LUFS- und Energieverlauf über das Set, Übergang als **Fenster mit Unsicherheitsband** statt als Sekundenangabe. Gleichzeitig `bpm_drift` und `phrase_alignment_score` aus der Anzeige nehmen, bis sie etwas messen. |
| **Warum plausibel** | Die Bausteine sind vorhanden und befüllt: 50 Reports mit `volumeCurve`, 31 mit `loudness`, 431 Transitions mit `start_sec`/`end_sec`, Fingerprint-Abdeckung 43–104 % der Setlänge (Median ~67 %), der `≈ Position geschätzt`-Badge in `SetTransitionsExplorer.tsx:590-596` ist bereits gebaut. Umgekehrt sind `bpm_drift` in 90 % von 431 Transitions exakt 0,0 und `phrase_beats_off` gleichverteilt — beides wird in `SetTimeline.tsx:102-103` angezeigt und in `SetTransitionsExplorer.tsx:233` in einen Ratschlag übersetzt. |
| **Killer-Test** | Kein Messexperiment, sondern ein Nutzer-Test: einen so umgebauten Report für zwei bis drei echte Sets erzeugen und einem DJ vorlegen, der nicht Sebastian ist. Die Frage ist nicht „stimmt es", sondern „ist es ohne die Übergangsbewertung noch etwas wert". Fällt die Antwort nein aus, ist der Weg tot und A1 bleibt Voraussetzung fürs Live-Gehen. Ein Tag Vorbereitung, ein Gespräch. |
| **Messgröße** | Keine der Referenzmetrik-Größen — bewusst. Diese Idee ändert die Erkennung nicht, sie ändert, was ausgeliefert wird. Kontrollgröße: Recall und Precision dürfen sich nicht verändern (sie werden nicht angefasst). |
| **Aufwand** | Anzeige-Umbau 2–3 Tage. Das Entfernen der beiden Schein-Messwerte: Stunden. |
| **Was es kaputtmachen kann** | Es nimmt dem Report zwei Zahlen, die heute Substanz vortäuschen — genau das ist der Zweck. Konflikt mit der Ehrlichkeitslinie besteht **in der Gegenrichtung**: sie zu behalten ist der Verstoß. Risiko: Das Produkt wirkt kleiner. Es wäre dann kleiner und wahr statt größer und teilweise erfunden. |

---

# 4 · Empfehlung

**Zuerst K1 — die zweite Labelrunde auf einem bereits gelabelten Set, mit dem
Zusatzfeld „was markierst du eigentlich".**

Der eine Satz dazu: Solange nicht feststeht, ob der menschliche Bezugspunkt auf
weniger als 8 s reproduzierbar ist, kann niemand sagen, ob das Akzeptanzkriterium
von Job B erreichbar ist — und jede weitere Woche Arbeit an Schätzern läuft
gegen ein Ziel, dessen Schärfe ungeprüft ist.

Danach, in dieser Reihenfolge und je nach Ergebnis:

- **σ des Menschen unter 5 s:** Der Zielwert ist scharf, die Verfahren sind
  schuld. Dann K2 als nächstes, weil es die einzige geprüfte externe Quelle für
  eine Größe ist, die im Haus nachweislich fehlt.
- **σ des Menschen über 15 s:** Das Akzeptanzkriterium in
  `CLAUDE_CODE_SPEC_2026-07-29.md` neu schreiben — von einem Punkt auf ein
  Intervall (B1/C1) — und K3 vorziehen. Ein Produkt, das ein ehrliches Fenster
  zeigt, ist dann nicht die Notlösung, sondern die richtige Darstellung.

Unabhängig davon und sofort, weil billig und von allem anderen unberührt:

1. Den `uint16`-Überlauf in `landmark_match.py:72` und `:93` beheben und einen
   Test mit mehr als 26 min Material ergänzen. Zwei Zeilen plus ein Test.
2. Die 8 Ground-Truth-Dateien ohne Ergebnis-JSON und die 10 mit einem einzigen
   Verdict kennzeichnen oder aussortieren — sie machen 21 % der Klickarbeit
   trainingsunwirksam und verzerren die Referenzmetrik.
3. `--mode dedup` zur Vorgabe machen und zusätzlich nach `fileName` gruppieren,
   nicht nach `analysisId`. Sonst zählt REC001 weiter elfmal.

**Was ich nicht empfehle:** weitere Sets zu labeln, bevor K1 beantwortet ist.
Die Lernkurve sagt, dass 20 zusätzliche Sets 0,1 pp Precision bringen; die
Zeitregression sagt, dass sie am Timing nichts ändern können. Das ist der teure
Weg mit dem gemessen kleinsten Ertrag.

---

# 5 · Was ich nicht beantworten konnte

**Ob der Blend-Onset grundsätzlich messbar ist.** Ich habe vier Schätzer gebaut
und alle vier verfehlen die Referenz. Das sind vier Versuche aus einer Sitzung,
keine erschöpfende Suche. Sie verschieben die Beweislast, sie schließen nichts
aus. Was fehlt: ein Verfahren, das Track A *aktiv herausrechnet* (Stem-Trennung
oder spektrale Subtraktion des ausgerichteten Track-A-Signals) und erst im
Residuum nach B sucht. Dafür bräuchte ich die Stem-Trennung, die in `c176da4`
gerade abgeschaltet wurde, und deutlich mehr Rechenzeit.

**Was Sebastian beim Labeln tatsächlich markiert.** Die drei übereinstimmenden
Messungen aus 1.6 legen nahe, dass es nicht der Einsatz von Track B ist. Das ist
eine Vermutung aus Indizien. Beantworten kann sie nur er selbst — deshalb das
Zusatzfeld in K1.

**Die genaue Lizenz von EDM-CUE.** Der Code ist MIT, der Datensatz liegt auf
Hugging Face und enthält kein Audio. Welche Lizenz für die Annotationen gilt,
habe ich auf der Projektseite nicht gefunden und nicht auf Hugging Face
nachgeprüft. Vor jeder Nutzung zu klären.

**Die Rechtslage bei fremden DJ-Sets.** Sechs der gelabelten Aufnahmen sind
fremde Mitschnitte, die 43 % der bewerteten Marker tragen. Für die lokale
Analyse ist das eine andere Frage als für ein Produkt, das solche Sets
verarbeitet oder Ergebnisse daraus veröffentlicht. Ich habe das nicht geprüft;
es gehört geklärt, bevor fremdes Material Teil des Produktversprechens wird.

**Wie lange ein Label-Durchgang wirklich dauert.** Es gibt keine Zeitstempel je
Handgriff — `updatedAt` in der Ground Truth ist nur der letzte Speicherzeitpunkt,
das Backend-Log (`dd/backend_run.log`) hat keine Zeitmarken je Zeile. Meine
Angabe von 15–35 min je Set ist eine Schätzung aus Handgriffzahl und
Setlänge, keine Messung. Ein Zeitstempel je `POST .../feedback/verdict` würde
das mit zwei Zeilen Code beantworten.

**Ob der Precision-für-Recall-Tausch dem Produkt guttut.** Der Sweep zeigt,
dass er verfügbar ist (R 45 % / P 70 % gegen R 94 % / P 50 %). Ob ein DJ lieber
wenige richtige oder viele teils falsche Marker sieht, ist eine Produktfrage,
keine Messfrage. Der Gate in `retrain_model.py:37` entscheidet sie heute
implizit zugunsten des Recalls.

---

## Skripte zu den Messungen

Alle im Sitzungs-Scratchpad, alle ohne Seiteneffekte auf das Repo:

| Datei | beantwortet |
|---|---|
| `runde1.py`, `runde1b.py`, `runde1c.py` | Kosten je Set, Label-Qualität, Aufnahme-Dedup |
| `lernkurve2.py`, `lernkurve3.py` | Betriebspunkt-Sweep und Lernkurve |
| `nms.py`, `nms2.py` | Entdopplung der Marker, inklusive Orakel-Schranke |
| `zeit_regression.py` | R² = 0,082 — die zentrale Messung |
| `onset.py`, `lm_onset.py` | die vier Blend-Onset-Schätzer |
| `rb.py`, `rb2.py`, `rb3.py`, `cues.py`, `playlists.py` | rekordbox-XML, Cues, Playlists |
| `fehlalarm.py`, `messwerte.py` | Struktur der Fehlalarme, befüllte Messwerte |

`zeit_regression.py`, `nms2.py` und `lernkurve2.py` gehören meiner Ansicht nach
ins Repo unter `tools/eval/` — sie laufen ohne Audio und beantworten Fragen, die
bei jeder künftigen Änderung wieder gestellt werden.
