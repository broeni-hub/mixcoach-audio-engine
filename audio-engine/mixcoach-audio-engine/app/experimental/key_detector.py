import librosa
import numpy as np


KEYS_MAJOR = [
    "C Major", "C# Major", "D Major", "D# Major", "E Major", "F Major",
    "F# Major", "G Major", "G# Major", "A Major", "A# Major", "B Major"
]

KEYS_MINOR = [
    "C Minor", "C# Minor", "D Minor", "D# Minor", "E Minor", "F Minor",
    "F# Minor", "G Minor", "G# Minor", "A Minor", "A# Minor", "B Minor"
]


MAJOR_PROFILE = np.array([
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88
])

MINOR_PROFILE = np.array([
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17
])


CAMELOT_MAP = {
    "C Major": "8B",
    "G Major": "9B",
    "D Major": "10B",
    "A Major": "11B",
    "E Major": "12B",
    "B Major": "1B",
    "F# Major": "2B",
    "C# Major": "3B",
    "G# Major": "4B",
    "D# Major": "5B",
    "A# Major": "6B",
    "F Major": "7B",

    "A Minor": "8A",
    "E Minor": "9A",
    "B Minor": "10A",
    "F# Minor": "11A",
    "C# Minor": "12A",
    "G# Minor": "1A",
    "D# Minor": "2A",
    "A# Minor": "3A",
    "F Minor": "4A",
    "C Minor": "5A",
    "G Minor": "6A",
    "D Minor": "7A",
}


def _rotate_profile(profile, shift):
    return np.roll(profile, shift)


def detect_key(audio):
    y = audio.waveform
    sr = audio.sample_rate

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    if np.sum(chroma_mean) == 0:
        return {
            "key": "Unknown",
            "camelot": None,
            "confidence": 0.0,
        }

    chroma_norm = chroma_mean / np.linalg.norm(chroma_mean)

    scores = []

    for i in range(12):
        major_profile = _rotate_profile(MAJOR_PROFILE, i)
        minor_profile = _rotate_profile(MINOR_PROFILE, i)

        major_profile = major_profile / np.linalg.norm(major_profile)
        minor_profile = minor_profile / np.linalg.norm(minor_profile)

        major_score = float(np.dot(chroma_norm, major_profile))
        minor_score = float(np.dot(chroma_norm, minor_profile))

        scores.append((KEYS_MAJOR[i], major_score))
        scores.append((KEYS_MINOR[i], minor_score))

    scores.sort(key=lambda item: item[1], reverse=True)

    best_key, best_score = scores[0]
    second_score = scores[1][1]

    confidence = max(0.0, min(1.0, best_score - second_score + 0.5))

    return {
        "key": best_key,
        "camelot": CAMELOT_MAP.get(best_key),
        "confidence": round(confidence, 2),
    }