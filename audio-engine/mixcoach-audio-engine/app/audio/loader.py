from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import librosa
import numpy as np


@dataclass
class LoadedAudio:
    filename: str
    waveform: np.ndarray
    sample_rate: int
    duration_seconds: float
    channels: int
    is_mono: bool


def load_audio_file(
    file: BinaryIO,
    filename: str,
    target_sample_rate: int = 22050,
    max_duration_seconds: int = 120,
) -> LoadedAudio:
    """
    Load an audio file into a mono waveform for analysis.

    This function does not score or interpret the music.
    It only prepares clean audio data for later analysis.
    """

    suffix = Path(filename).suffix.lower()

    if suffix not in {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"}:
        raise ValueError(f"Unsupported audio format: {suffix}")

    waveform, sample_rate = librosa.load(
        file,
        sr=target_sample_rate,
        mono=True,
        duration=max_duration_seconds,
    )

    if waveform.size == 0:
        raise ValueError("Audio file could not be loaded or is empty.")

    duration_seconds = float(librosa.get_duration(y=waveform, sr=sample_rate))

    return LoadedAudio(
        filename=filename,
        waveform=waveform,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
        channels=1,
        is_mono=True,
    )
    