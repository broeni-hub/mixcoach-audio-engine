"""Kernlogik: aus einem Pool von Einzeltracks programmatisch einen Mix mit
exakter Ground Truth bauen.

Speicher-Strategie: Tracks werden EINZELN geladen (nur das benoetigte
Zeitfenster, via librosa offset/duration), der Mix waechst segmentweise -
nie mehr als zwei Track-Fenster gleichzeitig im RAM (Tail des aktuellen +
Head des naechsten Tracks waehrend eines Uebergangs).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from . import __version__
from .config import (
    MAX_BPM_STRETCH_FRACTION,
    MAX_BPM,
    MAX_DRIFT_CORRECTION_FRACTION,
    MIN_BPM,
    MIN_TRACK_DURATION_SECONDS,
    SAMPLE_RATE,
    SEGMENT_SECONDS,
)
from .schema import MixLabel, TrackEntry, TransitionEntry
from .track_prep import TrackAnalysis, analyze_track, camelot_distance, style_cluster
from .transitions import (
    estimate_phase_offset_samples,
    expected_quality_label,
    gain_ratio,
    key_constraint_for_profile,
    pick_transition_start,
    render_transition,
    sample_profile_params,
)

AUDIO_SUFFIXES = (".mp3", ".wav", ".flac", ".m4a", ".aiff", ".aif")
SEGMENT_WINDOW_SECONDS = 2 * SEGMENT_SECONDS  # Ziel-Fensterlaenge je Track im Mix
CANDIDATE_SAMPLE_SIZE = 12  # so viele Kandidaten pro Kettenglied pruefen (nicht den ganzen Pool)
MAX_CHAIN_ATTEMPTS = 8
# Kurzer Audio-Puffer VOR dem eigentlichen Fenster-Start (analysis.intro_end_sec)
# eines "naechsten" Tracks, NUR fuer die Phasenkorrektur in build_mix - siehe
# _load_preroll(). 1s deckt den ±0.5-Beat-Suchraum von
# estimate_phase_offset_samples selbst bei MIN_BPM=70 (halber Beat ~0.43s)
# und die deliberate OFF_BEAT_MS_RANGE (max 300ms) komfortabel ab.
HEAD_PREROLL_SECONDS = 1.0


def scan_track_pool(tracks_dir: Path, genres: tuple[str, ...] = ()) -> list[Path]:
    tracks_dir = Path(tracks_dir)
    paths = [
        p for p in tracks_dir.rglob("*")
        if p.suffix.lower() in AUDIO_SUFFIXES
        and (not genres or any(g.lower() in str(p).lower() for g in genres))
    ]
    return sorted(paths)


class ChainBuildError(RuntimeError):
    pass


def _bpm_compatible(bpm_a: float, bpm_b: float) -> bool:
    if bpm_a <= 0:
        return False
    return abs(bpm_b - bpm_a) / bpm_a <= MAX_BPM_STRETCH_FRACTION


def _select_chain(
    pool: list[Path],
    n_tracks: int,
    rng: random.Random,
    profile_sequence: list[str],
    analysis_cache: dict[str, TrackAnalysis],
) -> list[TrackAnalysis]:
    """Waehlt n_tracks Tracks: BPM-Nachbarn innerhalb MAX_BPM_STRETCH_FRACTION,
    kein Track doppelt im Mix, key_clash/train_wreck-Uebergaenge erzwingen
    ein Trackpaar mit Camelot-Distanz >= KEY_CLASH_MIN_CAMELOT_DISTANCE."""

    def get_analysis(path: Path) -> Optional[TrackAnalysis]:
        """None statt Exception bei kaputten/unlesbaren Dateien - ein
        einzelner defekter Track in einer >6000-Datei-Library darf die
        Kettenwahl nicht abbrechen, nur diesen Kandidaten verwerfen."""
        key = str(path)
        if key in analysis_cache:
            return analysis_cache[key]
        try:
            analysis = analyze_track(path)
        except Exception:
            return None
        if analysis.duration_seconds < MIN_TRACK_DURATION_SECONDS:
            return None
        analysis_cache[key] = analysis
        return analysis

    remaining = list(pool)
    rng.shuffle(remaining)

    chain: list[TrackAnalysis] = []
    used: set[Path] = set()
    while remaining and not chain:
        first_path = remaining.pop()
        first = get_analysis(first_path)
        if first is not None:
            chain.append(first)
            used.add(first_path)
    if not chain:
        raise ChainBuildError("Kein lesbarer Track im Pool gefunden.")

    for i in range(1, n_tracks):
        key_constraint = key_constraint_for_profile(profile_sequence[i - 1]) if i - 1 < len(profile_sequence) else None
        prev = chain[-1]

        found: Optional[TrackAnalysis] = None
        found_path: Optional[Path] = None

        # Stil-Kompatibilitaet: BPM+Tonart allein reichen nicht - unter dem
        # breiten --genres-Filter landeten z.B. Minimal Techno und Afro
        # House im selben Pool und wurden trotz stilistischem Bruch gepaart
        # (Sebastians Feedback: "stilistisch kaum zueinander passend",
        # 2026-07-14). STYLE_CLUSTERS in config.py definiert, welche Ordner
        # als gegenseitig kompatibel gelten. ERST auf Pfad-Ebene filtern
        # (billig, keine Audio-Analyse), NICHT erst nach dem teuren
        # analyze_track() pruefen - sonst verbrennt das kleine
        # Zufalls-Sample (CANDIDATE_SAMPLE_SIZE*MAX_CHAIN_ATTEMPTS Versuche
        # aus dem GESAMTEN, stilistisch gemischten Pool) fast immer auf
        # Kandidaten, die sowieso am Stil scheitern - das liess in der
        # ersten Version praktisch jede Kette scheitern.
        prev_cluster = style_cluster(prev.source_path)
        pool_iter = [
            p for p in remaining
            if p not in used and style_cluster(p) == prev_cluster
        ]
        rng.shuffle(pool_iter)

        for attempts, path in enumerate(pool_iter, start=1):
            if attempts > CANDIDATE_SAMPLE_SIZE * MAX_CHAIN_ATTEMPTS:
                break
            candidate = get_analysis(path)
            if candidate is None:
                continue
            if not (MIN_BPM <= candidate.bpm <= MAX_BPM):
                continue
            if not _bpm_compatible(prev.bpm, candidate.bpm):
                continue
            if key_constraint is not None:
                mode, threshold = key_constraint
                dist = camelot_distance(prev.camelot, candidate.camelot)
                if dist is None:
                    continue
                if mode == "max" and dist > threshold:
                    continue
                if mode == "min" and dist < threshold:
                    continue
            found, found_path = candidate, path
            break

        if found is None:
            raise ChainBuildError(
                f"Kein kompatibler naechster Track gefunden (Kettenposition {i}, "
                f"vorheriger BPM={prev.bpm}, key_constraint={key_constraint})."
            )
        chain.append(found)
        used.add(found_path)

    return chain


def _load_window(analysis: TrackAnalysis, want_seconds: float) -> np.ndarray:
    """Laedt ab dem Ende des erkannten Intros (analysis.intro_end_sec), NICHT
    ab Dateianfang - sonst ist der Kopf jedes eingeblendeten Tracks dessen
    eigenes leises Intro statt "in the groove" laufender Musik. Ohne diesen
    Versatz klang jeder Uebergang wie Fade-out-dann-Fade-in statt einem
    echten Overlap zweier energiereicher Abschnitte (Sebastians Rating-
    Stichprobe vom 2026-07-13: durchgaengig 1-2 von 5)."""
    import librosa
    start = min(analysis.intro_end_sec, max(0.0, analysis.duration_seconds - 10.0))
    duration = min(want_seconds, analysis.duration_seconds - start)
    y, _ = librosa.load(analysis.source_path, sr=SAMPLE_RATE, mono=True,
                        offset=start, duration=duration)
    return y


def _load_preroll(analysis: TrackAnalysis, seconds: float) -> np.ndarray:
    """Kurzer Audio-Puffer VOR analysis.intro_end_sec (dem sonstigen Fenster-
    Start, siehe _load_window) - erlaubt der Phasenkorrektur in build_mix,
    B auch in Richtung "frueher im Track einsteigen" zu verschieben. Ohne
    diesen Puffer wurde jede Korrektur in diese Richtung stillschweigend auf
    0 (= keine Korrektur) gekappt, weil kein Audio vor Fenster-Index 0
    verfuegbar war - gemessen: ~210ms unkorrigierbarer Rest-Versatz selbst im
    guenstigsten Fall (identische Tonart, fast identisches Tempo, 2026-07-14).
    Leeres Array, wenn der Track keinen Vorlauf vor intro_end_sec hat."""
    import librosa
    nominal_start = min(analysis.intro_end_sec, max(0.0, analysis.duration_seconds - 10.0))
    actual = min(seconds, nominal_start)
    if actual <= 0:
        return np.zeros(0, dtype=np.float32)
    y, _ = librosa.load(analysis.source_path, sr=SAMPLE_RATE, mono=True,
                        offset=nominal_start - actual, duration=actual)
    return y


RESURGENCE_RMS_RATIO = 2.0  # ab diesem Vielfachen des Referenzpegels gilt der Abschnitt als "Energie ist zurueck"
MIN_OVERLAP_BEATS_AFTER_TRIM = 4.0


def _trim_overlap_for_resurgence(
    analysis: TrackAnalysis, start_sec: float, overlap_seconds: float, bpm: float,
) -> float:
    """Kappt einen Overlap, wenn die Energie DES AUSLAUFENDEN TRACKS
    innerhalb des gewaehlten Overlap-Fensters wieder deutlich ansteigt
    (typisches Breakdown-dann-Hook-Arrangement) - sonst kollidiert eine
    zurueckkehrende Melodie mit dem neuen Track, mitten im Blend (Sebastians
    Feedback: Melodie aus Track 1 "kickt wieder rein" bei einem 64-Beat-
    Overlap, 2026-07-14 - RMS-Kurve zeigte einen klaren Sprung von ~0.02 auf
    ~0.18 genau an der von ihm gehoerten Stelle). Nutzt die ohnehin schon pro
    Track berechnete Energiekurve (analysis.rms_times/rms_values) - kein
    Demucs/Stem-Trennung noetig. rms_times ist absolute Datei-Zeit (siehe
    analyze_track), hier auf Fenster-relative Zeit umgerechnet, analog zum
    Phrasen-Grenzen-Fix oben."""
    offset = analysis.intro_end_sec
    span = [
        (t - offset, v) for t, v in zip(analysis.rms_times, analysis.rms_values)
        if start_sec <= t - offset <= start_sec + overlap_seconds
    ]
    if len(span) < 4:
        return overlap_seconds

    reference_window = span[:3]
    reference = max(1e-6, float(np.median([v for _, v in reference_window])))

    consecutive_high = 0
    for t, v in span[2:]:
        if v > reference * RESURGENCE_RMS_RATIO:
            consecutive_high += 1
            if consecutive_high >= 2:
                trimmed = max(0.0, t - start_sec)
                beat_len = 60.0 / bpm if bpm > 0 else 0.5
                trimmed_beats = max(MIN_OVERLAP_BEATS_AFTER_TRIM, np.floor(trimmed / beat_len))
                return min(overlap_seconds, trimmed_beats * beat_len)
        else:
            consecutive_high = 0
    return overlap_seconds


VOCAL_MIN_SAMPLES_SECONDS = 1.5  # wie app/audio/scoring/vocal_overlap.py
VOCAL_SILENCE_RMS = 0.002  # wie app/audio/scoring/vocal_overlap.py SILENCE_RMS
# Anteil vom EIGENEN MAXIMUM (wie vocal_overlap.py's ACTIVE_RATIO=0.35),
# NICHT ein Vielfaches des Medians - eine Schwelle relativ zum Median hat
# durchgehenden Gesang (z.B. eine ganze, gleichmaessig gesungene Strophe)
# nie als "aktiv" erkannt, weil der Pegel kaum ueber seinen eigenen Median
# hinausschwankt (leer getestet an zwei garantiert durchgehend gesungenen
# 4hero-Strophen, 2026-07-14 - Median-Schwelle loeste in beiden nie aus).
VOCAL_ACTIVE_RATIO = 0.35
VOCAL_WINDOW_SECONDS = 1.0


def _vocal_rms_curve(vocals: np.ndarray, sample_rate: int, window_seconds: float = VOCAL_WINDOW_SECONDS) -> tuple[list[float], list[float]]:
    """Grobe RMS-Kurve NUR des isolierten Vocals-Stems, gleiche
    Fensterlaenge wie app/audio/energy.calculate_energy_curve fuer
    Konsistenz mit _trim_overlap_for_resurgence."""
    n = max(1, int(window_seconds * sample_rate))
    times: list[float] = []
    values: list[float] = []
    for start in range(0, len(vocals), n):
        chunk = vocals[start:start + n]
        if chunk.size == 0:
            continue
        times.append(start / sample_rate)
        values.append(float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2))))
    return times, values


def _trim_overlap_for_vocal_clash(
    tail_candidate: np.ndarray, head_candidate: np.ndarray, sample_rate: int,
    overlap_seconds: float, bpm: float,
) -> float:
    """Kappt den Overlap zusaetzlich, wenn BEIDE Tracks im selben Abschnitt
    hoerbaren Gesang haben - _trim_overlap_for_resurgence (RMS der GANZEN
    Mischung) erkennt nur allgemeine Energie-Ruecksprnge, nicht z.B. leisen
    Gesang ueber leiser Instrumental-Begleitung, der trotzdem matschig klingt,
    sobald zwei Gesangsspuren gleichzeitig laufen (Sebastians Wunsch:
    "Timing sollte bei monotonem Beat liegen, nicht bei Vocal-Parts, die sich
    ueberlappen koennten", 2026-07-14). Nutzt dieselbe Demucs-Trennung wie
    app/audio/scoring/vocal_overlap.py (dort: Bewertung EINES bereits
    gebauten Uebergangs; hier: VORAB pruefen, ob der gewaehlte Ausschnitt
    ueberhaupt geeignet ist). Faellt ehrlich auf "nichts aendern" zurueck,
    wenn Demucs nicht verfuegbar ist oder fehlschlaegt - kein geratener Wert.
    Kandidaten-Audio bewusst VOR Gain-Staging/Phasenkorrektur (grobe
    Content-Pruefung, keine sample-genauen Verschiebungen noetig)."""
    from app.audio.scoring import stems as stem_lib

    min_samples = int(VOCAL_MIN_SAMPLES_SECONDS * sample_rate)
    if tail_candidate.size < min_samples or head_candidate.size < min_samples:
        return overlap_seconds

    tail_sep = stem_lib.separate_window(tail_candidate, sample_rate)
    head_sep = stem_lib.separate_window(head_candidate, sample_rate)
    if tail_sep is None or head_sep is None:
        return overlap_seconds

    stem_sr = stem_lib.stems_samplerate()
    tail_times, tail_vals = _vocal_rms_curve(tail_sep["vocals"], stem_sr)
    head_times, head_vals = _vocal_rms_curve(head_sep["vocals"], stem_sr)
    if len(tail_vals) < 2 or len(head_vals) < 2:
        return overlap_seconds

    tail_max = max(tail_vals)
    head_max = max(head_vals)
    if max(tail_max, head_max) < VOCAL_SILENCE_RMS:
        return overlap_seconds  # in keinem Stem hoerbarer Gesang - kein Risiko

    tail_active = {round(t, 1): v >= tail_max * VOCAL_ACTIVE_RATIO for t, v in zip(tail_times, tail_vals)}
    head_active = {round(t, 1): v >= head_max * VOCAL_ACTIVE_RATIO for t, v in zip(head_times, head_vals)}

    clash_times = sorted(
        t for t, active in tail_active.items() if active and head_active.get(t, False)
    )
    if not clash_times:
        return overlap_seconds

    first_clash = clash_times[0]
    beat_len = 60.0 / bpm if bpm > 0 else 0.5
    trimmed_beats = max(MIN_OVERLAP_BEATS_AFTER_TRIM, np.floor(first_clash / beat_len))
    return min(overlap_seconds, trimmed_beats * beat_len)


def _apply_content_trims(
    analysis: TrackAnalysis, start_sec: float, overlap_seconds: float, bpm: float,
    window_use: np.ndarray, next_window_raw: np.ndarray, sample_rate: int,
) -> float:
    """Wendet beide Content-Kuerzungen nacheinander an (RMS-Ruecksprung,
    dann Demucs-Vocal-Clash) und gibt den resultierenden Overlap in
    Sekunden zurueck. Kandidaten-Audio bewusst grob (vor Gain/Phase)."""
    trimmed = _trim_overlap_for_resurgence(analysis, start_sec, overlap_seconds, bpm)
    start_idx = int(start_sec * sample_rate)
    overlap_idx = int(trimmed * sample_rate)
    tail_candidate = window_use[start_idx:start_idx + overlap_idx]
    head_candidate = next_window_raw[:overlap_idx]
    return _trim_overlap_for_vocal_clash(tail_candidate, head_candidate, sample_rate, trimmed, bpm)


# Unter dieser Laenge klingt selbst ein technisch sauberer Blend wie ein
# harter Schnitt statt einem echten Uebergang (siehe CLEAN_OVERLAP_BEATS_
# CHOICES in config.py, aus genau diesem Grund auf 16/32/64 begrenzt).
# Nur fuer "clean" relevant - off_beat/key_clash duerfen laut Design auch
# kurze Overlaps haben (OVERLAP_BEATS_CHOICES enthaelt bewusst 4/8).
MIN_SAFE_CLEAN_OVERLAP_BEATS = 16.0


def _pick_safe_clean_start(
    analysis: TrackAnalysis, phrase_boundaries: list[float], tail_duration: float,
    overlap_seconds: float, bpm: float, window_use: np.ndarray,
    next_window_raw: np.ndarray, sample_rate: int,
) -> tuple[float, float]:
    """Wie pick_transition_start, aber probiert bei "clean" mehrere
    Phrasenanker durch (spaetester zuerst), statt nur den spaetesten zu
    nehmen und dann bestmoeglich zu kuerzen - sonst kann eine kurzfristige
    Melodie-Rueckkehr/Vocal-Kollision einen absurd kurzen "Blend" erzwingen,
    der wie ein harter Schnitt klingt statt einem echten Uebergang
    (Sebastians Feedback: "Clean-Uebergaenge sind eigentlich harte Cuts,
    tbh", 2026-07-14 - eine 4-Beat-Kuerzung war genau das). Gibt
    (start_sec, overlap_seconds) zurueck; faellt auf den spaetesten Anker
    mit bestmoeglicher Kuerzung zurueck, wenn KEIN Anker die Mindestlaenge
    erreicht (ehrlich kurz statt eine Ausnahme/Endlosschleife)."""
    latest_allowed = max(0.0, tail_duration - overlap_seconds)
    candidate_starts = sorted(
        {b for b in phrase_boundaries if b <= latest_allowed} | {latest_allowed},
        reverse=True,
    )
    beat_len = 60.0 / bpm if bpm > 0 else 0.5

    fallback: Optional[tuple[float, float]] = None
    for candidate_start in candidate_starts:
        candidate_overlap = _apply_content_trims(
            analysis, candidate_start, overlap_seconds, bpm, window_use, next_window_raw, sample_rate,
        )
        if fallback is None:
            fallback = (candidate_start, candidate_overlap)
        if candidate_overlap / beat_len >= MIN_SAFE_CLEAN_OVERLAP_BEATS:
            return candidate_start, candidate_overlap

    return fallback if fallback is not None else (latest_allowed, overlap_seconds)


def _phrase_boundaries_in_window(analysis: TrackAnalysis, window_seconds: float, bars_per_phrase: int = 8) -> list[float]:
    """Phrasengrenzen aus analysis.phrase_grids sind absolute Datei-Zeiten
    (ab Sekunde 0 der Originaldatei), aber window_use beginnt erst bei
    analysis.intro_end_sec (siehe _load_window) - Index 0 im Fenster ist
    also NICHT Datei-Zeit 0. Ohne die Umrechnung wurden Phrasengrenzen aus
    dem uebersprungenen Intro (Datei-Zeit < intro_end_sec) faelschlich als
    Fenster-relative Ankerpunkte benutzt - der Uebergang landete dadurch
    oft einige Sekunden VOR der tatsaechlichen Phrasengrenze im Fenster
    (Sebastians Feedback: "Timing passt noch nicht ganz", 2026-07-14).
    window_relative_outro (unten) macht dieselbe Umrechnung bereits richtig -
    hier fehlte sie."""
    grid = analysis.phrase_grids.get(bars_per_phrase, [])
    offset = analysis.intro_end_sec
    return [b - offset for b in grid if offset <= b <= offset + window_seconds]


def build_mix(
    track_paths: list[Path],
    profile_sequence: list[str],
    rng: random.Random,
    mix_id: str,
    analysis_cache: Optional[dict[str, TrackAnalysis]] = None,
) -> tuple[np.ndarray, MixLabel]:
    """Baut EINEN Mix aus vorgegebenen Tracks + Quality-Profile-Sequenz
    (len(profile_sequence) == len(track_paths) - 1)."""
    if len(track_paths) < 2:
        raise ValueError("Mindestens 2 Tracks pro Mix noetig.")
    if len(profile_sequence) != len(track_paths) - 1:
        raise ValueError("profile_sequence muss genau len(tracks)-1 Eintraege haben.")

    analysis_cache = analysis_cache if analysis_cache is not None else {}

    def get_analysis(path: Path) -> TrackAnalysis:
        key = str(path)
        if key not in analysis_cache:
            analysis_cache[key] = analyze_track(path)
        return analysis_cache[key]

    analyses = [get_analysis(p) for p in track_paths]
    windows = [_load_window(a, SEGMENT_WINDOW_SECONDS) for a in analyses]

    mix_parts: list[np.ndarray] = []
    track_entries: list[TrackEntry] = []
    transition_entries: list[TransitionEntry] = []
    cursor_sec = 0.0
    # Tatsaechlich gespieltes Tempo je Track-Index - NICHT analyses[i].bpm
    # (das waere das unveraenderte Original). Bei Ketten von 3+ Tracks
    # wurde bisher faelschlich das Original-Tempo des VORGAENGERS als
    # Ziel fuer die Zeitangleichung genutzt, statt dessen tatsaechlich
    # gespieltes (ggf. selbst schon gestrecktes) Tempo - dadurch driftete
    # ab dem ZWEITEN Uebergang in einer Kette ein echter, mehrere-Prozent-
    # Tempo-Versatz ein (gefunden an einem 4-Track-Mix: Track 1 spielte
    # bei 123.05, Track 2 wurde aber auf 126.05 angeglichen - Track 1s
    # ORIGINAL-Tempo, nicht sein tatsaechliches. Sebastians Feedback:
    # "Tempi sind unterschiedlich, klingt holprig", "Beats passen nicht
    # aufeinander", 2026-07-14). Nur der ERSTE Uebergang einer Kette blieb
    # zufaellig unbetroffen (Track 0 wird nie gestreckt, bpm_in_mix ==
    # analyses[0].bpm dort sowieso) - deshalb ist der Bug bei 2-Track-
    # Testmixes bisher nie aufgefallen.
    actual_bpm_by_index: dict[int, float] = {}

    for i, (analysis, window) in enumerate(zip(analyses, windows)):
        bpm_in_mix = analysis.bpm
        stretch_method = "none"
        window_use = window

        if i > 0:
            prev_bpm = actual_bpm_by_index[i - 1]
            if profile_sequence[i - 1] != "off_beat" or True:
                # Tempo wird IMMER an den Vorgaenger angeglichen, ausser das
                # Profil verlangt explizit Tempo-Mismatch (aktuell keins -
                # off_beat/key_clash/train_wreck simulieren Fehler ueber
                # Beat-Phase/Tonart, nicht ueber falsches Tempo).
                ratio = prev_bpm / analysis.bpm if analysis.bpm > 0 else 1.0
                if abs(ratio - 1.0) > 1e-3:
                    # pedalboard.time_stretch (Spotify) nutzt intern dieselbe
                    # Rubberband-Engine, aber vorkompiliert per pip - kein
                    # externes CLI-Tool/Download noetig (der urspruengliche
                    # pyrubberband-Weg braeuchte zusaetzlich die
                    # rubberband-CLI-Binary, die es fuer Windows nicht
                    # unkompliziert per Paketquelle gibt, 2026-07-14).
                    # librosa's Phasenvocoder bleibt nur als letzter
                    # Rueckfall, falls pedalboard mal fehlt/fehlschlaegt.
                    try:
                        import pedalboard
                        # pedalboard.time_stretch gibt (anders als librosa)
                        # (channels, samples) zurueck, auch bei Mono-Input -
                        # .reshape(-1) macht das mit dem Rest der Pipeline
                        # (durchgehend flache 1D-Mono-Arrays) kompatibel.
                        window_use = pedalboard.time_stretch(
                            window_use.astype(np.float32), SAMPLE_RATE, stretch_factor=ratio,
                        ).reshape(-1)
                        stretch_method = "pedalboard"
                    except Exception:
                        import librosa
                        window_use = librosa.effects.time_stretch(window_use, rate=ratio)
                        stretch_method = "librosa"
                    bpm_in_mix = prev_bpm

        actual_bpm_by_index[i] = bpm_in_mix

        overlap_seconds = 0.0
        beat_offset_samples = 0
        curve = "linear"
        transition_type = "crossfade"
        phrase_offset_beats = 0.0
        beat_offset_ms = 0.0
        overlap_beats = 0.0

        if i < len(analyses) - 1:
            profile = profile_sequence[i]
            params = sample_profile_params(profile, rng)
            transition_type = params["transition_type"]
            curve = params["curve"]
            overlap_beats = params["overlap_beats"]
            phrase_offset_beats = params["phrase_offset_beats"]
            beat_offset_ms = params["beat_offset_ms"]
            overlap_seconds = overlap_beats * 60.0 / bpm_in_mix
            beat_offset_samples = int(beat_offset_ms / 1000.0 * SAMPLE_RATE)

            phrase_boundaries = _phrase_boundaries_in_window(analysis, len(window_use) / SAMPLE_RATE)
            # Uebergang nicht spaeter als den (fensterrelativen) Outro-Beginn
            # zulassen - sonst landet der Blend im bereits ausklingenden Teil
            # des Tracks und klingt nach Fade-out statt echtem Overlap.
            window_relative_outro = max(0.0, analysis.outro_start_sec - analysis.intro_end_sec)
            tail_duration = min(len(window_use) / SAMPLE_RATE, window_relative_outro) \
                if window_relative_outro > 0 else len(window_use) / SAMPLE_RATE
            if transition_type == "cut":
                start_sec = pick_transition_start(
                    phrase_boundaries, tail_duration,
                    overlap_seconds, bpm_in_mix, phrase_offset_beats,
                )
            elif profile == "clean":
                start_sec, overlap_seconds = _pick_safe_clean_start(
                    analysis, phrase_boundaries, tail_duration, overlap_seconds,
                    bpm_in_mix, window_use, windows[i + 1], SAMPLE_RATE,
                )
                overlap_beats = overlap_seconds * bpm_in_mix / 60.0
            else:
                start_sec = pick_transition_start(
                    phrase_boundaries, tail_duration,
                    overlap_seconds, bpm_in_mix, phrase_offset_beats,
                )
                overlap_seconds = _apply_content_trims(
                    analysis, start_sec, overlap_seconds, bpm_in_mix,
                    window_use, windows[i + 1], SAMPLE_RATE,
                )
                overlap_beats = overlap_seconds * bpm_in_mix / 60.0

            tail_a = window_use[:int(start_sec * SAMPLE_RATE) + int(overlap_seconds * SAMPLE_RATE)]
            solo_part = window_use[:int(start_sec * SAMPLE_RATE)]
        else:
            solo_part = window_use
            tail_a = None

        mix_parts.append(solo_part)
        track_start = cursor_sec
        cursor_sec += len(mix_parts[-1]) / SAMPLE_RATE

        if tail_a is not None:
            next_analysis = analyses[i + 1]
            next_window_raw = windows[i + 1]
            overlap_samples = int(overlap_seconds * SAMPLE_RATE)
            a_overlap_ref = tail_a[-overlap_samples:] if overlap_samples <= len(tail_a) else tail_a

            # Kurzer Vorlauf-Puffer vor next_window_raw's Index 0, NUR fuer
            # die Phasenkorrektur unten - siehe _load_preroll(). preroll_len
            # ist ab hier die Basis-Verschiebung fuer "b_start=0" (=
            # nominaler Fenster-Anfang, keine Korrektur).
            preroll = _load_preroll(next_analysis, HEAD_PREROLL_SECONDS)
            preroll_len = len(preroll)
            if preroll_len:
                next_window_raw = np.concatenate([preroll, next_window_raw])

            # Gain-Staging auf das GANZE naechste Fenster anwenden (nicht nur
            # auf den Overlap-Ausschnitt) - sonst springt die Lautstaerke von
            # Track B genau am Ende des Blends zurueck auf seinen Rohpegel,
            # was einen neuen, unnatuerlichen Sprung erzeugt (gefunden ueber
            # Sebastians Rating-Stichprobe, 2026-07-13). "cut" bewusst
            # ausgenommen - ein hoerbarer Pegelsprung gehoert zu "abrupt" dazu.
            # Referenz bewusst am NOMINALEN Fenster-Anfang (+preroll_len)
            # gemessen, nicht bei Index 0 - sonst waere die Referenz der
            # (meist leisere) Vorlauf-Puffer statt des tatsaechlichen
            # Overlap-Materials.
            if transition_type != "cut" and len(next_window_raw) >= preroll_len + overlap_samples:
                gain = gain_ratio(a_overlap_ref, next_window_raw[preroll_len:preroll_len + overlap_samples])
                next_window_raw = next_window_raw * gain
                windows[i + 1] = next_window_raw[preroll_len:]

            # Beat-PHASE ausrichten, zusaetzlich zur Tempo-Angleichung oben -
            # gleiche BPM heisst noch lange nicht, dass die Kicks beider
            # Tracks auch zeitlich uebereinanderfallen. Nur automatisch
            # korrigieren, wenn das Profil nicht bereits bewusst eine
            # Verschiebung will (off_beat/train_wreck setzen beat_offset_ms
            # selbst, das soll disharmonisch bleiben).
            drift_correction_samples = 0
            if beat_offset_samples == 0 and transition_type != "cut" and bpm_in_mix > 0:
                beat_len_samples = int(60.0 / bpm_in_mix * SAMPLE_RATE)
                region_len = min(len(a_overlap_ref), len(next_window_raw), beat_len_samples * 4)
                if region_len > beat_len_samples:
                    # Anfang des Overlaps: A- und B-Material an der GLEICHEN
                    # relativen Overlap-Position vergleichen (vorher stand
                    # hier faelschlich a_overlap_ref[-region_len:] - das
                    # Ende von A's Tail gegen den Anfang von B's Fenster,
                    # was bei 16-64-Beat-Overlaps NICHT dieselbe reale
                    # Zeitposition ist. Gefunden beim Nachmessen des
                    # gemeldeten Drifts, 2026-07-14).
                    #
                    # Vorzeichen: estimate_phase_offset_samples(a, b, ...)
                    # liefert das Lag L, fuer das a(t+L) am besten zu b(t)
                    # passt - d.h. B's Ereignisse liegen L Samples VOR denen
                    # von A. Um das auszugleichen, muss B-Material aus einer
                    # FRUEHEREN Quellposition benutzt werden (b_start=-L),
                    # nicht aus einer spaeteren (b_start=+L). Empirisch
                    # nachgemessen (2026-07-14): b_start=+L verschlimmerte
                    # den Rest-Versatz messbar statt ihn zu beheben - das
                    # war seit der ersten Phase-Korrektur (2026-07-13) so.
                    beat_offset_samples = -estimate_phase_offset_samples(
                        a_overlap_ref[:region_len],
                        next_window_raw[preroll_len:preroll_len + region_len],
                        SAMPLE_RATE, beat_len_samples,
                    )
                    # +preroll_len: b_start=0 im alten Sinn (keine Korrektur)
                    # liegt jetzt bei Index preroll_len, nicht 0 - siehe
                    # _load_preroll(). Ohne diese Verschiebung waere jede
                    # Korrektur mit beat_offset_samples<0 weiterhin auf 0
                    # gekappt worden, trotz des neuen Puffers.
                    b_start = max(0, min(preroll_len + beat_offset_samples, len(next_window_raw) - overlap_samples))

                    # Ende des Overlaps: dieselbe Messung, nur am ANDEREN
                    # Ende des Overlap-Fensters (unter Beruecksichtigung von
                    # b_start). Ein einmaliger globaler Tempo-Match + eine
                    # einmalige Korrektur am Anfang reicht nicht, wenn A/B
                    # minimal unterschiedliches LOKALES Tempo haben - der
                    # Versatz waechst dann ueber den Overlap hinweg weiter
                    # (gemessen: ~70ms am Anfang -> ~230ms am Ende eines
                    # 16-Beat-Overlaps, Sebastians Rating dazu: 3/5,
                    # "Beats liegen nicht exakt uebereinander", 2026-07-14).
                    a_end_region = a_overlap_ref[-region_len:]
                    b_end_start = b_start + overlap_samples - region_len
                    if b_end_start >= 0 and b_end_start + region_len <= len(next_window_raw):
                        b_end_region = next_window_raw[b_end_start:b_end_start + region_len]
                        # Gleiche Vorzeichen-Konvention wie oben: das
                        # zurueckgegebene Lag ist "B liegt L Samples VOR A",
                        # also muss die Korrektur mit -L angesetzt werden.
                        end_lag = -estimate_phase_offset_samples(
                            a_end_region, b_end_region, SAMPLE_RATE, beat_len_samples,
                        )
                        max_drift = int(overlap_samples * MAX_DRIFT_CORRECTION_FRACTION)
                        drift_correction_samples = max(-max_drift, min(max_drift, end_lag))

            # Absolute Position in next_window_raw (inkl. preroll_len-Basis) -
            # gilt fuer BEIDE Faelle: automatisch gesuchte Korrektur (b_start
            # oben schon so berechnet) UND bewusst gesetzter Versatz
            # (off_beat/train_wreck, dort wurde b_start nie gesetzt).
            b_start_absolute = max(0, min(preroll_len + beat_offset_samples, len(next_window_raw) - overlap_samples))

            overlap_audio = render_transition(
                a_overlap_ref,
                next_window_raw, SAMPLE_RATE, transition_type, curve,
                overlap_samples, b_start_absolute,
                bass_swap=(transition_type == "eq_blend"),
                drift_correction_samples=drift_correction_samples,
            )
            mix_parts.append(overlap_audio)
            overlap_start_sec = cursor_sec
            cursor_sec += len(overlap_audio) / SAMPLE_RATE
            overlap_end_sec = cursor_sec

            dist = camelot_distance(analysis.camelot, next_analysis.camelot)
            transition_entries.append(TransitionEntry(
                index=i,
                type=transition_type,
                quality_profile=profile,
                overlap_start=round(overlap_start_sec, 2),
                overlap_end=round(overlap_end_sec, 2),
                center_time=round((overlap_start_sec + overlap_end_sec) / 2, 2),
                overlap_beats=overlap_beats,
                crossfade_curve=curve,
                phrase_offset_beats=phrase_offset_beats,
                beat_offset_ms=round(beat_offset_ms, 1),
                key_compatibility_camelot_distance=dist,
                expected_quality_label=expected_quality_label(
                    profile, phrase_offset_beats=phrase_offset_beats,
                    beat_offset_ms=beat_offset_ms, camelot_distance_value=dist,
                ),
            ))
            # naechster Track startet NACH dem Overlap - Kopf des Overlaps
            # wird beim naechsten Schleifendurchlauf uebersprungen. Muss
            # denselben b_start_absolute nutzen wie render_transition(),
            # sonst springt die Solo-Fortsetzung von B auf einen anderen
            # Sample als den letzten im Overlap gespielten zurueck/vor - ein
            # hoerbarer Stotterer/Phasensprung genau am Ende jedes
            # phasenkorrigierten Uebergangs (gefunden beim Review von
            # Sebastians "besser, aber immer noch nicht harmonisch"-
            # Feedback, 2026-07-14).
            windows[i + 1] = next_window_raw[b_start_absolute + overlap_samples:]

        track_end = cursor_sec
        track_entries.append(TrackEntry(
            index=i,
            source_file=str(analysis.source_path),
            bpm_original=analysis.bpm,
            bpm_in_mix=round(bpm_in_mix, 2),
            key=analysis.key,
            camelot=analysis.camelot,
            start_in_mix=round(track_start, 2),
            end_in_mix=round(track_end, 2),
            stretch_method=stretch_method,
        ))

    waveform = np.concatenate(mix_parts).astype(np.float32)
    label = MixLabel(
        mix_id=mix_id,
        generator_version=__version__,
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        sample_rate=SAMPLE_RATE,
        duration_seconds=round(len(waveform) / SAMPLE_RATE, 2),
        tracks=track_entries,
        transitions=transition_entries,
    )
    return waveform, label


def generate_one_mix(
    pool: list[Path],
    n_tracks: int,
    profile_distribution: dict[str, float],
    rng: random.Random,
    mix_id: str,
    analysis_cache: Optional[dict[str, TrackAnalysis]] = None,
) -> tuple[np.ndarray, MixLabel]:
    profiles = list(profile_distribution.keys())
    weights = list(profile_distribution.values())
    profile_sequence = [rng.choices(profiles, weights=weights, k=1)[0] for _ in range(n_tracks - 1)]

    analysis_cache = analysis_cache if analysis_cache is not None else {}
    chain = _select_chain(pool, n_tracks, rng, profile_sequence, analysis_cache)
    chain_paths = [Path(a.source_path) for a in chain]

    return build_mix(chain_paths, profile_sequence, rng, mix_id, analysis_cache)
