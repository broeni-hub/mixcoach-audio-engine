# MixCoach — Claude Code Spec, 2026-07-29

Zwei unabhängige Jobs. **Job A und Job B in getrennten Sessions bearbeiten.**
Job A ist Voraussetzung für alles, was Audio anfasst. Job B braucht kein Audio und
kann parallel laufen.

---

## Kontext (bitte zuerst lesen)

Repo-Root: `MixCoach/`

```
MixCoach/
├── audio-engine/mixcoach-audio-engine/
│   ├── app/
│   │   ├── library/manager.py            # Fingerprint-/Index-Verwaltung
│   │   ├── experimental/detection/       # transition_detector.py, segment_builder.py
│   │   ├── experimental/transitions.py   # erzeugt center_time/start_time/end_time
│   │   ├── audio/scoring/                # composite, harmonic_clash, vocal_overlap,
│   │   │                                 #   exit_quality, beat_alignment  → NICHT ANFASSEN
│   │   └── calibration/                  # build_features, fit_composite_weights, retrain
│   ├── ground_truth/*.json               # 24 Dateien
│   ├── tools/                            # synth_mixer/ + Fingerprint-Experimente
│   └── datasets/synthetic/v1/            # 162 synthetische Mixes
└── daten/
    ├── library/index.json                # 6113 Tracks
    ├── library/fp/<tid>.npy              # Chroma 12×N, Hop 372 ms
    ├── library/lm/<tid>.npz              # Landmark-Hashes (hashes/frames)
    └── ground_truth/*.json               # 45 Dateien
```

### Befund aus der Ground-Truth-Auswertung (69 Dateien, 638 bewertete Transitions)

| Verdict | n | Anteil |
|---|---|---|
| `correct` | 189 | 30 % |
| `timing_off` | 287 | 45 % |
| `not_a_transition` | 162 | 25 % |
| `missed` (zusätzlich erfasst) | 178 | — |

Daraus: **Recall 73 %, Precision 75 %, strikt-korrekt 30 %.**
Detection funktioniert. Timing nicht.

Von den 287 `timing_off` mit `correctedSec`:

- **86 % = Engine zu spät**, 14 % zu früh
- **Median 30 s zu spät**, σ = 53 s
- Ein globaler −30 s-Shift hebt „innerhalb 8 s" nur von 5 % auf 21 % und **verändert σ nicht**

Ein Bias, den ein konstanter Offset nicht beseitigt, ist kein Kalibrierungsfehler.
**Ursache:** `detect_transition_zones()` sucht eine lokale RMS-Delle (Abfall + Anstieg).
Das ist im DJ-Mix der Breakdown vor dem Drop von Track B — also das *Ende* des Blends.
Der Mensch labelt den *Anfang* des Blends. Die Differenz ist die Transitionslänge, und
die variiert zwischen 8 und 64 Takten. Deshalb die große Streuung.

**Das ist ein Repräsentationsfehler: die Engine gibt einen Punkt aus, wo ein Intervall
hingehört.** → Job B.

---

# JOB A — Library-Index auf macOS repathen

## Problem

Der Rechner wurde von Windows auf macOS gewechselt. Alle 6.113 Pfade in
`daten/library/index.json` sind Windows-Pfade der Form
`C:/Users/Sebro/Music/...`. **Auf diesem Rechner auflösbar: 0 von 6.113.**
Damit ist jede Operation tot, die Audio nachlädt.

## Zwei Fakten, die den Job bestimmen

1. `app/library/manager.py:56` — `_track_id(path) = hashlib.md5(path.encode()).hexdigest()[:16]`.
   Die ID ist **eine reine Funktion des Pfad-Strings**. Ein neuer Pfad ⇒ eine neue ID ⇒
   alle 12.226 vorhandenen Feature-Dateien (`fp/` + `lm/`) wären verwaist.
   Ein naiver Rescan wirft also die komplette Fingerprint-Arbeit weg.
   Umgekehrt heißt das aber auch: **das Remapping ist deterministisch berechenbar.**
   Nichts muss neu extrahiert werden — nur umbenannt.

2. `app/library/manager.py:112-115` — Skip-Logik:
   ```python
   if known and known.get("mtime") == mtime and (FP_DIR / f"{tid}.npy").exists():
       return "skipped"
   ```
   Wenn die Kopie auf den Mac die mtimes ändert, gilt jeder Track als verändert und
   wird neu fingerprintet (Stunden Rechenzeit, ohne Nutzen).
   **Deshalb: mtime nach dem Kopieren aus dem Dateisystem neu in den Index schreiben.**
   Nicht auf `cp -p` / `rsync -t` verlassen — das Skript muss robust sein, egal wie kopiert wurde.

## Voraussetzung

Die Musik-Library muss physisch auf dem Mac liegen. `~/Music` ist derzeit leer.
Der neue Wurzelpfad ist Input für das Skript, nicht geraten.

## Aufgabe

Neues Skript: `audio-engine/mixcoach-audio-engine/tools/repath_library_index.py`

CLI:

```
python -m tools.repath_library_index \
    --old-root "C:/Users/Sebro/Music" \
    --new-root "/Users/sebastianbroening/Music" \
    [--dry-run]
```

Ablauf:

1. **Backup** von `index.json` nach `index.json.bak-<ISO8601>`. Ohne Backup nichts schreiben.
2. Index laden. Für jeden `(tid, meta)`:
   - `new_path = meta["path"].replace(old_root, new_root)`, danach Separatoren auf `/` normalisieren
   - Existiert `new_path` auf der Platte? Falls nein → in Liste `missing` sammeln, Eintrag **unverändert lassen**
   - `new_tid = md5(new_path.encode("utf-8","replace")).hexdigest()[:16]`
   - Neue `mtime` per `os.stat(new_path).st_mtime_ns` lesen
3. **Kollisionsprüfung:** Falls zwei verschiedene alte tids auf dieselbe neue tid mappen →
   abbrechen und beide Pfade ausgeben. Nicht raten.
4. **Umbenennen in zwei Phasen** (alte und neue IDs können sich überschneiden):
   - Phase 1: `fp/<old>.npy` → `fp/<new>.npy.tmp`, `lm/<old>.npz` → `lm/<new>.npz.tmp`
   - Phase 2: alle `.tmp`-Endungen entfernen
   Bricht Phase 1 ab, ist der Zustand über die `.tmp`-Dateien rekonstruierbar.
5. Neuen Index schreiben: Keys = neue tids, `path` = neuer Pfad, `mtime` = neu gelesen,
   alle übrigen Felder (`title`, `artist`, `bpm`, `key`, `duration`) unverändert übernehmen.
6. **Report** auf stdout: `remapped`, `missing_on_disk`, `orphan_fp`, `orphan_lm`,
   `collisions`. Bei `--dry-run` nur den Report, keine Schreibvorgänge.

## Akzeptanzkriterien

Alle vier müssen erfüllt sein:

1. Jeder Key in `index.json` hat sowohl `fp/<tid>.npy` als auch `lm/<tid>.npz` — **100 %**.
2. Keine verwaisten Dateien in `fp/` oder `lm/`, die in keinem Index-Eintrag vorkommen.
3. Mindestens **95 %** der `path`-Werte sind auf der Platte auflösbar.
   Liegt der Wert darunter: Report ausgeben und **stoppen**, nicht weiterarbeiten —
   dann stimmt die Ordnerstruktur unter `--new-root` nicht mit der alten überein.
4. **Der entscheidende Test:** Fingerprint-Lauf erneut starten. Ergebnis muss
   `skipped = <n>, done = 0, failed = 0` sein. Jedes `done > 0` bedeutet, dass die
   mtime-Behandlung falsch ist.

## Nicht tun

- Keine Änderung an `_track_id()` selbst. Die Funktion ist in Ordnung; nur die Daten sind alt.
  (Ob die ID langfristig content-basiert sein sollte, ist eine separate Diskussion —
  nicht Teil dieses Jobs.)
- Keine Neu-Extraktion von Chroma oder Landmarks.
- Keine Änderung an `app/audio/scoring/*`, keine bestehenden Endpoints anfassen.

---

# JOB B — Transitions als Intervall statt als Punkt

## Problem

Die Engine gibt `mid_sec` / `center_time` aus, also einen Punkt. Eine DJ-Transition ist
aber ein Intervall von typischerweise 16–64 Takten. `app/experimental/transitions.py:47-49`
täuscht ein Intervall nur vor:

```python
center_time = times[i]
start_time  = max(0.0, center_time - pre_seconds)
end_time    = min(duration, center_time + post_seconds)
```

Das ist ein fixes Fenster um den Punkt, kein erkanntes Intervall.

Ergebnis: Engine und Mensch meinen verschiedene Zeitpunkte, und 45 % aller Bewertungen
landen in `timing_off`, obwohl die Transition korrekt gefunden wurde.

## Aufgabe

### Schritt 1 — Diagnose reproduzierbar machen

Neues Skript: `tools/analyze_timing_bias.py`

Liest **beide** Ground-Truth-Verzeichnisse (`ground_truth/` und `../../daten/ground_truth/`)
und gibt aus:

- Verdict-Verteilung, Recall, Precision, strikt-korrekt-Quote
- Für alle `timing_off` mit `correctedSec`: Verteilung von `correctedSec - midSec`
  (Anteil zu spät / zu früh, Median, σ, Perzentile der Absolutfehler)
- Anteil innerhalb 4 s / 8 s / 16 s — **vorher und nachher**, damit jede Änderung messbar ist

Dieses Skript ist ab jetzt die Referenzmetrik. Es muss ohne Audio laufen.
Sollwerte zur Verifikation der Implementierung — das Skript muss den heutigen Stand
exakt reproduzieren:

```
n = 287, zu spät 86 %, Median -29.85 s, σ = 52.87 s,
innerhalb 8 s = 5 %, innerhalb 16 s = 22 %
```

### Schritt 2 — Echtes Intervall detektieren

`detect_transition_zones()` bleibt als **Kandidatengenerator** erhalten (Recall 73 % ist brauchbar).
Neu ist die Verfeinerung pro Kandidat:

- Vom Kandidatenpunkt aus **rückwärts** suchen (Fenster bis 120 s) nach dem Blend-Onset
- Signal dafür: der Moment, an dem eine zweite harmonische/rhythmische Schicht einsetzt.
  Nutzbare Merkmale auf dem Mix-Audio allein: Anstieg der Chroma-Entropie, Novelty auf der
  Self-Similarity-Matrix über Chroma/MFCC, Zunahme der spektralen Dichte, Dekorrelation
  zwischen Bass- und Mittenband
- Ausgabe pro Transition: `start_sec`, `end_sec`, `duration_sec`, `confidence`
- `center_time` weiterhin mitliefern, damit nichts Bestehendes bricht

Konvention, die explizit im Code dokumentiert werden muss:

> `start_sec` = der erste Moment, in dem Track B hörbar wird.
> `end_sec` = der Moment, in dem Track A nicht mehr hörbar ist.

### Schritt 3 — Metrik umstellen

Bewertung ab jetzt `start_sec` gegen den menschlichen Referenzpunkt:

- Primär gegen die **287 `timing_off` mit `correctedSec`** — das ist das saubere Signal
- Die **189 `correct`** dienen nur als Regressionswächter: dort ist `midSec` der vom Menschen
  akzeptierte Wert. Achtung, diese Gruppe ist nicht sauber interpretierbar — wenn die Engine
  bisher das Blend-*Ende* markiert hat, hat der Mensch bei `correct` ein Ende akzeptiert.
  Vermutlich handelt es sich um kurze Übergänge/harte Schnitte, bei denen Start ≈ Ende.
  **Nicht auf diese Gruppe hin optimieren**, nur auf Verschlechterung überwachen.

## Akzeptanzkriterien

Gemessen mit `tools/analyze_timing_bias.py` auf den 287 `timing_off`:

1. Median des vorzeichenbehafteten Fehlers: von −29.9 s auf **|Median| < 8 s**
2. Anteil innerhalb 8 s: von 5 % auf **≥ 50 %**
3. σ **deutlich unter 53 s** — das ist der eigentliche Beweis, dass es kein Offset-Fix ist
4. Die 189 `correct` verschlechtern sich um höchstens 10 Prozentpunkte
5. Recall bleibt ≥ 73 %, d. h. die Kandidatengenerierung darf nicht schlechter werden

Kriterium 3 ist das wichtigste. Sinkt σ nicht, wurde nur ein konstanter Offset
eingebaut und das eigentliche Problem besteht weiter.

## Zwischencheckpoint

Nach Schritt 1 stoppen und die Zahlen zeigen, bevor Schritt 2 beginnt.
Wenn `analyze_timing_bias.py` die Sollwerte oben nicht reproduziert, stimmt etwas am
Einlesen der Ground Truth nicht — dann hat Weiterbauen keinen Sinn.

## Nicht tun

- `app/audio/scoring/*` nicht anfassen. Der Composite-Rebuild bleibt unberührt.
- Keine Änderung an bestehenden API-Endpoints oder Frontend-Seiten.
- Keine Grid-Search über die Schwellenwerte in `detect_transition_zones()`
  (`local_drop > 0.08`, `local_rise > 0.06`). Das ist der falsche Hebel — belegt durch
  die Tatsache, dass ein globaler Offset σ nicht verändert.
- Keine neuen Trainingsdaten beschaffen. Dieser Job braucht ausschließlich vorhandene Daten.

---

# Offener Punkt für später (nicht Teil von Job A oder B)

`app/audio/scoring/beat_alignment.py` soll den Beat-Phasenversatz bewerten — laut
Label-Analyse **24 % des menschlichen Urteils**. Die vorhandenen Chroma-Features in
`daten/library/fp/` haben aber einen Hop von **372 ms**, während ein Beat bei 124 BPM
**484 ms** dauert.

Damit ist Beat-Phase aus diesen Features prinzipiell nicht messbar — der Quantisierungsfehler
liegt in der Größenordnung eines ganzen Beats.

**Zu prüfen:** Lädt `beat_alignment.py` das Audio in voller Sample-Rate nach, oder arbeitet
es auf den dezimierten Chroma-Features? Im zweiten Fall bewertet das Modul Rauschen und
verfälscht das Composite-Gewicht.
