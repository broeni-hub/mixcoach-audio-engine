"""Composite-Quality-Score aus 5 Dimensionen (V3-Scoring).

Hintergrund: eine Auswertung von 239 von Sebastian bewerteten Uebergaengen
ergab Spearman-Korrelation ~0 zwischen dem bestehenden quality_score
(transition_quality.py) und den menschlichen Bewertungen - der bestehende
Score gewichtet zu 70% Timing (Phrase 35% + Tempo 35%), kaum Klangqualitaet.
Die 5 Dimensionen hier zielen bewusst auf Klang statt nur Timing:

  1. harmonic_clash  - Chroma-Vergleich im Overlap-Fenster (Demucs-Stems)
  2. vocal_overlap    - laufen beide Gesangsspuren gleichzeitig? (Demucs)
  3. exit_quality     - wie saubere klingt der Fade-Out von Track 1?
  4. beat_alignment   - Puls-Regelmaessigkeit im Blend-Fenster
  5. phrase_timing    - der bestehende Phrasen-Score, nur geringer gewichtet

ERSETZT NICHT quality_score/scores (transition_quality.py) - der bleibt
unveraendert, weil Frontend + labels_prefilled.csv/analyses.json direkt
darauf zugreifen. composite_quality_score ist ein ZUSAETZLICHES Feld.

GEWICHTS-STAND (2026-07-12): erster echter Fit mit app/calibration/
fit_composite_weights.py, NICHT mehr Gleichverteilung. Datenbasis: nur 20
gematchte Uebergaenge aus 5 neu analysierten Sets (14 Training/6 Test) -
kleine Stichprobe, aber schon ein deutlicher Sprung gegenueber der
Ausgangslage (quality_score vs. human_rating: -0.23; composite_quality_score
vs. human_rating: 0.47 Training / 0.62 Test). exit_quality und phrase_timing
fielen bei dieser Stichprobe auf 0 - kann echt sein oder Stichprobenrauschen.
Sobald mehr Sets mit Composite-Score analysiert + bewertet sind, das Fit-
Skript erneut laufen lassen und hier aktualisieren.
"""

from typing import Dict, List, Optional

DEFAULT_WEIGHTS: Dict[str, float] = {
    "harmonic_clash": 0.09,
    "vocal_overlap": 0.42,
    "exit_quality": 0.0,
    "beat_alignment": 0.49,
    "phrase_timing": 0.0,
}


def composite_score(
    harmonic_clash: Optional[int],
    vocal_overlap: Optional[int],
    exit_quality: Optional[int],
    beat_alignment: Optional[int],
    phrase_timing: Optional[int],
    weights: Optional[Dict[str, float]] = None,
) -> Optional[int]:
    """Gewichteter Mittelwert ueber die messbaren Dimensionen. Fehlende
    (None) werden ausgelassen und die restlichen Gewichte neu normiert -
    wie ueberall sonst im Codebase (siehe transition_quality._combined_score),
    nie mit 0 bestraft, was den Score kuenstlich absenken wuerde."""
    w = weights or DEFAULT_WEIGHTS
    values = {
        "harmonic_clash": harmonic_clash,
        "vocal_overlap": vocal_overlap,
        "exit_quality": exit_quality,
        "beat_alignment": beat_alignment,
        "phrase_timing": phrase_timing,
    }
    available = [
        (values[key], w[key]) for key in values
        if values[key] is not None and w.get(key, 0) > 0
    ]
    if not available:
        return None

    total_weight = sum(weight for _, weight in available)
    if total_weight <= 0:
        return None

    value = sum(score * weight for score, weight in available) / total_weight
    return int(round(value))


def annotate_composite_scores(
    transitions_detailed: List[Dict], weights: Optional[Dict[str, float]] = None,
) -> None:
    """Haengt composite_quality_score + composite_breakdown an jeden
    Uebergang. Voraussetzung: harmonic_clash_score, vocal_overlap_score,
    exit_quality_score, beat_alignment_score wurden bereits annotiert
    (siehe pipeline.py); phrase_timing kommt aus dem bestehenden
    scores['phrase'] von transition_quality.evaluate_transitions."""
    for t in transitions_detailed:
        phrase_timing = (t.get("scores") or {}).get("phrase")

        breakdown = {
            "harmonic_clash": t.get("harmonic_clash_score"),
            "vocal_overlap": t.get("vocal_overlap_score"),
            "exit_quality": t.get("exit_quality_score"),
            "beat_alignment": t.get("beat_alignment_score"),
            "phrase_timing": phrase_timing,
        }

        t["composite_quality_score"] = composite_score(
            harmonic_clash=breakdown["harmonic_clash"],
            vocal_overlap=breakdown["vocal_overlap"],
            exit_quality=breakdown["exit_quality"],
            beat_alignment=breakdown["beat_alignment"],
            phrase_timing=breakdown["phrase_timing"],
            weights=weights,
        )
        t["composite_breakdown"] = breakdown
