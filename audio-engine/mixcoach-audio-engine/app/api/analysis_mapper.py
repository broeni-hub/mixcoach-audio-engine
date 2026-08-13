from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from app.audio.dramaturgie import bogen
from app.audio.pipeline.scoring_version import scoring_stamp

# Scores, die die Set-Pipeline derzeit NICHT misst, werden bewusst als
# None (null) ausgegeben statt mit erfundenen Zahlen befuellt.
# Grundsatz: Nur anzeigen, was wirklich gemessen wurde.
#
# beatmatching und timing sind am 31.07.2026 dazugekommen. Beide waren
# befuellt, aber die Zahl dahinter traegt nicht (gemessen an 19 echten
# Aufnahmen / 258 Uebergaengen, Testfixtures mix.wav + synthetic_mix.wav
# ausgeschlossen):
#
#   beatmatching = Mittel des Tempo-Scores aus bpm_drift. bpm_drift ist in
#   89 % der Uebergaenge exakt 0,0, weil die Tempo-Schaetzung fuer
#   benachbarte Segmente denselben Wert liefert - ueber ALLE 19 Aufnahmen
#   gibt es nur 14 verschiedene Tempowerte. Ergebnis: beatmatching lag bei
#   12 von 19 Aufnahmen auf exakt 100, Spanne 91-100. Eine Kopfzahl, die
#   keinen DJ von einem anderen unterscheiden kann.
#
#   timing = Mittel des Phrasen-Scores aus phrase_beats_off. Das Raster
#   wird in phrase_grid.py am ersten Beat des erkannten Segments verankert;
#   genau diese Grenze verfehlt die Engine mit sigma = 52,87 s, das sind
#   bei 125 BPM rund 3,4 Phrasen. Der Bezugspunkt wandert also weiter als
#   die Groesse, die er messen soll (0-16 Beats).
#
# Unabhaengig bestaetigt, mit anderer Methode und anderer Datenbasis:
# app/audio/scoring/composite.py haelt fest, dass der alte quality_score
# (zu 70 % aus genau diesen beiden Groessen) gegen 239 menschliche
# Bewertungen eine Spearman-Korrelation von ~0 hat, und setzt
# phrase_timing im gefitteten Composite auf Gewicht 0,0.
#
# Die Rohwerte bleiben im Payload (phrase_beats_off, phrase_alignment_score,
# bpm_drift je Uebergang) - sie werden fuer Auswertung und Export gebraucht.
# Was entfaellt, ist die NOTE und die daraus abgeleitete Handlungsanweisung.
NOT_YET_MEASURED = ["eq", "creativity", "frequency", "beatmatching", "timing"]


def map_set_analysis_to_frontend_result(filename: str, analysis: Dict) -> Dict:
    tempo = analysis.get("tempo", {})
    quality = analysis.get("quality", {})
    coach = analysis.get("coach_summary", {})
    energy = analysis.get("energy", {})

    warnings = _build_warnings(analysis)

    bpm = _measured_bpm(tempo)
    overall = _measured_int(quality.get("overall"))
    verlauf = _map_loudness_curve(analysis) or _map_energy_curve(energy)
    dominant = analysis.get("dominant_key") or {}

    return {
        "id": str(uuid4()),
        "fileName": filename,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mapperVersion": "honest-v2",
        # Welche Rechenvorschrift die Messwerte erzeugt hat. Ohne diese Angabe
        # ist kein Vergleich ueber Zeit zulaessig - und der Vergleich ueber Zeit
        # IST das Produkt (Erlebnis-Punkt 4). Herleitung und Changelog:
        # app/audio/pipeline/scoring_version.py
        #
        # Nicht verwechseln mit dem alten quality["scoring_version"]: das steht
        # seit jeher fest auf "v2-transition-quality", wird nie erhoeht und hat
        # es nie in einen gespeicherten Report geschafft (50 von 50 ohne Spur).
        # Wer danach gesucht hat, hat sich in Sicherheit gewiegt.
        **scoring_stamp(),

        "bpm": bpm,
        "key": dominant.get("key"),
        "camelot": dominant.get("camelot"),
        "transitionLength": None,

        "energyCurve": _map_energy_curve(energy),
        # Echte K-gewichtete Lautheit (BS.1770) statt des frueheren
        # Energie-Duplikats - zwei identische Charts sahen aus wie zwei
        # Messungen (Sebastians Frage 2026-07-17). Fallback auf die
        # Energiekurve nur fuer Analysen, die vor der Einfuehrung von
        # loudness_curve im Pipeline-Result entstanden sind.
        "volumeCurve": verlauf,

        # Beschreibung genau DER Kurve, die auch gezeichnet wird - nicht
        # einer zweiten, intern gerechneten. Sonst koennte der Text etwas
        # anderes behaupten als das Bild daneben zeigt.
        #
        # Rein beschreibend, ohne Note: siehe app/audio/dramaturgie.py.
        # Nachgemessen an 19 echten Aufnahmen (31.07.2026): der Verlauf ist
        # deterministisch (zwei Analysen derselben Aufnahme ergeben
        # identische Kurven, Median-Abstand 0,000 ueber 66 Paare) und
        # unterscheidet die Aufnahmen (Median-Abstand 0,180 zwischen
        # verschiedenen). Das ist der Unterschied zu den Groessen in
        # NOT_YET_MEASURED.
        "energyArc": bogen(verlauf, round(float(analysis.get("duration", 0))) or None),

        "frequency": None,

        "scores": {
            # v2: echte Messwerte aus der Uebergangs-Bewertung.
            # beatmatching/timing: siehe NOT_YET_MEASURED oben. Bewusst None
            # und nicht der berechnete Wert - eine Note, die bei 12 von 19
            # Aufnahmen 100 lautet, ist keine Messung.
            "beatmatching": None,
            "eq": None,
            "timing": None,
            "creativity": None,
            "flow": _measured_int(quality.get("energy_flow")),
            "musicality": _measured_int(quality.get("harmonic")),
            "overall": overall,
        },

        "notMeasured": NOT_YET_MEASURED,
        "analysisWarnings": warnings,

        "timeline": _map_timeline(analysis),

        "strengths": coach.get("positives", ["Set analysis completed."]),
        "weaknesses": coach.get("improvements", ["No major issues detected."]),

        "feedback": {
            "worked": coach.get("positives", [])[:2],
            "improve": coach.get("improvements", [])[:2],
            "exercise": _build_exercise(coach),
            "confidence": overall if overall is not None else 0,
        },

        "exercises": [
            {
                "title": "Transition Review",
                "description": "Listen to the detected transition points and check whether the phrase timing feels natural.",
                "xp": 40,
            }
        ],

        "setTransitions": _map_set_transitions(analysis),
        "library": analysis.get("library"),
        "loudness": analysis.get("loudness"),
        "totalDurationSec": round(float(analysis.get("duration", 0))),
        "findings": _map_findings(analysis),
    }


def _measured_bpm(tempo: Dict) -> Optional[int]:
    """BPM nur zurueckgeben, wenn wirklich gemessen. Kein 120er-Default."""
    value = tempo.get("tempo")

    if value is None:
        return None

    return int(round(float(value)))


def _measured_int(value) -> Optional[int]:
    """Score nur zurueckgeben, wenn wirklich berechnet. Kein 70er-Default."""
    if value is None:
        return None

    return int(round(float(value)))


def _build_warnings(analysis: Dict) -> List[str]:
    """Explizite Warnungen statt stiller Defaults, wenn die Analyse unsicher ist."""
    warnings: List[str] = []

    tempo = analysis.get("tempo", {})
    quality = analysis.get("quality", {})
    energy = analysis.get("energy", {})

    if tempo.get("tempo") is None:
        warnings.append("Tempo konnte nicht gemessen werden.")
    elif float(tempo.get("confidence", 0)) < 0.5:
        warnings.append(
            "Die Tempo-Erkennung ist unsicher (Confidence "
            f"{tempo.get('confidence')}). BPM-Wert mit Vorsicht interpretieren."
        )

    if quality.get("overall") is None:
        warnings.append("Es konnte kein Qualitaets-Score berechnet werden.")

    if not energy.get("points"):
        warnings.append("Es konnte keine Energie-Kurve berechnet werden.")

    if not analysis.get("transition_zones"):
        warnings.append(
            "Es wurden keine Uebergangszonen erkannt. Entweder ist das Set "
            "sehr glatt gemischt oder die Erkennung hat nicht angeschlagen."
        )

    beat_grid = analysis.get("beat_grid", {})
    duration = float(analysis.get("duration", 0) or 0)
    if duration > 0 and beat_grid:
        beats_per_minute_found = beat_grid.get("beat_count", 0) / (duration / 60.0)
        if beats_per_minute_found < 60:
            warnings.append(
                "Die Beat-Erkennung hat ungewoehnlich wenige Beats gefunden - "
                "Phrase-Timing-Werte mit Vorsicht interpretieren."
            )

    transitions = analysis.get("transitions_detailed", [])
    unmeasured_tempo = [t for t in transitions if t.get("bpm_before") is None or t.get("bpm_after") is None]
    if transitions and len(unmeasured_tempo) > len(transitions) / 2:
        warnings.append(
            "Bei mehr als der Haelfte der Uebergaenge konnte das Tempo der "
            "umliegenden Segmente nicht gemessen werden (Segmente zu kurz)."
        )

    return warnings


# Anzeige-Spanne fuer die Lautheitskurve: -45 LUFS (praktisch leise) bis
# -5 LUFS (sehr laut ausgesteuert) -> 0..100. Clamping statt Min/Max-
# Normierung pro Set, damit die Kurve zwischen Sets VERGLEICHBAR bleibt
# (ein durchgehend leises Set soll flach aussehen, nicht kuenstlich voll).
_LUFS_DISPLAY_MIN = -45.0
_LUFS_DISPLAY_MAX = -5.0


def _map_loudness_curve(analysis: Dict) -> List[Dict]:
    """Rohe LUFS-Kurve aus dem Pipeline-Result -> 0..100-Anzeigepunkte.
    Leere Liste, wenn die Analyse (noch) keine Lautheitskurve enthaelt -
    der Aufrufer faellt dann auf die Energiekurve zurueck."""
    points = analysis.get("loudness_curve") or []
    span = _LUFS_DISPLAY_MAX - _LUFS_DISPLAY_MIN
    mapped = []
    for point in points:
        lufs = point.get("lufs")
        if lufs is None:
            continue
        norm = (float(lufs) - _LUFS_DISPLAY_MIN) / span
        mapped.append({
            "t": int(float(point.get("time", 0))),
            "value": int(round(max(0.0, min(1.0, norm)) * 100)),
            "lufs": round(float(lufs), 1),
        })
    return mapped


def _map_energy_curve(energy: Dict) -> List[Dict]:
    points = energy.get("points", [])

    if not points:
        # Ehrlich bleiben: keine Daten -> leere Kurve, keine erfundene Linie.
        return []

    max_rms = max(float(point.get("rms", 0)) for point in points) or 1.0

    mapped = [
        {
            "t": int(float(point.get("time", 0))),
            "value": int(round((float(point.get("rms", 0)) / max_rms) * 100)),
        }
        for point in points
    ]

    return _downsample_curve(mapped, max_points=240)


def _downsample_curve(points: List[Dict], max_points: int) -> List[Dict]:
    if len(points) <= max_points:
        return points

    step = len(points) / max_points
    result = []

    for index in range(max_points):
        start = int(index * step)
        end = int((index + 1) * step)
        chunk = points[start:end] or [points[start]]

        avg_t = round(sum(point["t"] for point in chunk) / len(chunk))
        avg_value = round(sum(point["value"] for point in chunk) / len(chunk))

        result.append(
            {
                "t": int(avg_t),
                "value": int(avg_value),
            }
        )

    return result


def _map_timeline(analysis: Dict) -> List[Dict]:
    events = []

    for event in analysis.get("timeline", []):
        seconds = float(event.get("time", 0))
        events.append(
            {
                "time": _format_time(seconds),
                "label": event.get("description", event.get("type", "Event")),
                "type": _timeline_type(event.get("type")),
            }
        )

    if not events:
        events.append(
            {
                "time": "00:00",
                "label": "Set analysis started",
                "type": "info",
            }
        )

    return events[:12]


def _map_set_transitions(analysis: Dict) -> List[Dict]:
    """Uebergaenge im Format, das das Frontend (report-view) erwartet.

    Wichtig: snake_case-Felder wie start_sec, bpm_before usw. -
    das alte Format {index, time, confidence} konnte die UI nicht lesen.
    """
    transitions = []

    for t in analysis.get("transitions_detailed", []):
        scores = t.get("scores", {})
        transitions.append(
            {
                "index": t["index"],
                "start_sec": t["start_sec"],
                "mid_sec": t["mid_sec"],
                "end_sec": t["end_sec"],
                "bpm_before": t.get("bpm_before"),
                "bpm_after": t.get("bpm_after"),
                "bpm_drift": t.get("bpm_drift"),
                "key_before": t.get("key_before"),
                "key_after": t.get("key_after"),
                "camelot_before": t.get("camelot_before"),
                "camelot_after": t.get("camelot_after"),
                "phrase_beats_off": t.get("phrase_beats_off"),
                "phrase_alignment_score": scores.get("phrase"),
                "energy_dip_pct": t.get("energy_dip_pct"),
                "bass_overlap_score": t.get("bass_overlap_score"),  # nur bei Fingerprint-Paar messbar
                "quality_score": t.get("quality_score"),
                # Composite-Score (V3, siehe app/audio/scoring/composite.py) -
                # zusaetzlich zu quality_score, nicht dessen Ersatz.
                "composite_quality_score": t.get("composite_quality_score"),
                "composite_breakdown": t.get("composite_breakdown"),
                "harmonic_clash_score": t.get("harmonic_clash_score"),
                "vocal_overlap_score": t.get("vocal_overlap_score"),
                "exit_quality_score": t.get("exit_quality_score"),
                "beat_alignment_score": t.get("beat_alignment_score"),
                "label": t.get("label", "neutral"),
                "feedback": t.get("feedback"),
                "feedback_en": t.get("feedback_en"),
                "loudness_jump_db": t.get("loudness_jump_db"),
                "track_out": t.get("track_out"),
                "track_in": t.get("track_in"),
                "detection": t.get("detection"),
                # Trackwechsel sicher (Fingerprint), aber in einer Erkennungs-
                # luecke nur geschaetzt positioniert - Frontend zeigt das ehrlich.
                "position_estimated": t.get("position_estimated", False),
                "gap_seconds": t.get("gap_seconds"),
                "possible_unrecognized_track": t.get("possible_unrecognized_track", False),
                "type": t.get("type"),
                "confidence": t.get("detection_confidence"),
            }
        )

    return transitions


def _map_findings(analysis: Dict) -> List[Dict]:
    findings = []

    for index, finding in enumerate(analysis.get("rule_findings", []), start=1):
        findings.append(
            {
                "rule_id": str(index),
                "rule_slug": finding.get("type", "finding"),
                "title": finding.get("type", "Finding"),
                "diagnosis": finding.get("message", ""),
                "fix": finding.get("message", ""),
                "severity": _finding_severity(finding.get("severity")),
                "metric": None,
                "value": None,
            }
        )

    return findings


def _format_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes = seconds // 60
    rest = seconds % 60
    return f"{minutes:02d}:{rest:02d}"


def _timeline_type(event_type: str) -> str:
    if event_type in {"track_change", "transition"}:
        return "warning"

    if event_type in {"track_start", "set_start"}:
        return "info"

    return "good"


def _finding_severity(severity: str) -> str:
    if severity == "high":
        return "critical"

    if severity == "medium":
        return "warning"

    return "info"


def _build_exercise(coach: Dict) -> str:
    improvements = coach.get("improvements", [])

    if improvements:
        return improvements[0]

    return "Review the detected transition zones and compare them with your intended mix points."
