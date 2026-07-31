import os
from typing import Dict, List, Optional

from app.audio.beats import detect_beat_grid, segment_tempos
from app.audio.coach_summary import generate_coach_summary
from app.audio.energy import calculate_energy_curve
from app.audio.event_builder import build_mix_events
from app.audio.phrase_grid import build_phrase_grid
from app.audio.rule_engine import evaluate_set_rules
from app.audio.segment_keys import detect_segment_keys_from_chroma, dominant_key
from app.audio.bass_overlap import annotate_bass_overlap
from app.audio.loudness import (
    annotate_transitions as annotate_loudness,
    loudness_curve,
    set_loudness_summary,
)
from app.audio.library_match import (
    fill_gaps_by_segment,
    match_library,
    merge_with_fingerprints,
    transitions_from_matches,
)
from app.library import manager as library_manager
from app.audio.ml_classifier import (
    compute_hiband_envelope,
    compute_mfcc_matrix,
    select_track_changes_ml,
)
from app.audio.track_change_classifier import (
    compute_chroma_matrix,
    detect_track_changes,
)
from app.audio.set_analyzer_helpers import (
    analyze_set_dramaturgy,
    build_set_segments,
    detect_set_transition_zones,
    _score_energy_flow,
)
from app.audio.tempo import detect_tempo
from app.audio.timeline_builder import build_timeline
from app.audio.track_boundary_detector import (
    build_track_segments_from_boundaries,
    detect_track_boundaries,
)
from app.audio.transition_quality import (
    aggregate_transition_scores,
    evaluate_transitions,
)
from app.audio.scoring.beat_alignment import annotate_beat_alignment
from app.audio.scoring.exit_quality import annotate_exit_quality
from app.audio.scoring.stem_annotate import annotate_stem_based_scores
from app.audio.scoring.composite import annotate_composite_scores

# Demucs-Stem-Trennung pro Uebergang ist der teuerste Analyse-Schritt (siehe
# app/audio/scoring/stems.py). Harmonic-Clash/Vocal-Overlap bleiben ohne sie
# ehrlich None statt die Analyse zu verlangsamen oder Werte zu erfinden.
#
# DEFAULT SEIT 30.07.2026: AUS. Gemessen an einem 70-Minuten-Set kostet
# Demucs 25s je Uebergangsfenster x 17 Uebergaenge = 7,1 min von insgesamt
# 10,5 min Analysezeit - also rund 70% der Rechenzeit. Der einzige Abnehmer
# dieser Werte ist composite_quality_score; der wird zwar bis
# analysis_mapper.py in das Frontend-JSON gemappt, aber im gesamten
# React-Code kein einziges Mal ausgelesen (geprueft: 0 Treffer fuer
# "composite_quality_score", "harmonic_clash", "vocal_overlap",
# "exit_quality", "beat_alignment" unter Frontend/src/). Es wurden also
# 70% der Rechenzeit fuer eine Zahl aufgewendet, die kein Nutzer sieht.
#
# Wieder einschalten: MIXCOACH_ENABLE_STEM_SCORING=1
STEM_SCORING_ENABLED = os.environ.get("MIXCOACH_ENABLE_STEM_SCORING", "0") != "0"


def run_set_pipeline(audio, progress=None) -> Dict:
    def report(stage: str, pct: int):
        if progress is not None:
            progress(stage, pct)

    report("preprocessing", 5)
    energy = calculate_energy_curve(audio, window_seconds=1.0)
    tempo = detect_tempo(audio)
    report("feature_extraction", 15)

    all_zones = detect_set_transition_zones(energy)
    dramaturgy = analyze_set_dramaturgy(energy)
    report("transition_detection", 25)

    # --- Boundary-Detection v3: ML-Klassifikator (Gradient Boosting),
    # trainiert auf 5 annotierten Sets, LOSO-validiert: R 88% / P 83%.
    # Fallback auf die heuristische Fusion (v2), wenn kein Modell da ist
    # oder das ML nichts auswaehlt (z.B. voellig untypisches Material). ---
    chroma = compute_chroma_matrix(audio.waveform, audio.sample_rate)
    report("transition_detection", 40)
    mfcc = compute_mfcc_matrix(audio.waveform, audio.sample_rate)
    env_hi = compute_hiband_envelope(audio.waveform, audio.sample_rate)
    report("beatgrid_detection", 45)

    # Beats VOR der Auswahl: die Foote-Novelty (beat-synchron) ist
    # Modell-Feature UND liefert die beat-genaue Start-Verfeinerung.
    beat_grid = detect_beat_grid(audio)
    report("transition_detection", 55)

    ml_selection = select_track_changes_ml(
        all_zones, chroma, mfcc, env_hi,
        audio.duration_seconds, audio.sample_rate,
        beats=beat_grid["beats"], energy_points=energy.get("points", []),
    )

    _, classified_zones = detect_track_changes(
        all_zones, chroma, audio.sample_rate, audio.duration_seconds,
    )

    if ml_selection:
        transition_zones = ml_selection
    else:
        transition_zones, _ = detect_track_changes(
            all_zones, chroma, audio.sample_rate, audio.duration_seconds,
        )

    # --- Library-Fingerprinting: hat der DJ seine Tracks importiert,
    # liefern Fingerprint-Treffer exakte Grenzen + echte Tracknamen.
    # ML/Heuristik bleibt fuer nicht zugeordnete Abschnitte zustaendig. ---
    library_matches = []
    fp_transitions = []
    try:
        library_fps = library_manager.load_fingerprints()
    except Exception:
        library_fps = []
    if library_fps:
        library_matches = match_library(chroma, library_fps, audio.sample_rate)

        # Landmark-Luecken-Fuellung (Shazam-artig, app/audio/landmark_match.
        # gap_fill) ABSICHTLICH NICHT hier verdrahtet: holt zwar harmonisch
        # statische Tracks nach (gemessen 2026-07-15: Recall 0.90 -> 0.925
        # an einer 84-Track-Teilmenge, Precision 1.0), aber am vollen
        # 6113-Track-Index (2026-07-16) zeigte sich, dass eine LIVE-taugliche
        # Kostenschranke noch fehlt: die korrekte volle Suche kostet ~2000s
        # PRO ERKENNUNGSLUECKE (und selbst "vollstaendig erkannte" Sets
        # koennen so eine Luecke haben, wenn ein Chroma-Treffer nur knapp
        # ueber der Schwelle lag), ein probierter billiger Vorfilter
        # (screen_score, rohe Hash-Anzahl) erwies sich als nachweislich
        # falsch (verpasste den einzigen sicher trennbaren Zielfall). Bis
        # ein echter, gemessen validierter Vorfilter existiert, bleibt
        # gap_fill() ein offline nutzbares, getestetes Werkzeug (siehe
        # tools/benchmark_landmark_gapfill.py), aber kein Teil der Live-
        # Analyse - eine 2000s-Verzoegerung waere fuer Nutzer inakzeptabel.

        # Segment-Zweitpass (Chroma, KEIN Landmark): unbenannte Luecken
        # einzeln nachmatchen - deutlich staerkeres Signal als der
        # Voll-Set-Match, weil das Suchproblem pro Luecke viel enger ist
        # (gemessen 2026-07-17 an MixCoach2: 3 von 4 Luecken-Tracks
        # gewannen ihr Segment klar, die der Voll-Match komplett verfehlte;
        # Annahme-Regeln in fill_gaps_by_segment schuetzen die Precision).
        try:
            library_matches = fill_gaps_by_segment(
                chroma, library_matches, library_fps, audio.sample_rate,
            )
        except Exception:
            pass  # Zweitpass darf die Analyse nie abbrechen

        fp_transitions = transitions_from_matches(library_matches)
        if fp_transitions:
            transition_zones = merge_with_fingerprints(
                transition_zones, fp_transitions, library_matches,
            )

    energy_events = [
        z for z in classified_zones
        if all(abs(float(z["time"]) - b["time"]) >= 45.0 for b in transition_zones)
    ]

    # Segmente = echte Tracks (nicht jedes Energie-Event zerteilt das Set).
    segments = build_set_segments(audio.duration_seconds, transition_zones)

    # --- Phase 2: Phrasen, Tonarten, Uebergangs-Qualitaet ---
    tempos = segment_tempos(beat_grid["beats"], segments)
    report("phrase_detection", 70)
    phrase_boundaries = build_phrase_grid(beat_grid["beats"], segments)
    report("key_detection", 75)
    segment_key_list = detect_segment_keys_from_chroma(
        chroma, audio.sample_rate, segments,
    )

    report("transition_analysis", 85)
    transitions_detailed = evaluate_transitions(
        transition_zones=transition_zones,
        segments=segments,
        segment_tempos=tempos,
        segment_keys=segment_key_list,
        phrase_boundaries=phrase_boundaries,
        duration=audio.duration_seconds,
    )

    # Lautheits-Spruenge (K-gewichtet, BS.1770): "kam 3 dB zu laut rein".
    loud_times, loud_values = loudness_curve(audio.waveform, audio.sample_rate)
    annotate_loudness(transitions_detailed, loud_times, loud_values,
                      audio.duration_seconds)

    if fp_transitions:
        for t in transitions_detailed:
            for ft in fp_transitions:
                if abs(t["mid_sec"] - ft["mid"]) <= 60.0:
                    t["track_out"] = " - ".join(
                        x for x in (ft.get("from_artist"), ft.get("from_title")) if x
                    ) or None
                    t["track_in"] = " - ".join(
                        x for x in (ft.get("to_artist"), ft.get("to_title")) if x
                    ) or None
                    t["detection"] = "fingerprint"
                    # Trackwechsel per Fingerprint sicher, aber in einer Luecke
                    # nur geschaetzt positioniert -> ehrlich weiterreichen.
                    t["position_estimated"] = bool(ft.get("position_estimated"))
                    t["gap_seconds"] = ft.get("gap_seconds")
                    t["possible_unrecognized_track"] = bool(
                        ft.get("possible_unrecognized_track")
                    )
                    break

    # Bass-Overlap: nur messbar zwischen zwei sicher erkannten Tracks.
    if len(library_matches) >= 2:
        try:
            annotate_bass_overlap(transitions_detailed, library_matches,
                                  audio.waveform, audio.sample_rate)
        except Exception:
            pass  # Messung darf die Analyse nie abbrechen

    # --- Composite-Score (V3): 5 klangbasierte Dimensionen zusaetzlich zum
    # bestehenden quality_score, siehe app/audio/scoring/composite.py. ---
    annotate_beat_alignment(transitions_detailed, beat_grid["beats"])
    annotate_exit_quality(transitions_detailed, energy.get("points", []))
    if STEM_SCORING_ENABLED:
        report("transition_analysis", 88)
        try:
            annotate_stem_based_scores(transitions_detailed, audio.waveform, audio.sample_rate)
        except Exception:
            pass  # Demucs darf die Analyse nie abbrechen - Felder bleiben None
    annotate_composite_scores(transitions_detailed)

    quality = score_set_quality_v2(
        energy=energy,
        dramaturgy=dramaturgy,
        transitions_detailed=transitions_detailed,
    )

    track_boundaries = detect_track_boundaries(
        {
            "duration": audio.duration_seconds,
            "transition_zones": transition_zones,
        }
    )

    detected_tracks = build_track_segments_from_boundaries(
        duration=audio.duration_seconds,
        boundaries=track_boundaries,
    )

    timeline = build_timeline(
        {
            "track_boundaries": track_boundaries,
            "transition_zones": transition_zones,
            "detected_tracks": detected_tracks,
        }
    )

    events = build_mix_events(
        {
            "duration": audio.duration_seconds,
            "track_boundaries": track_boundaries,
            "transition_zones": transition_zones,
            "detected_tracks": detected_tracks,
        }
    )

    analysis = {
        "filename": audio.filename,
        "duration": audio.duration_seconds,
        "tempo": tempo,
        "energy": energy,
        "transition_zones": transition_zones,
        "energy_events": energy_events,
        "segments": segments,
        "dramaturgy": dramaturgy,
        "quality": quality,
        "beat_grid": {
            "tempo_global": beat_grid["tempo_global"],
            "beat_count": beat_grid["beat_count"],
        },
        "segment_tempos": tempos,
        "segment_keys": segment_key_list,
        "dominant_key": dominant_key(segment_key_list),
        "phrase_boundary_count": len(phrase_boundaries),
        "transitions_detailed": transitions_detailed,
        "track_boundaries": track_boundaries,
        "detected_tracks": detected_tracks,
        "loudness": set_loudness_summary(loud_times, loud_values),
        # Rohe K-gewichtete Lautheitskurve (LUFS-artig, BS.1770) fuer die
        # "Volume/Loudness"-Anzeige im Report - VORHER wurde volumeCurve im
        # Mapper einfach aus der Energiekurve dupliziert (zwei identische
        # Charts, sah aus wie zwei Messungen; Sebastians Frage 2026-07-17).
        "loudness_curve": [
            {"time": float(t), "lufs": float(v)}
            for t, v in zip(loud_times, loud_values)
        ],
        "library": {
            "tracks_in_library": len(library_fps),
            "matches": [
                {"title": m.get("title"), "artist": m.get("artist"),
                 "start": m["start"], "end": m["end"], "score": m["score"]}
                for m in library_matches
            ],
        },
        "timeline": timeline,
        "events": events,
    }

    report("coaching_generation", 92)
    analysis["rule_findings"] = evaluate_set_rules(analysis)
    analysis["coach_summary"] = generate_coach_summary(analysis)
    report("report", 98)

    return analysis


def score_set_quality_v2(
    energy: Dict,
    dramaturgy: Dict,
    transitions_detailed: List[Dict],
) -> Dict:
    """Set-Qualitaet aus der QUALITAET der Uebergaenge, nicht ihrer Anzahl.

    v1 bewertete Energie-Glaette (bestraft Breakdowns) und Uebergangs-
    DICHTE (misst den Detektor, nicht den DJ). v2 mittelt die echten
    Uebergangs-Scores: Phrase-Timing, Tempo-Match, Harmonie, Energieform.
    """
    aggregates = aggregate_transition_scores(transitions_detailed)

    flow = _score_energy_flow(energy)
    dramaturgy_score = _dramaturgy_score(dramaturgy.get("energy_trend"))

    # Stand 31.07.2026: overall ruht nur noch auf dem, was misst.
    #
    # Entfallen sind phrase_timing (0,30) und beatmatching (0,30). Beide sind
    # in derselben Sitzung als nicht tragend nachgewiesen worden - siehe
    # NOT_YET_MEASURED in app/api/analysis_mapper.py: bpm_drift ist in 89 %
    # der Uebergaenge exakt 0 (nur 14 verschiedene Tempowerte ueber 19
    # Aufnahmen), das Phrasenraster haengt an einer Segmentgrenze, die mit
    # sigma = 52,87 s wandert.
    #
    # Die Folge war messbar: beatmatching lag bei 12 von 19 Aufnahmen auf
    # exakt 100 (Spanne 91-100) und hat mit 30 % Gewicht den Gesamtwert
    # zusammengedrueckt. scores.overall spannte ueber alle 19 Aufnahmen nur
    # 12 Punkte (65-77, Median 73) - eine Kopfzahl, die keinen DJ von einem
    # anderen unterscheiden kann. Die verbliebenen Teile streuen ueber 25 bis
    # 26 Punkte.
    #
    # Ebenfalls entfallen: dramaturgy_score (0,10). Er vergibt rising 90,
    # stable 75, falling 60 - ein Set, das ruhig ausklingt, wird bestraft,
    # ohne dass irgendetwas belegt, dass Aufbauen besser ist. Das ist eine
    # Geschmacksentscheidung im Gewand eines Messwerts und faellt unter
    # dieselbe Regel wie die beiden oberen.
    #
    # Alle drei bleiben im Rueckgabe-Dict stehen: sie werden ausgewertet und
    # exportiert. Sie bilden nur keine Note mehr.
    weighted = [
        (aggregates["harmonic"], 0.10),
        (aggregates["energy_shape"], 0.10),
        (flow, 0.10),
    ]
    available = [(s, w) for s, w in weighted if s is not None]

    overall: Optional[float] = None
    if available:
        total_weight = sum(w for _, w in available)
        overall = round(sum(s * w for s, w in available) / total_weight, 2)

    return {
        "overall": overall,
        "phrase_timing": aggregates["phrase_timing"],
        "beatmatching": aggregates["beatmatching"],
        "harmonic": aggregates["harmonic"],
        "energy_shape": aggregates["energy_shape"],
        "energy_flow": flow,
        "dramaturgy": dramaturgy_score,
        "rating": _rating(overall),
        "scoring_version": "v2-transition-quality",
    }


def _dramaturgy_score(trend: Optional[str]) -> float:
    if trend == "rising":
        return 90.0
    if trend == "stable":
        return 75.0
    if trend == "falling":
        return 60.0
    return 50.0


def _rating(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "okay"
    return "needs_work"
