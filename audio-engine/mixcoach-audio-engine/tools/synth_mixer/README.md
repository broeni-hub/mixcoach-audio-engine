# synth_mixer

Generiert synthetische DJ-Mixes aus einem Track-Pool, mit exakter,
maschinell erzeugter Ground Truth (Uebergangs-Zeitpunkte + Parameter) - fuer
das Training/Testen der Transition-Detection, ohne jeden Uebergang von Hand
labeln zu muessen.

## Aufruf

```
python -m tools.synth_mixer.cli generate ^
    --tracks-dir C:\Users\Sebro\Music ^
    --out-dir .\datasets\synthetic\v1 ^
    --num-mixes 200 --tracks-per-mix 4-8 --seed 42 ^
    --genres house,electro ^
    --profile-distribution clean=0.5,off_phrase=0.1,off_beat=0.1,key_clash=0.1,abrupt=0.1,train_wreck=0.1
```

Erzeugt pro Mix eine WAV-Datei (`<out_dir>/mixes/<mix_id>.wav`) und ein
Label-JSON (`<out_dir>/labels/<mix_id>.json`, Schema siehe `schema.py`).
Ein `manifest.json` im `out_dir` haelt alle Generierungs-Parameter fest -
bei gleichem `--seed` ist der Lauf reproduzierbar. Bereits vorhandene
`mix_id`s werden uebersprungen (Resume-faehig).

`--genres` filtert nach Ordner-Substring (case-insensitive) relativ zu
`--tracks-dir`, z.B. `house,funk,electro`.

## Module

- `config.py` - alle Parameter-Ranges/Presets an einem Ort.
- `track_prep.py` - BPM/Beat-Grid, Downbeats, Phrasen-Raster (8/16/32 Bars),
  Tonart (Krumhansl via bestehendem `app.audio.segment_keys`), RMS-Kurve.
  Cached als `<track>.analysis.json` neben der Audiodatei.
- `transitions.py` - Crossfade-Kurven (linear/equal_power/exponential/
  s_curve), Cut, EQ-Blend (Bass-Swap), Quality-Profile-Parameter,
  deterministische `expected_quality_label`-Zuordnung (Tabelle im Docstring
  von `expected_quality_label`).
- `generator.py` - baut Trackketten (BPM-Kompatibilitaet, Camelot-Distanz
  fuer key_clash/train_wreck) und rendert den Mix segmentweise.
- `cli.py` - Kommandozeilen-Interface, Resume, Manifest.
- `schema.py` - pydantic-Label-Schema (`MixLabel`, `TrackEntry`,
  `TransitionEntry`).
- `dataset_loader.py` - Anbindungspunkt fuer eine Eval-Pipeline.

## Anbindung an eine Eval-Pipeline

`mixcoach_eval_pipeline.py` existiert im Projekt noch nicht (Stand
2026-07-12) - es gibt also aktuell keine bestehenden Feldnamen, an die sich
`schema.py` haette anpassen muessen. Sobald diese Pipeline gebaut wird:

```python
from tools.synth_mixer.dataset_loader import SyntheticDataset

dataset = SyntheticDataset(Path("datasets/synthetic/v1"))
for entry in dataset:
    waveform, sample_rate = entry.load_audio()
    # entry.label.transitions -> Liste von TransitionEntry mit center_time,
    # expected_quality_label, quality_profile etc. als Ground Truth.
```

`SyntheticDataset` iteriert ueber alle vorhandenen Mix/Label-Paare, validiert
jedes Label per pydantic beim Laden und laedt Audio erst bei Bedarf.

## Bekannte Grenzen

- Deckt keine echten Live-Fader-Bewegungen, Loops, Scratches, FX ab -
  ergaenzt "Stufe 2" (echte Mixes + Fingerprint-Alignment), ersetzt sie nicht.
- Tempo-Angleichung nutzt `pyrubberband`, falls installiert, sonst
  `librosa.effects.time_stretch` (Fallback wird pro Track im Label als
  `stretch_method` vermerkt). Trackpaare mit noetigem Stretch > 8% werden
  beim Kettenbau verworfen, nicht erzwungen.
- mp3-Export ist in `cli.py` als Option vorgesehen, aber noch nicht
  verdrahtet (kein Encoder eingebunden) - faellt aktuell immer auf WAV
  zurueck, mit Hinweis auf der Konsole.
