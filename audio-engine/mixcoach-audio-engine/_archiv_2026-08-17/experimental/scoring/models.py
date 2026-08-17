from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


ImpactLevel = Literal["low", "medium", "high"]


class ScoreResult(BaseModel):
    name: str
    score: float
    weight: float
    impact: ImpactLevel
    explanation: str
    details: Dict[str, Any] = {}


class Recommendation(BaseModel):
    category: str
    message: str
    severity: ImpactLevel
    related_score: Optional[str] = None