"""Composite-Score-Gewichte gegen labels_prefilled.csv fitten.

Sucht die Gewichte (harmonic_clash, vocal_overlap, exit_quality,
beat_alignment, phrase_timing), die composite_quality_score am staerksten
mit Sebastians menschlichen Bewertungen (human_rating, 1-5) korrelieren -
Spearman (Rang-Korrelation), robust gegen die Skalen-Differenz zwischen
1-5-Sternen und 0-100-Score.

Ablauf:
  1. Liest labels_prefilled.csv (nur Zeilen mit ausgefuelltem human_rating).
  2. Laedt pro Zeile die passende analysis_results/{set_id}.json - auch aus
     analysis_results/archived/, falls die Analyse zwischenzeitlich
     archiviert wurde (Delete-Button/Duplikat-Aufraeumen loeschen nichts
     hart) - und sucht darin den Uebergang, dessen mid_sec am naechsten an
     transition_center_time liegt. Toleranz grosszuegiger als in
     export_labels_v3.py, weil transition_center_time bei "timing_off"-
     Verdicts der KORRIGIERTE Zeitpunkt ist, nicht der rohe Engine-Wert.
  3. Nur Uebergaenge mit vorhandenem composite_breakdown zaehlen - das gibt
     es erst fuer Analysen, die NACH dem Composite-Score-Umbau gelaufen
     sind. Aeltere Analysen muessten dafuer neu analysiert werden.
  4. Zufallssuche (viele zufaellige Gewichte auf dem Simplex) + lokale
     Verfeinerung der besten Kandidaten, auf einem Trainings-Split gefittet
     und auf einem unabhaengigen Test-Split validiert - damit die
     gefundenen Gewichte nicht nur auf den Trainingsdaten gut aussehen.

Aufruf (im Projektordner):
    python -m app.calibration.fit_composite_weights
    python -m app.calibration.fit_composite_weights --labels-csv labels_prefilled.csv --results-dir analysis_results
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scipy.stats import spearmanr

from app.paths import RESULTS_DIR

DIMENSIONS = ["harmonic_clash", "vocal_overlap", "exit_quality", "beat_alignment", "phrase_timing"]
MATCH_TOLERANCE_SECONDS = 15.0
N_RANDOM_SAMPLES = 4000
N_REFINE_ROUNDS = 300
TEST_FRACTION = 0.3
RANDOM_SEED = 42
MIN_EXAMPLES = 20

Example = Tuple[Dict[str, Optional[float]], float, Optional[float]]  # (dim_scores, rating, old_quality_score)


def _find_result_json(results_dir: Path, set_id: str) -> Optional[Path]:
    direct = results_dir / f"{set_id}.json"
    if direct.exists():
        return direct
    archived = results_dir / "archived" / f"{set_id}.json"
    if archived.exists():
        return archived
    return None


def _load_transitions(path: Path) -> List[Dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    transitions = data.get("setTransitions") or data.get("transitions") or []
    return [t for t in transitions if isinstance(t, dict)]


def _closest_transition(transitions: List[Dict], target_time: float) -> Optional[Dict]:
    best, best_diff = None, MATCH_TOLERANCE_SECONDS
    for t in transitions:
        mid = t.get("mid_sec")
        if mid is None:
            continue
        diff = abs(float(mid) - target_time)
        if diff <= best_diff:
            best, best_diff = t, diff
    return best


def _read_csv_text(path: Path) -> str:
    """Excel speichert CSVs beim Nachbearbeiten oft als Windows-1252 statt
    UTF-8 um (z.B. durch Umlaute in Kommentaren wie 'Türkiye') - robust
    gegen beide Faelle statt hart abzubrechen."""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_training_examples(labels_csv: Path, results_dir: Path) -> List[Example]:
    examples: List[Example] = []
    json_cache: Dict[str, List[Dict]] = {}
    skipped_no_json = 0
    skipped_no_match = 0
    skipped_no_breakdown = 0

    text = _read_csv_text(labels_csv)
    reader = csv.DictReader(text.splitlines(), delimiter=";")
    for row in reader:
        rating_raw = (row.get("human_rating") or "").strip()
        if not rating_raw:
            continue
        try:
            rating = float(rating_raw)
        except ValueError:
            continue

        set_id = row.get("set_id") or ""
        if set_id not in json_cache:
            path = _find_result_json(results_dir, set_id)
            json_cache[set_id] = _load_transitions(path) if path else []
        transitions = json_cache[set_id]
        if not transitions:
            skipped_no_json += 1
            continue

        try:
            target_time = float(row["transition_center_time"])
        except (KeyError, ValueError, TypeError):
            continue

        match = _closest_transition(transitions, target_time)
        if match is None:
            skipped_no_match += 1
            continue

        breakdown = match.get("composite_breakdown")
        if not breakdown or all(breakdown.get(d) is None for d in DIMENSIONS):
            skipped_no_breakdown += 1
            continue

        scores = {dim: breakdown.get(dim) for dim in DIMENSIONS}
        examples.append((scores, rating, match.get("quality_score")))

    print(f"Geladen: {len(examples)} Uebergaenge mit Bewertung + Composite-Scores.")
    if skipped_no_json:
        print(f"  Uebersprungen (Ergebnis-JSON fehlt, auch nicht in archived/): {skipped_no_json}")
    if skipped_no_match:
        print(f"  Uebersprungen (kein Uebergang innerhalb {MATCH_TOLERANCE_SECONDS:.0f}s gefunden): {skipped_no_match}")
    if skipped_no_breakdown:
        print(f"  Uebersprungen (Analyse lief vor dem Composite-Score-Umbau, kein composite_breakdown): {skipped_no_breakdown}")
    return examples


def _composite(scores: Dict[str, Optional[float]], weights: Dict[str, float]) -> Optional[float]:
    available = [(scores[d], weights[d]) for d in DIMENSIONS if scores.get(d) is not None and weights.get(d, 0) > 0]
    if not available:
        return None
    total_weight = sum(w for _, w in available)
    if total_weight <= 0:
        return None
    return sum(s * w for s, w in available) / total_weight


def _spearman_for_weights(examples: List[Example], weights: Dict[str, float]) -> Optional[float]:
    predicted, actual = [], []
    for scores, rating, _ in examples:
        c = _composite(scores, weights)
        if c is None:
            continue
        predicted.append(c)
        actual.append(rating)
    if len(predicted) < 5:
        return None
    corr, _ = spearmanr(predicted, actual)
    return corr if corr == corr else None  # NaN-Schutz (z.B. konstante Werte bei zu wenig Streuung)


def _random_weights(rng: random.Random) -> Dict[str, float]:
    raw = [rng.random() for _ in DIMENSIONS]
    total = sum(raw) or 1.0
    return {dim: v / total for dim, v in zip(DIMENSIONS, raw)}


def _perturb(weights: Dict[str, float], rng: random.Random, scale: float = 0.15) -> Dict[str, float]:
    raw = {dim: max(0.0, w + rng.uniform(-scale, scale)) for dim, w in weights.items()}
    total = sum(raw.values()) or 1.0
    return {dim: v / total for dim, v in raw.items()}


def fit_weights(examples: List[Example], seed: int = RANDOM_SEED):
    rng = random.Random(seed)
    shuffled = examples[:]
    rng.shuffle(shuffled)
    split = max(1, int(len(shuffled) * (1 - TEST_FRACTION)))
    train, test = shuffled[:split], shuffled[split:]

    best_weights, best_train_corr = _random_weights(rng), -2.0
    for _ in range(N_RANDOM_SAMPLES):
        w = _random_weights(rng)
        corr = _spearman_for_weights(train, w)
        if corr is not None and corr > best_train_corr:
            best_weights, best_train_corr = w, corr

    for _ in range(N_REFINE_ROUNDS):
        candidate = _perturb(best_weights, rng)
        corr = _spearman_for_weights(train, candidate)
        if corr is not None and corr > best_train_corr:
            best_weights, best_train_corr = candidate, corr

    test_corr = _spearman_for_weights(test, best_weights)
    return best_weights, best_train_corr, test_corr, len(train), len(test)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fittet Composite-Score-Gewichte gegen labels_prefilled.csv.")
    parser.add_argument("--labels-csv", type=Path, default=Path("labels_prefilled.csv"))
    # Vorgabe war bis 11.08.2026 das relative "analysis_results" - und das ist
    # im Engine-Ordner die VERALTETE Kopie von vor der Migration (CLAUDE.md).
    # Das Skript las damit einen Stand von vor dem 17.07., fand keine
    # composite_breakdowns und meldete "vorhandene Sets muessten neu analysiert
    # werden" - obwohl im echten Datenstamm alles vorlag. Eine Fehlmeldung, die
    # nach einem Datenproblem aussieht und keines ist. Jetzt derselbe Weg wie
    # ueberall sonst: app/paths.py, gesteuert ueber MIXCOACH_DATA_DIR.
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    if not args.labels_csv.exists():
        print(f"FEHLER: {args.labels_csv} nicht gefunden.")
        return 1
    if not args.results_dir.exists():
        print(f"FEHLER: {args.results_dir} nicht gefunden.")
        return 1

    examples = load_training_examples(args.labels_csv, args.results_dir)
    if len(examples) < MIN_EXAMPLES:
        print(f"\nZu wenige gelabelte Uebergaenge mit Composite-Scores (< {MIN_EXAMPLES}).")
        print("Composite-Scores gibt es erst fuer Analysen, die NACH dem Scoring-Umbau")
        print("gelaufen sind - vorhandene Sets muessen dafuer neu analysiert werden.")
        return 1

    # Alter engine_quality_score direkt gegen human_rating - der Vergleichswert,
    # den der ganze Umbau verbessern soll (Ausgangslage laut Sebastian: ~0).
    old_predicted = [q for _, _, q in examples if q is not None]
    old_actual = [r for _, r, q in examples if q is not None]
    if len(old_predicted) >= 5:
        old_corr, _ = spearmanr(old_predicted, old_actual)
    else:
        old_corr = None

    weights, train_corr, test_corr, n_train, n_test = fit_weights(examples)

    print(f"\nTrainings-Set: {n_train} Uebergaenge, Test-Set: {n_test} Uebergaenge.")
    if old_corr is not None:
        print(f"Alter quality_score vs. human_rating (Ausgangslage):  {old_corr:.3f}")
    print(f"Neuer composite_quality_score, Training:                {train_corr:.3f}")
    print("Neuer composite_quality_score, Test (unabhaengig):      "
          + (f"{test_corr:.3f}" if test_corr is not None else "(zu wenige Testfaelle)"))

    print("\nGefittete Gewichte:")
    for dim, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        print(f"  {dim:16s} {w:.3f}")

    print("\nZum Uebernehmen: DEFAULT_WEIGHTS in app/audio/scoring/composite.py")
    print("mit den obigen Werten ersetzen (Summe muss nicht exakt 1 sein - wird")
    print("beim Scoring automatisch normiert).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
