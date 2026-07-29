"""Synthetische Trainings-Mixes mit exakter Ground Truth (Stufe 1 des
Skalierungsplans) - erzeugt echte Uebergaenge zwischen zwei Library-Tracks
mit bekanntem Zeitpunkt, statt sie muehsam von Hand zu labeln.

Idee: zwei Tracks aus der Library (Rekordbox-Import, siehe app/library/
manager.py) werden am Ende von Track A / Anfang von Track B ineinander
geblendet. Weil WIR den Blend bauen, kennen wir den Uebergangszeitpunkt
exakt - kein Hoeren, kein Excel noetig. Variiert werden:

  - Overlap-Laenge (4/8/16/32 Beats)
  - Blend-Kurve (linear, equal_power/DJ-Mixer-Style, cut)
  - Tempo-Angleichung an/aus (Time-Stretch von Track B auf Track A's BPM)
  - Beat-genaue Ausrichtung an/aus ("guter" vs. bewusst schlecht getimter
    Uebergang - beides sind ECHTE Uebergaenge, nur unterschiedlich sauber)
  - Bass-Swap (EQ-Fade im Tiefton zusaetzlich zum Lautstaerke-Blend)

Nutzt build_set_rows() 1:1 wie echte Sets (dieselbe Feature-Extraktion wie
Training UND Live-Inferenz - kein Train/Serve-Drift). Deckt bewusst nur
House/Funk/Electro ab (Sebastians Wunsch) - andere Genres ggf. spaeter mit
--genres nachziehen.

Bekannte Grenze (wie im Skalierungsplan erwaehnt): synthetische Mixes
decken keine Live-Fader-Bewegungen, Loops, Scratches, FX ab - das bleibt
Aufgabe von Stufe 2 (echte Mixes + Fingerprint-Alignment).

Aufruf (im Projektordner):
    python -m app.calibration.generate_synthetic_mixes
    python -m app.calibration.generate_synthetic_mixes --n-mixes 300 --seed 0
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

SR = 22050
# Tail von A / Head von B, die geladen werden - grosszuegig, damit der
# Uebergang NICHT in der "edge"-Zone landet (ml_classifier.py verwirft
# Kandidaten < 90s nach Start / < 60s vor Ende immer).
SEGMENT_SECONDS = 130.0
OVERLAP_BEATS_CHOICES = (4, 8, 16, 32)
CURVES = ("linear", "equal_power", "cut")
GENRES_DEFAULT = ("house", "funk", "electro")
BASS_HZ = 120.0
MIN_BPM, MAX_BPM = 70.0, 180.0

OUT_PATH = Path(__file__).parent / "synthetic_mixes_v1.json"


def load_pool(index_path: Path, genres: tuple[str, ...]) -> list[dict]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    pool = []
    for tid, meta in index["tracks"].items():
        path = meta.get("path", "")
        if not Path(path).exists():
            continue
        bpm = meta.get("bpm")
        if not bpm or not (MIN_BPM <= bpm <= MAX_BPM):
            continue
        duration = meta.get("duration") or 0
        if duration < SEGMENT_SECONDS + 20.0:
            continue
        if genres and not any(g.lower() in path.lower() for g in genres):
            continue
        pool.append({"id": tid, "path": path, "bpm": float(bpm), "duration": duration,
                     "title": meta.get("title"), "artist": meta.get("artist")})
    return pool


def _load_tail(path: str, duration: float, seconds: float) -> np.ndarray:
    import librosa
    offset = max(0.0, duration - seconds)
    y, _ = librosa.load(path, sr=SR, mono=True, offset=offset, duration=seconds)
    return y


def _load_head(path: str, seconds: float) -> np.ndarray:
    import librosa
    y, _ = librosa.load(path, sr=SR, mono=True, offset=0.0, duration=seconds)
    return y


def _local_beat_offset(y: np.ndarray, near_sample: int, bpm: float, aligned: bool) -> int:
    """Verschiebt den Overlap-Start auf den naechsten Beat (aligned=True:
    zusaetzlich auf eine 4-Beat-Bar-Grenze) - oder laesst ihn unveraendert
    (aligned=False -> bewusst schlecht getimter Uebergang)."""
    import librosa
    beat_len = int(60.0 / bpm * SR)
    if not aligned:
        return near_sample
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=SR)
        _, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=SR)
        beats = librosa.frames_to_samples(beat_frames)
    except Exception:
        beats = np.array([], dtype=int)
    candidates = beats[beats > 0] if len(beats) else np.array([near_sample])
    if len(candidates) == 0:
        return near_sample
    nearest = int(candidates[np.argmin(np.abs(candidates - near_sample))])
    return max(beat_len, nearest)


def _fade_curves(curve: str, n: int) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    if curve == "linear":
        return 1.0 - t, t
    if curve == "equal_power":
        return np.cos(t * np.pi / 2), np.sin(t * np.pi / 2)
    # "cut": kein echter Blend - B setzt hart ein, A stoppt hart (mit
    # 5ms-Ramp gegen Klick-Artefakte, kein musikalischer Blend).
    ramp = min(n, int(0.005 * SR))
    out = np.ones(n)
    inn = np.zeros(n)
    if ramp > 0:
        out[-ramp:] = np.linspace(1.0, 0.0, ramp)
        inn[:ramp] = np.linspace(0.0, 1.0, ramp)
    else:
        out[:] = 0.0
        inn[:] = 1.0
    return out, inn


def _bass_filtered(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from scipy.signal import butter, sosfilt
    sos = butter(4, BASS_HZ, btype="low", fs=SR, output="sos")
    low = sosfilt(sos, y)
    return low, y - low


def make_transition(
    tail_a: np.ndarray, bpm_a: float,
    head_b: np.ndarray, bpm_b: float,
    overlap_beats: int, curve: str, tempo_match: bool,
    phrase_aligned: bool, bass_swap: bool,
) -> tuple[np.ndarray, float]:
    """Baut EINEN Uebergang A->B. Rueckgabe: (Mix-Waveform, Uebergangszeit_sek)."""
    import librosa

    if tempo_match and bpm_b > 0:
        ratio = bpm_b / bpm_a
        head_b = librosa.effects.time_stretch(head_b, rate=ratio)

    overlap_samples = int(overlap_beats * 60.0 / bpm_a * SR)
    overlap_samples = max(int(0.05 * SR), min(overlap_samples,
                          len(tail_a) - SR, len(head_b) - SR))

    near = len(tail_a) - overlap_samples
    start = _local_beat_offset(tail_a, near, bpm_a, phrase_aligned)
    start = min(start, len(tail_a) - overlap_samples - 1)
    start = max(start, 0)

    lead_in = tail_a[:start]
    a_overlap = tail_a[start:start + overlap_samples]
    b_overlap = head_b[:overlap_samples]
    lead_out = head_b[overlap_samples:]

    fade_out, fade_in = _fade_curves(curve, overlap_samples)

    if bass_swap:
        a_low, a_hi = _bass_filtered(a_overlap)
        b_low, b_hi = _bass_filtered(b_overlap)
        # Tiefton wird schneller getauscht als der Rest - typischer Bass-Swap.
        bass_fade_out, bass_fade_in = _fade_curves("equal_power", overlap_samples)
        mixed_overlap = (
            a_hi * fade_out + a_low * bass_fade_out
            + b_hi * fade_in + b_low * bass_fade_in
        )
    else:
        mixed_overlap = a_overlap * fade_out + b_overlap * fade_in

    waveform = np.concatenate([lead_in, mixed_overlap, lead_out]).astype(np.float32)
    transition_time = (len(lead_in) + overlap_samples / 2.0) / SR
    return waveform, transition_time


def generate_one(pool: list[dict], rng: random.Random) -> tuple[np.ndarray, dict, dict]:
    track_a, track_b = rng.sample(pool, 2)

    tail_a = _load_tail(track_a["path"], track_a["duration"], SEGMENT_SECONDS)
    head_b = _load_head(track_b["path"], SEGMENT_SECONDS)

    params = {
        "overlap_beats": rng.choice(OVERLAP_BEATS_CHOICES),
        "curve": rng.choice(CURVES),
        "tempo_match": rng.random() < 0.7,   # 70% sauber angeglichen, 30% bewusst nicht
        "phrase_aligned": rng.random() < 0.7,  # 70% beat-genau, 30% bewusst daneben
        "bass_swap": rng.random() < 0.3,
    }

    waveform, t = make_transition(
        tail_a, track_a["bpm"], head_b, track_b["bpm"], **params,
    )

    truth = {"positives": [round(t, 2)], "negatives": []}
    meta = {
        "track_a": f"{track_a.get('artist', '')} - {track_a.get('title', '')}".strip(" -"),
        "track_b": f"{track_b.get('artist', '')} - {track_b.get('title', '')}".strip(" -"),
        "bpm_a": track_a["bpm"], "bpm_b": track_b["bpm"],
        "transition_time": round(t, 2),
        **params,
    }
    return waveform, truth, meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetische Trainings-Mixes generieren.")
    parser.add_argument("--library-index", type=Path,
                        default=Path(r"C:\Projekte\Projekte\MixCoach\daten\library\index.json"))
    parser.add_argument("--genres", default=",".join(GENRES_DEFAULT),
                        help="Komma-getrennte Ordner-Filter (Substring, case-insensitive).")
    parser.add_argument("--n-mixes", type=int, default=150)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--meta-out", type=Path, default=None,
                        help="Optional: Parameter jedes Mixes als JSON mitschreiben (Debug/Nachvollziehbarkeit).")
    args = parser.parse_args()

    from app.calibration.build_features import build_set_rows

    genres = tuple(g.strip() for g in args.genres.split(",") if g.strip())
    pool = load_pool(args.library_index, genres)
    print(f"{len(pool)} Tracks im Pool (Filter: {genres or 'keiner'}, "
          f"Mindestlaenge {SEGMENT_SECONDS + 20:.0f}s, BPM {MIN_BPM:.0f}-{MAX_BPM:.0f}).")
    if len(pool) < 2:
        print("FEHLER: zu wenige Tracks im Pool.")
        return 1

    rng = random.Random(args.seed)
    all_rows = []
    all_meta = []
    ok, failed = 0, 0

    for i in range(1, args.n_mixes + 1):
        t0 = time.time()
        try:
            waveform, truth, meta = generate_one(pool, rng)
            set_name = f"synthmix_{i:04d}"
            rows = build_set_rows(f"<synthetic:{set_name}>", truth, set_name=set_name, waveform=waveform)
        except Exception as e:
            print(f"[{i}/{args.n_mixes}] FEHLER: {e}")
            failed += 1
            continue
        all_rows.extend(rows)
        all_meta.append(meta)
        ok += 1
        if i % 10 == 0 or i == args.n_mixes:
            print(f"[{i}/{args.n_mixes}] {meta['track_a'][:30]} -> {meta['track_b'][:30]} "
                  f"(overlap={meta['overlap_beats']} beats, {meta['curve']}, "
                  f"tempo_match={meta['tempo_match']}, aligned={meta['phrase_aligned']}) "
                  f"{time.time() - t0:.1f}s")

    args.out.write_text(json.dumps(all_rows), encoding="utf-8")
    print(f"\n{ok} Mixes erzeugt, {failed} fehlgeschlagen.")
    print(f"{len(all_rows)} Trainings-Kandidaten geschrieben -> {args.out}")

    if args.meta_out:
        args.meta_out.write_text(json.dumps(all_meta, indent=1), encoding="utf-8")
        print(f"Mix-Parameter geschrieben -> {args.meta_out}")

    print("\nNaechster Schritt: retrain_model.py laedt diese Datei automatisch mit,")
    print("wenn sie existiert (siehe SYNTHETIC_MIXES in retrain_model.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
