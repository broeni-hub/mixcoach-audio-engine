"""Listet ALLE generierten synthetischen Uebergaenge (alle Mixes, alle
Transitions je Mix) fuer manuelles Nachhoeren+Bewerten auf - gleiches
Workflow-Muster wie labels_prefilled.csv (Excel, human_rating 1-5
nachtragen). Du entscheidest selbst, welche Zeilen du tatsaechlich
bewertest (Stichprobe nach eigenem Ermessen) - das Skript filtert nicht vor.

Aufruf (im Projektordner):
    python -m app.calibration.export_synth_mixer_sample_for_rating --dataset-dir datasets/synthetic/v1

Optional --limit-per-profile N, falls doch eine vorgefilterte Stichprobe
gewuenscht ist (Default: aus, alles wird gelistet).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path


def seconds_to_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Alle synthetischen Uebergaenge fuer manuelles Rating exportieren.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--limit-per-profile", type=int, default=None,
                        help="Optional: nur N Uebergaenge je quality_profile ziehen (Default: alle listen).")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=Path("synth_mixer_labels_prefilled.csv"))
    args = parser.parse_args()

    labels_dir = args.dataset_dir / "labels"
    mixes_dir = args.dataset_dir / "mixes"
    if not labels_dir.exists():
        print(f"FEHLER: {labels_dir} nicht gefunden.")
        return 1

    label_files = sorted(labels_dir.glob("*.json"))
    by_profile: dict[str, list[dict]] = defaultdict(list)
    n_mixes = 0
    n_transitions = 0

    for label_path in label_files:
        data = json.loads(label_path.read_text(encoding="utf-8"))
        mix_id = data["mix_id"]
        audio_path = mixes_dir / f"{mix_id}.wav"
        if not audio_path.exists():
            continue  # Label ohne zugehoerige Audio-Datei (z.B. fehlgeschlagener Mix)
        n_mixes += 1
        for t in data["transitions"]:
            n_transitions += 1
            by_profile[t["quality_profile"]].append({
                "mix_id": mix_id,
                "audio_file": str(audio_path.resolve()),
                "center_time": t["center_time"],
                "quality_profile": t["quality_profile"],
                "expected_quality_label": t["expected_quality_label"],
                "crossfade_curve": t["crossfade_curve"],
                "key_compatibility_camelot_distance": t["key_compatibility_camelot_distance"],
            })

    rows: list[dict] = []
    if args.limit_per_profile is None:
        for candidates in by_profile.values():
            rows.extend(candidates)
    else:
        rng = random.Random(args.seed)
        for candidates in by_profile.values():
            rows.extend(rng.sample(candidates, min(args.limit_per_profile, len(candidates))))

    rows.sort(key=lambda r: (r["mix_id"], r["center_time"]))

    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "mix_id", "audio_file", "center_time", "time_mmss",
            "quality_profile", "expected_quality_label",
            "human_rating", "comment",
            "crossfade_curve", "key_compatibility_camelot_distance",
        ])
        for row in rows:
            writer.writerow([
                row["mix_id"], row["audio_file"],
                f"{row['center_time']:.1f}", seconds_to_mmss(row["center_time"]),
                row["quality_profile"], row["expected_quality_label"],
                "", "",
                row["crossfade_curve"], row["key_compatibility_camelot_distance"],
            ])

    print(f"{n_mixes} Mixes mit Audio gefunden, {n_transitions} Uebergaenge insgesamt.")
    print(f"{len(rows)} Zeilen geschrieben -> {args.out}"
          + (f" (--limit-per-profile {args.limit_per_profile})" if args.limit_per_profile else " (alle, keine Vorauswahl)"))
    print("\nNaechster Schritt: CSV in Excel oeffnen, audio_file an der Stelle time_mmss")
    print("anhoeren, human_rating (1-5) eintragen (nur bei den Zeilen, die du dir")
    print("anhoerst - leere Zeilen sind kein Problem), als CSV speichern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
