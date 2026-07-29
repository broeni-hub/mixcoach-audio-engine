from typing import Dict

from app.audio.pipeline.pipeline import run_set_pipeline


def analyze_set(audio, progress=None) -> Dict:
    return run_set_pipeline(audio, progress=progress)