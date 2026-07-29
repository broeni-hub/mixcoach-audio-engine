"""
MixCoach – Label-Export v3: liest Ergebnis-JSONs UND ground_truth-only Sets.

Liest die Ergebnis-JSONs (Format "honest-v2" mit setTransitions) und die
Ground-Truth-Verdicts, erzeugt:
  - labels_prefilled.csv  -> vorbefuellte Label-Tabelle fuer Excel
  - analyses.json         -> Input fuer die Eval-Pipeline

Aufruf (im Projektordner):
    python export_labels_v3.py --results-dir analysis_results --rater sebro
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def seconds_to_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def get_transition_time(t: dict) -> float | None:
    for key in ("mid_sec", "midSec", "center_time", "centerTime"):
        if t.get(key) is not None:
            return float(t[key])
    return None


def beats_to_seconds(beats: float | None, bpm: float | None) -> float | None:
    if beats is None or not bpm:
        return None
    return abs(beats) * 60.0 / float(bpm)


def load_ground_truth(gt_dir: Path, analysis_id: str) -> dict:
    path = gt_dir / f"{analysis_id}.json"
    if not path.exists():
        return {"verdicts": {}, "missed": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"verdicts": {}, "missed": []}


def match_verdict(verdicts: dict, mid_sec: float, tolerance: float = 5.0) -> dict:
    """Verdict zum Uebergang finden - robust ueber die Zeit, nicht den Index."""
    best, best_diff = {}, tolerance
    for entry in verdicts.values():
        v_sec = entry.get("midSec")
        if v_sec is None:
            continue
        diff = abs(float(v_sec) - mid_sec)
        if diff <= best_diff:
            best, best_diff = entry, diff
    return best


def csv_is_empty(path: Path) -> bool:
    """True, wenn Datei fehlt oder nur eine Kopfzeile enthaelt."""
    if not path.exists():
        return True
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return len(rows) <= 1


def main() -> int:
    parser = argparse.ArgumentParser(description="MixCoach Label-Export v2")
    parser.add_argument("--results-dir", type=Path, default=Path("analysis_results"))
    parser.add_argument("--ground-truth-dir", type=Path, default=Path("ground_truth"))
    parser.add_argument("--rater", default="")
    parser.add_argument("--out-csv", type=Path, default=Path("labels_prefilled.csv"))
    parser.add_argument("--out-analyses", type=Path, default=Path("analyses.json"))
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"FEHLER: Ordner '{args.results_dir}' nicht gefunden.")
        return 1

    if not csv_is_empty(args.out_csv):
        print(f"ABBRUCH: {args.out_csv} enthaelt bereits Daten - nicht "
              f"ueberschrieben, damit keine eingetragenen Labels verloren gehen.")
        print("Datei umbenennen oder mit --out-csv anderen Namen angeben.")
        return 1

    analyses_export: dict[str, dict] = {}
    rows: list[list] = []
    skipped = 0
    unrecognized: list[str] = []

    for path in sorted(args.results_dir.glob("*.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARNUNG: {path.name} nicht lesbar ({e}) - uebersprungen.")
            continue

        analysis_id = result.get("id", path.stem)
        file_name = result.get("fileName") or result.get("filename") or ""
        transitions = result.get("setTransitions") or result.get("transitions")

        if not isinstance(transitions, list):
            unrecognized.append(path.name)
            continue

        gt = load_ground_truth(args.ground_truth_dir, analysis_id)
        verdicts: dict = gt.get("verdicts", {})
        export_transitions: list[dict] = []

        for t in transitions:
            if not isinstance(t, dict):
                continue
            mid = get_transition_time(t)
            if mid is None:
                continue

            verdict_entry = match_verdict(verdicts, mid)
            verdict = verdict_entry.get("verdict", "")

            if verdict == "not_a_transition":
                skipped += 1
                continue

            time_used = mid
            verdict_info = verdict
            if verdict == "timing_off" and verdict_entry.get("correctedSec") is not None:
                time_used = float(verdict_entry["correctedSec"])
                verdict_info = f"timing_off (Engine: {mid:.1f}s -> korrigiert)"

            beats_off = t.get("phrase_beats_off")
            bpm = t.get("bpm_before") or result.get("bpm")
            diff_sec = beats_to_seconds(beats_off, bpm)

            export_transitions.append({
                "center_time": time_used,
                "diff_seconds": round(diff_sec, 2) if diff_sec is not None else None,
                "phrase_beats_off": beats_off,
                "engine_quality_score": t.get("quality_score"),
                "engine_alignment_score": t.get("phrase_alignment_score"),
            })

            rows.append([
                analysis_id, file_name, f"{time_used:.1f}",
                "",  # human_rating -> ausfuellen
                args.rater,
                verdict_info,
                t.get("quality_score", ""),
                beats_off if beats_off is not None else "",
                t.get("label", ""),
                "",  # comment -> ausfuellen
                seconds_to_mmss(time_used),
                "erkannt",
            ])

        for sec in gt.get("missed", []):
            sec = float(sec)
            export_transitions.append({
                "center_time": sec, "diff_seconds": None,
                "phrase_beats_off": None,
                "engine_quality_score": None, "engine_alignment_score": None,
            })
            rows.append([
                analysis_id, file_name, f"{sec:.1f}",
                "", args.rater, "missed (von dir markiert)",
                "", "", "", "", seconds_to_mmss(sec), "missed",
            ])

        analyses_export[analysis_id] = {
            "fileName": file_name,
            "transitions": export_transitions,
        }

    # ------------------------------------------------------------------
    # Sets, die NUR in ground_truth existieren (Ergebnis-JSON fehlt):
    # Zeiten kommen direkt aus den Verdicts/Missed-Markierungen.
    # ------------------------------------------------------------------
    gt_only_count = 0
    if args.ground_truth_dir.exists():
        for gt_path in sorted(args.ground_truth_dir.glob("*.json")):
            analysis_id = gt_path.stem
            if analysis_id in analyses_export:
                continue
            gt = load_ground_truth(args.ground_truth_dir, analysis_id)
            verdicts = gt.get("verdicts", {})
            missed = gt.get("missed", [])
            if not verdicts and not missed:
                continue

            gt_only_count += 1
            export_transitions = []

            for entry in verdicts.values():
                verdict = entry.get("verdict", "")
                if verdict == "not_a_transition":
                    skipped += 1
                    continue
                mid = entry.get("midSec")
                if mid is None:
                    continue
                time_used = float(mid)
                verdict_info = verdict
                if verdict == "timing_off" and entry.get("correctedSec") is not None:
                    time_used = float(entry["correctedSec"])
                    verdict_info = f"timing_off (Engine: {float(mid):.1f}s -> korrigiert)"
                export_transitions.append({
                    "center_time": time_used, "diff_seconds": None,
                    "phrase_beats_off": None,
                    "engine_quality_score": None, "engine_alignment_score": None,
                })
                rows.append([
                    analysis_id, "(Ergebnis-JSON fehlt)", f"{time_used:.1f}",
                    "", args.rater, verdict_info, "", "", "",
                    "", seconds_to_mmss(time_used), "nur_ground_truth",
                ])

            for sec in missed:
                sec = float(sec)
                export_transitions.append({
                    "center_time": sec, "diff_seconds": None,
                    "phrase_beats_off": None,
                    "engine_quality_score": None, "engine_alignment_score": None,
                })
                rows.append([
                    analysis_id, "(Ergebnis-JSON fehlt)", f"{sec:.1f}",
                    "", args.rater, "missed (von dir markiert)",
                    "", "", "", "", seconds_to_mmss(sec), "missed",
                ])

            analyses_export[analysis_id] = {
                "fileName": "(Ergebnis-JSON fehlt)",
                "transitions": export_transitions,
            }

    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "set_id", "file_name", "transition_center_time",
            "human_rating", "rater", "verdict_info",
            "engine_quality_score", "phrase_beats_off", "engine_label",
            "comment", "time_mmss", "quelle",
        ])
        writer.writerows(rows)

    args.out_analyses.write_text(
        json.dumps(analyses_export, indent=2), encoding="utf-8"
    )

    print("Fertig.")
    print(f"  Sets verarbeitet:               {len(analyses_export)}")
    print(f"  Zeilen in {args.out_csv}:  {len(rows)}")
    print(f"  Uebersprungen (not_a_transition): {skipped}")
    print(f"  Eval-Input geschrieben:         {args.out_analyses}")
    if gt_only_count:
        print(f"  Sets NUR aus ground_truth:      {gt_only_count} "
              f"(Ergebnis-JSON fehlt - Zeiten aus deinen Verdicts uebernommen)")
    if unrecognized:
        print(f"\nACHTUNG: Keine Transition-Liste gefunden in:")
        for name in unrecognized:
            print(f"  - {name}")
    print(f"\nNaechster Schritt: {args.out_csv} in Excel oeffnen, "
          f"human_rating (1-5) und comment ausfuellen. Als CSV speichern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
