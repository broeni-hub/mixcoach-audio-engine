from typing import Dict

import librosa
import numpy as np


def detect_vocals(audio) -> Dict:
    y = audio.waveform
    sr = audio.sample_rate

    if y is None or len(y) == 0:
        return {
            "has_vocals": False,
            "vocal_score": 0.0,
            "confidence": 0.0,
            "method": "empty_audio",
        }

    stft = np.abs(librosa.stft(y))
    frequencies = librosa.fft_frequencies(sr=sr)

    vocal_mask = (frequencies >= 300) & (frequencies <= 3400)

    if not np.any(vocal_mask):
        return {
            "has_vocals": False,
            "vocal_score": 0.0,
            "confidence": 0.0,
            "method": "frequency_band",
        }

    total_energy = float(np.mean(stft))
    vocal_energy = float(np.mean(stft[vocal_mask]))

    if total_energy <= 0:
        vocal_score = 0.0
    else:
        vocal_score = vocal_energy / total_energy

    vocal_score = round(float(vocal_score), 3)

    has_vocals = vocal_score >= 1.15
    confidence = min(1.0, abs(vocal_score - 1.0))

    return {
        "has_vocals": has_vocals,
        "vocal_score": vocal_score,
        "confidence": round(float(confidence), 3),
        "method": "frequency_band",
    }