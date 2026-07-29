import librosa


def detect_beats(audio):

    y = audio.waveform
    sr = audio.sample_rate

    tempo, beat_frames = librosa.beat.beat_track(
        y=y,
        sr=sr,
    )

    beat_times = librosa.frames_to_time(
        beat_frames,
        sr=sr,
    )

    return {
        "tempo": float(tempo[0] if hasattr(tempo, "__len__") else tempo),
        "beats": beat_times.tolist(),
    }