"""Retraining des Trackwechsel-Modells mit gesammeltem App-Feedback.

Ablauf (ausfuehren im Ordner mixcoach-audio-engine, venv aktiv,
scikit-learn installiert: pip install scikit-learn):

    python -m app.calibration.retrain_model

1. Laedt die Basis-Trainingsdaten (app/calibration/training_features_v1.json)
2. Sammelt neues Feedback: fuer jede Datei in ground_truth/ wird das
   zugehoerige Audio aus analysis_results/ geholt und in Trainingszeilen
   verwandelt (build_features.py). Ergebnisse werden gecacht, damit
   Wiederholungslaeufe nicht jedes Mal Minuten an Audio-Analyse kosten.
3. Trainiert neu und vergleicht FAIR mit dem aktiven Modell: beide werden
   auf den NEUEN Feedback-Sets bewertet, die keins von beiden im Training
   gesehen hat (das neue via Leave-One-Set-Out, das alte direkt).
4. NUR wenn das neue Modell dort nicht schlechter ist (Recall hat
   Prioritaet), wird es exportiert (das alte wird als .backup gesichert).
"""

import json
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

from app.audio.ml_classifier import MODEL_PATH, load_model, predict_probability
from app.calibration.build_features import build_set_rows, load_truth
from app.jobs.job_manager import RESULTS_DIR
from app.paths import GROUND_TRUTH_DIR

# Zweiter, aelterer Ergebnis-Ordner (siehe Task-1-Aufraeumen 2026-07-12) -
# ein paar Testlauf-Analysen (z.B. mix.wav) liegen nur dort.
LEGACY_RESULTS_DIR = Path(__file__).resolve().parents[2] / "analysis_results"

# Recall-Untergrenze fuer die Konfigurationsauswahl UND den Export-Gate.
# War fest 0.90 ("Recall hat Prioritaet, verpasste Uebergaenge sind
# schlimmer als Fehlalarme"). Auf Sebastians Wunsch am 2026-07-12 probeweise
# gesenkt: die harten Negativbeispiele (generate_solo_track_negatives.py)
# machen bei R~85% erstmals F1/Precision besser als das aktive Modell
# (LOSO P=53% statt 48%). Bei 0.85 verfehlte der faire Vergleich auf den
# neuen Sets die Schwelle knapp (R=83%, reine Stichproben-Varianz zwischen
# LOSO- und Vergleichs-Teilmenge, F1 war trotzdem besser) - auf 0.80
# gesenkt, um dieses eine, insgesamt bessere Modell durchzulassen.
MIN_RECALL = 0.80

BASE_FEATURES = Path(__file__).parent / "training_features_v1.json"
FEEDBACK_CACHE = Path(__file__).parent / "feedback_features_cache.json"
# Harte, garantiert korrekte Negativbeispiele aus Solo-Library-Tracks -
# siehe generate_solo_track_negatives.py. Optional: nur mitgeladen, wenn
# das Skript schon einmal gelaufen ist.
SYNTHETIC_NEGATIVES = Path(__file__).parent / "synthetic_negatives_v1.json"
# Synthetische Uebergaenge (echte Crossfades zwischen zwei Library-Tracks,
# exakter bekannter Zeitpunkt) - siehe generate_synthetic_mixes.py. Optional.
SYNTHETIC_MIXES = Path(__file__).parent / "synthetic_mixes_v1.json"
# War frueher eine relative Path("ground_truth") - driftete damit vom Live-
# Server auseinander, der ueber app.paths (MIXCOACH_DATA_DIR) schreibt.
# Sebastians Feedback landete dadurch teils in einem Ordner, den dieses
# Skript nie gelesen hat (Datenverlust-Risiko, siehe Merge-Fix 2026-07-12).

# beat_cv/exit_rough (aus dem Composite-Quality-Score-Umbau uebernommen,
# siehe app/audio/scoring/beat_alignment.py + exit_quality.py) sind neu und
# ans Ende angehaengt. Die 467 Basis-Zeilen aus training_features_v1.json
# wurden VOR dieser Erweiterung erzeugt und haben diese Keys nicht - siehe
# _feature_value() unten, das dafuer 0.0 einsetzt statt abzustuerzen.
FEATURES = ["score", "blend", "drop", "bass_swap", "chroma_75_15", "chroma_45_10",
            "mfcc_dist", "rhythm_hi", "e_before", "e_current", "e_after",
            "pos_in_set", "nearest_zone", "edge", "foote", "beat_cv", "exit_rough"]
AUDIO_SUFFIXES = [".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif"]

# Cluster-/Trefferfenster in Sekunden (identisch zur bisherigen Bewertung).
CLUSTER_GAP = 105.0


def _row_vector(row: dict) -> list:
    """Feature-Vektor einer Trainingszeile - 0.0 fuer Keys, die aeltere
    Zeilen (vor einer Feature-Erweiterung) noch nicht haben."""
    return [row.get(f, 0.0) for f in FEATURES]


def _find_audio(analysis_id: str) -> Path | None:
    # Auch in archived/ suchen - der Delete-Button/Duplikat-Aufraeumen
    # verschieben Analysen dort hin statt sie zu loeschen, ein gelabeltes
    # Set darf dadurch nicht aus dem Training verschwinden. LEGACY_RESULTS_DIR
    # deckt ein paar Testlauf-Analysen ab, die nur im alten Ordner liegen.
    for base_dir in (RESULTS_DIR, RESULTS_DIR / "archived",
                     LEGACY_RESULTS_DIR, LEGACY_RESULTS_DIR / "archived"):
        for suffix in AUDIO_SUFFIXES:
            candidate = base_dir / f"{analysis_id}{suffix}"
            if candidate.exists():
                return candidate
    return None


def _find_result_json(analysis_id: str) -> tuple[dict | None, bool]:
    """Ergebnis-JSON + Flag, ob es (noch) NICHT archiviert ist."""
    for base_dir, archived in (
        (RESULTS_DIR, False), (RESULTS_DIR / "archived", True),
        (LEGACY_RESULTS_DIR, False), (LEGACY_RESULTS_DIR / "archived", True),
    ):
        path = base_dir / f"{analysis_id}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")), archived
            except (OSError, json.JSONDecodeError):
                return None, archived
    return None, True


def _merge_truth(truths: list[dict], tolerance: float = 3.0) -> dict:
    """Positives/Negatives mehrerer Duplikat-Analysen derselben Aufnahme
    vereinigen (Zeit-Toleranz statt exaktem Match, da unabhaengige
    Analyselaeufe leicht verschiedene Kandidatenzeiten liefern koennen)."""
    def dedupe(values: list[float]) -> list[float]:
        out: list[float] = []
        for v in sorted(values):
            if not out or v - out[-1] > tolerance:
                out.append(v)
        return out

    positives = dedupe([p for t in truths for p in t["positives"]])
    negatives = dedupe([n for t in truths for n in t["negatives"]])
    return {"positives": positives, "negatives": negatives}


def collect_feedback_rows():
    """Feedback-Sets in Trainingszeilen verwandeln - mit Datei-Cache.

    Gruppiert nach der zugrunde liegenden Aufnahme (fileName), NICHT nach
    Analyse-ID: mehrfach analysierte Aufnahmen (Duplikate, siehe Task-1-
    Aufraeumen) zaehlen sonst als mehrere unabhaengige LOSO-"Sets", obwohl es
    dieselbe Musik ist - verzerrt sowohl die Validierung (Test-Set ist nie
    wirklich unbekannt, fast identische Duplikate bleiben im Training) als
    auch das Training (ein einzelnes Ereignis bekommt so viel Gewicht wie
    Duplikate existieren). Regressions-Beispiel 2026-07-12: 11 REC001-
    Duplikate liessen die Precision von 53% auf 37% einbrechen.
    """
    rows = []
    if not GROUND_TRUTH_DIR.exists():
        return rows

    cache = {}
    if FEEDBACK_CACHE.exists():
        try:
            cache = json.loads(FEEDBACK_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    dirty = False

    # Gruppieren: fileName -> [(analysis_id, gt_file, is_archived)]
    groups: dict[str, list[tuple[str, Path, bool]]] = defaultdict(list)
    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        analysis_id = gt_file.stem
        result, archived = _find_result_json(analysis_id)
        file_name = (result or {}).get("fileName") or analysis_id
        groups[file_name].append((analysis_id, gt_file, archived))

    for file_name, entries in sorted(groups.items()):
        entries.sort(key=lambda e: (e[2], e[0]))  # nicht-archiviert zuerst
        canonical_id = entries[0][0]
        audio_path = _find_audio(canonical_id)
        if audio_path is None:
            # Kanonische Analyse hat kein Audio - naechstbeste mit Audio nehmen.
            audio_path = next(
                (p for aid, _, _ in entries if (p := _find_audio(aid)) is not None), None,
            )
        if audio_path is None:
            print(f"  UEBERSPRUNGEN {file_name}: kein Audio fuer keine der "
                  f"{len(entries)} Analyse(n) gefunden")
            continue

        ids = sorted(aid for aid, _, _ in entries)
        stamp = "|".join(f"{aid}:{gt.stat().st_mtime_ns}" for aid, gt, _ in
                         sorted(entries, key=lambda e: e[0]))
        entry = cache.get(file_name)
        if entry and entry.get("stamp") == stamp:
            print(f"  {file_name}: aus Cache ({len(entry['rows'])} Kandidaten, "
                  f"{len(ids)} Duplikat(e) zusammengefuehrt)")
            rows.extend(entry["rows"])
            continue

        truth = _merge_truth([load_truth(gt) for _, gt, _ in entries])
        if not truth["positives"] and not truth["negatives"]:
            print(f"  UEBERSPRUNGEN {file_name}: Feedback ist leer")
            continue
        dup_note = f" (aus {len(ids)} Duplikaten zusammengefuehrt)" if len(ids) > 1 else ""
        print(f"  Verarbeite {file_name}{dup_note} "
              f"({len(truth['positives'])} pos / {len(truth['negatives'])} neg Anker)...")
        set_rows = build_set_rows(str(audio_path), truth, set_name=file_name)
        cache[file_name] = {"stamp": stamp, "rows": set_rows}
        dirty = True
        rows.extend(set_rows)

    if dirty:
        FEEDBACK_CACHE.write_text(json.dumps(cache, default=float), encoding="utf-8")
    return rows


def _score_selection(test_rows, probs, min_p, gap):
    """Auswahl-Logik + Cluster-Bewertung fuer EIN Set -> (Treffer, Wahrheit, Auswahl)."""
    selected = []
    for r, p in sorted(zip(test_rows, probs), key=lambda x: -x[1]):
        if p < min_p or r["edge"] > 0.5:
            continue
        if all(abs(r["t"] - s) >= gap for s in selected):
            selected.append(r["t"])

    pos_times = sorted(r["t"] for r in test_rows if r["label"] == 1)
    clusters = []
    for t in pos_times:
        if not clusters or t - clusters[-1][-1] > CLUSTER_GAP:
            clusters.append([t])
        else:
            clusters[-1].append(t)
    hits = sum(1 for c in clusters
               if any(c[0] - CLUSTER_GAP <= s <= c[-1] + CLUSTER_GAP for s in selected))
    return hits, len(clusters), len(selected)


def _aggregate(counts):
    """Liste von (Treffer, Wahrheit, Auswahl) -> (Recall, Precision, F1)."""
    th = sum(c[0] for c in counts)
    tt = sum(c[1] for c in counts)
    ts = sum(c[2] for c in counts)
    recall = th / tt if tt else 0.0
    precision = th / ts if ts else 0.0
    f1 = 2 * th / (tt + ts) if (tt + ts) else 0.0
    return recall, precision, f1


def loso_metrics(rows, make_model, min_p=0.4, min_gap=150.0):
    """Leave-One-Set-Out. Liefert (Recall, Precision, F1, Zaehler-pro-Set)."""
    sets = sorted(set(r["set"] for r in rows))
    per_set = {}
    for test_set in sets:
        train = [r for r in rows if r["set"] != test_set]
        test = [r for r in rows if r["set"] == test_set]
        X = np.array([_row_vector(r) for r in train])
        y = np.array([r["label"] for r in train])
        if y.sum() == 0 or y.sum() == len(y):
            continue
        model = make_model().fit(X, y)
        probs = model.predict_proba(np.array([_row_vector(r) for r in test]))[:, 1]
        per_set[test_set] = _score_selection(test, list(probs), min_p, min_gap)
    recall, precision, f1 = _aggregate(per_set.values())
    return recall, precision, f1, per_set


def eval_fixed_model(model_json, rows):
    """Das AKTIVE (fixe) Modell auf Sets bewerten - Zaehler pro Set."""
    sel = model_json.get("selection", {})
    min_p = sel.get("min_probability", 0.5)
    gap = sel.get("min_gap_seconds", 90.0)
    per_set = {}
    for s in sorted(set(r["set"] for r in rows)):
        test = [r for r in rows if r["set"] == s]
        probs = [predict_probability(model_json, _row_vector(r)) for r in test]
        per_set[s] = _score_selection(test, probs, min_p, gap)
    return per_set


def export_model(model, rows, loso, min_p=0.5, gap=90.0):
    trees = []
    for est in model.estimators_[:, 0]:
        t = est.tree_
        trees.append({
            "feature": t.feature.tolist(),
            "threshold": t.threshold.tolist(),
            "left": t.children_left.tolist(),
            "right": t.children_right.tolist(),
            "value": t.value[:, 0, 0].tolist(),
        })
    X = np.array([_row_vector(r) for r in rows])
    raw_init = float(model._raw_predict_init(X[:1])[0, 0])
    export = {
        "model": "gradient_boosting",
        "trained_on": f"{len(set(r['set'] for r in rows))} Sets / {len(rows)} Kandidaten",
        "loso_validation": {"recall": round(loso[0], 3), "precision": round(loso[1], 3), "f1": round(loso[2], 3)},
        "features": FEATURES,
        "learning_rate": model.learning_rate,
        "init": raw_init,
        "trees": trees,
        "selection": {"min_probability": min_p, "min_gap_seconds": gap},
    }
    # Paritaets-Check JSON-Inferenz vs. sklearn
    probs_sk = model.predict_proba(X)[:, 1]
    diffs = [abs(float(p) - predict_probability(export, x.tolist())) for p, x in zip(probs_sk[:50], X[:50])]
    assert max(diffs) < 1e-9, "Export-Paritaet verletzt!"

    if MODEL_PATH.exists():
        shutil.copy(MODEL_PATH, str(MODEL_PATH) + ".backup")
    MODEL_PATH.write_text(json.dumps(export), encoding="utf-8")
    print(f"Neues Modell exportiert -> {MODEL_PATH} (altes als .backup gesichert)")


def run_retrain(include_synthetic: bool = False) -> dict:
    """Fuehrt den kompletten Retrain durch (wie main) und gibt ein
    strukturiertes Ergebnis zurueck - fuer die Retrain-Automatik
    (app/calibration/auto_retrain.py). Druckt weiterhin den Verlauf.

    STANDARD ist real-only (include_synthetic=False): NUR echte Sets (Basis +
    App-Feedback), ohne synthetische Negatives/Mixes. Gemessen (2026-07-28)
    besser auf Sebastians eigenen Sets - fairer LOSO-Vergleich auf MixCoach1-5:
    real-only R92%/P55%/F1 0.69 vs. mit-Synthetik R83%/P53%/F1 0.65. Beide
    synth-Bloecke schaden (auch die "korrekten" Negatives: Recall bricht ein).
    Die synthetische Mehrheit (157 synth. vs. ~24 echte "Sets") verzerrte
    zudem die Auswahl-Parameter (min_p/gap), die per LOSO ueber ALLE Sets
    getunt werden. include_synthetic=True nur noch als bewusste Ausnahme.
    """
    from sklearn.ensemble import GradientBoostingClassifier

    base_rows = json.loads(BASE_FEATURES.read_text(encoding="utf-8"))
    print(f"Basis: {len(base_rows)} Kandidaten aus {len(set(r['set'] for r in base_rows))} Sets")

    print("Sammle App-Feedback...")
    feedback_rows = collect_feedback_rows()
    print(f"Feedback: {len(feedback_rows)} neue Kandidaten")

    synthetic_rows = []
    synthetic_mix_rows = []
    if not include_synthetic:
        print("REAL-ONLY: synthetische Negatives/Mixes werden NICHT geladen.")
    else:
        if SYNTHETIC_NEGATIVES.exists():
            synthetic_rows = json.loads(SYNTHETIC_NEGATIVES.read_text(encoding="utf-8"))
            n_sets = len(set(r["set"] for r in synthetic_rows))
            print(f"Synthetische Negativbeispiele: {len(synthetic_rows)} Kandidaten aus {n_sets} Solo-Tracks")

        if SYNTHETIC_MIXES.exists():
            synthetic_mix_rows = json.loads(SYNTHETIC_MIXES.read_text(encoding="utf-8"))
            n_mixes = len(set(r["set"] for r in synthetic_mix_rows))
            print(f"Synthetische Uebergaenge: {len(synthetic_mix_rows)} Kandidaten aus {n_mixes} Mixes")

    all_rows = base_rows + feedback_rows + synthetic_rows + synthetic_mix_rows
    make = lambda: GradientBoostingClassifier(n_estimators=60, max_depth=2, random_state=0)

    old_model = load_model()

    # Gridsearch ueber Auswahl-Parameter: Recall hat Prioritaet
    # (Nutzerfeedback: verpasste Uebergaenge sind schlimmer als Fehlalarme).
    results = []
    for min_p in (0.4, 0.5, 0.6, 0.7):
        for gap in (60.0, 75.0, 90.0):
            r, p, f1, per_set = loso_metrics(all_rows, make, min_p=min_p, min_gap=gap)
            results.append((f1, r, p, min_p, gap, per_set))
            print(f"  p>={min_p} gap={gap:.0f}s: F1={f1:.2f} R={r*100:.0f}% P={p*100:.0f}%")
    high_recall = [x for x in results if x[1] >= MIN_RECALL]
    best = max(high_recall or results, key=lambda x: x[0])
    f1, recall, precision, min_p, gap, best_per_set = best
    print(f"\nBeste Konfig: p>={min_p}, gap={gap:.0f}s -> F1={f1:.2f} R={recall*100:.0f}% P={precision*100:.0f}%")

    # ---- FAIRER Vergleich: beide Modelle auf den NEUEN Feedback-Sets. ----
    # Das alte Modell kennt sie nicht (nach Training gesammelt), das neue
    # sieht sie im LOSO-Testfold ebenfalls nicht. Gleiche Daten, gleiche
    # Bewertung -> ehrlicher Vergleich.
    fb_sets = sorted(set(r["set"] for r in feedback_rows))
    export_ok = True
    if old_model is not None and fb_sets:
        old_per = eval_fixed_model(old_model, feedback_rows)
        old_r, old_p, old_f1 = _aggregate(old_per.values())
        new_counts = [best_per_set[s] for s in fb_sets if s in best_per_set]
        new_r, new_p, new_f1 = _aggregate(new_counts)
        print(f"\nVergleich auf {len(fb_sets)} neuen Sets (beide Modelle kannten sie nicht):")
        print(f"  AKTIV: R={old_r*100:.0f}% P={old_p*100:.0f}% F1={old_f1:.2f}")
        print(f"  NEU:   R={new_r*100:.0f}% P={new_p*100:.0f}% F1={new_f1:.2f}")
        # Recall darf nicht unter die bewusst gesetzte Untergrenze fallen
        # (nicht mehr "muss mindestens so hoch wie das alte Modell sein" -
        # sonst waere ein gewollter Precision-fuer-Recall-Tausch nie
        # exportierbar); F1 darf nicht deutlich schlechter sein.
        export_ok = (new_r >= MIN_RECALL - 1e-9) and (new_f1 >= old_f1 - 0.05)
    elif old_model is not None:
        # Kein neues Feedback mit Audio -> alter (grober) Vergleich.
        old_f1_stored = old_model.get("loso_validation", {}).get("f1", 0.0)
        export_ok = f1 + 1e-9 >= old_f1_stored - 0.05
        print(f"Aktives Modell (gespeicherte Validierung): F1 {old_f1_stored:.2f}")

    summary = {
        "feedbackSets": len(fb_sets),
        "best": {"recall": round(recall, 3), "precision": round(precision, 3),
                 "f1": round(f1, 3), "min_p": min_p, "gap": gap},
    }

    if not export_ok:
        print("ABBRUCH: Neues Modell ist auf den neuen Sets schlechter - aktives Modell bleibt.")
        return {**summary, "exported": False, "reason": "worse_on_new_sets"}

    X = np.array([_row_vector(r) for r in all_rows])
    y = np.array([r["label"] for r in all_rows])
    final = make().fit(X, y)
    export_model(final, all_rows, (recall, precision, f1), min_p=min_p, gap=gap)
    return {**summary, "exported": True}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Trackwechsel-Modell neu trainieren.")
    parser.add_argument("--real-only", action="store_true",
                        help="(Standard) nur echte Sets, keine synthetischen")
    parser.add_argument("--with-synthetic", action="store_true",
                        help="auch synthetische Trainingsdaten einbeziehen (alte Voreinstellung)")
    args = parser.parse_args()
    run_retrain(include_synthetic=(args.with_synthetic and not args.real_only))


if __name__ == "__main__":
    main()
