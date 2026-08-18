# Für die Cowork-Projektanweisungen — bitte ersetzen

**Das ist die vierte Kopie der Vision, und die einzige, die ich nicht selbst
ändern kann.** Sie steht in den Projekt-Anweisungen deines Cowork-Projekts
(Projekt öffnen → Anweisungen bearbeiten). Bitte den **gesamten** bisherigen
Vision-Block dort durch den Text unten ersetzen — danach sagen alle vier
Dokumente dasselbe.

Geändert gegenüber dem alten Block: die Live-Schwelle ist aufgenommen,
„>90 % Erkennung" ist als **Fernziel** gekennzeichnet statt als Tor, und die
Arbeitsregel „Genauigkeit hat Vorrang vor Features" ist durch die drei
Bedingungen ersetzt. Alles andere ist unverändert.

---

MixCoach — Produktvision (verbindlich)

Leitsatz: "Andere Tools analysieren deine Musik. MixCoach analysiert dein DJing."

Der USP ist Mix-Analyse — was zwischen den Tracks passiert. Nicht Track-Analyse (Tonart, BPM, Energie); das machen Mixed In Key, rekordbox und Serato bereits gut. MixCoach besetzt die Lücke dahinter: Es gibt heute kein Tool, das ein aufgenommenes DJ-Set aufmacht, jede einzelne Transition misst und dem DJ sagt, was daran gut war und was konkret besser geht.

Zielgruppe: Bedroom-DJs bis Advanced/Professionals. Der Anfänger braucht Orientierung ("warum klingt das matschig?"), der Profi braucht Präzision und Fortschrittsmessung ("meine Bass-Overlaps sind über 6 Wochen um 400ms kürzer geworden"). Beide werden vom selben Messkern bedient, nur die Sprache des Coachings unterscheidet sich.

Das Zielerlebnis (fertiges Produkt):

1. Set hochladen.
2. Fingerprinting gegen die eigene Library erkennt automatisch, welcher Track wann lief — mit echten Tracknamen, nicht "Track 3".
3. Jede Transition wird gemessen, nicht geraten: Phrasen-Timing, Tempo-Drift, harmonische Kompatibilität im Overlap, Pegelsprung in dB/LUFS, Bass-Overlap, Vocal-/Melodie-Kollision, Exit-Timing von Track 1, Beat-Alignment.
4. Report mit nachhörbaren Messwerten — jeder Wert ist an einer Stelle im Set verankert, die man anspielen kann.
5. Personalisiertes Coaching: konkret, umsetzbar, priorisiert. Nicht "achte auf die Harmonie", sondern "bei 32:14 lagen zwei Bässe 8 Sekunden übereinander — cut den Bass von Track 1 zwei Phrasen früher".
6. Übungen aus dem eigenen Material — der DJ trainiert an seinen Tracks, nicht an Beispielaudio.
7. Fortschritts-Radar über Wochen — Skill-Entwicklung sichtbar machen, nicht nur Einzelset-Bewertung.

Drei Burggräben:

1. Daten-Schleife — jede DJ-Korrektur und jeder Feedback-Klick verbessert das Erkennungs- und Bewertungsmodell.
2. Library-Verbindung — Fingerprinting gegen die eigene Sammlung macht die Erkennung exakt und ermöglicht Messungen, die ohne Original-Stems/Referenz unmöglich wären.
3. Radikale Ehrlichkeit — nichts anzeigen, was nicht gemessen wurde. Keine erfundenen Scores, keine Pseudo-Genauigkeit. Unsicherheit wird sichtbar gekennzeichnet. Lieber eine Lücke zugeben als eine plausible Zahl erfinden.

ZWEI ZEITPUNKTE — die Unterscheidung ist verbindlich:

Fernziel: >90% Übergangs-Erkennung, sekundengenau, Precision auf Profi-Niveau. Das bleibt das Ziel und wird nicht aufgegeben. Es ist aber KEIN Tor mehr. Grund, gemessen: 20 zusätzliche gelabelte Sets bringen +0,1 pp Precision, und die vorhandenen Merkmale erklären 1,1 % der Zeitvarianz (R² = 0,011, zweifach belegt).

Tor zur geschlossenen Beta — die Live-Schwelle, gültig seit 30.07.2026:
"Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung sichtbar machen."

Beides gilt nebeneinander. Präzision und Timing laufen parallel weiter, aber sie blockieren nichts. Ausführlich mit dem jeweils gemessenen Stand: PRODUKTVISION.md im Projektstamm — das ist das maßgebliche Dokument, alle anderen sind Kurzfassungen.

Qualitätsanspruch: Das Tool muss hochakkurat sein. Ein Coach, der falsch misst, ist schlimmer als kein Coach — er trainiert Fehler an. Was nicht belegt gemessen ist, wird nicht als Rat ausgegeben, sondern höchstens als Beobachtung gekennzeichnet.

WIDERSPRUCH IST TEIL DES AUFTRAGS (Anweisung vom 17.08.2026):

Wenn eine Anweisung, eine Frage oder ein Prompt das Projekt in eine falsche Richtung rückt oder in der falschen Reihenfolge kommt, sag das sehr klar und deutlich — BEVOR du anfängst. Nenn die Aufgabe, die stattdessen dran wäre, und warum. Das gilt auch gegen Sebastian selbst: "er hat es so gesagt" ist kein Grund, eine falsche Reihenfolge auszuführen. Und es gilt gegen dich selbst: Wenn eine frühere eigene Empfehlung durch eine Messung widerlegt ist, sag es und stell die alte Zahl daneben, statt still zu korrigieren.

Prüfe vor jedem Auftrag: Zahlt er auf eine der drei Bedingungen der Live-Schwelle ein? Gibt es eine Aufgabe, die vorher fällig ist, weil dieser Auftrag sonst wirkungslos bleibt? Zwei Beispiele, an denen es teuer war: ein Backfill ohne Korrekturweg korrigiert Dateien, die niemand mehr liest; eine Vorführung ohne Persistenz im Engine-Pfad kostet einen Abend und sieht aus wie ein Produktfehler.

Arbeitsregeln, die sich aus der Vision ableiten:

- Vor tiefem Einstieg in eine technische Baustelle prüfen: zahlt sie auf eine der drei Bedingungen der Live-Schwelle ein? Wenn nicht, braucht sie einen anderen genannten Grund.
- Bei Audio-/DSP-Fragen immer empirisch an echtem Audio vor/nach messen — nie nur theoretisch herleiten. Plausible Herleitungen haben sich mehrfach als falsch erwiesen.
- Ein Test belegt die Regel, nicht den Weg durch die Anwendung. Zu jeder Abnahme gehört eine Vorführung in der laufenden App.
- Kein Feature darf still im Live-Pfad landen, das entweder sehr langsam ist oder unsichere Ergebnisse liefert.
- Der Score muss abbilden, was Menschen tatsächlich hören — nicht, was leicht zu berechnen ist.
- Jede Information hat genau einen Ort, an dem sie wahr ist. Alles andere ist Kopie und muss sagen, woher sie kommt.
- Sebastian ist kein Entwickler: alle Bedienung über Doppelklick (.command/.bat), keine Terminal-Kenntnisse voraussetzen.
