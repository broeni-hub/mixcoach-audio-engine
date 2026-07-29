"""Retrain-Automatik: startet den Modell-Retrain automatisch, sobald genug
NEUES Feedback vorliegt - damit Sebastians Label-Arbeit maximal wirkt, ohne
dass er einen Befehl tippen muss.

Prinzip:
  - Jede gelabelte Aufnahme (ground_truth/<id>.json) + ihr Aenderungszeit-
    punkt wird verfolgt. Neu ODER geaenderte Labels (z.B. nachtraegliche
    "Startet woanders"-Korrekturen) zaehlen als neues Trainingssignal.
  - Ab RETRAIN_THRESHOLD neuen/geaenderten Sets wird retrain_model
    ausgeloest. Das eingebaute Sicherheits-Gate dort entscheidet, ob das
    neue Modell wirklich besser ist - die Automatik faellt nie ein Modell
    ohne diese Pruefung.
  - Nach einem Lauf wird der Zustand fortgeschrieben (was war dabei), damit
    nicht dieselben Sets erneut zaehlen.

Status (count_new_sets) speist auch die App-Anzeige "X von N bis zum
naechsten Auto-Retrain".

Aufruf:
    python -m app.calibration.auto_retrain            # laeuft, wenn genug neu
    python -m app.calibration.auto_retrain --status   # nur zeigen, nicht laufen
    python -m app.calibration.auto_retrain --force     # jetzt, egal wie viel neu
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.audio.ml_classifier import MODEL_PATH, load_model
from app.paths import GROUND_TRUTH_DIR

# Roadmap A1: "Ab ~10 weiteren Sets mit Audio lohnt der naechste Trainingslauf."
RETRAIN_THRESHOLD = 10
STATE_PATH = Path(__file__).parent / "auto_retrain_state.json"


def _current_labeled() -> dict[str, int]:
    """Aktueller Stand aller Labels: {ground_truth-Id -> Aenderungszeit (ns)}."""
    out: dict[str, int] = {}
    if not GROUND_TRUTH_DIR.exists():
        return out
    for gt in GROUND_TRUTH_DIR.glob("*.json"):
        try:
            out[gt.stem] = gt.stat().st_mtime_ns
        except OSError:
            continue
    return out


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"seen": {}, "lastRetrainAt": None, "lastResult": None}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")


def count_new_sets() -> dict:
    """Wie viele Sets sind seit dem letzten Retrain neu oder geaendert?"""
    state = _load_state()
    seen: dict[str, int] = state.get("seen") or {}
    current = _current_labeled()
    new_ids = [sid for sid, mt in current.items() if seen.get(sid) != mt]

    active = load_model() or {}
    loso = active.get("loso_validation") or {}
    return {
        "newSets": len(new_ids),
        "threshold": RETRAIN_THRESHOLD,
        "totalLabeled": len(current),
        "ready": len(new_ids) >= RETRAIN_THRESHOLD,
        "lastRetrainAt": state.get("lastRetrainAt"),
        "lastResult": state.get("lastResult"),
        "activeModel": {
            "recall": loso.get("recall"),
            "precision": loso.get("precision"),
            "f1": loso.get("f1"),
        },
        "modelExists": MODEL_PATH.exists(),
    }


def run_if_ready(force: bool = False, include_synthetic: bool = False) -> dict:
    """Retrain starten, wenn genug neu (oder force). Aktualisiert den Zustand
    nur bei einem tatsaechlich durchgefuehrten Lauf.

    STANDARD ist real-only (include_synthetic=False, siehe
    retrain_model.run_retrain - gemessen besser auf echten Sets). Damit laeuft
    AUCH die automatische Ausloesung real-only.
    """
    status = count_new_sets()
    if not force and not status["ready"]:
        print(f"Noch nicht genug: {status['newSets']}/{RETRAIN_THRESHOLD} neue Sets "
              f"seit dem letzten Retrain. Kein Lauf.")
        return {"ran": False, **status}

    mode = "REAL-ONLY (keine Synthetik)" if not include_synthetic else "mit Synthetik"
    print(f"Starte Retrain ({status['newSets']} neue Sets, force={force}, {mode}) ...\n")
    from app.calibration.retrain_model import run_retrain
    result = run_retrain(include_synthetic=include_synthetic)

    state = _load_state()
    state["seen"] = _current_labeled()  # ab jetzt gelten alle aktuellen Labels als gesehen
    state["lastRetrainAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["lastResult"] = result
    _save_state(state)

    verb = "EXPORTIERT (neues Modell aktiv)" if result.get("exported") else "verworfen (altes Modell bleibt)"
    print(f"\nErgebnis: {verb}. Details im Status.")
    return {"ran": True, "result": result, **count_new_sets()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrain-Automatik.")
    parser.add_argument("--status", action="store_true", help="nur Stand zeigen")
    parser.add_argument("--force", action="store_true", help="jetzt laufen, egal wie viel neu")
    parser.add_argument("--real-only", action="store_true",
                        help="(Standard) nur echte Sets, keine synthetischen")
    parser.add_argument("--with-synthetic", action="store_true",
                        help="auch synthetische Trainingsdaten einbeziehen (alte Voreinstellung)")
    args = parser.parse_args()

    if args.status:
        s = count_new_sets()
        print(f"Neue/geaenderte Sets seit letztem Retrain: {s['newSets']}/{s['threshold']}")
        print(f"Gelabelte Sets gesamt: {s['totalLabeled']}")
        print(f"Letzter Retrain: {s['lastRetrainAt'] or 'noch nie'}")
        am = s["activeModel"]
        if am.get("f1") is not None:
            print(f"Aktives Modell (LOSO): R={am['recall']} P={am['precision']} F1={am['f1']}")
        return 0

    run_if_ready(force=args.force,
                 include_synthetic=(args.with_synthetic and not args.real_only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
