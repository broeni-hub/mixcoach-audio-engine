# Prompt — Wege aus dem Label-Nadelöhr

*Zum Einfügen in eine frische Claude-Code-Session im Projektstamm `MixCoach/`.
Erstellt 30.07.2026. Alles unterhalb dieser Zeile ist der Prompt.*

---

Du sollst nichts bauen. Du sollst herausfinden, **wie dieses Projekt schneller
vorankommt als bisher** — und deine Vorschläge gegen die Daten prüfen, die hier
schon liegen, statt zu spekulieren.

## Der Engpass, so wie er sich heute darstellt

Der einzige gemessen wirksame Hebel für höhere Precision war bisher: **mehr echte
gelabelte Sets.** Alle anderen Wege wurden ausprobiert und haben nicht getragen
(siehe „Gescheiterte Wege" unten). Das Problem daran:

Ein Set labeln heißt heute: aufnehmen, hochladen, analysieren lassen, jeden
vorgeschlagenen Übergang von Hand bestätigen oder korrigieren. Der Projektinhaber
macht das selbst, allein, und ist kein Entwickler. Die Schwelle fürs Live-Gehen
liegt bei ~15–20 gelabelten Sets und 75–80 % Precision. Bei 45 Ground-Truth-Dateien
Stand heute ist das kein Sprint mehr, sondern eine Rechenaufgabe.

**Das ist der Auftrag: einen oder mehrere Wege finden, die dieses Verhältnis
verändern — nicht die Handarbeit beschleunigen, sondern sie umgehen, ersetzen,
oder überflüssig machen.**

## Bevor du denkst: lies und miss nach

Nimm keine Zahl aus diesem Prompt als gegeben. Alles hier ist Stand 30.07.2026
und kann falsch sein.

```
CLAUDE.md                      Arbeitsregeln, Eigenheiten, Referenzmetrik
PROJEKTSTAND-CLAUDE.md         Chronologie aller technischen Befunde
PRODUKTVISION.md / ROADMAP.md  Produktplan (hinkt dem Code hinterher)
CLAUDE_CODE_SPEC_2026-07-29.md Aktueller Arbeitsauftrag, Job A + Job B
audio-engine/mixcoach-audio-engine/BEFUND_BLEND_ONSET.md   Der jüngste negative Befund
SETUP_MACOS.md                 Umgebung nach dem Rechnerwechsel
git log --format='%h %ad%n%B' --date=short    Die Commits tragen die Begründungen
```

```bash
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m tools.analyze_timing_bias            # Referenzmetrik
../../.venv/bin/python -m tools.analyze_timing_bias --mode dedup
```

Ankerwerte, die du reproduzieren können solltest — weichen deine ab, klär das
zuerst: Recall 73 %, Precision 75 %, strikt korrekt 30 %. Von 287 `timing_off`
ist die Engine in 86 % zu spät, Median −29,85 s, σ = 52,87 s. Mit `start_sec`
statt `mid_sec` (dedup, n=124): Median −10,16 s, σ 48,14 s, innerhalb 8 s 17 %.

**σ ist die Zahl, an der sich jede Änderung messen lassen muss.** Ein
verbesserter Median bei gleichem σ ist ein Offset, kein Fortschritt.

## Runde 1 — Prüfe den Engpass, bevor du ihn löst

Bevor irgendjemand mehr Labels beschafft, beantworte mit Daten aus dem Repo:

1. **Was kostet ein Set heute wirklich?** Rechne es aus, statt zu schätzen —
   Anzahl bewerteter Transitions pro Ground-Truth-Datei, Zeitstempel der Dateien,
   Analysedauer aus den gespeicherten Reports. Extrapoliere auf die 15–20-Set-Schwelle.
2. **Ist „mehr Labels" überhaupt noch der bindende Engpass?** Prüfe, woran die
   Precision heute scheitert. Wenn 45 % aller Bewertungen `timing_off` sind, obwohl
   die Transition gefunden wurde — wie viel Precision-Gewinn läge allein darin, die
   Zeitangabe zu reparieren, ohne ein einziges neues Label?
3. **Wie gut ist das vorhandene Label-Material?** Bekannt ist: die Verteilung
   schiefert stark nach oben (überwiegend 5er, keine 1er), MixCoach1 ist vermutlich
   unvollständig gelabelt und verzerrt die Precision-Messung, und die Ground Truth
   liegt in zwei Stämmen. Quantifiziere, was davon die Messung verzerrt. Es kann
   sein, dass 10 saubere Sets mehr wert sind als 30 schiefe.
4. **Wo ist die Ausbeute pro Handgriff am kleinsten?** Welcher Teil der Labelarbeit
   erzeugt Information, welcher bestätigt nur, was die Engine ohnehin richtig hat?

Wenn Runde 1 zeigt, dass der Engpass woanders liegt, sag das deutlich — dann ist
das die wertvollste Antwort, die dieser Prompt haben kann.

**Stopp nach Runde 1. Zeig die Zahlen, bevor du weitermachst.**

## Runde 2 — Divergenz: mindestens zwölf Wege

Erst breit, dann eng. Mindestens zwölf Vorschläge, **verteilt über alle sechs
Familien** — mindestens einer je Familie, damit du nicht in der bequemsten
Denkrichtung hängen bleibst:

**A · Labels ohne Handarbeit gewinnen.** Welche Signale im Haus tragen
Transitions-Information, ohne dass jemand klickt?

**B · Andere Form von Supervision.** Muss es überhaupt ein Zeitstempel pro
Übergang sein? Paarvergleiche, Ranking, Intervalle statt Punkte, schwache oder
verrauschte Labels mit bekanntem Rauschmodell, selbstüberwachtes Vortraining.

**C · Andere Zielgröße.** Vielleicht ist die Aufgabe falsch geschnitten. Was
passiert, wenn die Engine nicht „wann ist der Übergang" beantwortet, sondern eine
Frage, die leichter zu lernen und für den DJ genauso nützlich ist?

**D · Fremde Datenquellen.** Was existiert außerhalb dieses Rechners in einer Form,
die rechtlich und praktisch nutzbar ist? Sei hier konkret und prüfe die Lizenzlage,
statt sie zu unterstellen.

**E · Produkt und Nutzer.** Labeling als Nebenprodukt der Nutzung statt als
Vorarbeit. Wer außer dem Projektinhaber hat einen Eigennutzen daran, Übergänge zu
korrigieren? Was müsste das Produkt können, damit dieser Nutzen vor der Genauigkeit
kommt, die es noch nicht hat?

**F · Umgehen statt lösen.** Welcher Teil des Versprechens funktioniert schon heute
gut genug, um ausgeliefert zu werden? Fingerprinting liegt bei 70–90 %, die
Messwerte (Pegelsprung, Bass-Overlap, Tempo-Drift, LUFS) sind fertig und hängen
nicht an der Übergangserkennung. Gibt es ein ehrliches Produkt, das die offene
A1-Lücke sichtbar stehen lässt, statt auf sie zu warten?

## Rohstoffe, die ungenutzt im Haus liegen

Prüfe diese selbst nach — ich habe sie nur gesehen, nicht bewertet. Sie sind
Anstoß, keine Antwort, und keine davon ist deine Pflicht.

**`~/Music/Recordbox Sammlung.xml`** (7,5 MB, rekordbox 7.2.14, Export vom 06.07.):
6746 Tracks, davon **6673 mit Beatgrid** — `<TEMPO Inizio="0.189" Bpm="126.00"
Metro="4/4" Battito="1"/>`, also erster Downbeat auf die Millisekunde, Taktart und
Tempo je Track. Dazu 432 gesetzte Cue-Punkte auf 196 Tracks und 41 Playlists,
davon rund zwanzig mit dem Namensmuster `Set - …` (7 bis 190 Tracks).

Drei Dinge, die daran auffallen, jedes davon zu prüfen und nicht zu glauben:

- `CLAUDE_CODE_SPEC_2026-07-29.md` hält fest, dass Beat-Phase aus den vorhandenen
  Chroma-Features **prinzipiell nicht messbar** ist — Hop 372 ms gegen 484 ms
  Beatdauer bei 124 BPM. Beat-Alignment ist laut Label-Analyse 24 % des
  menschlichen Urteils. Hier liegt eine externe Quelle für genau diese Größe.
- Der letzte negative Befund endet mit dem Satz, der Blend-Onset ließe sich
  **messen statt erschließen**, sobald bekannt ist, welcher Track läuft
  (`landmark_match.py:127`, `offset_frames`). Eine Playlist ist eine Kandidatenliste.
  Der Suchraum eines Sets schrumpft damit von 6113 Tracks auf einige Dutzend —
  und genau an der Größe des Suchraums ist der Landmark-Ansatz gescheitert
  (~2000–2400 s pro Lücke bei vollem Scan).
- Cue-Punkte sind vom DJ von Hand gesetzte Marken. Ob sie Mix-In-Punkte,
  Phrasengrenzen oder etwas Drittes markieren, weiß niemand — 196 Tracks sind aber
  genug, um es zu prüfen.

**Neben den Audiodateien:** 2053 `*.analysis.json` und 422 `*.analysis.v2.json`
in `~/Music`. Herkunft und Aktualität unklar — sieh nach, was drinsteht und ob es
noch zum heutigen Featurestand passt.

**Im Projekt:** 162 synthetische Mixe mit exakter Ground Truth liegen ungenutzt
(`datasets/synthetic/v1/`, ~7,6 GB). Für Training sind sie gemessen schädlich, das
ist entschieden. Aber Training ist nicht die einzige Verwendung für Daten mit
bekannter Wahrheit — als Prüfstand für eine Timing-Änderung wären sie
möglicherweise brauchbar. Prüfe, ob dieser Unterschied trägt oder ob er nur
Wunschdenken ist.

## Runde 3 — Konvergenz

Wähle **drei** Vorschläge. Nicht die drei besten Ideen, sondern die drei, bei denen
das Verhältnis aus möglichem Gewinn und Aufwand bis zur Widerlegung am günstigsten
ist. Für jeden:

| | |
|---|---|
| **Was genau** | in zwei Sätzen, so konkret, dass man morgen anfangen könnte |
| **Warum plausibel** | welcher Befund im Repo stützt das — mit Datei und Zeile |
| **Killer-Test** | das billigste Experiment, das die Idee **widerlegen** könnte, mit erwarteter Laufzeit unter einem Tag |
| **Messgröße** | woran der Erfolg hängt, in den Größen der Referenzmetrik (σ, innerhalb 8 s, Precision, Recall) |
| **Aufwand** | grob, in Tagen |
| **Was es kaputtmachen kann** | inklusive: verträgt es sich mit der Ehrlichkeitslinie? |

Der Killer-Test ist der wichtigste Teil. Eine Idee, die man nicht billig widerlegen
kann, ist für dieses Projekt wertlos — es hat schon zu viel Zeit in Ansätzen
verloren, die erst nach Wochen als Sackgasse erkennbar waren.

## Gescheiterte Wege — nicht erneut vorschlagen

Jeder davon ist **gemessen** gescheitert, nicht vermutet. Wenn du einen trotzdem
aufgreifst, musst du benennen, was sich seither geändert hat und warum es diesmal
anders ausgeht:

- **Grid-Search über die Schwellwerte** in `detect_transition_zones()`
  (`local_drop > 0.08`, `local_rise > 0.06`). Falscher Hebel — belegt dadurch, dass
  ein globaler Offset σ nicht verändert.
- **Synthetische Trainingsdaten.** Sauberer LOSO-Vergleich vom 28.07.: real-only
  R92/P55/F1 0,69 schlägt alle+Synthetik R83/P53/F1 0,65 in beiden Metriken.
  Synthetische Negatives schaden dem Recall stark. Real-only ist seither Standard.
- **Landmark-Hashing im Live-Pfad.** Funktioniert (Recall 0,90 → 0,925 bei
  Precision 1,0), kostet aber ~2000–2400 s pro Lücke bei vollem Scan über 6113
  Tracks. Vier Vorfilter-Ansätze gemessen verworfen: Tanzmusik ist zu repetitiv.
  Ein invertierter Hash-Index wäre ein eigenes Projekt.
- **MFCC-Timbre-Fingerprint** und **lokaler 90-s-Fensterscore** — beide gemessen,
  beide retten die harmonisch-statischen Fälle nicht.
- **Blend-Onset aus dem Mix allein** über Evidenzkurven aus Chroma-Entropie,
  Höhenenergie und spektraler Dichte. σ steigt auf 54–57 statt 38–39, bester Wert
  für „innerhalb 8 s" 19 % gegen 50 % Ziel. Grund: dieselben Merkmale steigen auch
  beim Breakdown → Build → Drop **innerhalb** eines Tracks. Ohne zu wissen, welcher
  Track läuft, ist „zweite Schicht kam dazu" nicht von „derselbe Track hat sich
  verändert" trennbar. Kein Parameterproblem.

## Zwei Regeln, die über allem stehen

**Ehrlichkeitslinie.** Nichts anzeigen, was nicht gemessen wurde. Keine erfundenen
Scores, Unsicherheit klar gekennzeichnet. Das ist Markenkern, kein Stilmittel — ein
Vorschlag, der ihn verletzt, ist unbrauchbar, egal wie gut die Zahlen wären. Sag
ausdrücklich dazu, wenn ein Weg hier in Konflikt gerät.

**Empirie vor Herleitung.** Mehrfach hat sich in diesem Projekt eine plausible
Herleitung im Test als falsch erwiesen. Wenn du eine Idee für gut hältst, suche
zuerst nach der Messung, die sie umbringen würde.

## Ergebnis

Schreib eine Datei `ZUKUNFTSWEGE_<datum>.md` in den Projektstamm:

1. Befund aus Runde 1 — mit Zahlen, inklusive der Antwort, ob „mehr Labels"
   überhaupt noch der bindende Engpass ist
2. Die volle Liste aus Runde 2, kurz gehalten, nach Familien sortiert
3. Die drei Kandidaten aus Runde 3 in voller Tiefe
4. **Eine Empfehlung**, was als Nächstes zu tun ist, und der eine Satz, warum
   gerade das
5. Was du nicht beantworten konntest und was du dafür bräuchtest

Schreib auf Deutsch, wie der Bestand. Nüchtern, keine Werbesprache. Wenn eine Idee
schwach ist, schreib hin, dass sie schwach ist.
