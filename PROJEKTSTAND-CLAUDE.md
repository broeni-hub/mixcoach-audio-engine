# MixCoach — Projektstand (für Claude Code / zum Weiterarbeiten)

**Zweck dieser Datei:** Wenn dieses Projekt auf einem neuen PC weitergeführt wird, hat eine dort neu gestartete Claude-Code-Session KEIN Gedächtnis an die bisherige Arbeit (das Claude-Memory-System liegt lokal auf dem alten PC). Diese Datei fasst alle wichtigen technischen Erkenntnisse, Entscheidungen, Sackgassen und den aktuellen Stand zusammen, damit die Arbeit nahtlos weitergeht. Bitte diese Datei am Anfang jeder neuen Session lesen.

Stand: 28.–30.07.2026. Alle Zeitangaben im Format TT.MM.JJJJ.

---

## 1. Vision (nicht antasten ohne Rücksprache mit Sebastian)

"Andere Tools analysieren deine Musik. MixCoach analysiert dein DJing." USP ist **Mix-Analyse** (was zwischen den Tracks passiert), nicht Track-Analyse (Tonart/BPM — das machen Mixed In Key/rekordbox/Serato schon).

Erlebnis: Set hochladen → per Fingerprinting automatisch erkennen, welcher Track wann lief (sekundengenau, echte Tracknamen) → Report mit nachhörbaren Messwerten (Phrasen-Timing, Tempo-Drift, Harmonie, Pegelsprung in dB, Bass-Overlap) → personalisiertes Coaching → Übungen aus eigenem Material → Fortschritts-Radar über Wochen.

Drei Burggräben: (1) **Daten-Schleife** — jeder Feedback-Klick verbessert das Erkennungsmodell; (2) **Library-Verbindung** — Fingerprinting macht Erkennung exakt UND ermöglicht sonst unmögliche Messungen; (3) **radikale Ehrlichkeit** — nichts anzeigen, was nicht gemessen wurde, keine erfundenen Scores, Unsicherheit klar kennzeichnen (z.B. "≈ Position geschätzt").

**Wichtigste Arbeitsregel:** Vor tiefem Einstieg in eine technische Baustelle immer kurz prüfen, ob sie dem übergeordneten Ziel dient (>90% Übergangs-Erkennung, "perfekter DJ-Coach") — siehe `ROADMAP.md`/`PRODUKTVISION.md`, aber Vorsicht: **der Code ist oft weiter als diese Dokumente** (Stand 06.07.2026, nicht durchgängig aktualisiert). Vor Planung immer den tatsächlichen Code-/Datenstand prüfen (Dateidaten in `daten/analysis_results`, `app/models/`, `app/calibration/`), nicht nur die Docs.

**Zweite wichtige Arbeitsregel:** Bei Audio-/DSP-Fixes (Timing, Schwellwerte, Vorzeichen) IMMER empirisch vor/nach an echtem Audio messen, nicht nur theoretisch herleiten oder Code-Review allein vertrauen. Mehrfach hat sich eine plausible Herleitung im Test als falsch erwiesen (siehe Abschnitt 4).

Sebastian (Projektinhaber) ist **kein Entwickler** — alle Bedienung muss über Doppelklick-`.bat`-Dateien laufen, keine Terminal-Kenntnisse voraussetzen.

---

## 2. Ordnerstruktur & wichtige Pfade

```
C:\Projekte\Projekte\MixCoach\          <- Projekt-Root (KEIN Git-Repo — kein Versionsschutz!)
├── ROADMAP.md, PRODUKTVISION.md         <- Produktplan, Stand 06.07. — hinkt dem Code hinterher
├── PROJEKTSTAND-CLAUDE.md               <- diese Datei
├── MixCoach-Start.bat                   <- Hauptstart: Engine (Port 8000) + App (Port 8080), öffnet Browser
├── MixCoach-Retrain.bat                 <- Modell-Retrain, nur wenn genug neue Labels (gated, real-only)
├── MixCoach-Retrain-Jetzt.bat           <- Retrain sofort erzwingen (--force, real-only)
├── MixCoach-Modell-Zurueck.bat          <- 1-Klick-Revert auf letztes Modell-Backup
├── audio-engine/
│   └── mixcoach-audio-engine/           <- Python-Backend (FastAPI)
│       ├── requirements.txt             <- NEU erzeugt (30.07.2026) für die Übertragung, siehe Abschnitt 6
│       ├── app/
│       │   ├── audio/                   <- Detektoren: track_change_classifier, foote.py (Boundary),
│       │   │                               library_match.py (Chroma-Fingerprinting), landmark_match.py
│       │   │                               (Shazam-Hashing, NUR offline nutzbar), loudness.py (LUFS),
│       │   │                               bass_overlap.py, transition_quality.py, rematch.py
│       │   ├── coach/profile.py         <- Coaching-Profil-Logik
│       │   ├── calibration/
│       │   │   ├── retrain_model.py     <- Retraining (Gradient Boosting), real-only ist Standard
│       │   │   └── auto_retrain.py      <- verfolgt neue Labels, Schwelle 10 neue Sets
│       │   └── models/track_change_gbm.json  <- AKTIVES Modell (+ mehrere .backup-Varianten)
│       ├── tools/                       <- Diagnose-/Benchmark-/Experiment-Skripte (siehe Abschnitt 4)
│       ├── tests/
│       └── dd/                          <- alte/interne Start-Skripte + Logs (start-backend.bat etc.,
│                                            NICHT mehr der Haupt-Startweg, siehe Abschnitt 6)
├── Frontend/                            <- Vite/React (TanStack Router) + Supabase
│   ├── .env                             <- Supabase-URL + "anon"-Key (öffentlich, kein Geheimnis) +
│   │                                        VITE_AUDIO_ENGINE_URL=http://127.0.0.1:8000
│   └── src/
└── daten/                               <- **AKTUELLE, MASSGEBLICHE Laufzeit-Daten** (MIXCOACH_DATA_DIR)
    ├── analysis_results/                <- alle Analyse-Reports (inkl. archived/)
    ├── ground_truth/                    <- DJ-Korrekturen/Labels (45 Dateien, Stand 30.07.) — Herzstück
    │                                        für Retrain-Qualität
    └── library/                         <- Fingerprint-Index: 6113 Tracks, fp/ (Chroma) + lm/ (Landmark)
```

**Wichtig zu wissen:**
- `audio-engine/mixcoach-audio-engine/analysis_results/`, `/ground_truth/` (24 Dateien) und `/analyses.json` im Backend-Ordner selbst sind **veraltete Kopien von vor der Migration** (17.07.2026) zu `daten/`. Die Datei `daten/ground_truth/` (45 Dateien) ist eine Obermenge und die einzige, die die laufende Engine tatsächlich liest (`MIXCOACH_DATA_DIR`). Bei Zweifel gilt `daten/` als Quelle der Wahrheit.
- `audio-engine/mixcoach-audio-engine/datasets/synthetic/` (~7,6 GB) enthält synthetische Trainings-Mixes. Seit der Entscheidung vom 28.07.2026 (Abschnitt 4) wird **synthetisches Material standardmäßig NICHT mehr fürs Training genutzt** (schadet der Precision auf echten Sets) — dieser Ordner ist für den laufenden Betrieb aktuell entbehrlich, nur für den `synth_mixer`/Landmark-Forschungszweig relevant.
- Es gibt **keine Git-Historie**. Jede größere Änderung nur über die vorhandenen `.backup`-Dateien (Modelle) rückgängig machbar — beim Löschen/Überschreiben von Dateien besonders vorsichtig sein.

---

## 3. Betriebs-/Technik-Setup (wichtig für den neuen PC)

- **Python:** Die Engine läuft NICHT über die `.venv`-Ordner im Projekt (`audio-engine/.venv`, `%LOCALAPPDATA%\MixCoach\venv` — beide sind Altlasten/kaum genutzt), sondern über eine **Microsoft-Store-Installation von Python 3.10** (`python` im PATH löst über den Windows-App-Execution-Alias dorthin auf). Dort sind alle Pakete (librosa, demucs, torch, fastapi, uvicorn, scikit-learn, lightgbm …) direkt installiert — **ohne eigenes `requirements.txt`** (war bisher nirgends dokumentiert). Für die Übertragung wurde am 30.07.2026 ein vollständiges `pip freeze` als `audio-engine/mixcoach-audio-engine/requirements.txt` erzeugt (142 Pakete).
- **Node/npm:** Node v24.14.0, npm 11.9.0 (Frontend läuft mit `npm run dev` auf Port 8080, NICHT dem Vite-Standard 5173).
- **Datenverzeichnis:** `MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten` wird von `MixCoach-Start.bat` gesetzt. Ohne diese Variable läuft die Engine mit leerem Fingerprint-Index.
- **Start:** `MixCoach-Start.bat` öffnet zwei Fenster ("MixCoach Engine", "MixCoach App") + Browser auf `/app/analyses`. Beide Fenster offen lassen, zum Beenden schließen.
- **Fallback-Falle (wichtig, siehe Abschnitt 4):** Läuft die Engine nicht, rechnet der Browser lautlos mit einer schwachen Client-Heuristik weiter, die auf sauber gemixten Sets kaum Übergänge findet. Es gibt inzwischen einen Upload-Preflight, der das verhindert (`engineReachable()`-Check vor jedem Upload) und einen roten Warnbanner bei alten Fallback-Reports.

---

## 4. Chronologie der wichtigsten technischen Erkenntnisse

### Boundary-Detection (ML-Klassifikator, wann ist ein Übergang)
Stand 10.07.: Foote-Novelty v5, LOSO Recall 91%/Precision 74%. Laut ROADMAP Ziel 80%+ Precision über mehr gelabelte Sets.

### Synth-Mixer (`tools/synth_mixer/`) — synthetische Trainings-Mixes mit exakter Ground Truth
Lange Bug-Iteration (14.07.): Overlap-Kontinuität, Vorzeichenfehler in Phasenkorrektur, fehlender Vorlauf-Puffer, Phrasen-Grenzen-Verwechslung, Stil-Kompatibilität bei Trackpaarung, Demucs-basierte Overlap-Kürzung gegen zurückkehrende Melodien/Gesangs-Überlappung. BPM-Erkennungs-Bias (librosa zieht viele Tracks auf ~120-123 BPM) im Synth-Mixer gefixt, **bewusst NICHT** im produktiven `app/audio/beats.py` (bräuchte eigenen Retrain-Pass).

### Library-Fingerprinting (Chroma) — `app/audio/library_match.py`
War schon Ende-zu-Ende verdrahtet (weiter als ROADMAP.md vermuten lässt). Messbasiert optimiert (15.07.): **Baseline Recall 0,70/Precision 0,97 → final Recall 0,90/Precision 1,0** über `SCREEN_TOP_K` 250→2000 und `MIN_SCORE` 0,40→0,30 (später 0,32, siehe unten). Bekannte strukturelle Grenze: ~10% harmonisch-statische Tracks (kaum Chroma-Varianz) bleiben unerkennbar mit reinem Chroma-Ansatz.

**Verworfene Fix-Ideen (gemessen, nicht nur vermutet):** MFCC-Timbre-Fingerprint (rettet die schwierigen Fälle nicht, Neu-Indexierung nicht gerechtfertigt), lokaler 90s-Fenster-Score (nicht trennbar von Fremd-Tracks).

### Landmark-Hashing (Shazam-Prinzip) — `app/audio/landmark_match.py`
Gebaut & gemessen (15.–16.07.): holt den extremsten harmonisch-statischen Fall (Boratto) zusätzlich, Recall 0,90→0,925 bei Precision 1,0 gehalten. **Aber: NICHT im Live-Pfad verdrahtet** — der volle (ungefilterte) Scan über 6113 Tracks kostet ~2000-2400s PRO LÜCKE. Mehrere Vorfilter-Ansätze (rohe Hash-Anzahl, Rare-Hash-Offset, Mini-Match-Subsampling, Band-Split) wurden **alle gemessen verworfen** — Tanzmusik ist zu repetitiv (Hashes wiederholen sich massiv), jede billige Näherung trennt die Zielfälle nicht zuverlässig von Fremd-Tracks. Ein echter Fix bräuchte einen invertierten Hash-Index (Architekturwechsel, eigenes Speicher-Engineering-Projekt) — als Folgeprojekt umrissen, nicht begonnen. `gap_fill()` bleibt als getestetes, aber offline-only nutzbares Werkzeug (`tools/benchmark_landmark_gapfill.py`), `pipeline.py` ruft es nicht mehr live auf (Ehrlichkeits-Prinzip: kein Feature, das entweder sehr langsam ist oder falsche Ergebnisse liefert, darf still im Live-Pfad landen).

### Segment-Zweitpass + geschätzte Lücken-Übergänge
`fill_gaps_by_segment` (17.07.) rettet Tracks, die im Voll-Set-Matching verloren gehen, aber in ihrem eigenen Zeitfenster klar gewinnen. `MIN_SCORE` dabei auf 0,32 nachgeschärft (ein realer Fehlalarm exakt auf der alten Schwelle gefunden).
Am 27.07. gelöst: Wenn zwei benannte Tracks ohne Übergangs-Marker dazwischen erscheinen (Fingerprint-Lücke >30s), wird jetzt ein Übergang in die Lücken-Mitte gesetzt mit `position_estimated=True` (+ `possible_unrecognized_track` ab 120s) statt ihn ersatzlos wegzulassen — im Frontend als "≈ Position geschätzt"-Badge sichtbar (Ehrlichkeits-Prinzip: Wechsel ist Tatsache, Position ist Schätzung, beides klar kennzeichnen).

### Feedback-getriebenes Nachmatchen (`app/audio/rematch.py`, 17.07.)
DJ-Korrekturen liefern exakte Segmentgrenzen → Re-Matching pro Segment. Endpoint `POST /analysis/{id}/rematch`, Frontend-Button "Mit meinen Korrekturen neu erkennen". Ist die konkrete Umsetzung der Vision-Datenschleife.

### Precision-Retrain-Historie — WICHTIGSTE Erkenntnis zuletzt (28.07.2026)
Mehrere Retrain-Läufe mit synthetischen Zusatzdaten (Negatives, Mixes) haben die Precision NICHT verlässlich verbessert, teils den Recall stark verschlechtert. **Sauberer LOSO-Vergleich am 28.07. auf MixCoach1-5:** real-only (24 echte Sets) R92/P55/F1 0,69 schlägt alle+Synthetik R83/P53/F1 0,65 in BEIDEN Metriken. Isoliert schadeten v.a. synthetische Negatives dem Recall stark. **Entscheidung: real-only ist jetzt STANDARD** für `run_retrain()` und `run_if_ready()` (auch für die Retrain-Automatik). Synthetik nur noch über bewussten `--with-synthetic`-Opt-in.
**Der einzige gemessen wirksame Hebel für höhere Precision bleibt: mehr echte gelabelte Sets**, nicht weiteres Tuning an vorhandenen Daten. MixCoach1 ist vermutlich unvollständig gelabelt (nur 2 Positives) und verzerrt die Precision-Messung.

### Retrain-Automatik (17.07., real-only seit 28.07.)
`app/calibration/auto_retrain.py`: zählt neue/korrigierte Ground-Truth-Dateien, Schwelle 10, startet Retrain automatisch bei genug Neuem (Gate entscheidet weiter über Export — nur besseres Modell wird aktiv). Frontend-Karte auf der Progress-Seite zeigt Fortschritt ("X von 10 neuen Sets"). Bedienung: `MixCoach-Retrain.bat` (gated) / `MixCoach-Retrain-Jetzt.bat` (sofort, real-only).

### Fallback-Falle & Upload-Preflight (17.07.)
Siehe Abschnitt 3. Drei Fixes: Backend `GET /analysis` listet gespeicherte Analysen serverseitig, Analysen-Seite bietet Import per Klick an, Fallback-Reports tragen `engine:"local"` + roten Warnbanner. Am 17.07. abends zusätzlich: **Upload-Preflight** (`engineReachable()`-Ping vor Upload, klare Fehlermeldung statt stillem Fallback), Fallback-Reports werden nicht mehr unter dem Datei-Hash gecacht.

### LUFS / Loudness-Kurve (17.07., Roadmap A3)
Energy- und Volume-Kurve waren identisch (Mapper-Bug). Fix: Pipeline liefert jetzt echte K-gewichtete Lautheitskurve, `tools/backfill_loudness_curves.py` hat alle 15 damaligen Reports nachträglich befüllt.

### Coach-Profil (16.07.)
War zu ~90% vorgebaut, einzige Lücke war das fehlende Mounten des Panels auf der Coach-Seite — behoben. Upload-Limit auf Wunsch 400→500 MB angehoben.

---

## 5. Ehrlicher Stand & nächste Schritte (Stand 28.07.2026, Sebastians Frage "wann live?")

Kernbotschaft: **Das Produkt-Erlebnis ist gut, das Produkt-Urteil noch nicht.** Teil 1 Engine — A1 Präzision ist die offene Kernlücke (~50% Fehlalarm-Rate auf schweren Sets, Timing oft zu spät), A2 Fingerprinting stark (~70-90% auf eigenen Sets), A3 Messwerte fertig, A4 Coaching verdrahtet, A5 Technik teilweise. Teil 2 Frontend weiter als gedacht (F2/F3 fertig), es fehlt F1 (Demo-Report/Onboarding) und bewusst noch F5 (Paywall). Teil 3 Online bewusst zuletzt.

> **Überholt am 30.07.2026.** Die frühere Schwelle lautete: „~15-20 gelabelte
> Sets, Precision ~75-80%, zuverlässiges Timing." Sie beruhte auf der Annahme,
> dass mehr gelabelte Sets die Precision tragen. Die Annahme ist gemessen
> widerlegt — 20 zusätzliche Sets bringen **+0,1 pp**, und die vorhandenen
> Merkmale erklären **8 % der Zeitvarianz** (`ZUKUNFTSWEGE_2026-07-30.md`).
> Die Schwelle festzuhalten hieße, den Livegang an eine Frage zu binden, die
> niemand terminieren kann. Der Absatz bleibt als Beleg stehen, gilt aber nicht
> mehr.

### Die geltende Live-Schwelle (seit 30.07.2026)

> **Live-reif ist MixCoach, wenn jeder angezeigte Wert gemessen ist, die Historie
> einen Gerätewechsel überlebt, und drei Sets desselben DJs eine Entwicklung
> sichtbar machen.**

Drei Bedingungen, alle prüfbar, keine davon abhängig von einer offenen
Forschungsfrage:

1. **Jeder angezeigte Wert ist gemessen.** Schließt `phrase_alignment_score` in
   seiner heutigen Form aus (`phrase_beats_off` ist über 0–16 Beats
   gleichverteilt) und verlangt, dass `notMeasured` auf tatsächlich fehlende
   Messungen reagiert statt eine feste Dreierliste zu führen. Das ist der
   Markenkern, in eine Abnahmebedingung übersetzt.
2. **Die Historie überlebt einen Gerätewechsel.** Heute liegt sie in
   `localStorage` (`Frontend/src/lib/store.ts:68/76`). Ohne Serverspeicherung
   kann Erlebnis-Punkt 4 nicht existieren — und der ist laut Geschäftsmodell das,
   wofür bezahlt wird.
3. **Drei Sets zeigen eine Entwicklung.** Der Beweis, dass aus Messwerten
   Coaching wird. Auf Größen, die tragen: Pegelsprung in dB, Bass-Overlap,
   LUFS-Verlauf, Tonartabstand.

Die Übergangs-Präzision bleibt ein Ziel, aber **kein Tor**. Sie läuft parallel
weiter und blockiert nichts mehr. Herleitung und Zahlenstand:
`STANDORTBESTIMMUNG_2026-07-30.md`.

**Empfohlene Reihenfolge (fortgeschrieben 10.08.2026):**

~~1. `PROMPT_K1_2026-07-30.md` abarbeiten.~~ **Erledigt am 31.07.**, Ergebnis in
`K1_AUFBAU_2026-07-31.md`, nachgemessen und zusammengeführt am 10.08. in
`SITZUNG_2026-08-10.md`. Der Ehrlichkeitsverstoß ist geräumt, der
`uint16`-Überlauf behoben, die Daten-Schleife nachgeprüft (sie trägt **halb**:
Recall ja, Precision nein), und das Messinstrument für „sekundengenau" steht
startklar.

1. **Zweite Labelrunde** (`MixCoach-Zweitrunde.command`) — wartet auf Sebastian,
   ein Abend. Entscheidet, ob „sekundengenau" in `PRODUKTVISION.md` bleiben kann.
2. **Historie aus dem Browser nach Supabase.** Höchster Hebel, reine
   Handwerksarbeit, unberührt.
3. **Messwerte füllen** — `bass_overlap_score` 67/431, `loudness_jump_db`
   214/431, `composite_quality_score` 128/431. Seit dem 10.08. ist der Grund
   belegt: alle drei hängen an der abgeschalteten Stem-Trennung
   (`STEM_SCORING_ENABLED`). **Ein Schalter blockiert drei Vision-Zusagen.**
4. Coach auf messbaren Boden stellen — nur aus Größen, die tragen.
5. Demo-Report und Teilen (F1, Erlebnis-Punkt 5).
6. Online gehen (Teil 3).

Dazu ein Einzeiler, der jederzeit fällig ist: **ein Retrain**, damit der am
10.08. erweiterte Betriebspunkt (`gap` bis 150 s statt 90 s) wirksam wird. Das
aktive Modell fährt weiter den alten.

**Nicht:** weiteres Landmark-Tuning, weitere Synth-Retrains, weitere gelabelte
Sets — alle drei Wege sind gemessen ausgereizt (Abschnitt 4 und
`ZUKUNFTSWEGE_2026-07-30.md`). Seit dem 10.08. kommt dazu: **kein weiteres
Tuning an Modell oder Merkmalen zur Precision-Steigerung.** Die Auswahl schöpft
93–95 % ihrer Orakel-Schranke aus; die Precision ist durch die Markerzahl
gedeckelt, nicht durch die Trennschärfe (`tools/eval/nms2.py`).

**Offene Kern-Lücke (nicht vergessen):** Es gibt bis heute keine systematische Genauigkeitsmessung des Fingerprint-Matchings auf echten Sets — nur Einzelfall-Diagnosen. `daten/ground_truth/` sind größtenteils ML-Grenz-Urteile (Übergang/kein Übergang), keine vollständigen Track-Identitäts-Labels. Ein echter Fingerprint-Benchmark auf realen Sets mit bekannter Tracklist wäre der nächste saubere Schritt, wenn A2 weiter verbessert werden soll — aber das ist nachrangig zu A1.

---

## 6. Diese Datei + Übertragung auf neuen PC

Am 30.07.2026 wurde eine Übertragung auf einen anderen PC vorbereitet: `PROJEKTSTAND-CLAUDE.md` (diese Datei), `audio-engine/mixcoach-audio-engine/requirements.txt` (pip freeze der echten Engine-Pakete) und `MixCoach-Backup-Erstellen.bat` (Kopier-Skript) wurden neu angelegt. Details zum Wiederherstellen: siehe `UEBERTRAGUNG-ANLEITUNG.docx` im Projekt-Root.
