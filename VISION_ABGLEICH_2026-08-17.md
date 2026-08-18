# Vision-Abgleich und kritische Punkte

**Stand: 17.08.2026** · Ergänzung zu `PROJEKT_REVIEW_2026-08-17.md`
Frage: *Halten wir uns noch an die Vision — oder weichen wir ab?*

---

## Die kurze Antwort

**Wir weichen ab, an drei Stellen, und zwei davon sind bewusst und richtig.
Die dritte weiß niemand.**

1. **Bewusst:** Die Erkennung ist kein Tor mehr. Die Vision sagt „Genauigkeit
   hat Vorrang vor Features"; seit dem 30.07. gilt die Live-Schwelle, und sie
   sagt das Gegenteil. Die Entscheidung war gemessen begründet — aber sie steht
   **in keinem Vision-Text**.
2. **Bewusst:** „Was MixCoach nicht messen kann, zeigt es nicht an" ist aus
   einer Anzeigeregel zum Betriebsprinzip geworden. Hier sind wir **über** der
   Vision.
3. **Unbemerkt:** Der Coach, die Fortschrittskurve und der LLM-Prompt ruhen
   heute vollständig auf dem **Pegelsprung**. Das ist Gain-Staging — die
   schmalste der acht in der Vision versprochenen Dimensionen. **MixCoach
   coacht gerade Pegel, nicht Übergänge.**

---

## 1 · Zwei Vision-Wahrheiten nebeneinander

`PRODUKTVISION.md` ist zuletzt am **29.07.2026** angefasst worden — einen Tag,
bevor die Live-Schwelle die alte Zielsetzung ersetzt hat. Dasselbe gilt für den
Vision-Block in den Cowork-Projektanweisungen.

| Aussage | steht in | sagt |
|---|---|---|
| „Ziel ist >90 % Übergangs-Erkennung" · „Solange die Erkennung nicht trägt, hat Genauigkeit Vorrang vor Features, Design und Reichweite" | Projektanweisungen, `PRODUKTVISION.md` | Erkennung zuerst |
| „Live-reif ist MixCoach, wenn jeder Wert gemessen ist, die Historie einen Gerätewechsel überlebt und drei Sets eine Entwicklung zeigen" | `CLAUDE.md`, `ROADMAP.md`, `STANDORTBESTIMMUNG`, beide Reviews | Erkennung ist **kein Tor** |

Nachgezählt: Die Schwelle steht in **7 Dateien**. In `PRODUKTVISION.md` steht
sie **null Mal**.

**Das ist derselbe Fehlerbauplan, der dieses Projekt am meisten gekostet hat** —
zwei Ground-Truth-Ordner, zwei Analysewege, drei Kopien jeder Analyse — nur
diesmal eine Ebene höher: **zwei Produktdefinitionen.** Wer die Vision liest,
arbeitet an der Erkennung. Wer `CLAUDE.md` liest, arbeitet am Coach. Beide
berufen sich zu Recht auf ein verbindliches Dokument.

Die letzten drei Wochen sind der Beleg: An der Erkennung hat sich **nichts**
bewegt (σ 54,58 s, Ziffer für Ziffer identisch seit dem 31.07.), und es war
richtig so — der Fortschritt kam aus Report, Coach und Historie. Nach dem
Vision-Text wäre das ein Regelverstoß.

---

## 2 · Die Versprechen, einzeln gegen die Messung

### Erlebnis 1 — „sekundengenau, wo jeder Übergang beginnt und endet"

| | |
|---|---|
| Versprochen | sekundengenau, auch bei drop-losem Techno, auch bei 2-Stunden-Sets |
| Gemessen | σ **54,58 s** · 5 % innerhalb 8 s · 22 % innerhalb 16 s |

**Nicht eingelöst, und mit den heutigen Mitteln nicht einlösbar.** Vier
Blend-Onset-Schätzer sind gemessen gescheitert, die 17 Merkmale erklären 1,1 %
der Zeitvarianz.

Das Instrument, das entscheiden sollte, **ob der Satz überhaupt bleiben kann**
— die zweite, blinde Labelrunde — steht seit dem **31.07.** startklar und ist
nie gelaufen. Solange es nicht gelaufen ist, weiß niemand, ob ein Mensch selbst
sekundengenau labeln kann. Der Satz steht derweil im Verkaufsversprechen.

### Erlebnis 2 — „echte Tracknamen" und „die Messwerte, die zählen"

Die Vision nennt fünf Werte namentlich. Gemessen gegen deine eigenen
Bewertungen:

| Versprochener Wert | Befüllung | Spearman | trägt? |
|---|---|---|---|
| Lautheits-Sprünge | 86,4 % | **−0,377** | **ja** |
| Phrasen-Timing in Beats | 100 % | −0,037 | nein |
| Tempo-Drift | 100 % | in 89 % exakt 0,0 | nein |
| Harmonische Kompatibilität | 78,7 % | −0,137 | nein |
| Energieverlauf | 50,2 % | +0,062 | nein |

**Von fünf namentlich versprochenen Messwerten trägt einer.**

„Echte Tracknamen": **20,4 %** der Übergänge tragen beide Namen. Das Beispiel
im Vision-Text („Amelie Lens → FJAAK, Übergang bei 14:32, 24 Beats Blend")
beschreibt einen Fall, der in einem von fünf Übergängen eintritt.

### Erlebnis 2b — „Was MixCoach nicht messen kann, zeigt es nicht an"

**Eingelöst, und übererfüllt.** 52 von 52 Reports mit `beatmatching: null`,
110 von 110 Übungen mit einer Zahl, 233 Beobachtungen ausdrücklich **ohne**
Handlungsaufforderung, weil für sie kein Zusammenhang belegt ist.

Das ist die einzige Stelle, an der das Produkt mehr tut als die Vision
verlangt.

### Erlebnis 3 — „Übungen aus deinem eigenen Material"

**Eingelöst seit dem 14.08.** Die Vision verspricht wörtlich: *„Mixe Übergang 3
aus deinem Set vom 04.07. noch einmal — gleiche Tracks, Ziel: unter 4 Beats
Abweichung."* Was heute dasteht: *„Bei 24:53 (FaltyDL → Lone) kam der neue
Track 4,0 dB leiser rein. Mix ihn nochmal, Ziel: unter 1 dB."*

Gleiche Form, andere Größe — und die andere Größe ist die, die misst.

**Offen bleibt der zweite Halbsatz der Vision:** *„Der Coach erkennt Muster,
die du selbst nicht siehst: ‚Dein Phrase-Timing ist stark — außer wenn du in
schnellere Tracks mischst.'"* Musterkennung über Bedingungen hinweg gibt es
nicht. Der Coach nennt Einzelstellen, keine Muster.

### Erlebnis 4 — „Das Skill-Radar (Timing, Beatmatching, Harmonie, Energieführung, Dramaturgie)"

Die Vision benennt fünf Achsen. Gemessen:

```
beatmatching   0 / 52 Reports befüllt
timing         0 / 52
eq             0 / 52
creativity     0 / 52
flow          52 / 52
musicality    52 / 52
```

**Vier der sechs Achsen sagen seit dem 15.08. „nicht gemessen"** — ehrlich, und
genau deshalb sichtbar leer. Drei der fünf namentlich in der Vision genannten
Achsen sind darunter.

Die eine Kurve, die eine Entwicklung belegt, steht seit dem 15.08. daneben:
2,80 → 1,85 dB über 13 Aufnahmen, r = −0,622. **Sie heißt nicht wie eine der
fünf versprochenen Achsen.**

### Erlebnis 5 — „Teilen als Trophäe"

Nicht begonnen. 10 % seit dem 30.07. unverändert.

---

## 3 · Die drei Burggräben

| Burggraben | Vision sagt | Gemessen |
|---|---|---|
| **1 · Daten-Schleife** | „Jeder neue Nutzer macht das Produkt für alle besser. Ein Nachahmer startet bei null." | Mehr Labels kaufen **Recall** (+17,4 pp von 4→24 Sets), **keine Precision** (+1,6 pp bei ±6,0 pp Streuung). Das Wachstumsargument trägt **zur Hälfte**. Und: **0 fremde Nutzer** haben je einen Klick beigetragen. |
| **2 · Library-Verbindung** | „Tools ohne diese Verbindung raten; MixCoach weiß." | Trägt. 6113 Tracks, Recall 0,90 bei Precision 1,0. Aber **6673 rekordbox-Beatgrids und 432 Cue-Punkte liegen ungenutzt** — der Teil des Schatzes, der „wissen statt raten" erst einlösen würde. |
| **3 · Ehrlichkeit** | „MixCoach misst konservativ, kennzeichnet Unsicherheit, lässt jeden Wert nachhören." | **Übererfüllt.** |

---

## 4 · Die Abweichung, die niemand notiert hat

Der Leitsatz lautet: *„Andere Tools analysieren deine Musik. MixCoach
analysiert dein DJing."* Und: der USP ist **Mix-Analyse — was zwischen den
Tracks passiert.**

Heute ruht praktisch alles Wertschöpfende auf **einer** Größe:

- alle 110 Übungen
- die einzige Fortschrittskurve
- die Priorität im LLM-Prompt

Diese Größe ist `|loudness_jump_db|` — **wie viel lauter oder leiser der neue
Track hereinkommt.** Das ist Gain-Staging am Mixer. Eine echte DJ-Fähigkeit,
messbar, mit einer Einheit, die jeder versteht — und die **schmalste** der acht
Dimensionen, die die Vision für „jede Transition wird gemessen" aufzählt.

Es ist außerdem die einzige der acht, die man **ohne** Kenntnis des Mixes
messen könnte. Sie braucht weder Fingerprinting noch Library noch
Übergangserkennung im engeren Sinn — nur die Lautheitskurve und zwei
Zeitpunkte.

**Das heißt nicht, dass es falsch war.** Es ist die einzige Größe mit belegtem
Zusammenhang zum menschlichen Urteil, und sie zu wählen war die ehrliche
Entscheidung. Aber die Folge gehört ausgesprochen:

> Das Produkt, das antritt, um Übergänge zu coachen, coacht heute Pegel — und
> die beiden Burggräben, die es dafür gebaut hat (Fingerprinting,
> Übergangserkennung), tragen zu dieser einen Leistung fast nichts bei.

---

## 5 · Die kritischen Punkte, nach Schwere

### Schwer

**K1 · Eine Säule.** Coach, Fortschritt und LLM-Priorität ruhen auf einer
Größe, belegt an **einer** Stichprobe (n = 146) von **einem** Rater. Bestätigt
sie sich nicht, fallen Punkt 3 und Punkt 4 gleichzeitig.
→ Gegenmittel: **J7** und **ein zweiter Rater**, je ein Abend, beide seit
Wochen vorbereitet.

**K2 · Zwei Produktdefinitionen.** `PRODUKTVISION.md` und die
Projektanweisungen kennen die Live-Schwelle nicht und verlangen weiter
Erkennung vor Features. Jede künftige Sitzung kann sich auf das eine oder das
andere berufen.
→ Gegenmittel: **eine Entscheidung, eine Stunde Doku.** Siehe Abschnitt 6.

**K3 · „sekundengenau" steht weiter im Versprechen.** Gemessen 5 % innerhalb
8 s. Das Instrument zur Klärung wartet seit dem 31.07.
→ Gegenmittel: **die zweite Labelrunde**, ein Abend.

### Mittel

**K4 · Null fremde Nutzer.** Die Zielgruppenannahme („Hunderttausende
ambitionierte Hobby-DJs") ist nie geprüft worden. Es gibt keinen Demo-Report
und kein Onboarding — niemand außer dir kann das Produkt ohne Begleitung
verstehen. Alle 358 Bewertungen, alle 21 Aufnahmen, alle Entscheidungen stammen
von einer Person.

**K5 · Bass-Overlap.** In der Vision namentlich als nahe Ausbaustufe und
Alleinstellung genannt („beide Bässe liefen 16 Beats übereinander"). Steht bei
**15,8 %** und ist zu 90 % exakt 0 oder 100 — ein Schalter, keine Abstufung.
Der Wert, den sonst niemand anbietet, ist der am schlechtesten befüllte.

**K6 · Das Anmeldesystem gehört Lovable.** Nachgemessen am 16.08.: Das
Supabase-Projekt lässt kein eigenes OAuth-Secret zu, der Broker liegt auf
fremdem Hosting. Für Teil 3 ist das eine Abhängigkeit, die in keiner Planung
steht.

**K7 · Die Erkennung bewegt sich nicht — und niemand arbeitet daran.** Das ist
im Einklang mit der Live-Schwelle und im Widerspruch zur Vision. Solange K2
offen ist, ist unklar, ob das ein Plan oder ein Versäumnis ist.

### Leicht, aber überfällig

**K8 · `app/experimental/`** — 39 Dateien, 0 Importe von außen, und
`CLAUDE.md:33` schickt jeden Leser weiter dorthin. **Fünfmal verschoben.**

**K9 · `main` 30 Commits hinterher**, drei alte Worktrees, `memory.md` führt
zwei Werkzeuge als gebaut, die nie existiert haben.

---

## 6 · Was zu entscheiden ist

Zwei Entscheidungen, beide deine, beide heute möglich.

### Entscheidung 1 · Welche Vision gilt?

**Weg A — Die Vision nachziehen.** `PRODUKTVISION.md` bekommt die
Live-Schwelle, „sekundengenau" wird zu dem, was messbar ist, und das
Skill-Radar wird nach den Achsen benannt, die es hat. Ehrlich, konsequent zum
Markenkern — und es nimmt dem Verkaufstext etwas weg.

**Weg B — Zur Vision zurückkehren.** Die Erkennung wird wieder das Tor. Dann
sind Coach und Fortschritt Vorarbeit, und die nächsten Wochen gehören
`start_sec`, den rekordbox-Beatgrids und einem zweiten Rater.

**Weg C — Beides bewusst nebeneinander.** Die Vision bleibt das Fernziel, die
Live-Schwelle das Tor zur Beta — aber **das muss in beiden Dokumenten stehen**,
sonst ist es kein Weg, sondern der Zustand von heute.

**Mein Rat: C, und zwar schriftlich.** Die Live-Schwelle ist gut begründet und
hat in drei Wochen mehr bewegt als die drei Monate davor. Aber ein Fernziel,
das nur in einem Dokument steht, und ein Tor, das nur im anderen steht, ist
genau die Doppelhaltung, die dieses Projekt schon zweimal teuer bezahlt hat.

### Entscheidung 2 · Wie heißt das, was der Coach heute kann?

Solange nur der Pegelsprung trägt, ist „MixCoach analysiert dein DJing"
größer als das, was das Produkt einlöst. Zwei ehrliche Möglichkeiten:

- **Eng benennen und stark sein:** „MixCoach hört, ob deine Übergänge sauber
  gepegelt sind — und zeigt dir über Wochen, ob du besser wirst." Das ist
  wahr, belegt, und kein anderes Tool sagt es.
- **Breit bleiben und die Lücke füllen:** dann brauchen mindestens zwei
  weitere der acht Dimensionen einen belegten Zusammenhang, bevor der Leitsatz
  wieder gedeckt ist.

Das ist keine Doku-Frage, sondern die Frage, was auf der Startseite steht,
wenn der erste fremde DJ kommt.

---

## 7 · Was der Abgleich nicht in Frage stellt

Damit die Bilanz nicht kippt:

Die **Ehrlichkeit** ist der Burggraben, der am weitesten trägt — weiter als die
Vision ihn beschreibt. Ein Produkt, das 233 Beobachtungen ausdrücklich **nicht**
zu Ratschlägen macht, weil der Zusammenhang fehlt, hat etwas, das kein
Wettbewerber nachbaut, ohne seine Zahlen zu verlieren.

Die **Library-Verbindung** trägt technisch: 6113 Tracks, Recall 0,90 bei
Precision 1,0.

Und die **Fortschrittskurve** ist echt. Sie ist schmal, sie ruht auf einer
Größe und 13 Aufnahmen — aber sie ist gemessen, sie zeigt in die richtige
Richtung, und sie ist das erste Mal, dass dieses Produkt sein zentrales
Versprechen einlöst: *„Bin ich besser geworden?" — und die Antwort ist eine
Kurve, keine Vermutung.*
