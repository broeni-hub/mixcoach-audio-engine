# MixCoach — Projektkontext

DJ-Set-Analyse: Aufnahme rein, Report mit bewerteten Übergängen raus.
Der USP ist die Transition, nicht der Track — siehe `PRODUKTVISION.md`
und `ROADMAP.md`. Aktueller Arbeitsauftrag: `CLAUDE_CODE_SPEC_2026-07-29.md`.

## Aufbau

```
audio-engine/mixcoach-audio-engine/   FastAPI-Backend + Analyse
  app/audio/scoring/                  Composite-Bewertung — NICHT ANFASSEN
  app/experimental/detection/         Kandidatensuche für Übergänge
  app/library/manager.py              Fingerprint-/Index-Verwaltung
  app/paths.py                        Datenstamm, siehe unten
  tools/                              Auswertungs- und Wartungsskripte
daten/                                Datenstamm (MIXCOACH_DATA_DIR)
  library/index.json                  6113 Tracks
  library/fp/<tid>.npy                Chroma, Hop 372 ms
  library/lm/<tid>.npz                Landmark-Hashes
Frontend/                             TanStack Start + React 19 + Supabase
```

## Umgebung

Python **3.12** in `.venv/` im Projektstamm (System-Python 3.9 reicht nicht:
`app/main.py:240` nutzt `str | None` in einer Signatur, die FastAPI zur
Laufzeit auswertet). Node 24 und Python 3.12 liegen unter `~/.local`,
per `~/.zshrc` im PATH.

`MIXCOACH_DATA_DIR` **muss gesetzt sein** und auf `daten/` zeigen. Ohne die
Variable fällt `app/paths.py` auf den Engine-Ordner zurück, und die App sucht
Library, Ergebnisse und Ground Truth am falschen Ort. Genau so ist die Ground
Truth auf zwei Stämme auseinandergelaufen — `daten/ground_truth/` (45 Dateien)
und `audio-engine/mixcoach-audio-engine/ground_truth/` (24, davon 18
byteidentisch). Beim Auswerten immer bewusst entscheiden, welcher Stand gilt.

Details und offene Blocker: `SETUP_MACOS.md`.

## Zwei Eigenheiten, die man kennen muss

**Track-IDs hängen am Pfad-String.** `manager.py:56` bildet die ID als
`md5(path)[:16]`. Ein geänderter Pfad heißt neue ID heißt verwaiste
Fingerprints. Deshalb nie „einfach neu scannen", sondern
`tools/repath_library_index.py` benutzen.

**NFC/NFD.** Windows schreibt Dateinamen als NFC, macOS liefert oft NFD.
Beide Formen finden dieselbe Datei über `exists()`, ergeben aber
verschiedene md5-Summen und damit verschiedene Track-IDs. Pfade, die in
Track-IDs eingehen, immer auf die Schreibweise bringen, die `os.scandir`
zurückgibt.

## Referenzmetrik

`tools/analyze_timing_bias.py` ist die Messlatte für die Erkennung. Läuft
ohne Audio und ohne numpy.

```bash
.venv/bin/python -m tools.analyze_timing_bias --check     # muss grün sein
```

Stand 29.07.2026: Recall 73 %, Precision 75 %, strikt korrekt 30 %.
Von den 287 `timing_off` ist die Engine in 86 % **zu spät**, Median −29,85 s,
σ = 52,87 s.

Die Diagnose dazu: `detect_transition_zones()` sucht eine RMS-Delle — das ist
im DJ-Mix der Breakdown vor dem Drop, also das *Ende* des Blends. Der Mensch
labelt den *Anfang*. Die Differenz ist die Transitionslänge (8–64 Takte),
daher die große Streuung. Ein globaler Offset behebt das nicht und lässt σ
unverändert. **σ ist die Zahl, an der sich jede Änderung messen lassen muss.**

## Arbeitsregeln

- `app/audio/scoring/*` nicht anfassen (Composite-Rebuild).
- Bestehende API-Endpoints und Frontend-Seiten nicht verändern.
- Keine Grid-Search über die Schwellwerte in `detect_transition_zones()` —
  belegt falscher Hebel, siehe oben.
- Ehrlichkeitslinie: nichts anzeigen, was nicht gemessen wurde. Das ist
  Markenkern, kein Stilmittel.
- Kommentare und Doku auf Deutsch, wie im Bestand.

## Tests

```bash
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m pytest tests/ -q      # 195 Tests, alle grün
```
