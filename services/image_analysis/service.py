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
You are a designer and marketing analyst. Your job is to document this advertisement with clinical \
precision — vivid, factual, and strictly neutral. Do not say whether the ad is good or bad. \
Do not praise or criticise it. Just describe exactly what you see.

Return ONLY a valid JSON object — no markdown, no explanation, no code fences. \
Start your response with { and end with }.

The JSON must have exactly these fields:

{
  "vivid_description": "<Immersive prose, 250–350 words. Describe spatial layout, the first thing the eye lands on, depth and layers, lighting quality, colour relationships, negative space, overall composition balance, and atmosphere. Write as if the reader cannot see the image at all.>",

  "copy_verbatim": "<Every line of text visible in the ad, copied exactly as written. Separate lines with ' | '. Include headlines, body copy, taglines, pricing, disclaimers, and any other readable text. If no text is present, write null.>",
  "copy_meaning": "<What the text communicates as a complete message — the idea or value proposition being sold. One concise paragraph. Neutral, no opinion.>",
  "typography_style": "<The character of the font(s): serif or sans-serif, weight (thin/regular/bold/black), and whether the style reads as premium, casual, urgent, playful, technical, or something else. Note if multiple fonts are used.>",
  "typography_hierarchy": "<Which text element is largest or most visually dominant (primary), what follows in weight (secondary), and what is fine print or tertiary. Describe size and weight contrast between levels.>",

  "colour_palette": ["<most dominant colour — name it and describe its role and emotional quality>", "<secondary colour — name it and describe its role>", "<accent or tertiary colour if present, or omit this entry>"],
  "colour_scheme_type": "<e.g. monochromatic, complementary, analogous, split-complementary, high-contrast achromatic, warm-dominant, cool-dominant, etc.>",
  "colour_psychology": "<What emotions or associations the colour choices are intended to trigger — e.g. trust, excitement, luxury, urgency, calm, energy. Neutral and observational, not evaluative.>",

  "has_deal": <true if any discount, bundle, promotional offer, or special pricing is visible; false otherwise>,
  "pricing_verbatim": "<Verbatim price or offer text exactly as it appears in the image, or null if none>",
  "deal_type": "<one of: bundle, percentage-off, amount-off, limited-time, free-gift, trade-in, financing, membership — or null if no deal is present>",
  "deal_conditions": "<Any terms, conditions, or fine print related to the offer, verbatim or closely paraphrased. null if none visible.>",

  "background_description": "<The physical environment or setting — studio backdrop, lifestyle scene, abstract gradient, outdoor location, plain colour, etc. Describe the mood and context it creates.>",
  "background_objects": "<Other props, objects, or supporting elements visible beyond the main product. List each with a brief description. Write 'none' if there are no secondary objects.>",
  "visual_layers": "<Describe what occupies the foreground, midground, and background of the composition.>",
  "object_count": <integer — approximate count of distinct visual elements including products, people, props, text blocks, logos, decorative elements>,

  "people_present": <true if any people or body parts are visible; false otherwise>,
  "people_description": "<If people are present: count, apparent age range, gender, ethnicity if determinable, activity, and facial expression or mood. null if no people.>",

  "product_placement": "<Where the product sits in the frame — left/right/centre, foreground/background — how large it appears relative to the whole image, and what frames or surrounds it.>",
  "brand_presence": "<Brand name and/or logo — exact location in frame, approximate size relative to image, and whether it reads as subtle / moderate / dominant at a glance.>",

  "visual_hierarchy": ["<the first thing the eye is drawn to>", "<second>", "<third>", "<fourth if applicable>"],
  "emotional_tone": "<The dominant feeling the ad is designed to evoke — e.g. aspiration, nostalgia, urgency, trust, excitement, exclusivity, warmth, power. One phrase.>",
  "implied_audience": "<Who this ad is targeting. Be specific about inferred age range, gender, lifestyle, income level, and psychographics — based only on what the visual language and design choices signal.>"
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
    Format all loaded images as a structured context block for persona injection.
    Personas can reference images by filename or as 'the first image', 'the second image', etc.
    Handles both new rich-schema entries and old cached entries gracefully.
    """
    if not images:
        return ""

    def _opt(label: str, value) -> str:
        """Render a labelled line only when value is non-None and non-empty."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return f"{label}: {'yes' if value else 'no'}\n"
        if isinstance(value, list):
            return f"{label}: {', '.join(str(v) for v in value)}\n" if value else ""
        return f"{label}: {value}\n" if str(value).strip() else ""

    parts = []
    for i, img in enumerate(images, start=1):
        r = img.analysis
        block = f"Image {i} — {img.filename}\n"
        block += f"{r.vivid_description}\n"

        # ── Text & copy ──────────────────────────────────────────────────────
        if r.copy_verbatim:
            block += f"\nText visible in ad: {r.copy_verbatim}\n"
        if r.copy_meaning:
            block += f"Message: {r.copy_meaning}\n"
        if r.typography_style or r.typography_hierarchy:
            style = r.typography_style or ""
            hier = r.typography_hierarchy or ""
            if style and hier:
                block += f"Typography: {style} — hierarchy: {hier}\n"
            else:
                block += f"Typography: {style or hier}\n"

        # ── Colour ───────────────────────────────────────────────────────────
        if r.colour_palette:
            block += f"\nColour palette: {', '.join(r.colour_palette)}\n"
        block += _opt("Colour scheme", r.colour_scheme_type)
        block += _opt("Colour psychology", r.colour_psychology)

        # ── Deal / pricing ───────────────────────────────────────────────────
        pricing = r.pricing_verbatim or r.pricing_text
        if r.has_deal:
            deal_str = "\nDeal: "
            deal_str += r.deal_type if r.deal_type else "present"
            if pricing:
                deal_str += f" — {pricing}"
            if r.deal_conditions:
                deal_str += f" ({r.deal_conditions})"
            block += deal_str + "\n"
        elif r.has_deal is False:
            block += "\nDeal: none\n"
        elif pricing:
            block += f"\nPricing / offer: {pricing}\n"

        # ── Composition & background ─────────────────────────────────────────
        block += _opt("\nBackground", r.background_description)
        block += _opt("Objects", r.background_objects)
        block += _opt("Layers", r.visual_layers)
        if r.object_count is not None:
            block += f"Visual element count: ~{r.object_count}\n"

        # ── People ───────────────────────────────────────────────────────────
        if r.people_present and r.people_description:
            block += f"People: {r.people_description}\n"
        elif r.people_present is False:
            block += "People: none\n"

        # ── Product & brand ──────────────────────────────────────────────────
        block += _opt("\nProduct placement", r.product_placement)
        block += _opt("Brand", r.brand_presence)

        # ── Overall ──────────────────────────────────────────────────────────
        if r.visual_hierarchy:
            block += f"\nEye path: {' → '.join(r.visual_hierarchy)}\n"
        block += _opt("Emotional tone", r.emotional_tone)
        block += _opt("Implied audience", r.implied_audience)

        parts.append(block.rstrip())

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
