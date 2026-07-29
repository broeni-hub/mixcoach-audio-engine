"""Ground-Truth-Feedback von Nutzern.

Jeder DJ, der im Report einen Uebergang bestaetigt ("stimmt"), ablehnt
("kein Uebergang") oder einen fehlenden markiert, erweitert den
Trainings-Datensatz der Engine. Das ist der Daten-Kreislauf, der die
Erkennung von Hand-Kalibrierung (n=5 Sets) zu gelernten Modellen bringt.

Ablage: siehe app/paths.py - gemeinsamer Datenstamm mit den
Analyse-Ergebnissen (GROUND_TRUTH_DIR).
"""
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.paths import GROUND_TRUTH_DIR

_lock = threading.Lock()


def _path(analysis_id: str) -> Path:
    return GROUND_TRUTH_DIR / f"{analysis_id}.json"


def _empty(analysis_id: str) -> Dict:
    return {
        "analysisId": analysis_id,
        "verdicts": {},   # transition_index (str) -> {"midSec", "verdict"}
        "missed": [],     # Sekunden, an denen ein Uebergang fehlte
        "updatedAt": None,
    }


def load_feedback(analysis_id: str) -> Dict:
    path = _path(analysis_id)
    if not path.exists():
        return _empty(analysis_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty(analysis_id)


def save_verdict(
    analysis_id: str,
    index: int,
    mid_sec: float,
    verdict: str,
    corrected_sec: Optional[float] = None,
) -> Dict:
    """Bestaetigung/Ablehnung/Zeitkorrektur eines erkannten Uebergangs.

    verdict "timing_off" bedeutet: Der Uebergang ist echt, aber die Engine
    hat den Zeitpunkt falsch gesetzt - corrected_sec ist die vom DJ
    angesteuerte echte Startstelle. Fuers Training doppelt wertvoll:
    bestaetigt den Uebergang UND liefert den praezisen Zeitpunkt."""
    with _lock:
        data = load_feedback(analysis_id)
        entry = {
            "midSec": round(float(mid_sec), 2),
            "verdict": verdict,
        }
        if corrected_sec is not None:
            entry["correctedSec"] = round(float(corrected_sec), 2)
        data["verdicts"][str(index)] = entry
        data["updatedAt"] = time.time()
        _write(data)
    return data


def save_missed(analysis_id: str, sec: float) -> Dict:
    """Vom Nutzer markierter, von der Engine verpasster Uebergang.

    Innerhalb von 15s wird dedupliziert (Doppelklicks, Korrekturen).
    """
    with _lock:
        data = load_feedback(analysis_id)
        sec = round(float(sec), 2)
        if all(abs(sec - existing) > 15.0 for existing in data["missed"]):
            data["missed"].append(sec)
            data["missed"].sort()
        data["updatedAt"] = time.time()
        _write(data)
    return data


def _write(data: Dict) -> None:
    # Zielordner sicherstellen, statt sich auf den mkdir-Nebeneffekt beim
    # Import von app/paths.py zu verlassen. Der greift nur fuer den einen
    # Pfad, der beim Start galt - zeigt GROUND_TRUTH_DIR spaeter woanders
    # hin (Test, geaenderte MIXCOACH_DATA_DIR, geloeschter Ordner), lief
    # das Schreiben vorher auf FileNotFoundError.
    path = _path(data["analysisId"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
