"""Beat-Alignment im Uebergangsfenster - misst echtes Beatmatching.

Unterschied zum bestehenden Tempo-Score (transition_quality._tempo_match_score):
Der Tempo-Score vergleicht nur die BPM-ZAHLEN vor/nach dem Uebergang - zwei
Tracks koennen exakt dieselbe BPM haben und trotzdem "phasig" laufen, wenn
ihre Beats nicht exakt uebereinanderfallen (haerbar als Flanging/Stolpern).

Es gibt hier keinen separaten Beat-Tracker pro Track - nur EIN globaler
Beat-Tracker ueber die gesamte Aufnahme (siehe app/audio/beats.py). Bei
sauberem Beatmatching liefert der im Blend-Fenster einen regelmaessigen Puls;
bei Phasenversatz/ungenauem Beatmatching werden die Abstaende unregelmaessig
(der Tracker "eiert" zwischen den beiden ueberlagerten Pulsen). Gemessen wird
daher die REGELMAESSIGKEIT der Beat-Abstaende im Blend-Fenster (Variations-
koeffizient), nicht ein direkter Phasenvergleich zweier Raster - ehrlich
dokumentierte Vereinfachung, kein erfundener Phasenwert.
"""

from typing import Dict, List, Optional

import numpy as np

MIN_BEATS_IN_WINDOW = 4
# Ab diesem Variationskoeffizienten gilt der Puls als komplett zerfahren.
CV_AT_ZERO_SCORE = 0.35


def _interval_cv(beats_in_window: List[float]) -> Optional[float]:
    """Variationskoeffizient der Beat-Abstaende - 0 = perfekt regelmaessig."""
    if len(beats_in_window) < MIN_BEATS_IN_WINDOW:
        return None

    intervals = np.diff(np.array(beats_in_window))
    intervals = intervals[(intervals > 0.15) & (intervals < 2.0)]  # 30-400 BPM

    if len(intervals) < MIN_BEATS_IN_WINDOW - 1:
        return None

    mean_interval = float(np.mean(intervals))
    if mean_interval <= 0:
        return None

    return float(np.std(intervals) / mean_interval)


def _beat_alignment_score(cv: Optional[float]) -> Optional[int]:
    if cv is None:
        return None
    score = 100.0 - (cv / CV_AT_ZERO_SCORE) * 100.0
    return int(round(max(0.0, min(100.0, score))))


def annotate_beat_alignment(transitions_detailed: List[Dict], beats: List[float]) -> None:
    """Haengt beat_alignment_score an jeden Uebergang - None, wenn zu wenige
    Beats im gemessenen Fenster liegen (Set-Rand, sehr kurzer Blend)."""
    for t in transitions_detailed:
        start = t.get("start_sec")
        end = t.get("end_sec")
        if start is None or end is None:
            t["beat_alignment_score"] = None
            continue

        window_beats = [b for b in beats if float(start) <= b <= float(end)]
        cv = _interval_cv(window_beats)
        score = _beat_alignment_score(cv)

        t["beat_alignment_score"] = score
        t.setdefault("scores", {})["beat_alignment"] = score
