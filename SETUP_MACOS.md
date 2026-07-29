# MixCoach auf macOS — Stand nach dem Umzug

Stand: 29.07.2026 · Rechnerwechsel Windows → Mac (Apple Silicon)

Das Projekt lag auf dem Windows-Rechner in einer über Jahre gewachsenen
Umgebung, von der beim Kopieren nur die Dateien mitgekommen sind — nicht die
Werkzeuge und nicht die Konfiguration. Dieses Dokument hält fest, was
wiederhergestellt ist, was noch fehlt, und wie man alles startet.

---

## Was schon läuft

| | |
|---|---|
| Versionskontrolle | `git` initialisiert, erster Commit = Zustand direkt nach dem Umzug |
| Python-Umgebung | `.venv/` im Projektstamm, alle Audio-Bibliotheken installiert |
| MP3/WAV-Dekodierung | funktioniert ohne ffmpeg (libsndfile 1.2.2) |
| Referenzmetrik | `tools/analyze_timing_bias.py`, Selbsttest grün |
| Repath-Werkzeug | `tools/repath_library_index.py` + 11 Tests, wartet auf die Musik |

## Was noch fehlt — vier Dinge, drei davon brauchen dich

### 1. Die Musik-Library ist nicht auf dem Mac ⛔ blockiert Job A

`daten/library/index.json` enthält 6113 Tracks mit Pfaden der Form
`C:/Users/Sebro/Music/…`. Auf diesem Rechner auflösbar: **0**.
`~/Music` enthält nur den leeren Apple-Music-Ordner.

Die Fingerprints (`daten/library/fp/` + `lm/`, 12226 Dateien, 1,6 GB) sind
dagegen vollständig da. Sie sind Stunden Rechenzeit wert und **müssen nicht
neu erzeugt werden** — dafür ist das Repath-Skript da.

**Wichtig:** Die Ordnerstruktur unterhalb der Musik-Wurzel muss dieselbe
bleiben wie auf Windows. Also alles, was unter `C:/Users/Sebro/Music/` lag,
unverändert unter den neuen Wurzelordner kopieren. Wird währenddessen
umsortiert, findet das Skript die Dateien nicht wieder und stoppt.

Danach:

```bash
cd audio-engine/mixcoach-audio-engine
export MIXCOACH_DATA_DIR="$(cd ../../daten && pwd)"

# 1. Erst schauen, nichts anfassen:
../../.venv/bin/python -m tools.repath_library_index \
    --old-root "C:/Users/Sebro/Music" \
    --new-root "/Users/sebastianbroening/Music" \
    --dry-run

# 2. Wenn der Report ≥95 % auflösbar meldet und 0 Kollisionen:
../../.venv/bin/python -m tools.repath_library_index \
    --old-root "C:/Users/Sebro/Music" \
    --new-root "/Users/sebastianbroening/Music"

# 3. Der eigentliche Beweis — ein Fingerprint-Lauf muss done=0 melden.
```

Vor jedem Schreiben legt das Skript ein Backup `index.json.bak-<Zeitstempel>`
an. Zusätzlich liegt der Ausgangs-Index im ersten Git-Commit.

### 2. Python 3.9 ist zu alt ⛔ blockiert das Backend

Auf dem Mac liegt nur das System-Python **3.9.6**. `app/main.py:240`
verwendet aber `str | None` in einer Signatur, die FastAPI zur Laufzeit
auswertet — das ist Python-3.10-Syntax:

```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

Die Logs vom alten Rechner zeigen `cp312`/`cp313`, dort lief also 3.12/3.13.

Folge heute: Backend startet nicht, 4 Testdateien sind nicht einlesbar.
Der Rest der Engine (und beide neuen Werkzeuge) läuft auf 3.9 problemlos.

→ **Python ≥ 3.12 installieren, dann `.venv` neu anlegen.**

### 3. Node.js fehlt komplett ⛔ blockiert das Frontend

`node` und `npm` sind nicht installiert. `Frontend/node_modules/` ist zwar
mitkopiert (322 Pakete), aber darin liegen für Windows gebaute Binärteile —
das muss ohnehin neu installiert werden.

→ **Node.js LTS installieren, dann `npm ci` in `Frontend/`.**

### 4. Die Supabase-Zugangsdaten fehlen

`Frontend/src/integrations/supabase/client.server.ts` liest
`SUPABASE_URL` und `SUPABASE_SERVICE_ROLE_KEY` aus der Umgebung. Eine `.env`
ist nicht mitgekommen (zu Recht — die gehört nicht ins Repo). Die Werte
stehen im Supabase- bzw. Lovable-Projekt.

---

## Zwei Fallstricke, die Zeit kosten, wenn man sie nicht kennt

### MIXCOACH_DATA_DIR muss gesetzt sein

`app/paths.py` leitet den Datenstamm aus `MIXCOACH_DATA_DIR` ab und fällt
sonst auf den Engine-Ordner zurück. Die Library liegt aber unter `daten/`.
Ohne die Variable sucht die App ihre Daten am falschen Ort.

Genau das ist auf dem alten Rechner passiert und hat die Ground Truth auf
zwei Stämme aufgeteilt: `daten/ground_truth/` (45 Dateien) und
`audio-engine/mixcoach-audio-engine/ground_truth/` (24 Dateien, davon 18
byteidentisch mit der anderen Seite). Siehe `analyze_timing_bias.py --mode`.

```bash
export MIXCOACH_DATA_DIR="/Users/Shared/Files From c.localized/Projekte/Projekte/MixCoach/daten"
```

Am besten in `~/.zshrc` eintragen, damit es nicht wieder auseinanderläuft.

### Die Dateien gehören `root`

Der ganze Baum liegt unter `/Users/Shared` mit `root:wheel` und gesetztem
Sticky-Bit. Inhalte lassen sich ändern (Modus 777), aber Dateien nicht
umbenennen oder ersetzen — Werkzeuge, die atomar über „schreiben und
umbenennen" arbeiten, laufen auf `EACCES`. `git` verweigert den Dienst
ebenfalls, dafür ist bereits eine `safe.directory`-Ausnahme eingetragen.

Sauberer Weg (fragt nach deinem Passwort):

```bash
sudo chown -R "$(id -un):staff" "/Users/Shared/Files From c.localized/Projekte/Projekte/MixCoach"
```

---

## Startbefehle

Alle Pfade relativ zum Projektstamm.

```bash
export MIXCOACH_DATA_DIR="$(pwd)/daten"

# Backend (braucht Python ≥3.12, siehe oben)
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Tests
../../.venv/bin/python -m pytest tests/ -q

# Referenzmetrik der Transitions-Erkennung
../../.venv/bin/python -m tools.analyze_timing_bias
../../.venv/bin/python -m tools.analyze_timing_bias --check    # Sollwerte prüfen

# Frontend (braucht Node.js)
cd Frontend && npm ci && npm run dev
```

## Python-Umgebung neu aufbauen

```bash
python3 -m venv .venv
.venv/bin/pip install -r audio-engine/mixcoach-audio-engine/app/requirements.txt
```

`requirements.txt` war unvollständig — `pytest`, `httpx` und `scikit-learn`
waren auf dem alten Rechner von Hand nachinstalliert und fehlten in der
Datei. Ist ergänzt.

## Was nicht im Repo liegt

23 GB Rohdaten sind bewusst ausgeschlossen (`.gitignore`): Set-Aufnahmen,
Fingerprints unter `daten/library/fp` + `lm`, die 162 synthetischen Mixe,
`node_modules`, `.venv`. Alles davon ist aus Audio bzw. per Skript
reproduzierbar. Die Analyse-Ergebnisse **als JSON** sind dagegen versioniert
(5 MB) — sie sind die Datengrundlage der Ground-Truth-Auswertung.
