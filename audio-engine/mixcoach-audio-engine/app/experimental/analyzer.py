import librosa
import numpy as np


def _band_energy(spectrum, frequencies, low_hz, high_hz):
    mask = (frequencies >= low_hz) & (frequencies < high_hz)

    if not np.any(mask):
        return 0.0

    return float(np.mean(spectrum[mask]))

def detect_key(audio):

    y = audio.waveform
    sr = audio.sample_rate

    chroma = librosa.feature.chroma_cqt(
        y=y,
        sr=sr,
    )

    chroma_mean = np.mean(chroma, axis=1)

    notes = [
        "C","C#","D","D#","E","F",
        "F#","G","G#","A","A#","B"
    ]

    index = int(np.argmax(chroma_mean))

    confidence = float(
        chroma_mean[index] / np.sum(chroma_mean)
    )

    return {
        "key": notes[index],
        "confidence": round(confidence * 100, 2)
    }

def analyze_basic(audio):
    """
    Compute simple DSP metrics.
    """

    waveform = audio.waveform
    sr = audio.sample_rate

    rms = np.sqrt(np.mean(waveform ** 2))
    peak = np.max(np.abs(waveform))

    tempo, _ = librosa.beat.beat_track(
        y=waveform,
        sr=sr,
    )

    stft = np.abs(librosa.stft(waveform))
    spectrum = np.mean(stft, axis=1)
    frequencies = librosa.fft_frequencies(sr=sr)

    bass = _band_energy(spectrum, frequencies, 20, 250)
    low_mids = _band_energy(spectrum, frequencies, 250, 500)
    mids = _band_energy(spectrum, frequencies, 500, 2000)
    highs = _band_energy(spectrum, frequencies, 2000, 10000)

    total = bass + low_mids + mids + highs

    if total > 0:
        frequency_balance = {
            "bass": round((bass / total) * 100, 2),
            "low_mids": round((low_mids / total) * 100, 2),
            "mids": round((mids / total) * 100, 2),
            "highs": round((highs / total) * 100, 2),
        }
    else:
        frequency_balance = {
            "bass": 0.0,
            "low_mids": 0.0,
            "mids": 0.0,
            "highs": 0.0,
        }

    key = detect_key(audio)

    return {
        "duration": audio.duration_seconds,
        "sample_rate": sr,
        "rms": float(rms),
        "peak": float(peak),
        "tempo": float(tempo[0] if hasattr(tempo, "__len__") else tempo),
        "frequency_balance": frequency_balance,
        "key": key,
    }