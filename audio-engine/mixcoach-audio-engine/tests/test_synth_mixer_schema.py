"""Tests fuer das pydantic-Label-Schema (tools/synth_mixer/schema.py)."""

import pytest
from pydantic import ValidationError

from tools.synth_mixer.schema import MixLabel, TrackEntry, TransitionEntry


def _valid_label_dict():
    return {
        "mix_id": "synth_000001",
        "generator_version": "1.0.0",
        "created_at": "2026-07-12T12:00:00Z",
        "sample_rate": 22050,
        "duration_seconds": 512.3,
        "tracks": [
            {
                "index": 0, "source_file": "trackA.mp3",
                "bpm_original": 126.0, "bpm_in_mix": 126.0,
                "key": "8A", "camelot": "8A",
                "start_in_mix": 0.0, "end_in_mix": 245.1,
                "stretch_method": "none",
            },
        ],
        "transitions": [
            {
                "index": 0, "type": "eq_blend", "quality_profile": "off_phrase",
                "overlap_start": 230.5, "overlap_end": 245.1, "center_time": 237.8,
                "overlap_beats": 32, "crossfade_curve": "equal_power",
                "phrase_offset_beats": 6, "beat_offset_ms": 0,
                "key_compatibility_camelot_distance": 1, "expected_quality_label": 2,
            },
        ],
    }


def test_valid_label_parses():
    label = MixLabel.model_validate(_valid_label_dict())
    assert label.mix_id == "synth_000001"
    assert len(label.transitions) == 1
    assert label.transitions[0].expected_quality_label == 2


def test_round_trip_json():
    label = MixLabel.model_validate(_valid_label_dict())
    dumped = label.model_dump_json()
    reloaded = MixLabel.model_validate_json(dumped)
    assert reloaded == label


def test_quality_label_out_of_range_rejected():
    data = _valid_label_dict()
    data["transitions"][0]["expected_quality_label"] = 6
    with pytest.raises(ValidationError):
        MixLabel.model_validate(data)


def test_unknown_quality_profile_rejected():
    data = _valid_label_dict()
    data["transitions"][0]["quality_profile"] = "not-a-real-profile"
    with pytest.raises(ValidationError):
        MixLabel.model_validate(data)


def test_unknown_crossfade_curve_rejected():
    data = _valid_label_dict()
    data["transitions"][0]["crossfade_curve"] = "reverb-blend"
    with pytest.raises(ValidationError):
        MixLabel.model_validate(data)


def test_track_entry_defaults_stretch_method_to_none():
    entry = TrackEntry(
        index=0, source_file="x.mp3", bpm_original=120.0, bpm_in_mix=120.0,
        start_in_mix=0.0, end_in_mix=10.0,
    )
    assert entry.stretch_method == "none"
