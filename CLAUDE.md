# MixCoach — Projektkontext

DJ-Set-Analyse: Aufnahme rein, Report mit bewerteten Übergängen raus.
Der USP ist die Transition, nicht der Track — siehe `PRODUKTVISION.md`
und `ROADMAP.md`.

**Stand 10.08.2026:** `PROMPT_K1_2026-07-30.md` ist abgearbeitet, Ergebnis in
`K1_AUFBAU_2026-07-31.md`. Nachgemessen und zusammengeführt am 10.08.:
`SITZUNG_2026-08-10.md`. Offen und wartend auf Sebastian: die zweite,
blinde Labelrunde (`MixCoach-Zweitrunde.command`) und die Entscheidung zu
`quality_score`. Nächster Bauschritt laut Standortbestimmung: die Historie
aus `localStorage` nach Supabase.

## Die Live-Schwelle — Maßstab für jede Priorisierung

> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.**

Gilt seit 30.07.2026 und ersetzt „Precision 75–80 %". Grund: 20 zusätzliche
gelabelte Sets bringen +0,1 pp Precision, die vorhandenen Merkmale erklären 8 %
der Zeitvarianz. Präzision und Timing bleiben Ziele, sind aber **kein Tor** mehr.

Praktisch heißt das bei jeder Aufgabe: Sie zahlt auf eine der drei Bedingungen
ein, oder sie hat einen anderen genannten Grund. Herleitung und ausgezählter
Stand: `STANDORTBESTIMMUNG_2026-07-30.md`, Befund: `ZUKUNFTSWEGE_2026-07-30.md`.

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

Seit dem 31.07.2026 ist `--mode dedup` die **Vorgabe**: gezählt werden
Aufnahmen (`fileName`), nicht Ground-Truth-Dateien — sonst zählt REC001 elfmal.
`--check` sagt an, gegen welchen Stand es prüft.

Stand 31.07.2026, Sicht `dedup`: 28 Aufnahmen, 286 bewertete Übergänge,
Recall 71 %, Precision 74 %, strikt korrekt 29 %, **σ = 54,58 s**, Median
−29,43 s, 85 % zu spät. Die alte Sicht `spec` (69 „Sets", σ = 52,87 s) bleibt
über `--mode spec` abrufbar — **das Entdoppeln hat σ erhöht**, die
Doppelzählung hatte die Streuung geschönt.

Nur die 19 verwertbaren Aufnahmen (`dedup --nur-verwertbar`): Recall 74 %,
Precision 80 %, σ = 45,85 s.

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

## Was gemessen erledigt ist — nicht nochmal aufmachen

- **Mehr gelabelte Sets kaufen Recall, keine Precision.** Von 4 auf 24 Sets:
  Recall +17,4 pp, Precision +1,6 pp bei ±6,0 pp Ziehungsstreuung
  (`tools/eval/lernkurve.py`).
- **Die 17 Merkmale tragen die Zeit nicht.** R² = 0,011 auf 1303
  Kandidatenpaaren, ein konstanter Offset schafft dasselbe
  (`tools/eval/zeit_regression.py`). Zweifach belegt, 30.07. und 10.08.
- **Die Auswahl rankt nicht schlecht, sie setzt zu viele Marker.** 317 auf 170
  echte Übergänge, Ausschöpfung der Orakel-Schranke 93–95 %
  (`tools/eval/nms2.py`). Precision ist durch die Markerzahl gedeckelt.
- **Kein fünfter Blend-Onset-Schätzer.** Vier sind gemessen gescheitert.
- **Keine Synthetik im Training, kein Landmark-Vorfilter.** Beide gemessen
  verworfen, siehe `PROJEKTSTAND-CLAUDE.md` Abschnitt 4.

Wer eine dieser Fragen neu stellt, braucht einen neuen Eingang — nicht mehr
Daten und keine andere Zielgröße.

## Tests

```bash
cd audio-engine/mixcoach-audio-engine
../../.venv/bin/python -m pytest tests/ -q      # 226 Tests, alle grün
```

`tests/conftest.py` verhindert, dass Testläufe Analyse-JSONs im Datenstamm
hinterlassen. Vor dem 31.07. taten sie das — 62 Stück waren aufgelaufen und
haben eine Messung verschoben.
