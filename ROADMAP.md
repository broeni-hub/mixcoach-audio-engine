# MixCoach Roadmap: Vom Prototyp zum bezahlten Produkt

Stand: 06.07.2026 · Modell v4 aktiv (Erkennung ~98% Recall / ~62% Präzision auf schweren Sets)

---

> ## Die Live-Schwelle, gültig seit 30.07.2026
>
> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.**
>
> Diese Schwelle ersetzt „Präzision von 62% auf 80%+" als Tor zum Livegang. Der
> Grund ist gemessen, nicht taktisch: 20 zusätzliche gelabelte Sets bringen
> **+0,1 pp Precision**, und die vorhandenen Merkmale erklären **8 % der
> Zeitvarianz** (`ZUKUNFTSWEGE_2026-07-30.md`). Der bisherige Weg zur alten
> Schwelle führt nicht dorthin, und ein Ersatzweg ist nicht in Sicht.
>
> Präzision und Timing bleiben Ziele, aber sie sind **kein Tor** mehr. Sie laufen
> parallel weiter.
>
> Der Rest dieses Dokuments ist vom 06.07. und in Teilen überholt — die
> Aufgabenblöcke A1–A5, F1–F5 und Teil 3 gelten weiter, ihre Reihenfolge und
> Begründungen nicht überall. Aktueller Stand mit ausgezählten Zahlen:
> `STANDORTBESTIMMUNG_2026-07-30.md`.

---

## Ausgangslage ehrlich bewertet

Was heute funktioniert: Upload → Analyse → Report mit Übergängen, Anhören in der Waveform, Feedback-Buttons, die das Modell nachweislich verbessern (v3: 66% erkannt → v4: ~98%). Was fehlt, damit jemand monatlich zahlt: höhere Präzision (jeder dritte Marker ist noch ein Fehlalarm), Messwerte, die es sonst nirgends gibt, ein Produkt-Erlebnis statt Entwickler-Oberfläche — und das Ganze muss online erreichbar sein, nicht nur auf deinem PC.

Der USP ist stark: Mixed In Key, rekordbox und Serato analysieren Tracks, aber **niemand coacht Transitions**. Das ist die Lücke.

---

## Teil 1: Audio-Engine

### A1. Präzision hochziehen (laufend, kostet nichts)
Jedes analysierte Set bewerten (Stimmt / Kein Übergang / Startet woanders / Fehlt). Ab ~10 weiteren Sets mit Audio lohnt der nächste Trainingslauf (dank Cache jetzt in Sekunden). Ziel: Präzision von 62% auf 80%+.

> **Nachtrag 30.07.2026:** „kostet nichts" stimmt nicht. Ein Set labeln kostet
> einen Abend, und die Lernkurve sagt +0,1 pp Precision für 20 Sets. A1 ist
> weder billig noch der wirksame Hebel — und seit dem 30.07. kein Tor zum
> Livegang mehr. Keine weiteren Sets labeln, bevor K1 beantwortet ist
> (`PROMPT_K1_2026-07-30.md`).

### A2. Library-Fingerprinting (1–2 Wochen) — der Genauigkeits-Gamechanger
Der DJ lädt seine Tracks (oder rekordbox-Playlist) hoch. Die Engine erkennt per Fingerprint, WELCHER Track WANN im Set läuft → Übergänge nahezu 100% exakt, auch bei drop-losem Techno/House (dein erklärtes Hauptproblem). Nebeneffekt: Der Report zeigt echte Tracknamen statt "Track 3".

### A3. Neue Messwerte, die DJs wirklich vermissen (je 2–5 Tage)
- Lautheit/Gain-Sprünge (LUFS): "Track 4 kam 3 dB zu laut rein" — schnell umsetzbar
- Bass-Overlap/EQ-Verhalten: dröhnende Bässe im Übergang erkennen (aktuell ehrlich "nicht gemessen")
- Vocal-Clash: zwei Vocals gleichzeitig
- Bessere Key-Erkennung (aktuelles Verfahren ist solide, aber nicht Club-tauglich bei dichten Mixes)

### A4. Coaching statt Zahlen (1 Woche)
Aus Messwerten werden Übungsaufgaben: "Deine Übergänge starten im Schnitt 12 Beats neben der Phrase — übe 32-Beat-Einstiege mit Track X→Y." Plus Fortschritt über Sets hinweg: "Phrase-Timing in 4 Wochen von 55 auf 78."

### A5. Technik-Basis (parallel)
Analyse-Dauer senken (aktuell mehrere Minuten pro Set), MP3/M4A-Robustheit, 2h+-Sets, Testabdeckung halten.

---

## Teil 2: Frontend

### F1. Erster Eindruck (3–5 Tage)
Demo-Report ohne Upload ansehen können (Beispiel-Set vorinstalliert). Jede Metrik bekommt eine Klartext-Erklärung ("Was ist Phrase-Timing und warum ist 8 Beats daneben schlecht?"). Onboarding in 3 Schritten.

### F2. Report-Erlebnis (1 Woche)
Ist schon gut (Waveform, Anhören, Feedback). Dazu: Übergangs-Vergleich vorher/nachher abspielen, Report als PDF/Bild teilen (DJs zeigen gern her — kostenloses Marketing), Tracknamen aus A2.

### F3. Fortschritts-Dashboard (1 Woche) — der Abo-Grund
Ein Abo rechtfertigt sich durch Entwicklung über Zeit: Skill-Radar-Verlauf, Set-Historie mit Trend, "bestes Set", Wochenziele. Ohne das gibt es keinen Grund, Monat 2 zu bezahlen.

### F4. Politur (laufend)
Einheitlich Deutsch (oder DE/EN-Umschalter), freundliche Fehlermeldungen, Ladezustände, Mobile-Ansicht (DJs schauen Reports am Handy an).

### F5. Bezahlschranke reaktivieren (2–3 Tage, wenn Rest steht)
Free: 1 Set/Monat, Basis-Report. Pro (Ziel 9–14 €/Monat): unbegrenzt, Fingerprinting, Fortschritt, PDF-Export. Der Schalter (PAYWALL_DISABLED) existiert schon, Stripe-Anbindung fehlt.

---

## Teil 3: Der größte Brocken — Online gehen (2–4 Wochen)

Aktuell läuft alles auf deinem PC. Zahlende Kunden brauchen: Hosting fürs Backend (CPU-stark wegen Audio-Analyse), Datei-Speicher (Sets sind 100–500 MB), Nutzerkonten (Supabase ist im Frontend schon angelegt), DSGVO-Basics (Datenschutzerklärung, Löschkonzept). Kostenrahmen anfangs ~30–80 €/Monat Server. Erst nötig, wenn Fremde testen sollen — bis dahin ist lokal völlig richtig.

---

## Zeitplan (realistisch, in unserem Arbeitstempo)

| Phase | Inhalt | Dauer |
|-------|--------|-------|
| A (jetzt) | Feedback sammeln + Retrain, LUFS-Messung, Metrik-Erklärungen, Demo-Report | 1–2 Wochen |
| B | Library-Fingerprinting, Fortschritts-Dashboard, Report-Sharing | 2–4 Wochen |
| C | Hosting, Konten, Stripe, geschlossene Beta mit 10–20 DJs | 4–6 Wochen |
| D | Beta-Feedback einarbeiten, Preis testen, öffentlich | offen |

Grob: **in 2–3 Monaten beta-reif mit Bezahlfunktion.**

## Weiteres, das über Erfolg entscheidet

Beta-Tester früh suchen (DJ-Communities, lokale Szene) — deren Feedback-Klicks trainieren zugleich das Modell. Zielgruppe scharf halten: ambitionierte Hobby-DJs, nicht Profis. Urheberrecht ist beim privaten Set-Upload unkritisch, beim öffentlichen Teilen von Reports mit Audio nicht — Sharing daher ohne Audio. Und: Die Ehrlichkeits-Linie beibehalten (nichts anzeigen, was nicht gemessen wurde) — das unterscheidet MixCoach von Spielzeug-Tools und rechtfertigt Geld.

## Empfohlene nächste 3 Schritte

1. Du testest v4 mit 2–3 Sets und gibst Feedback-Klicks (verbessert Modell + validiert v4 live)
2. Library-Fingerprinting bauen (A2) — größter Genauigkeitssprung, dein Hauptproblem
3. LUFS/Lautheits-Messung (A3) — schneller, sichtbarer Mehrwert im Report
