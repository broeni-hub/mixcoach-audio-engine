"""Transition-Typen: Crossfade-Kurven, Cut, EQ-Blend (Bass-Swap) - plus die
Parameter-Realisierung und Qualitaets-Note pro quality_profile.
"""

from __future__ import annotations

import random
from typing import Optional

import numpy as np

from .config import (
    ABRUPT_OVERLAP_BEATS,
    BASS_HZ,
    CLEAN_MAX_CAMELOT_DISTANCE,
    CLEAN_OVERLAP_BEATS_CHOICES,
    CROSSFADE_CURVES,
    KEY_CLASH_MIN_CAMELOT_DISTANCE,
    OFF_BEAT_MS_RANGE,
    OFF_PHRASE_BEATS_RANGE,
    OVERLAP_BEATS_CHOICES,
)


def crossfade_curve(name: str, n: int) -> tuple[np.ndarray, np.ndarray]:
    """(fade_out, fade_in) je Sample im Overlap-Fenster. Alle Kurven:
    fade_out(0)=1/fade_out(1)=0, fade_in(0)=0/fade_in(1)=1."""
    if n <= 0:
        return np.zeros(0), np.zeros(0)
    t = np.linspace(0.0, 1.0, n, endpoint=False)

    if name == "linear":
        return 1.0 - t, t

    if name == "equal_power":
        # Energie-erhaltend: fade_out**2 + fade_in**2 == 1 (konstante
        # wahrgenommene Lautstaerke waehrend des Blends, DJ-Mixer-Standard).
        return np.cos(t * np.pi / 2), np.sin(t * np.pi / 2)

    if name == "exponential":
        k = 5.0
        norm = 1.0 - np.exp(-k)
        fade_out = (np.exp(-k * t) - np.exp(-k)) / norm
        fade_in = (np.exp(-k * (1.0 - t)) - np.exp(-k)) / norm
        return fade_out, fade_in

    if name == "s_curve":
        # Smoothstep: sanfter Start/Ende, steilere Mitte.
        fade_in = 3 * t**2 - 2 * t**3
        return 1.0 - fade_in, fade_in

    raise ValueError(f"Unbekannte Crossfade-Kurve: {name}")


def _bass_split(y: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    from scipy.signal import butter, sosfilt
    sos = butter(4, BASS_HZ, btype="low", fs=sample_rate, output="sos")
    low = sosfilt(sos, y)
    return low, y - low


def gain_ratio(reference: np.ndarray, target: np.ndarray, max_gain: float = 4.0) -> float:
    """RMS-Verhaeltnis reference/target, gedeckelt - der Gain-Faktor, den
    ein DJ von Hand am Kanal-Gain einstellen wuerde, BEVOR er die Fader
    bewegt. Ohne dieses Gain-Staging klingt jeder Uebergang wie ein
    Fade-out-dann-Fade-in statt einem echten Overlap, sobald die beiden
    Quell-Dateien unterschiedlich laut gemastert sind (gefunden ueber
    Sebastians Rating-Stichprobe: durchgaengig 1-2 von 5, 2026-07-13).
    Gedeckelt, damit ein nahezu stummer Abschnitt nicht ins Unermessliche
    verstaerkt wird."""
    ref_rms = float(np.sqrt(np.mean(reference**2))) if len(reference) else 0.0
    tgt_rms = float(np.sqrt(np.mean(target**2))) if len(target) else 0.0
    if tgt_rms <= 1e-6 or ref_rms <= 1e-6:
        return 1.0
    return min(max_gain, ref_rms / tgt_rms)


def _match_gain(reference: np.ndarray, target: np.ndarray, max_gain: float = 4.0) -> np.ndarray:
    """Skaliert target auf denselben RMS-Pegel wie reference (siehe gain_ratio)."""
    return target * gain_ratio(reference, target, max_gain)


def render_transition(
    tail_a: np.ndarray,
    head_b: np.ndarray,
    sample_rate: int,
    transition_type: str,
    curve: str,
    overlap_samples: int,
    beat_offset_samples: int = 0,
    bass_swap: bool = False,
    drift_correction_samples: int = 0,
) -> np.ndarray:
    """Baut den Overlap-Abschnitt (NICHT den ganzen Mix) - Aufrufer haengt
    Lead-in/Lead-out selbst davor/danach.

    beat_offset_samples verschiebt, WELCHER Ausschnitt von head_b im Overlap
    gespielt wird (simuliert unsauberes Beatmatching: B "kommt" zeitlich
    versetzt zur eigentlichen Beat-Position).

    drift_correction_samples gleicht Beat-DRIFT ueber die Laenge des Overlaps
    aus: ein einmaliger globaler Tempo-Match + eine einmalige Phasenkorrektur
    am Overlap-Anfang reichen nicht, wenn A/B minimal unterschiedliches
    LOKALES Tempo haben - der Versatz waechst dann Beat fuer Beat weiter
    (gemessen: ~70ms am Anfang -> ~230ms am Ende eines 16-Beat-Overlaps,
    2026-07-14). Wird ueber eine kleine zusaetzliche Mikro-Zeitstreckung von
    b_overlap realisiert (mehr/weniger Rohmaterial aus head_b lesen, auf
    genau overlap_samples zusammenstauchen/dehnen) - kein zweiter,
    unabhaengiger Parameter fuer eine "andere" Korrektur, sondern dieselbe
    Phasenkorrektur, nur ein zweites Mal (am Overlap-Ende statt -Anfang)
    gemessen, um die Drift-RATE statt nur den Start-Versatz zu erfassen."""
    overlap_samples = max(1, min(overlap_samples, len(tail_a), len(head_b)))
    a_overlap = tail_a[-overlap_samples:]

    b_start = max(0, min(beat_offset_samples, len(head_b) - overlap_samples))

    if drift_correction_samples != 0:
        raw_len = max(2, overlap_samples + drift_correction_samples)
        raw_len = min(raw_len, len(head_b) - b_start)
        b_raw = head_b[b_start:b_start + raw_len]
        if raw_len >= 2 and len(b_raw) >= 2:
            rate = len(b_raw) / overlap_samples
            try:
                import pedalboard
                b_overlap = pedalboard.time_stretch(
                    b_raw.astype(np.float32), sample_rate, stretch_factor=rate,
                ).reshape(-1)
            except Exception:
                import librosa
                b_overlap = librosa.effects.time_stretch(b_raw, rate=rate)
        else:
            b_overlap = head_b[b_start:b_start + overlap_samples]
    else:
        b_overlap = head_b[b_start:b_start + overlap_samples]

    if len(b_overlap) < overlap_samples:
        b_overlap = np.pad(b_overlap, (0, overlap_samples - len(b_overlap)))
    elif len(b_overlap) > overlap_samples:
        b_overlap = b_overlap[:overlap_samples]

    # Gain-Staging: B auf den Pegel von A bringen, bevor geblendet wird -
    # aber NICHT bei "cut" (ein harter Schnitt darf/soll nach einem
    # spuerbaren Lautstaerke-Sprung klingen, das macht "abrupt" gerade aus).
    if transition_type != "cut":
        b_overlap = _match_gain(a_overlap, b_overlap)

    if transition_type == "cut":
        # Harter Schnitt: kein musikalischer Blend, nur ein Mikro-Ramp
        # (~5ms) gegen digitale Klick-Artefakte.
        ramp = min(overlap_samples, int(0.005 * sample_rate))
        fade_out = np.ones(overlap_samples)
        fade_in = np.zeros(overlap_samples)
        if ramp > 0:
            fade_out[-ramp:] = np.linspace(1.0, 0.0, ramp)
            fade_in[-ramp:] = np.linspace(0.0, 1.0, ramp)
        else:
            fade_out[:] = 0.0
            fade_in[:] = 1.0
        return (a_overlap * fade_out + b_overlap * fade_in).astype(np.float32)

    fade_out, fade_in = crossfade_curve(curve, overlap_samples)

    if transition_type == "eq_blend" or bass_swap:
        a_low, a_hi = _bass_split(a_overlap, sample_rate)
        b_low, b_hi = _bass_split(b_overlap, sample_rate)
        # Tiefton wird ueber equal_power getauscht, unabhaengig von der
        # gewaehlten Hauptkurve - klassischer Bass-Swap-Effekt.
        bass_out, bass_in = crossfade_curve("equal_power", overlap_samples)
        mixed = a_hi * fade_out + a_low * bass_out + b_hi * fade_in + b_low * bass_in
    else:
        mixed = a_overlap * fade_out + b_overlap * fade_in

    return mixed.astype(np.float32)


def estimate_phase_offset_samples(a_region: np.ndarray, b_region: np.ndarray,
                                  sample_rate: int, beat_len_samples: int) -> int:
    """Sucht per Kreuzkorrelation der Onset-Staerke die Verschiebung von B,
    die ihren rhythmischen Puls am besten an A anpasst (+-0.5 Beat Suchraum).

    Tempo-Angleichung (Time-Stretch auf dieselbe BPM) reicht NICHT fuer
    echtes Beatmatching - die Beat-PHASE kann trotzdem versetzt sein (die
    Kicks beider Tracks fallen nicht auf denselben Zeitpunkt), was sich wie
    Disharmonie/Stolpern anhoert. Das hier ist der fehlende zweite Schritt,
    den ein DJ von Hand macht (Pitch-Bend, bis die Kicks uebereinanderfallen).
    Suchraum bewusst auf +-0.5 statt +-1 Beat begrenzt: bei (nahezu)
    periodischem Material (Vierviertel-Beat) ist eine Verschiebung um fast
    einen vollen Beat rhythmisch fast genauso plausibel wie die echte kleine
    Korrektur - das haette sonst gelegentlich die falsche, aber "aliasing"-
    aehnlich hoch bewertete Verschiebung gewaehlt.
    Rueckgabe: Sample-Versatz fuer b_region (0, wenn nicht messbar)."""
    import librosa
    hop = 512
    onset_a = librosa.onset.onset_strength(y=a_region, sr=sample_rate, hop_length=hop)
    onset_b = librosa.onset.onset_strength(y=b_region, sr=sample_rate, hop_length=hop)
    search_frames = max(1, int(beat_len_samples / hop / 2))
    n = min(len(onset_a), len(onset_b))
    if n < search_frames * 2:
        return 0

    best_lag, best_score = 0, -np.inf
    for lag in range(-search_frames, search_frames + 1):
        if lag >= 0:
            a_seg, b_seg = onset_a[lag:n], onset_b[0:n - lag]
        else:
            a_seg, b_seg = onset_a[0:n + lag], onset_b[-lag:n]
        if len(a_seg) < 8:
            continue
        # Mittelwert statt Summe: sonst gewinnen laengere Ueberlappungen
        # (kleine |lag|) systematisch NICHT gegen kuerzere Rand-Segmente,
        # die zufaellig (v.a. bei periodischem Material) hoeher korrelieren.
        score = float(np.mean(a_seg * b_seg))
        if score > best_score:
            best_score, best_lag = score, lag

    return best_lag * hop


def sample_profile_params(profile: str, rng: random.Random) -> dict:
    """Konkrete Parameter fuer ein quality_profile wuerfeln. key_clash/
    train_wreck erzwingen KEINE Trackauswahl hier - das macht generator.py
    beim Trackpaaren (Camelot-Distanz ist eine Eigenschaft des Paars, nicht
    der Uebergangs-Rendering-Parameter)."""
    if profile == "clean":
        return {
            "transition_type": rng.choice(("crossfade", "eq_blend")),
            "overlap_beats": rng.choice(CLEAN_OVERLAP_BEATS_CHOICES),
            "curve": rng.choice(("equal_power", "linear", "s_curve")),
            "phrase_offset_beats": 0.0,
            "beat_offset_ms": 0.0,
        }
    if profile == "off_phrase":
        lo, hi = OFF_PHRASE_BEATS_RANGE
        return {
            "transition_type": "crossfade",
            "overlap_beats": rng.choice(OVERLAP_BEATS_CHOICES),
            "curve": rng.choice(CROSSFADE_CURVES),
            "phrase_offset_beats": float(rng.randint(lo, hi)),
            "beat_offset_ms": 0.0,
        }
    if profile == "off_beat":
        lo, hi = OFF_BEAT_MS_RANGE
        return {
            "transition_type": "crossfade",
            "overlap_beats": rng.choice(OVERLAP_BEATS_CHOICES),
            "curve": rng.choice(CROSSFADE_CURVES),
            "phrase_offset_beats": 0.0,
            "beat_offset_ms": rng.uniform(lo, hi) * rng.choice((-1, 1)),
        }
    if profile == "key_clash":
        return {
            "transition_type": "crossfade",
            "overlap_beats": rng.choice(OVERLAP_BEATS_CHOICES),
            "curve": rng.choice(CROSSFADE_CURVES),
            "phrase_offset_beats": 0.0,
            "beat_offset_ms": 0.0,
        }
    if profile == "abrupt":
        lo, hi = ABRUPT_OVERLAP_BEATS
        return {
            "transition_type": "cut",
            "overlap_beats": float(rng.randint(lo, hi)),
            "curve": "linear",
            "phrase_offset_beats": float(rng.randint(2, 8)),  # "an unpassender Stelle"
            "beat_offset_ms": 0.0,
        }
    if profile == "train_wreck":
        lo_b, hi_b = OFF_BEAT_MS_RANGE
        lo_p, hi_p = OFF_PHRASE_BEATS_RANGE
        return {
            "transition_type": "crossfade",
            "overlap_beats": rng.choice(OVERLAP_BEATS_CHOICES),
            "curve": rng.choice(CROSSFADE_CURVES),
            "phrase_offset_beats": float(rng.randint(lo_p, hi_p)),
            "beat_offset_ms": rng.uniform(lo_b, hi_b) * rng.choice((-1, 1)),
        }
    raise ValueError(f"Unbekanntes quality_profile: {profile}")


def key_constraint_for_profile(profile: str) -> Optional[tuple[str, int]]:
    """Tonart-Vorgabe fuer die TRACKPAARUNG (nicht fuer das Rendering) je
    quality_profile:
      ("max", N) -> Camelot-Distanz des Paars muss <= N sein (passende Keys)
      ("min", N) -> Camelot-Distanz des Paars muss >= N sein (Clash)
      None       -> keine Tonart-Vorgabe

    "clean" erfordert per Definition passende Keys (+-1 Camelot) - ohne
    diese Vorgabe waeren zufaellig stark clashende Paare trotzdem als
    expected_quality_label=5 gelabelt worden (Bug, gefunden beim ersten
    echten Mini-Mix mit realer Library-Musik, 2026-07-13)."""
    if profile == "clean":
        return ("max", CLEAN_MAX_CAMELOT_DISTANCE)
    if profile in ("key_clash", "train_wreck"):
        return ("min", KEY_CLASH_MIN_CAMELOT_DISTANCE)
    return None


def expected_quality_label(
    profile: str,
    *,
    phrase_offset_beats: float = 0.0,
    beat_offset_ms: float = 0.0,
    camelot_distance_value: Optional[int] = None,
) -> int:
    """Deterministische Qualitaets-Note (1-5) aus quality_profile + den
    tatsaechlich realisierten Parametern. MAPPING-TABELLE (verbindlich):

      clean                                              -> 5
      off_phrase,  |phrase_offset_beats| <= 4              -> 3
      off_phrase,  |phrase_offset_beats| >  4              -> 2
      off_beat,    |beat_offset_ms| <= 150                  -> 3
      off_beat,    |beat_offset_ms| >  150                  -> 2
      key_clash,   camelot_distance <= 4 (oder unbekannt)    -> 2
      key_clash,   camelot_distance >  4                     -> 1
      abrupt                                                  -> 2
      train_wreck                                             -> 1
    """
    if profile == "clean":
        return 5
    if profile == "off_phrase":
        return 3 if abs(phrase_offset_beats) <= 4 else 2
    if profile == "off_beat":
        return 3 if abs(beat_offset_ms) <= 150 else 2
    if profile == "key_clash":
        if camelot_distance_value is None:
            return 2
        return 2 if camelot_distance_value <= 4 else 1
    if profile == "abrupt":
        return 2
    if profile == "train_wreck":
        return 1
    raise ValueError(f"Unbekanntes quality_profile: {profile}")


def pick_transition_start(
    phrase_boundaries_in_tail: list[float],
    tail_duration: float,
    overlap_seconds: float,
    bpm: float,
    phrase_offset_beats: float,
) -> float:
    """Start des Overlaps INNERHALB des A-Tails (Sekunden ab Tail-Anfang).

    phrase_offset_beats=0 -> auf die letzte Phrasengrenze vor Tail-Ende
    ausgerichtet ("clean"). Ungleich 0 -> bewusst um so viele Beats daneben
    (off_phrase/train_wreck). Ohne erkannte Phrasengrenze im Tail: Fallback
    auf einen festen Punkt vor dem Tail-Ende (bleibt reproduzierbar)."""
    beat_len = 60.0 / bpm if bpm > 0 else 0.5
    latest_allowed = tail_duration - overlap_seconds

    candidates = [b for b in phrase_boundaries_in_tail if b <= latest_allowed]
    anchor = max(candidates) if candidates else max(0.0, latest_allowed)

    start = anchor + phrase_offset_beats * beat_len
    return float(min(max(0.0, start), max(0.0, latest_allowed)))
