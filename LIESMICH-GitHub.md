# MixCoach über GitHub synchron halten

*Erstellt am 30.07.2026 — ersetzt das USB-Stick-Verfahren für Code. Für die Audio-Daten bleibt der Stick nötig, siehe Abschnitt 4.*

## Warum

Bisher gab es keinen gemeinsamen Ablageort: jede Übertragung war Handarbeit per Stick,
und genau dadurch entsteht Versatz zwischen den Rechnern. Mit GitHub genügt künftig
ein Klick zum Hochladen und `git pull` auf der anderen Seite.

Das Repository ist mit **916 KB und 401 Dateien sehr klein** — die großen Daten sind
per `.gitignore` bewusst ausgeschlossen. GitHub ist dafür also bestens geeignet.

---

## 1. GitHub-Repository anlegen (im Browser, einmalig)

1. Auf https://github.com einloggen (oder kostenlos registrieren).
2. Oben rechts `+` → **New repository**.
3. Name: `mixcoach`
4. Sichtbarkeit: **Private** ← wichtig
5. **Keine Haken** bei "Add a README", ".gitignore" oder "license" —
   das Repository muss komplett leer bleiben, sonst schlägt der erste Push fehl.
6. **Create repository** klicken.
7. Die angezeigte URL kopieren, Form: `https://github.com/DEINNAME/mixcoach.git`

### Access Token erzeugen (statt Passwort)

GitHub akzeptiert beim Hochladen kein normales Passwort mehr:

1. https://github.com/settings/tokens → **Generate new token (classic)**
2. Note: `MixCoach`, Expiration: `No expiration`
3. Haken **nur** bei `repo`
4. **Generate token**, den angezeigten Text sofort kopieren und sicher ablegen
   (z.B. im Passwort-Manager) — er wird nur ein einziges Mal angezeigt.

Diesen Token gibst Du später ein, wenn Git nach dem *Passwort* fragt.

---

## 2. Auf dem Windows-PC hochladen

Doppelklick auf **`MixCoach-GitHub-Einrichten.bat`**, die kopierte URL einfügen, Enter.

Falls Git fehlt, meldet das Skript das — dann vorher https://git-scm.com/download/win
installieren (überall "Next", Standardeinstellungen).

**Ab jetzt im Alltag:** nach Arbeitssitzungen einfach `MixCoach-Hochladen.bat`
doppelklicken, kurz beschreiben was sich geändert hat, fertig.

---

## 3. Auf dem MacBook einrichten

### 3.1 Code holen

Terminal öffnen (Cmd+Leertaste → "Terminal") und eingeben:

    mkdir -p ~/Projekte && cd ~/Projekte
    git clone https://github.com/DEINNAME/mixcoach.git MixCoach
    cd MixCoach

Beim Login: Benutzername = GitHub-Name, Passwort = **der Access Token** aus Schritt 1.

### 3.2 Python 3.10 und Node installieren

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install python@3.10 node ffmpeg

`ffmpeg` gleich mitinstallieren — auf dem Mac wird es fast immer gebraucht.

### 3.3 Pakete installieren

    cd ~/Projekte/MixCoach/audio-engine
    python3.10 -m venv .venv
    source .venv/bin/activate
    cd mixcoach-audio-engine && pip install -r requirements.txt

    cd ~/Projekte/MixCoach/Frontend && npm install

### 3.4 Starten

Die `.bat`-Dateien funktionieren auf dem Mac **nicht** — sie sind Windows-only und
enthalten fest verdrahtete Pfade wie `C:\Projekte\Projekte\MixCoach`.

Stattdessen liegt im Projektordner `MixCoach-Start-Mac.command`. Einmalig freischalten:

    chmod +x ~/Projekte/MixCoach/MixCoach-Start-Mac.command

Danach genügt ein Doppelklick im Finder. Das Skript ermittelt seinen Projektpfad selbst
— es ist also egal, wo das Projekt auf dem Mac liegt.

---

## 4. Was GitHub NICHT überträgt

Das ist der wichtigste Abschnitt. Folgendes bleibt per `.gitignore` außen vor und muss
weiterhin per USB-Stick oder Cloud übertragen werden:

| Ordner | Größe | Brauchst Du das? |
|---|---|---|
| `daten/analysis_results/*.json` | **3,2 MB** | **Ja** — Deine 22 Analysen. Ohne sie ist die Verlaufsliste leer. |
| `daten/analysis_results/*.wav/.mp3` | 6,4 GB | Für Wiedergabe **und Retraining** |
| `daten/analysis_results/archived/*.json` | 340 KB | **Ja** — wird von `fit_composite_weights.py` mitgelesen |
| `daten/analysis_results/archived/*.wav` | 2,9 GB | **Ja, wenn Du trainieren willst** — enthält das Audio von 9 gelabelten Sets |
| `daten/library/fp/` | 243 MB | Nein — Fingerprint-Index, reproduzierbar |
| `audio-engine/.../datasets/` | ~7,6 GB | Nein — synthetische Trainingsdaten, seit 28.07. nicht mehr im Training |
| `Frontend/node_modules/`, `.venv/` | groß | Nein — entstehen bei Schritt 3.3 neu |

**Genaue Schritt-für-Schritt-Anleitung dafür: `LIESMICH-Daten-auf-den-Mac.md`**
und das Skript `MixCoach-Daten-Uebertragen.bat`.

**In Git enthalten** und damit automatisch dabei: der gesamte Code, die handgesetzten
Ground-Truth-Labels (`daten/ground_truth/`, 45 Dateien) und das trainierte Modell
(`app/models/track_change_gbm.json`). Das sind die nicht reproduzierbaren Dinge.

Praktisch heißt das: **einmal noch den Stick für `daten/analysis_results/`**, danach
läuft der Code-Abgleich über GitHub.

---

## 5. Der Claude-Code-Chatverlauf

Der läuft **nicht** über GitHub — er liegt außerhalb des Projektordners unter
`C:\Users\Sebro\.claude\projects\`. Dafür gibt es die separate Anleitung
`LIESMICH-Verlauf-Uebertragen.md` und das Skript
`MixCoach-ClaudeCode-Verlauf-Sichern.bat`.

---

## 6. Alltag danach

**Windows → Mac:**  `MixCoach-Hochladen.bat` doppelklicken, auf dem Mac `git pull`

**Mac → Windows:**  auf dem Mac `git add -A && git commit -m "..." && git push`,
auf Windows `git pull`

**Goldene Regel:** immer erst `git pull`, bevor Du auf einem Rechner zu arbeiten
anfängst. Dann kommen sich die beiden Seiten nie in die Quere.
