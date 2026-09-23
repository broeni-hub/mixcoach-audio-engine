"""Qualitaets-Bewertung pro Uebergang - das Kernversprechen von MixCoach.

Jeder erkannte Uebergang wird musikalisch bewertet:
- Phrase-Timing: Liegt der Uebergang auf einem Phrasenstart? (in Beats!)
- Tempo-Match: Passen die BPM der beiden Segmente zusammen?
- Harmonie: Passen die Tonarten (Camelot-Rad)?
- Energie: Wie tief ist der Energie-Einbruch?

Jede Metrik ist None, wenn sie nicht messbar war. Der Score wird nur
aus messbaren Teilen gebildet und das Feedback nennt konkrete Zahlen.
"""

from typing import Dict, List, Optional

from app.audio.phrase_grid import phrase_distance_beats
from app.audio.segment_keys import camelot_compatibility_score


def evaluate_transitions(
    transition_zones: List[Dict],
    segments: List[Dict],
    segment_tempos: List[Dict],
    segment_keys: List[Dict],
    phrase_boundaries: List[Dict],
    duration: float,
) -> List[Dict]:
    """Bewertet jeden Uebergang zwischen zwei benachbarten Segmenten."""
    tempo_by_index = {t["segment_index"]: t["bpm"] for t in segment_tempos}
    key_by_index = {k["segment_index"]: k for k in segment_keys}

    results: List[Dict] = []

    for i, zone in enumerate(transition_zones):
        center = float(zone["time"])

        # Zone i trennt Segment i+1 (davor) von Segment i+2 (danach) -
        # build_set_segments vergibt 1-basierte Indizes in Zeit-Reihenfolge.
        before_index = i + 1
        after_index = i + 2

        bpm_before = tempo_by_index.get(before_index)
        bpm_after = tempo_by_index.get(after_index)

        key_before = key_by_index.get(before_index, {})
        key_after = key_by_index.get(after_index, {})

        bpm_drift = (
            round(abs(bpm_before - bpm_after), 2)
            if bpm_before is not None and bpm_after is not None
            else None
        )

        tempo_score = _tempo_match_score(bpm_drift)
        harmonic_score = camelot_compatibility_score(
            key_before.get("camelot"), key_after.get("camelot"),
        )

        # WICHTIG: Nur das Phrasen-Raster des AUSLAUFENDEN Tracks verwenden.
        # Das Raster des neuen Segments ankert am Uebergang selbst - dagegen
        # zu messen waere ein Zirkelschluss (Ergebnis immer ~0 Beats).
        # Das Raster des auslaufenden Tracks ankert am vorherigen Uebergang
        # und misst, ob DIESER Uebergang auf dessen 32-Beat-Raster faellt.
        outgoing_boundaries = [
            b for b in phrase_boundaries
            if b.get("segment_index") == before_index
        ]
        beats_off = phrase_distance_beats(
            outgoing_boundaries, center, bpm_before or bpm_after,
        )
        phrase_score = _phrase_alignment_score(beats_off)

        energy_dip_pct = _energy_dip_pct(zone)
        energy_score = _energy_dip_score(energy_dip_pct)

        quality = _combined_score(
            phrase=phrase_score,
            tempo=tempo_score,
            harmonic=harmonic_score,
            energy=energy_score,
        )

        blend_start = zone.get("blend_start")
        results.append(
            {
                "index": i + 1,
                "start_sec": round(float(blend_start), 2) if blend_start is not None
                             else round(max(0.0, center - 16.0), 2),
                "mid_sec": round(center, 2),
                "end_sec": round(min(duration, center + 16.0), 2),
                "type": zone.get("type", "possible_transition"),
                "detection_confidence": zone.get("confidence"),
                "bpm_before": bpm_before,
                "bpm_after": bpm_after,
                "bpm_drift": bpm_drift,
                "key_before": key_before.get("key"),
                "key_after": key_after.get("key"),
                "camelot_before": key_before.get("camelot"),
                "camelot_after": key_after.get("camelot"),
                "phrase_beats_off": beats_off,
                "scores": {
                    "phrase": phrase_score,
                    "tempo": tempo_score,
                    "harmonic": harmonic_score,
                    "energy": energy_score,
                },
                "energy_dip_pct": energy_dip_pct,
                "quality_score": quality,
                "label": _label(quality),
                "feedback": _feedback(center, key_before, key_after, harmonic_score),
                "feedback_en": _feedback_en(center, key_before, key_after, harmonic_score),
            }
        )

    return results


def aggregate_transition_scores(transitions: List[Dict]) -> Dict:
    """Mittelt die Teil-Scores ueber alle Uebergaenge (nur gemessene)."""
    def mean_of(key: str) -> Optional[float]:
        values = [
            t["scores"][key] for t in transitions
            if t["scores"].get(key) is not None
        ]
        return round(sum(values) / len(values), 2) if values else None

    return {
        "phrase_timing": mean_of("phrase"),
        "beatmatching": mean_of("tempo"),
        "harmonic": mean_of("harmonic"),
        "energy_shape": mean_of("energy"),
    }


# ---------- Teil-Scores ----------


def _tempo_match_score(bpm_drift: Optional[float]) -> Optional[int]:
    if bpm_drift is None:
        return None
    if bpm_drift <= 1:
        return 100
    if bpm_drift <= 2:
        return 95
    if bpm_drift <= 4:
        return 85
    if bpm_drift <= 6:
        return 70
    if bpm_drift <= 8:
        return 55
    if bpm_drift <= 10:
        return 40
    return 20


def _phrase_alignment_score(beats_off: Optional[float]) -> Optional[int]:
    if beats_off is None:
        return None
    if beats_off <= 1:
        return 100
    if beats_off <= 2:
        return 90
    if beats_off <= 4:
        return 75
    if beats_off <= 8:
        return 55
    return 30


def _energy_dip_pct(zone: Dict) -> Optional[int]:
    before = zone.get("energy_before")
    current = zone.get("energy_current")

    if before is None or current is None or float(before) <= 0:
        return None

    dip = max(0.0, 1.0 - float(current) / float(before)) * 100
    return int(round(min(100.0, dip)))


def _energy_dip_score(dip_pct: Optional[int]) -> Optional[int]:
    """Sweet Spot ~30-50% Einbruch: hoerbar, aber kein Loch im Set."""
    if dip_pct is None:
        return None
    return int(round(max(0.0, 100.0 - abs(dip_pct - 40) * 1.5)))


def _combined_score(
    phrase: Optional[int],
    tempo: Optional[int],
    harmonic: Optional[int],
    energy: Optional[int],
) -> Optional[int]:
    weighted = [
        (phrase, 0.35),
        (tempo, 0.35),
        (harmonic, 0.15),
        (energy, 0.15),
    ]
    available = [(score, weight) for score, weight in weighted if score is not None]

    if not available:
        return None

    total_weight = sum(weight for _, weight in available)
    value = sum(score * weight for score, weight in available) / total_weight

    return int(round(value))


def _label(quality: Optional[int]) -> str:
    if quality is None:
        return "neutral"
    if quality >= 75:
        return "smooth"
    if quality < 55:
        return "rough"
    return "neutral"


# ---------- Feedback-Texte ----------
#
# Dieser Kanal ist seit dem 23.09.2026 LEER. Der Grund steht in _feedback().


def _feedback(
    center: float,
    key_before: Dict,
    key_after: Dict,
    harmonic_score: Optional[int],
) -> str:
    """Ein konkreter Satz pro Uebergang - seit dem 23.09.2026 gar keiner mehr.

    DREI ZWEIGE SIND HIER NACHEINANDER ENTFALLEN, immer aus demselben Grund:
    die Groesse, ueber die der Satz urteilte, hat keinen belegten
    Zusammenhang mit dem menschlichen Urteil.

    Am 14.08.2026 die ersten beiden:

    * phrase_beats_off ("liegt N Beats neben dem Phrasenstart"). Das Raster
      wird am ersten Beat des erkannten Segments verankert, und genau diese
      Grenze verfehlt die Erkennung mit sigma 54,58 s - bei 125 BPM rund
      3,5 Phrasen. Der Bezugspunkt wandert weiter als die Groesse, die er
      messen soll.
    * bpm_drift ("springt von X auf Y BPM"). In 89 % der Uebergaenge exakt
      0,0, weil die Tempo-Schaetzung fuer benachbarte Segmente denselben
      Wert liefert.

    Am 23.09.2026 der dritte und letzte: die HARMONIK.

        "Uebergang bei 11:28 wechselt harmonisch weit (F Minor -> A Minor,
         Camelot 4A -> 8A) - waehle einen Track im Nachbarfeld des
         Camelot-Rads."

    Dieser Satz stand in 311 von 313 Feedback-Saetzen des Bestands - 99 %.
    Er ist eine Handlungsaufforderung, also eine Behauptung ueber Qualitaet.
    Gemessen (tools/eval/harmonik.py, 23.09.2026, gegen dieselben
    Bewertungen wie der Beat-Jitter, mit dessen Zahl als Kontrolle):

        Camelot-Abstand        n=297   rho +0,063   p 0,28
        harmonic_clash_score   n=237   rho -0,138   p 0,034
        kompatibel (n=121) Median 4,0 gegen inkompatibel (n=176) Median 4,0
                                       Mann-Whitney p = 0,355

    Kein Zusammenhang, und das Vorzeichen des Abstands ist sogar positiv.
    Es liegt auch nicht an einer wackligen Tonarterkennung: ueber
    Wiederholungsanalysen derselben Aufnahme behalten 89 von 96 Uebergaengen
    ihre Tonart (93 %). Die Tonart wird zuverlaessig gemessen - sie sagt nur
    nichts ueber die Qualitaet des Uebergangs. Genau der Fall, den
    app/audio/nicht_gemessen.py "befuellt ist nicht gemessen" nennt; dort
    steht die Harmonik seit demselben Tag als unbelegte Dimension.

    DIE TATSACHE GEHT NICHT VERLOREN, nur die Aufforderung. Der weite
    Tonartwechsel steht weiter im Report - als Beobachtung, mit dem Zusatz
    "Ob dich das stoert, ist an deinen Bewertungen nicht ablesbar"
    (app/coach/uebungen.py:_beobachtungen). Diese Stelle hat die Regel
    bereits befolgt, als hier noch der Ratschlag stand; sie besitzt auch die
    Schwelle (SCHWELLE_CAMELOT_SCHRITTE). Hier eine zweite Fassung mit einer
    zweiten Schwelle (harmonic_score <= 40) zu halten, waere genau die
    Doppelung, an der dieses Projekt schon zweimal Tage verloren hat.

    Bleibt: ein LEERER Text. Das ist gewollt. coach_summary uebernimmt nur
    nicht-leere Saetze - und uebernahm bis zum 14.09. den Harmonik-Satz in
    12 von 59 Reports unter der Ueberschrift "das lief gut". Der
    Pegelsprung und der Bass-Overlap haengen ihre Saetze weiterhin an
    (app/audio/loudness.py, app/audio/bass_overlap.py); der Pegelsprung ist
    belegt, und diese Funktion verdoppelt ihn nicht.

    Die Signatur bleibt unveraendert, damit die Aufrufstelle und die
    Nachbarmodule nichts merken.
    """
    return ""


def _feedback_en(
    center: float,
    key_before: Dict,
    key_after: Dict,
    harmonic_score: Optional[int],
) -> str:
    """Englische Variante von _feedback - identische Logik, siehe dort.

    Wichtig: auch hier "" und nicht None. loudness.py und bass_overlap.py
    haengen ihren englischen Satz nur an, wenn das Feld nicht None ist.
    """
    return ""
