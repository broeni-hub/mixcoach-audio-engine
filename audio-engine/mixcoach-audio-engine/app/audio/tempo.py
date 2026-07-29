import librosa
import numpy as np


def detect_tempo(audio):
    y = audio.waveform
    sr = audio.sample_rate

    onset_env = librosa.onset.onset_strength(
        y=y,
        sr=sr,
    )

    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
    )

    beat_times = librosa.frames_to_time(
        beats,
        sr=sr,
    )

    if len(beat_times) < 3:
        return {
            "tempo": float(tempo),
            "confidence": 0.2,
            "stability": 0.0,
            "beats": beat_times.tolist(),
        }

    intervals = np.diff(beat_times)

    stability = 1 - np.std(intervals) / np.mean(intervals)

    stability = max(
        0,
        min(
            1,
            stability,
        ),
    )

    confidence = stability

    return {
        "tempo": round(float(tempo.item() if hasattr(tempo, "item") else tempo), 2),
        "confidence": round(float(confidence),2),
        "stability": round(float(stability),2),
        "beats": beat_times.tolist(),
    }