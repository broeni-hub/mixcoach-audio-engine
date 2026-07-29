from dataclasses import asdict, dataclass
from typing import Dict, List, Literal, Optional


EventType = Literal[
    "track_start",
    "track_change",
    "transition",
    "segment_start",
    "energy_peak",
    "energy_drop",
    "set_start",
    "set_end",
]


@dataclass
class MixEvent:
    time: float
    event_type: EventType
    confidence: Optional[float]
    description: str
    metadata: Dict


def event_to_dict(event: MixEvent) -> Dict:
    return asdict(event)


def events_to_dicts(events: List[MixEvent]) -> List[Dict]:
    return [event_to_dict(event) for event in events]