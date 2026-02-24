from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class AnalysisResult(BaseModel):
    vivid_description: str
    colour_palette: list[str]
    typography_notes: str
    product_placement: str
    pricing_text: Optional[str] = None
    emotional_tone: str
    implied_audience: str


class LoadedImage(BaseModel):
    filename: str
    hash: str
    analysis: AnalysisResult
