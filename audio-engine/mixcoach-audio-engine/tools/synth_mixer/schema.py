"""Pydantic-Label-Schema fuer generierte Mixes - typsicher lesbar fuer eine
kuenftige Eval-Pipeline (siehe dataset_loader.py). Feldnamen orientieren
sich am vorgegebenen Beispiel-Schema; mixcoach_eval_pipeline.py existiert im
Projekt noch nicht (Stand 2026-07-12) - es gibt also noch keine bestehenden
Feldnamen, an die sich dieses Schema anpassen muesste. Sobald die Pipeline
gebaut wird, ist dataset_loader.py der vorgesehene Adapter-Punkt.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

CrossfadeCurve = Literal["linear", "equal_power", "exponential", "s_curve", "cut"]
TransitionTypeName = Literal["crossfade", "cut", "eq_blend"]
QualityProfileName = Literal[
    "clean", "off_phrase", "off_beat", "key_clash", "abrupt", "train_wreck",
]
StretchMethod = Literal["none", "librosa", "pedalboard"]


class TrackEntry(BaseModel):
    index: int
    source_file: str
    bpm_original: float
    bpm_in_mix: float
    key: Optional[str] = None
    camelot: Optional[str] = None
    start_in_mix: float
    end_in_mix: float
    stretch_method: StretchMethod = "none"


class TransitionEntry(BaseModel):
    index: int
    type: TransitionTypeName
    quality_profile: QualityProfileName
    overlap_start: float
    overlap_end: float
    center_time: float
    overlap_beats: float
    crossfade_curve: CrossfadeCurve
    phrase_offset_beats: float = 0.0
    beat_offset_ms: float = 0.0
    key_compatibility_camelot_distance: Optional[int] = None
    expected_quality_label: int = Field(ge=1, le=5)


class MixLabel(BaseModel):
    mix_id: str
    generator_version: str
    created_at: str
    sample_rate: int
    duration_seconds: float
    tracks: List[TrackEntry]
    transitions: List[TransitionEntry]
