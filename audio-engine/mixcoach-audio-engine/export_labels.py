"""
MixCoach – Label-Export.

Fuehrt zwei Datenquellen zusammen:
  1. Analyse-Ergebnisse aus RESULTS_DIR (*.json mit transitions/phrases)
  2. Deine bisherigen Verdicts aus ground_truth/{analysis_id}.json

Erzeugt daraus:
  - labels_prefilled.csv  -> vorbefuellte Label-Tabelle (in Excel oeffnen,
                             nur noch human_rating 1-5 eintragen)
  - analyses.json         -> Input fuer die Eval-Pipeline
                             (mixcoach_eval_pipeline.py)

Logik pro Transition:
  - verdict "not_a_transition"  -> Zeile faellt raus (kein Rating noetig)
  - verdict "timing_off"        -> correctedSec wird als Zeitpunkt verwendet
  - verdict "correct" / keins   -> erkannter Zeitpunkt wird verwendet
  - "missed"-Markierungen       -> eigene Zeilen (Quelle: missed)

Aufruf (im Projektordner, dort wo auch ground_truth/ liegt):
    python export_labels.py
    python export_labels.py --results-dir results --rater sebro
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

# Feldnamen, die im Projekt vorkommen koennen (Backend vs. Frontend-Mapping)
TRANSITION_TIME_KEYS = ("center_time", "centerTime", "midSec", "mid_sec")
PHRASE_START_KEYS = ("start", "startSec", "start_sec", "startTime")
TRANSITION_LIST_KEYS = ("transitions",)
PHRASE_LIST_KEYS = ("phrases",)


def seconds_to_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def first_key(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


def find_list(result: dict, keys: tuple[str, ...]) -> list | None:
    """Sucht eine Liste erst auf oberster Ebene, dann eine Ebene tiefer
    (falls das Ergebnis z.B. unter result['analysis'] verschachtelt ist)."""
    for k in keys:
        if isinstance(result.get(k), list):
            return result[k]
    for value in result.values():
        if isinstance(value, dict):
            for k in keys:
                if isinstance(value.get(k), list):
                    return value[k]
    return None


def extract_times(items: list, keys: tuple[str, ...]) -> list[float]:
    times: list[float] = []
    for item in items:
        if isinstance(item, dict):
            v = first_key(item, keys)
            if v is not None:
                times.append(float(v))
        elif isinstance(item, (int, float)):
            times.append(float(item))
    return times


def load_result_files(results_dir: Path) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for path in sorted(results_dir.glob("*.json")):
        try:
            results[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARNUNG: {path.name} nicht lesbar ({e}) - uebersprungen.")
    return results


def load_ground_truth(gt_dir: Path, analysis_id: str) -> dict:
    path = gt_dir / f"{analysis_id}.json"
    if not path.exists():
        return {"verdicts": {}, "missed": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"verdicts": {}, "missed": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="MixCoach Label-Export")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="Ordner mit den Analyse-Ergebnis-JSONs "
                             "(RESULTS_DIR des job_managers)")
    parser.add_argument("--ground-truth-dir", type=Path,
                        default=Path("ground_truth"),
                        help="Ordner mit den Feedback-JSONs")
    parser.add_argument("--rater", default="", help="Name fuer die rater-Spalte")
    parser.add_argument("--out-csv", type=Path,
                        default=Path("labels_prefilled.csv"))
    parser.add_argument("--out-analyses", type=Path,
                        default=Path("analyses.json"))
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"FEHLER: Ergebnis-Ordner '{args.results_dir}' nicht gefunden.")
        print("Mit --results-dir den richtigen Pfad angeben "
              "(der Ordner, in dem die {analysis_id}.json-Dateien liegen).")
        return 1

    results = load_result_files(args.results_dir)
    if not results:
        print(f"FEHLER: Keine JSON-Dateien in '{args.results_dir}' gefunden.")
        return 1

    if args.out_csv.exists():
        print(f"ABBRUCH: {args.out_csv} existiert bereits - nicht "
              f"ueberschrieben, damit keine eingetragenen Labels verloren gehen.")
        return 1

    analyses_export: dict[str, dict] = {}
    rows: list[list] = []
    skipped_not_transition = 0
    unrecognized: list[str] = []

    for analysis_id, result in results.items():
        transitions_raw = find_list(result, TRANSITION_LIST_KEYS)
        phrases_raw = find_list(result, PHRASE_LIST_KEYS)

        if transitions_raw is None:
            unrecognized.append(analysis_id)
            continue

        t_times = extract_times(transitions_raw, TRANSITION_TIME_KEYS)
        p_times = extract_times(phrases_raw or [], PHRASE_START_KEYS)

        file_name = result.get("fileName") or result.get("filename") or ""
        gt = load_ground_truth(args.ground_truth_dir, analysis_id)
        verdicts: dict = gt.get("verdicts", {})

        export_transitions: list[dict] = []

        for idx, t in enumerate(t_times):
            verdict_entry = verdicts.get(str(idx), {})
            verdict = verdict_entry.get("verdict", "")

            if verdict == "not_a_transition":
                skipped_not_transition += 1
                continue

            # Bei timing_off die vom DJ korrigierte Zeit verwenden
            time_used = t
            note = verdict
            if verdict == "timing_off" and verdict_entry.get("correctedSec") is not None:
                time_used = float(verdict_entry["correctedSec"])
                note = f"timing_off (Engine: {t:.1f}s -> korrigiert)"

            export_transitions.append({"center_time": time_used})
            rows.append([
                analysis_id, file_name, f"{time_used:.1f}",
                "",  # human_rating -> ausfuellen
                args.rater,
                note,  # Verdict als Kontext vorgetragen
                "",  # comment -> ausfuellen
                seconds_to_mmss(time_used),
                "erkannt",
            ])

        # Vom DJ markierte, von der Engine verpasste Uebergaenge
        for sec in gt.get("missed", []):
            sec = float(sec)
            export_transitions.append({"center_time": sec})
            rows.append([
                analysis_id, file_name, f"{sec:.1f}",
                "", args.rater, "missed (von dir markiert)", "",
                seconds_to_mmss(sec), "missed",
            ])

        analyses_export[analysis_id] = {
            "transitions": export_transitions,
            "phrases": [{"start": p} for p in p_times],
        }

    # --- CSV schreiben ---
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "set_id", "file_name", "transition_center_time",
            "human_rating", "rater", "verdict_info", "comment",
            "time_mmss", "quelle",
        ])
        writer.writerows(rows)

    args.out_analyses.write_text(
        json.dumps(analyses_export, indent=2), encoding="utf-8"
    )

    # --- Zusammenfassung ---
    print(f"Fertig.")
    print(f"  Sets verarbeitet:            {len(analyses_export)}")
    print(f"  Zeilen in {args.out_csv}: {len(rows)}")
    print(f"  Uebersprungen (not_a_transition): {skipped_not_transition}")
    print(f"  Eval-Input geschrieben:      {args.out_analyses}")
    if unrecognized:
        print(f"\nACHTUNG: Bei {len(unrecognized)} Datei(en) wurde keine "
              f"transitions-Liste gefunden:")
        for aid in unrecognized[:5]:
            print(f"  - {aid}.json")
        print("Bitte den Anfang einer dieser Dateien in den Chat kopieren, "
              "dann passe ich die Feldnamen an.")
    print(f"\nNaechster Schritt: {args.out_csv} in Excel oeffnen und "
          f"human_rating (1-5) eintragen. Beim Speichern CSV-Format behalten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
