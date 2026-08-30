# Warum es sich nicht vorwärts anfühlt — ausgezählt

Stand 30.08.2026. Anlass: Sebastians Beobachtung, dass seit Wochen gebaut
wird, ohne dass das Produkt spürbar besser wird. Die Beobachtung ist keine
Stimmung. Sie ist messbar richtig, und hier stehen die Zahlen.

**Dieses Dokument ist kein Plan.** Es ist die Grundlage für eine
Entscheidung, und es ist absichtlich kurz.

---

## 1 · Die Zahl

77 Commits seit dem 31.07.2026. So verteilen sich die Codezeilen (ohne
`daten/`, ohne Markdown):

| Bereich | Zeilen |
|---|---|
| Werkzeuge (messen, backfillen) | **+4.098** |
| Tests | **+3.503** |
| Frontend | +2.008 |
| Coach + Ehrlichkeit | +1.494 |
| Engine sonstiges | +1.125 |
| **Erkennung + Modell** | **+102** |

**102 von 12.330 Zeilen — 0,8 % — gingen in das, was das Produkt tut.** Und
davon war das meiste ein Retrain-Skript, kein Algorithmus.

`app/audio/set_analyzer.py` und `set_analyzer_helpers.py` sind seit dem
**29.07.2026** unverändert — dem Tag des Mac-Umzugs.

Die Referenzmetrik meldet seit dem 31.07. in jeder Sitzung „reproduziert":
Recall 70 %, Precision 74 %, σ 54,58 s. **Vier Wochen ohne Bewegung an einer
einzigen Stelle.** In den Sitzungsberichten stand das jedes Mal als gute
Nachricht („nichts kaputtgemacht"). Das war irreführend; die eigentliche
Nachricht war, dass sich nichts bewegt.

---

## 2 · Vier Ursachen

**a) Am 30.07. wurde das Ziel ausgetauscht, weil das alte unerreichbar
schien.** Precision und Timing sind seitdem „kein Tor" mehr — gemessen
begründet (20 zusätzliche Sets bringen +0,1 pp Precision, R² = 0,011). An
ihre Stelle trat die Live-Schwelle: jeder Wert gemessen, Historie überlebt
einen Gerätewechsel, drei Sets zeigen eine Entwicklung.

Alle drei sind **durch Umbauen der Anzeige erfüllbar**, nicht durch besseres
Erkennen. Sie wurden erfüllt.

Die Folgefrage hat niemand gestellt: *Wenn das Kernversprechen nicht besser
wird — woher kommt dann der Wert?* Stattdessen wurde ein erreichbares
Ersatzziel gebaut und abgehakt.

**b) Der Ehrlichkeitsapparat ist zum Hauptprodukt geworden.** 62 % der Zeilen
sind Werkzeuge und Tests. Die „Befunde" der letzten zwei Wochen im Einzelnen:

- die Fortschrittskurve log sieben Tage lang (Probedateien)
- der Report sagte „beatmatching nicht gemessen" neben einer Beatmatching-Übung
- das Profil nannte fremde Sets „deins"
- `delta` täuscht in beide Richtungen
- das K1-Instrument belegte die Antwort vor
- die eigene Rangkorrelation gab bei flacher Reihe r = 1,0

Jeder einzelne ist ein **Defekt in unseren eigenen Instrumenten**. Keiner ist
eine Erkenntnis über DJing oder über Audio. Wir sind sehr gut darin geworden,
uns nicht selbst zu belügen — und keinen Schritt besser in dem, wofür ein DJ
zahlt.

**c) Das Hin und Her ist ein Regelkreis.** 15 von 77 Commits reparieren
eigene frühere Arbeit. Messen → Fehler in der Messung finden → korrigieren →
Fehler in der Korrektur finden. Jede Runde ist für sich sauber; zusammen
drehen sie sich um sich selbst.

K1 ist der Beweis: zweimal gebaut, zweimal gescheitert, vier Wochen vergangen,
Frage offen. Am 30.08. kam A2 dazu — als Vorschlag formuliert („sechs richtige
Marker schlagen zehn"), gemessen, selbst widerlegt. Ein halber Tag für ein
Nein.

**d) Es gibt keine Zahl für den Produktwert.** σ, Precision, Recall:
eingefroren. Live-Schwelle: erfüllt. J7 sollte die fehlende Zahl liefern und
lieferte p = 0,263. Seit einem Monat existiert keine Messgröße, die steigt,
wenn MixCoach für einen DJ besser wird.

---

## 3 · Was das Produkt heute wirklich ist

**Gut in einer Sache:** Es misst zwei Eigenschaften eines Übergangs belegbar
— Pegelsprung (ρ −0,34) und Beat-Jitter (ρ −0,34), beide gegen echte
Bewertungen geprüft. Das kann kein anderes Werkzeug am Markt.

**Schlecht in der, die die Vision verspricht:** Es findet Übergänge nicht
präzise. σ 54,6 s, 39 % der Marker sitzen richtig. Zweimal gemessen, dass das
mit den vorhandenen Mitteln nicht besser wird.

Seit einem Monat wird das Erste poliert und über das Zweite ehrlicher
berichtet. **Niemand hat je einen DJ gefragt, ob das Erste allein etwas wert
ist.**

---

## 4 · Die Entscheidung

**Aufhören zu bauen, bis Evidenz von außen da ist.**

Am Morgen des 30.08. lautete meine Empfehlung noch: erst A1–A3, dann testen.
Die sind fertig — das Fenster ersetzt die falsche Sekundenangabe, die
Tracklist bringt 0 % auf bis zu 100 % Tracknamen, A2 war ein Nullbefund.
**Damit ist der Grund zu warten weg.**

Gestrichen, einschließlich meines eigenen Vorschlags:

- **A4** (Gegenprobe an eigenen Sets) — das wäre wieder ich, der mich selbst prüft
- jede weitere Zeile Ehrlichkeitsapparat, bis jemand von außen den Report gesehen hat
- jedes weitere Messwerkzeug

Stattdessen der **Concierge-Test** aus `PLAN_3_MONATE_2026-08-27.md`, Phase B:
fünf DJs, ein Set, ein Report zurück. Kostet einen Abend und keine Zeile Code.

Die Frage ist nicht „ist der Report gut genug". Die Frage ist, **ob eine
ehrliche Messung von zwei Größen einem DJ überhaupt etwas wert ist.** Das ist
die einzige Zahl, die seit einem Monat fehlt — und die einzige, die entscheidet,
woran als Nächstes gebaut wird.

Lautet die Antwort nein, ist das nach einer Woche klar statt nach drei Monaten.
