from pydantic import BaseModel
from typing import List, Optional

class ProblemSegment(BaseModel):
    loop: str
    segment: str
    element: str
    explain: str

class PredictResponse(BaseModel):
    denial_probability: float
    reasons: List[str]
    problem_segments: List[ProblemSegment]
    fix_suggestions: List[str]
    corrected_837: Optional[str] = ""
