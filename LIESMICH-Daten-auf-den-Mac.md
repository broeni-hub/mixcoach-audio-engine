# Die Daten auf den Mac bekommen

*Erstellt am 30.07.2026. Ergänzung zu `LIESMICH-GitHub.md` — dort geht es um den Code, hier um die Daten.*

## Worum es geht

GitHub überträgt Code, Ground-Truth-Labels und das trainierte Modell. Was fehlt, sind
Deine **ausgewerteten Sets** — ohne sie ist die Verlaufsliste auf dem Mac leer und
Retraining ist nicht möglich.

## Wichtig vorweg: `archived/` ist kein Müll

Naheliegend wäre, den 2,9 GB großen Ordner `analysis_results/archived/` wegzulassen —
er ist schließlich durch den bekannten Delete-Bug entstanden (das Frontend löscht nur
den localStorage, die Dateien bleiben liegen).

**Das wäre ein Fehler.** Die Prüfung ergab:

| Von 45 gelabelten Ground-Truth-Sets | Anzahl |
|---|---|
| Audio liegt in `analysis_results/` | 20 |
| Audio liegt **nur in `archived/`** | **9** |
| Kein Audio mehr auffindbar | 16 |

Von den 29 noch trainierbaren Sets liegen also **9 ausschließlich im Archiv** — rund
ein Drittel Deiner Trainingsbasis. Zusätzlich liest `fit_composite_weights.py` die
archivierten JSONs bewusst mit aus.

Die archivierten JSONs (340 KB) kopiert das Skript deshalb **immer** mit.

---

## Welchen Weg willst Du?

**Weg A — nur die Analysen (3,5 MB, über die Cloud)**

Verlaufsliste vollständig, alle Übergänge und Scores da, `fit_composite_weights.py`
läuft. **Nicht möglich:** Wiedergabe/Wellenform und Modell-Retraining — beides braucht
die Audiodateien.

**Weg B — Analysen + alles Audio (9,3 GB, per USB-Stick)**

Alles, was auf dem Windows-PC geht, geht auch auf dem Mac. USB-Stick ab 16 GB.

Du kannst **erst A machen** und B später nachschieben — die Audiodateien werden einfach
danebengelegt, die JSONs bleiben unberührt.

---

## Schritt 1 — Auf dem Windows-PC exportieren

Doppelklick auf **`MixCoach-Daten-Uebertragen.bat`**.

- Weg A: `1` eingeben, Ziel z.B. `C:\Users\Sebro\Dropbox\MixCoach-Transfer`
- Weg B: `2` eingeben, Ziel z.B. `E:\MixCoach-Transfer`

Am Ende zeigt das Skript eine Prüfliste. **Diese Zahlen sollten stimmen:**

    Analysen              : 22
    Archivierte Analysen  : 16
    Audio-Dateien         : 22   (nur bei Weg B)
    Audio im Archiv       :  9   (nur bei Weg B)

Stimmen sie nicht, war das Ziel zu klein oder der Vorgang wurde abgebrochen. Skript
einfach erneut starten — es kopiert nur Fehlendes nach.

---

## Schritt 2 — Auf den Mac bringen

**Weg A (Cloud):** synchronisiert sich von selbst. Auf dem Mac dieselbe Cloud-App
installieren und warten, bis `MixCoach-Daten` da ist.

**Weg B (Stick):** Stick auswerfen (Rechtsklick → *Auswerfen*, nicht einfach abziehen —
sonst sind die Dateien womöglich unvollständig) und am Mac einstecken.

> **Stick-Format:** Ist der Stick **NTFS**-formatiert, kann der Mac ihn lesen, aber
> nicht beschreiben — zum Kopieren *auf* den Mac reicht das. Nur für die Gegenrichtung
> bräuchtest Du **exFAT**.
>
> **Bei 9,3 GB zusätzlich beachten:** Auf **FAT32** ist keine Datei über 4 GB erlaubt.
> Deine größten Mixe liegen bei ~470 MB, das passt — aber FAT32 fasst insgesamt nur
> begrenzt. exFAT ist die sichere Wahl.

---

## Schritt 3 — Auf dem Mac an die richtige Stelle legen

Voraussetzung: Das Repository ist geklont (Abschnitt 3.1 in `LIESMICH-GitHub.md`),
liegt also z.B. unter `~/Projekte/MixCoach`.

### Variante Terminal (empfohlen, weil prüfbar)

`/Volumes/STICKNAME` durch den echten Stick-Namen ersetzen — der steht in der
Finder-Seitenleiste:

    mkdir -p ~/Projekte/MixCoach/daten/analysis_results/archived

    cp -v /Volumes/STICKNAME/MixCoach-Transfer/MixCoach-Daten/analysis_results/* \
          ~/Projekte/MixCoach/daten/analysis_results/ 2>/dev/null

    cp -v /Volumes/STICKNAME/MixCoach-Transfer/MixCoach-Daten/analysis_results/archived/* \
          ~/Projekte/MixCoach/daten/analysis_results/archived/

Bei Weg A stattdessen aus dem Cloud-Ordner, z.B. `~/Dropbox/MixCoach-Transfer/...`.

### Variante Finder

1. Finder, `Cmd + Shift + G`, eingeben: `~/Projekte/MixCoach/daten`
2. Fehlt `analysis_results`, anlegen (Rechtsklick → *Neuer Ordner*, exakt so benannt),
   darin nochmal `archived`.
3. **Den Inhalt** der jeweiligen Ordner hineinziehen — nicht die Ordner selbst,
   sonst landet alles eine Ebene zu tief.

---

## Schritt 4 — Prüfen

Im Terminal:

    ls ~/Projekte/MixCoach/daten/analysis_results/*.json | wc -l
    ls ~/Projekte/MixCoach/daten/analysis_results/archived/*.json | wc -l

**Erwartet: 22 und 16.** Bei Weg B zusätzlich:

    ls ~/Projekte/MixCoach/daten/analysis_results/*.{wav,mp3} 2>/dev/null | wc -l
    ls ~/Projekte/MixCoach/daten/analysis_results/archived/*.{wav,mp3} 2>/dev/null | wc -l

**Erwartet: 22 und 9.**

Danach MixCoach starten (`MixCoach-Start-Mac.command` doppelklicken) und die
Verlaufsliste im Browser prüfen.

---

## Was ist mit `MIXCOACH_DATA_DIR`?

Die Engine findet ihre Daten über diese Umgebungsvariable (`app/paths.py`, Zeile 32) —
ist sie nicht gesetzt, nimmt sie den Projektordner. `MixCoach-Start-Mac.command` setzt
sie automatisch relativ zum eigenen Speicherort. Du musst nichts von Hand setzen.

Wichtig ist nur: Die Daten müssen in `daten/` **innerhalb des Projektordners** liegen.

---

## Häufige Stolpersteine

**Verlaufsliste bleibt leer, obwohl Dateien da sind.**
Meist liegen die JSONs eine Ebene zu tief, also in
`daten/analysis_results/analysis_results/`. Prüfen mit:

    ls ~/Projekte/MixCoach/daten/analysis_results | head

Da müssen direkt `.json`-Dateien erscheinen, kein Unterordner.

**`MixCoach-Start-Mac.command` lässt sich nicht öffnen.**
Einmalig freischalten:

    chmod +x ~/Projekte/MixCoach/MixCoach-Start-Mac.command

Meldet macOS einen unbekannten Entwickler: Rechtsklick → *Öffnen* → im Dialog nochmal
*Öffnen*. Nur beim ersten Mal nötig.

**`.DS_Store`-Dateien.** Harmlos, stehen bereits in der `.gitignore`.

---

## Danach: Delete-Bug angehen

Sobald der Umzug steht, lohnt sich der offene Punkt aus dem Projektstand: ein echter
`DELETE`-Endpunkt, der sauber nach `archived/` verschiebt, statt nur den localStorage
zu leeren. Sonst wächst auf dem Mac derselbe unübersichtliche Archivordner wieder heran
— und Du weißt beim nächsten Umzug wieder nicht, was davon Trainingsdaten sind.
