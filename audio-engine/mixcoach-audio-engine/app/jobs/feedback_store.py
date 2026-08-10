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
        # transition_index (str) -> {"midSec", "verdict", "at", ggf. "correctedSec"}
        "verdicts": {},
        "missed": [],     # Sekunden, an denen ein Uebergang fehlte
        "missedAt": [],   # Klickzeitpunkt je missed-Eintrag (parallel, additiv)
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
            # Zeitstempel je EINZELNEM Handgriff. updatedAt daneben ist nur
            # der letzte Speicherzeitpunkt der ganzen Datei und sagt nichts
            # darueber, wie lange ein Label-Durchgang gedauert hat - die
            # Angabe "15-35 min je Set" in ZUKUNFTSWEGE_2026-07-30.md ist
            # darum ausdruecklich eine Schaetzung aus Handgriffzahl und
            # Setlaenge. Mit diesem Feld wird daraus eine Messung: die
            # Abstaende aufeinanderfolgender at-Werte sind die Bearbeitungs-
            # zeit je Uebergang.
            "at": time.time(),
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
            # Zeitstempel PARALLEL statt im missed-Eintrag selbst: missed ist
            # eine Liste von Sekundenwerten, und darauf verlassen sich
            # analyze_timing_bias (len) und retrain_model/load_truth. Ein
            # Umbau auf Objekte waere ein Schema-Bruch fuer eine Messgroesse.
            # missedAt ist bewusst nur additiv und wird nicht sortiert - es
            # protokolliert die Reihenfolge der KLICKS, nicht der Zeitpunkte
            # im Set. Ohne diese Werte waere die Kostenrechnung schief:
            # 'missed' ist laut ZUKUNFTSWEGE 1.5 der teuerste Handgriff
            # (98 Stueck), er verlangt das Finden einer Stelle, die die
            # Engine gar nicht angeboten hat.
            data.setdefault("missedAt", []).append(time.time())
        data["updatedAt"] = time.time()
        _write(data)
    return data


def _write(data: Dict) -> None:
    # Zielordner selbst sicherstellen statt sich darauf zu verlassen, dass
    # app.paths ihn beim Import angelegt hat: GROUND_TRUTH_DIR wird in Tests
    # (und potenziell im Deployment) auf ein anderes Verzeichnis umgebogen,
    # das dann nicht existiert - vorher schlug das Schreiben mit
    # FileNotFoundError fehl, sichtbar an 3 roten Tests in test_feedback.py.
    path = _path(data["analysisId"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
