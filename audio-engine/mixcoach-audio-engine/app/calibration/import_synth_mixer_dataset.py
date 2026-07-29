"""Bruecke zwischen tools/synth_mixer (Mix-WAV + Label-JSON pro generiertem
Mix) und retrain_model.py (erwartet Trainingszeilen im build_set_rows-
Format, siehe app/calibration/build_features.py).

Nutzt fuer jeden Mix EXAKT dieselbe Feature-Extraktion wie echte Sets und
die Solo-Track-Negativbeispiele - kein Train/Serve-Drift. Jeder Uebergang
im Label wird zum positiven Anker (center_time); quality_profile/
expected_quality_label werden hier NICHT verwendet (die sind fuer den
Composite-Quality-Score gedacht, nicht fuer die Trackwechsel-Erkennung) -
jeder generierte Uebergang ist ein echter Trackwechsel, unabhaengig von
seiner Qualitaet.

Aufruf (im Projektordner):
    python -m app.calibration.import_synth_mixer_dataset --dataset-dir datasets/synthetic/v1
    python -m app.calibration.import_synth_mixer_dataset --dataset-dir datasets/synthetic/v1 --limit 40

--limit verarbeitet nur die ersten N Mixes (sortiert nach mix_id) - fuer
Mischungsverhaeltnis-Experimente (wie viele synthetische Mixes im Verhaeltnis
zu echten Feedback-Sets). Ergebnisse pro Mix werden gecacht (Datei-mtime),
damit ein --limit 40 nach einem --limit 159 nicht alles neu rechnet.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_OUT = Path(__file__).parent / "synthetic_mixes_v1.json"
ROW_CACHE = Path(__file__).parent / "synth_mixer_row_cache.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="tools/synth_mixer-Dataset in Trainingszeilen umwandeln.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None,
                        help="Nur die ersten N Mixes (sortiert nach mix_id) verwenden.")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Projektordner fuer `tools.*`
    from app.calibration.build_features import build_set_rows
    from tools.synth_mixer.dataset_loader import SyntheticDataset

    dataset = SyntheticDataset(args.dataset_dir)
    entries = sorted(dataset, key=lambda e: e.mix_id)
    if args.limit is not None:
        entries = entries[:args.limit]
    print(f"{len(entries)} von {len(dataset)} Mix/Label-Paaren in {args.dataset_dir} verwendet"
          f"{f' (--limit {args.limit})' if args.limit is not None else ''}.")
    if not entries:
        print("FEHLER: keine Mixes gefunden - erst tools.synth_mixer.cli generate laufen lassen.")
        return 1

    cache = {}
    if ROW_CACHE.exists():
        try:
            cache = json.loads(ROW_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    dirty = False

    all_rows = []
    ok, failed, cached = 0, 0, 0

    for entry in entries:
        stamp = str(entry.audio_path.stat().st_mtime_ns)
        hit = cache.get(entry.mix_id)
        if hit and hit.get("stamp") == stamp:
            all_rows.extend(hit["rows"])
            cached += 1
            continue

        t0 = time.time()
        try:
            waveform, sr = entry.load_audio()
            positives = [t.center_time for t in entry.label.transitions]
            truth = {"positives": positives, "negatives": []}
            rows = build_set_rows(str(entry.audio_path), truth, set_name=entry.mix_id, waveform=waveform)
        except Exception as e:
            print(f"  {entry.mix_id}: FEHLER ({e})")
            failed += 1
            continue
        all_rows.extend(rows)
        cache[entry.mix_id] = {"stamp": stamp, "rows": rows}
        dirty = True
        ok += 1
        print(f"  {entry.mix_id}: {len(positives)} Uebergaenge, {len(rows)} Kandidaten "
              f"({time.time() - t0:.0f}s)")

    if dirty:
        ROW_CACHE.write_text(json.dumps(cache, default=float), encoding="utf-8")

    args.out.write_text(json.dumps(all_rows), encoding="utf-8")
    print(f"\n{ok} neu verarbeitet, {cached} aus Cache, {failed} fehlgeschlagen.")
    print(f"{len(all_rows)} Trainings-Kandidaten geschrieben -> {args.out}")
    print("\nNaechster Schritt: python -m app.calibration.retrain_model "
          "(laedt SYNTHETIC_MIXES automatisch mit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
