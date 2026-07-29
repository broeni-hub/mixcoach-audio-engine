from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KeyAnalysis(BaseModel):
    key: str
    camelot: Optional[str] = None
    confidence: float


class FrequencyBalance(BaseModel):
    bass: float
    low_mids: float
    mids: float
    highs: float


class BasicAnalysis(BaseModel):
    duration: float
    sample_rate: int
    rms: float
    peak: float
    tempo: float
    frequency_balance: FrequencyBalance


class PhraseSection(BaseModel):
    start: float
    end: float
    bars: int


class TransitionCandidate(BaseModel):
    start_time: float
    center_time: float
    end_time: float
    duration: float
    type: str
    confidence: float
    reason: str
    energy_before: float
    energy_current: float
    energy_after: float


class StructureSection(BaseModel):
    start: float
    end: float
    section: str
    average_energy: float


class EnergyPoint(BaseModel):
    time: float
    rms: float
    peak: float


class EnergyAnalysis(BaseModel):
    points: List[EnergyPoint]
    average_rms: float
    max_peak: float


class TrackAnalysis(BaseModel):
    filename: str
    duration: float
    sample_rate: int
    tempo: float
    key: KeyAnalysis
    beat_count: int
    first_beats: List[float]
    basic: BasicAnalysis
    phrases: List[PhraseSection]
    transitions: List[TransitionCandidate]
    energy: EnergyAnalysis
    structure: List[StructureSection]
    raw: Optional[Dict[str, Any]] = None