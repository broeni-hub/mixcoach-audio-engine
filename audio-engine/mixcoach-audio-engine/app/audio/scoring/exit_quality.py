"""Track-1-Exit-Qualitaet via RMS-Verlauf.

Der bestehende Energy-Score (transition_quality._energy_dip_score) bewertet,
wie TIEF die Gesamtenergie im Uebergang einbricht (Sweet Spot ~30-50%).
Diese Dimension bewertet etwas anderes: wie SAUBER Track 1 dabei rausgeht -
eine gleichmaessig abklingende Kurve (Fade/EQ-Out) klingt kontrolliert, ein
zackiger Verlauf (mehrfaches Wiederkommen der Energie, harte Sprünge) klingt
nach einem ungenauen Cue oder wackligem Fader.

Nutzt die ohnehin pro Set berechnete 1s-RMS-Kurve (app/audio/energy.py) im
Fenster [start_sec, mid_sec] - kein zusaetzlicher Analyse-Durchlauf noetig.
Bekannte Vereinfachung (dokumentiert): ein sauberer, bewusst harter Cut wird
hier schlechter bewertet als ein Fade, obwohl beides gueltige DJ-Techniken
sind. Gemessen wird Kurven-Glaette, keine musikalische Absicht.
"""

from typing import Dict, List, Optional

import numpy as np

MIN_POINTS = 5
# Ab diesem Netto-Rueckgang (Anteil vom Startwert) gilt der Exit als "voll
# zurueckgenommen" - mehr bringt keine zusaetzlichen Punkte.
FULL_DECLINE_FRACTION = 0.5


def _points_in_window(energy_points: List[Dict], start: float, end: float) -> List[float]:
    return [
        float(p["rms"]) for p in energy_points
        if start <= float(p["time"]) <= end
    ]


def _roughness(rms: np.ndarray) -> float:
    """0 (glatt fallend) .. beliebig hoch (zackig) - positive Ruecksprünge
    relativ zur Gesamt-Spannweite der Kurve."""
    span = float(np.max(rms) - np.min(rms))
    if span <= 1e-9:
        return 0.0
    diffs = np.diff(rms)
    positive_jumps = diffs[diffs > 0]
    return float(np.sum(positive_jumps)) / span


def exit_quality_score(rms_values: List[float]) -> Optional[int]:
    """0-100: wie sauber/kontrolliert klingt der Fade-Out von Track 1."""
    if len(rms_values) < MIN_POINTS:
        return None

    arr = np.array(rms_values, dtype=float)
    if arr[0] <= 1e-9:
        return None  # Track war schon vorher praktisch stumm - nicht messbar

    roughness = _roughness(arr)
    smoothness_score = max(0.0, 1.0 - roughness)

    net_decline = (arr[0] - arr[-1]) / arr[0]
    decline_score = max(0.0, min(1.0, net_decline / FULL_DECLINE_FRACTION))

    combined = 0.6 * smoothness_score + 0.4 * decline_score
    return int(round(max(0.0, min(1.0, combined)) * 100))


def annotate_exit_quality(transitions_detailed: List[Dict], energy_points: List[Dict]) -> None:
    """Haengt exit_quality_score an jeden Uebergang - None, wenn das
    Vor-Fenster zu kurz oder Track 1 dort schon stumm war."""
    for t in transitions_detailed:
        start = t.get("start_sec")
        mid = t.get("mid_sec")
        if start is None or mid is None or float(mid) <= float(start):
            t["exit_quality_score"] = None
            continue

        rms_values = _points_in_window(energy_points, float(start), float(mid))
        score = exit_quality_score(rms_values)

        t["exit_quality_score"] = score
        t.setdefault("scores", {})["exit_quality"] = score
