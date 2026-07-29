"""Track-Vorbereitung: BPM/Beat-Grid, Downbeats/Bar-Grid, Phrasen-Raster,
Tonart, RMS-Kurve - einmal pro Track berechnet und als Cache-JSON neben der
Datei abgelegt (<trackname>.analysis.json).

Baut bewusst auf bestehenden app/audio/*-Funktionen auf (Chroma, Beat-Grid,
Camelot-Zuordnung, Energiekurve) statt sie zu duplizieren - dieselbe
Feature-Logik wie der Rest der Pipeline, kein Second-System-Risiko.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from app.audio.energy import calculate_energy_curve
from app.audio.segment_keys import CAMELOT_MAP, key_from_chroma_mean
from app.audio.track_change_classifier import compute_chroma_matrix

from .config import BEATS_PER_BAR, MAX_BPM, MIN_BPM, SAMPLE_RATE, BAR_PHRASE_LENGTHS

# v2, nicht mehr ".analysis.json": app/audio/beats.detect_beat_grid() nutzt
# librosa's Standard-Tempo-Schaetzung (start_bpm=120, sehr enger Prior) -
# die zieht viele UNTERSCHIEDLICH schnelle Tracks auf (fast) denselben Wert
# (~123 BPM gemessen bei mehreren komplett verschiedenen Songs aus der
# Library, 2026-07-14). Die Uebergaenge "matchen" dann ein Tempo, das gar
# nicht das echte Tempo ist - Beats laufen im Overlap auseinander, egal wie
# gut Phase/Gain/Overlap-Laenge sonst stimmen (Sebastians Rating: 3/5,
# "Beats liegen nicht sauber uebereinander"). Eigene zweistufige Schaetzung
# hier (Suche im weiten Bereich -> auf 70-180 BPM oktavieren -> Beat-Grid
# MIT diesem korrigierten Tempo als engem Prior neu bestimmen), damit sowohl
# die gemeldete BPM als auch die Beat-Positionen selbst stimmen. Bewusst NUR
# hier im Synth-Mixer geaendert, nicht in app/audio/beats.py - das speist den
# produktiven ML-Klassifikator, dessen Kalibrierung an der bisherigen
# (verzerrten) Tempo-Feature-Verteilung haengt; das braucht einen eigenen,
# vorsichtigen Retrain-Pass statt einer Nebenbei-Aenderung hier.
CACHE_SUFFIX = ".analysis.v2.json"
INTRO_OUTRO_RMS_FRACTION = 0.4  # Anteil vom Track-Durchschnitt, ab dem "leise" gilt


def _robust_tempo_and_beats(waveform: np.ndarray, sample_rate: int) -> tuple[float, list[float]]:
    """(bpm, beat_times) ohne den ~120-BPM-Attraktor-Bias von librosas
    Standard-Prior. Sucht das dominante Tempo breit, oktaviert es in den
    plausiblen Tanzmusik-Bereich (MIN_BPM..MAX_BPM), und bestimmt dann die
    Beat-Positionen NEU mit diesem Tempo als engem Prior (sonst waeren die
    Beat-Positionen selbst noch an der falschen Periodizitaet verankert)."""
    import librosa
    import librosa.feature.rhythm as rhythm_mod

    onset_env = librosa.onset.onset_strength(y=waveform, sr=sample_rate)
    rough = float(rhythm_mod.tempo(
        onset_envelope=onset_env, sr=sample_rate,
        start_bpm=120.0, std_bpm=60.0, max_tempo=300.0,
    )[0])

    corrected = rough
    while corrected < MIN_BPM and corrected > 0:
        corrected *= 2.0
    while corrected > MAX_BPM:
        corrected /= 2.0

    beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sample_rate, bpm=corrected, units="frames",
    )[1]
    beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate)
    return round(corrected, 2), [round(float(t), 3) for t in beat_times]


class _AudioLike:
    """Minimal-Wrapper, damit bestehende app/audio-Funktionen (die ein
    Objekt mit .waveform/.sample_rate erwarten) auf einem einzelnen
    geladenen Track arbeiten koennen, ohne LoadedAudio zu duplizieren."""

    def __init__(self, waveform: np.ndarray, sample_rate: int, filename: str):
        self.waveform = waveform
        self.sample_rate = sample_rate
        self.duration_seconds = len(waveform) / sample_rate
        self.filename = filename


@dataclass
class PhraseGrid:
    bars_per_phrase: int
    boundary_times: list[float] = field(default_factory=list)


@dataclass
class TrackAnalysis:
    source_path: str
    duration_seconds: float
    sample_rate: int
    bpm: float
    beat_times: list[float]
    downbeat_times: list[float]
    phrase_grids: dict[int, list[float]]  # bars_per_phrase -> boundary times
    key: Optional[str]
    camelot: Optional[str]
    key_confidence: float
    rms_times: list[float]
    rms_values: list[float]
    intro_end_sec: float
    outro_start_sec: float

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(data: dict) -> "TrackAnalysis":
        data = dict(data)
        data["phrase_grids"] = {int(k): v for k, v in data["phrase_grids"].items()}
        return TrackAnalysis(**data)


def _onset_envelope(waveform: np.ndarray, sample_rate: int) -> np.ndarray:
    import librosa
    return librosa.onset.onset_strength(y=waveform, sr=sample_rate)


def _detect_downbeats(waveform: np.ndarray, sample_rate: int, beats: list[float]) -> list[float]:
    """Downbeat-Phase heuristisch: von 4 moeglichen Phasen (welcher Beat ist
    Taktanfang) wird die gewaehlt, deren Kandidaten-Downbeats im Schnitt die
    hoechste Onset-Staerke tragen."""
    if len(beats) < BEATS_PER_BAR * 2:
        return beats[:1] if beats else []

    import librosa
    onset_env = _onset_envelope(waveform, sample_rate)
    hop_length = 512
    fps = sample_rate / hop_length

    best_phase, best_score = 0, -1.0
    for phase in range(BEATS_PER_BAR):
        candidates = beats[phase::BEATS_PER_BAR]
        frames = np.clip(
            (np.array(candidates) * fps).astype(int), 0, len(onset_env) - 1,
        )
        score = float(np.mean(onset_env[frames])) if len(frames) else -1.0
        if score > best_score:
            best_phase, best_score = phase, score

    return beats[best_phase::BEATS_PER_BAR]


def _phrase_grid_for_bars(downbeats: list[float], duration: float, bars_per_phrase: int) -> list[float]:
    """Phrasengrenzen alle `bars_per_phrase` Downbeats, ueber das Ende des
    Tracks hinaus extrapoliert (gleiche Idee wie app/audio/phrase_grid.py,
    hier parametrisiert auf 8/16/32-Bar-Raster statt fix 8 Bars)."""
    if len(downbeats) < bars_per_phrase:
        return []

    boundaries = [downbeats[i] for i in range(0, len(downbeats), bars_per_phrase)]
    bar_interval = (downbeats[-1] - downbeats[0]) / max(1, len(downbeats) - 1)
    phrase_seconds = bars_per_phrase * bar_interval

    next_time = boundaries[-1] + phrase_seconds
    while next_time <= duration + phrase_seconds and bar_interval > 0:
        boundaries.append(round(next_time, 3))
        next_time += phrase_seconds

    return boundaries


def _detect_key(waveform: np.ndarray, sample_rate: int) -> tuple[Optional[str], Optional[str], float]:
    chroma = compute_chroma_matrix(waveform, sample_rate)
    if chroma.shape[1] == 0:
        return None, None, 0.0
    result = key_from_chroma_mean(np.mean(chroma, axis=1))
    return result["key"], result["camelot"], float(result["confidence"])


def _intro_outro(rms_times: list[float], rms_values: list[float], duration: float) -> tuple[float, float]:
    if not rms_values:
        return 0.0, duration
    values = np.array(rms_values)
    threshold = float(np.mean(values)) * INTRO_OUTRO_RMS_FRACTION

    intro_end = 0.0
    for t, v in zip(rms_times, rms_values):
        if v >= threshold:
            intro_end = t
            break

    outro_start = duration
    for t, v in zip(reversed(rms_times), reversed(rms_values)):
        if v >= threshold:
            outro_start = t
            break

    return round(intro_end, 2), round(outro_start, 2)


def analyze_track(path: Path, use_cache: bool = True) -> TrackAnalysis:
    path = Path(path)
    cache_path = path.with_suffix(path.suffix + CACHE_SUFFIX)

    if use_cache and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("source_path") == str(path):
                return TrackAnalysis.from_json(cached)
        except (OSError, json.JSONDecodeError, TypeError, KeyError):
            pass  # Cache kaputt/veraltet -> neu berechnen

    import librosa
    waveform, sr = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    duration = len(waveform) / sr
    audio = _AudioLike(waveform, sr, path.name)

    bpm, beats = _robust_tempo_and_beats(waveform, sr)

    downbeats = _detect_downbeats(waveform, sr, beats)
    phrase_grids = {
        bars: _phrase_grid_for_bars(downbeats, duration, bars)
        for bars in BAR_PHRASE_LENGTHS
    }

    key, camelot, confidence = _detect_key(waveform, sr)

    energy = calculate_energy_curve(audio, window_seconds=1.0)
    rms_times = [p["time"] for p in energy["points"]]
    rms_values = [p["rms"] for p in energy["points"]]
    intro_end, outro_start = _intro_outro(rms_times, rms_values, duration)

    analysis = TrackAnalysis(
        source_path=str(path),
        duration_seconds=round(duration, 2),
        sample_rate=sr,
        bpm=round(float(bpm), 2),
        beat_times=[round(b, 3) for b in beats],
        downbeat_times=[round(b, 3) for b in downbeats],
        phrase_grids=phrase_grids,
        key=key,
        camelot=camelot,
        key_confidence=round(confidence, 3),
        rms_times=rms_times,
        rms_values=rms_values,
        intro_end_sec=intro_end,
        outro_start_sec=outro_start,
    )

    if use_cache:
        try:
            cache_path.write_text(json.dumps(analysis.to_json()), encoding="utf-8")
        except OSError:
            pass  # Cache-Schreibfehler duerfen die Analyse nicht abbrechen

    return analysis


def camelot_distance(a: Optional[str], b: Optional[str]) -> Optional[int]:
    """Schritte auf dem Camelot-Rad (0 = gleich, 1 = Nachbar/relativ Dur-
    Moll, ..., 6 = maximal entfernt). None, wenn eine Tonart unbekannt ist."""
    if not a or not b:
        return None
    try:
        num_a, mode_a = int(a[:-1]), a[-1]
        num_b, mode_b = int(b[:-1]), b[-1]
    except (ValueError, IndexError):
        return None

    if a == b:
        return 0
    ring_distance = min(abs(num_a - num_b), 12 - abs(num_a - num_b))
    mode_penalty = 0 if mode_a == mode_b else 1
    return ring_distance + mode_penalty


def style_cluster(path: Path) -> str:
    """Canonical Stil-Tag fuer eine Audiodatei: der Name des direkten
    Elternordners (z.B. "Afro House"), auf den Cluster-Reprsentanten
    (STYLE_CLUSTERS[0]) abgebildet, falls der Ordner in einem Cluster
    gelistet ist - sonst der Ordnername selbst (matcht dann nur sich
    selbst, keine Cross-Kombination mit anderen Ordnern)."""
    from .config import STYLE_CLUSTERS

    folder = Path(path).parent.name
    for cluster in STYLE_CLUSTERS:
        if folder in cluster:
            return cluster[0]
    return folder
