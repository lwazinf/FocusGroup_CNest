import base64
import hashlib
import json
import os
import re
from typing import Optional

from services.image_analysis.config import (
    OLLAMA_CLOUD_API_KEY,
    OLLAMA_CLOUD_BASE_URL,
    OLLAMA_VISION_MODEL,
    MAX_IMAGE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
)
from services.image_analysis.image_redis import get_analysis, set_analysis, get_index, get_filename
from services.image_analysis.models import AnalysisResult, LoadedImage


# ── Custom exceptions ─────────────────────────────────────────────────────────

class ImageTooLargeError(Exception):
    """Image exceeds the maximum allowed size."""

class UnsupportedFormatError(Exception):
    """Image file extension is not supported."""

class AnalysisError(Exception):
    """Ollama vision call failed or returned unparseable output."""


# ── Analysis prompt ───────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """\
You are an expert advertising analyst. Examine this advertisement image with precision.

Return ONLY a valid JSON object — no markdown, no explanation, no code fences. \
Start your response with { and end with }.

The JSON must have exactly these fields:

{
  "vivid_description": "<Immersive prose, 250–350 words. Cover spatial layout, what draws the eye first, colour relationships, typography, product placement, negative space, lighting quality, and emotional atmosphere. Write as if describing the ad to someone who cannot see it.>",
  "colour_palette": ["<dominant colour and its emotional quality>", "<secondary colour and its role>"],
  "typography_notes": "<Font style, weight, hierarchy, placement, and how text integrates with the imagery>",
  "product_placement": "<Where the product sits spatially, how much visual weight it carries, what surrounds it, and why that positioning matters>",
  "pricing_text": "<Verbatim pricing or offer text visible in the image, or null if none present>",
  "emotional_tone": "<The dominant feeling the advertisement aims to evoke — e.g. aspiration, warmth, urgency, exclusivity>",
  "implied_audience": "<Who this advertisement is targeting, inferred from visual language, values signalled, lifestyle cues, and design choices>"
}"""


# ── Ollama client ─────────────────────────────────────────────────────────────

def _get_ollama_client():
    """Return an Ollama Client configured for the cloud endpoint."""
    from ollama import Client
    headers = {}
    if OLLAMA_CLOUD_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_CLOUD_API_KEY}"
    return Client(host=OLLAMA_CLOUD_BASE_URL, headers=headers)


# ── Utilities ─────────────────────────────────────────────────────────────────

def compute_hash(raw_bytes: bytes) -> str:
    return hashlib.md5(raw_bytes).hexdigest()


def validate_image(path: str, raw_bytes: bytes) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported format: {ext}. Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )
    if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
        mb = len(raw_bytes) // (1024 * 1024)
        raise ImageTooLargeError(f"Image is {mb} MB — maximum allowed is 20 MB.")


def format_for_personas(images: list[LoadedImage]) -> str:
    """
    Format all loaded images as a combined context block for persona injection.
    Personas can reference images by filename or as 'the first image', 'the second image', etc.
    """
    if not images:
        return ""

    parts = []
    for i, img in enumerate(images, start=1):
        r = img.analysis
        palette = ", ".join(r.colour_palette)
        pricing = r.pricing_text if r.pricing_text else "none visible"
        parts.append(
            f"Image {i} — {img.filename}\n"
            f"{r.vivid_description}\n\n"
            f"Colour palette: {palette}\n"
            f"Typography: {r.typography_notes}\n"
            f"Product placement: {r.product_placement}\n"
            f"Pricing / offer text: {pricing}\n"
            f"Emotional tone: {r.emotional_tone}\n"
            f"Implied audience: {r.implied_audience}"
        )

    header = (
        f"{len(images)} advertisement image{'s have' if len(images) != 1 else ' has'} been shared in the room.\n"
        "You may refer to them by filename or as 'the first image', 'the second image', etc.\n\n"
    )
    return header + "\n\n---\n\n".join(parts)


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _call_ollama(raw_bytes: bytes) -> dict:
    """Base64-encode the image and call the Ollama vision model."""
    client = _get_ollama_client()
    b64 = base64.b64encode(raw_bytes).decode("utf-8")

    try:
        response = client.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": ANALYSIS_PROMPT,
                    "images": [b64],
                }
            ],
        )
    except Exception as e:
        raise AnalysisError(f"Ollama vision call failed: {e}") from e

    raw_text = response["message"]["content"].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]+\}', raw_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise AnalysisError("Ollama returned a response that could not be parsed as JSON.")


def analyze_image(path: str) -> tuple[LoadedImage, bool]:
    """
    Analyze a single image file.

    Returns (LoadedImage, from_cache).
    Raises: ImageTooLargeError, UnsupportedFormatError, AnalysisError.
    """
    with open(path, "rb") as f:
        raw_bytes = f.read()

    filename = os.path.basename(path)
    validate_image(path, raw_bytes)

    md5_hex = compute_hash(raw_bytes)

    # Cache hit — skip Ollama call
    cached = get_analysis(md5_hex)
    if cached:
        return LoadedImage(filename=filename, hash=md5_hex, analysis=AnalysisResult(**cached)), True

    # Call Ollama
    analysis_dict = _call_ollama(raw_bytes)

    try:
        result = AnalysisResult(**analysis_dict)
    except Exception as e:
        raise AnalysisError(f"Analysis response missing required fields: {e}") from e

    set_analysis(md5_hex, filename, result.model_dump())
    return LoadedImage(filename=filename, hash=md5_hex, analysis=result), False


def get_loaded_images() -> list[LoadedImage]:
    """Return all images currently in the session index, in upload order."""
    images = []
    for md5_hex in get_index():
        cached = get_analysis(md5_hex)
        filename = get_filename(md5_hex) or md5_hex
        if cached:
            images.append(LoadedImage(
                filename=filename,
                hash=md5_hex,
                analysis=AnalysisResult(**cached),
            ))
    return images
