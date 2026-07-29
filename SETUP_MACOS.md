# MixCoach auf macOS — Stand nach dem Umzug

Stand: 29.07.2026 · Rechnerwechsel Windows → Mac (Apple Silicon)

Vom Windows-Rechner sind nur die Dateien mitgekommen, nicht die Werkzeuge und
nicht die Konfiguration. Dieses Dokument hält fest, was wiederhergestellt ist,
was noch fehlt und wie man alles startet.

---

## Was läuft

| | |
|---|---|
| Versionskontrolle | `git` initialisiert, erster Commit = Zustand direkt nach dem Umzug |
| Python | **3.12.13** unter `~/.local/opt/python312`, `.venv/` im Projektstamm |
| Node.js | **24.18.0 LTS** unter `~/.local/opt/node` |
| Audio-Bibliotheken | numpy 2.4.6, scipy 1.18, librosa 0.11, numba 0.66, scikit-learn 1.9 |
| MP3/WAV-Dekodierung | funktioniert ohne ffmpeg (libsndfile 1.2.2) |
| Backend | startet, `/health` und `/library/tracks` (6113 Einträge) antworten |
| Testsuite | **195 Tests, alle grün** |
| Referenzmetrik | `tools/analyze_timing_bias.py`, Selbsttest reproduziert die Sollwerte |
| Repath-Werkzeug | `tools/repath_library_index.py` + 11 Tests, wartet auf die Musik |

Python und Node wurden bewusst als offizielle Tarballs nach `~/.local`
installiert statt per Homebrew oder `.pkg` — beides hätte `sudo` gebraucht.
Prüfsummen wurden gegen `SHASUMS256.txt` bzw. `SHA256SUMS` verifiziert.
`~/.zshrc` setzt `PATH` und `MIXCOACH_DATA_DIR`.

---

## Was noch fehlt

### 1. Dateirechte ⛔ blockiert das Frontend — **braucht dein Passwort**

Der ganze Baum liegt unter `/Users/Shared` mit `root:wheel` und gesetztem
Sticky-Bit. Inhalte lassen sich ändern (Modus 777), aber Dateien nicht
löschen, umbenennen oder ersetzen — das darf beim Sticky-Bit nur der
Eigentümer. Konkrete Folgen:

- `npm ci` bricht ab: `EACCES: permission denied, rmdir '…/node_modules/@ai-sdk'`
- Werkzeuge, die atomar über „schreiben und umbenennen" arbeiten, laufen auf `EACCES`
- `git` verweigerte den Dienst (dafür ist bereits eine `safe.directory`-Ausnahme gesetzt)

Ein Befehl behebt alles davon:

```bash
sudo chown -R "$(id -un):staff" "/Users/Shared/Files From c.localized/Projekte/Projekte/MixCoach"
```

Danach ist das Frontend zwei Befehle entfernt:

```bash
cd Frontend && npm ci && npm run dev
```

Das mitkopierte `node_modules/` (322 Pakete) ist unbrauchbar — es enthält
für Windows gebaute Binärteile, `esbuild` fehlt ganz. `npm ci` ersetzt es
vollständig aus `package-lock.json`. Es wurde bisher **nichts gelöscht**,
der fehlgeschlagene Lauf ist beim ersten `rmdir` gestoppt.

### 2. Die Musik-Library ist nicht auf dem Mac ⛔ blockiert Job A

`daten/library/index.json` enthält 6113 Tracks mit Pfaden der Form
`C:/Users/Sebro/Music/…`. Auf diesem Rechner auflösbar: **0**.
`~/Music` enthält nur den leeren Apple-Music-Ordner.

Die Fingerprints (`daten/library/fp/` + `lm/`, 12226 Dateien, 1,6 GB) sind
dagegen vollständig da. Sie sind Stunden Rechenzeit wert und **müssen nicht
neu erzeugt werden** — dafür ist das Repath-Skript da.

**Wichtig:** Die Ordnerstruktur unterhalb der Musik-Wurzel muss dieselbe
bleiben wie auf Windows. Alles, was unter `C:/Users/Sebro/Music/` lag,
unverändert unter den neuen Wurzelordner kopieren. Wird dabei umsortiert,
findet das Skript die Dateien nicht wieder und stoppt.

```bash
cd audio-engine/mixcoach-audio-engine

# 1. Erst schauen, nichts anfassen:
../../.venv/bin/python -m tools.repath_library_index \
    --old-root "C:/Users/Sebro/Music" \
    --new-root "$HOME/Music" \
    --dry-run

# 2. Wenn der Report ≥95 % auflösbar meldet und 0 Kollisionen:
../../.venv/bin/python -m tools.repath_library_index \
    --old-root "C:/Users/Sebro/Music" \
    --new-root "$HOME/Music"

# 3. Nachmessen:
../../.venv/bin/python -m tools.repath_library_index \
    --old-root x --new-root x --verify
```

Der eigentliche Beweis ist danach ein Fingerprint-Lauf: er muss
`skipped = <n>, done = 0, failed = 0` melden. Jedes `done > 0` heißt, dass
die mtime-Behandlung nicht greift.

Vor jedem Schreiben legt das Skript ein Backup `index.json.bak-<Zeitstempel>`
an. Zusätzlich liegt der Ausgangs-Index im ersten Git-Commit.

### 3. Die Supabase-Zugangsdaten fehlen

`Frontend/src/integrations/supabase/client.server.ts` liest `SUPABASE_URL`
und `SUPABASE_SERVICE_ROLE_KEY` aus der Umgebung. Vorlage liegt bereit:

```bash
cd Frontend && cp .env.example .env    # dann die echten Werte eintragen
```

Die Werte stehen im Supabase-Projekt unter Project Settings → API bzw. im
Lovable-Projekt unter Cloud. `.env` ist in `.gitignore` — der Service-Role-Key
umgeht Row Level Security und darf nicht ins Repo.

---

## Der Fallstrick, der die Ground Truth gespalten hat

`app/paths.py` leitet den Datenstamm aus `MIXCOACH_DATA_DIR` ab und fällt
sonst auf den Engine-Ordner zurück. Die Library liegt aber unter `daten/`.
Ohne die Variable sucht die App ihre Daten am falschen Ort.

Genau das ist auf dem alten Rechner passiert: die Ground Truth liegt heute in
zwei Stämmen — `daten/ground_truth/` (45 Dateien) und
`audio-engine/mixcoach-audio-engine/ground_truth/` (24 Dateien, davon 18
byteidentisch, 6 mit abweichendem Bewertungsstand).

Die dokumentierten Kennzahlen (638 bewertete Transitions, 287 `timing_off`)
entstehen nur, wenn man beide Ordner roh addiert — 24 Sets zählen dann
doppelt. `analyze_timing_bias.py` bietet deshalb beide Sichten an:
`--mode spec` reproduziert den dokumentierten Stand, `--mode dedup` zählt
jedes Set einmal. **Der Befund hält in beiden** (Median −29,1 s, σ 51,1 s,
86 % zu spät), die Diagnose ist also kein Artefakt der Doppelzählung.

`~/.zshrc` setzt die Variable jetzt dauerhaft, damit das nicht wieder passiert.

---

## Startbefehle

```bash
# Backend
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Tests
../../.venv/bin/python -m pytest tests/ -q

# Referenzmetrik der Transitions-Erkennung
../../.venv/bin/python -m tools.analyze_timing_bias
../../.venv/bin/python -m tools.analyze_timing_bias --check     # Sollwerte prüfen
../../.venv/bin/python -m tools.analyze_timing_bias --mode dedup

# Frontend (nach dem chown aus Punkt 1)
cd Frontend && npm ci && npm run dev
```

## Python-Umgebung neu aufbauen

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r audio-engine/mixcoach-audio-engine/app/requirements.txt
```

`requirements.txt` war unvollständig — `pytest`, `httpx` und `scikit-learn`
waren auf dem alten Rechner von Hand nachinstalliert und fehlten in der
Datei. Ist ergänzt.

## Was nicht im Repo liegt

23 GB Rohdaten sind bewusst ausgeschlossen (`.gitignore`): Set-Aufnahmen,
Fingerprints unter `daten/library/fp` + `lm`, die 162 synthetischen Mixe,
`node_modules`, `.venv`, `.env`. Alles davon ist aus Audio bzw. per Skript
reproduzierbar oder gehört aus Sicherheitsgründen nicht hinein. Die
Analyse-Ergebnisse **als JSON** sind dagegen versioniert (5 MB) — sie sind
die Datengrundlage der Ground-Truth-Auswertung.
