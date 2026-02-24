from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AnalysisResult(BaseModel):
    # Unknown keys from old cached entries are silently dropped so the cache
    # remains valid across schema upgrades.
    model_config = ConfigDict(extra="ignore")

    # ── Scene overview ────────────────────────────────────────────────────────
    vivid_description: str                           # 250–350 word immersive prose

    # ── Text & copy ───────────────────────────────────────────────────────────
    copy_verbatim: Optional[str] = None              # Every readable line, verbatim
    copy_meaning: Optional[str] = None              # What the copy communicates as a message
    typography_style: Optional[str] = None          # Font character, weight, style, feel
    typography_hierarchy: Optional[str] = None      # Primary / secondary / tertiary text

    # ── Colour ────────────────────────────────────────────────────────────────
    colour_palette: list[str] = []                   # Each colour with its role
    colour_scheme_type: Optional[str] = None        # e.g. complementary, monochromatic
    colour_psychology: Optional[str] = None         # Intended emotional effect

    # ── Offer & pricing ───────────────────────────────────────────────────────
    has_deal: Optional[bool] = None
    pricing_verbatim: Optional[str] = None          # Verbatim price / offer text
    pricing_text: Optional[str] = None              # Legacy alias — old cache compat
    deal_type: Optional[str] = None                 # bundle / percentage-off / etc.
    deal_conditions: Optional[str] = None           # Terms or fine print visible

    # ── Composition & background ──────────────────────────────────────────────
    background_description: Optional[str] = None   # Setting / environment
    background_objects: Optional[str] = None       # Other props and objects present
    visual_layers: Optional[str] = None            # Foreground / midground / background
    object_count: Optional[int] = None             # Approximate distinct visual elements

    # ── People ────────────────────────────────────────────────────────────────
    people_present: Optional[bool] = None
    people_description: Optional[str] = None       # Count, demographics, activity

    # ── Product & brand ───────────────────────────────────────────────────────
    product_placement: Optional[str] = None        # Spatial position, visual weight
    brand_presence: Optional[str] = None           # Logo / name prominence

    # ── Overall assessment ────────────────────────────────────────────────────
    visual_hierarchy: Optional[list[str]] = None   # What draws the eye, ranked
    emotional_tone: Optional[str] = None           # Dominant intended emotion
    implied_audience: Optional[str] = None         # Who this targets


class LoadedImage(BaseModel):
    filename: str
    hash: str
    analysis: AnalysisResult
