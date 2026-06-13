"""Photo vision analysis over OpenRouter.

Per the locked rule "AI vision output = observation, not metric": this returns descriptive,
relative observations (never a diagnosis or a hard metric), stamped with model id + confidence +
prompt version. Health/identity photo types (face/skin/body/nails/hair) route ONLY to the ZDR
Claude vision model — NEVER to nano-banana (which has no ZDR endpoint). Wardrobe (a separate
domain) is the only thing that goes to nano-banana, and is not handled here.

On any failure (no key, network, bad JSON) it returns None — a vision miss must never block or
lose a photo upload.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .config import settings

PROMPT_VERSION = "vision-v1"

# Health/identity photo types all route to the ZDR Claude vision model.
_HEALTH_TYPES = {"face", "skin", "body", "nails", "hair"}

_TYPE_GUIDANCE = {
    "skin": "hydration appearance, redness, visible breakouts/areas of concern, texture, oiliness/shine, tone evenness",
    "face": "overall skin condition, redness, breakouts, under-eye appearance, hydration, visible texture",
    "body": "posture, relative muscle definition/fullness, visible skin condition — describe only what is visible",
    "nails": "signs of nail-biting (short/uneven/torn edges), length, cuticle condition, ridging, discoloration",
    "hair": "density/coverage appearance, scalp visibility, frizz, shine, breakage at ends",
}

_SYSTEM = (
    "You are a careful visual logger for a personal health-tracking app. Describe ONLY what is "
    "visibly present in the photo as neutral, relative observations. Do NOT diagnose, do NOT give "
    "medical advice, do NOT estimate identity, age, or numeric metrics. If something is unclear, "
    "say so. Respond with ONLY a JSON object, no prose, no code fences."
)


def _model_id() -> str:
    """OpenRouter REST wants the bare vendor/slug; config stores the LiteLLM `openrouter/...` form."""
    m = settings.vision_health_model
    return m[len("openrouter/") :] if m.startswith("openrouter/") else m


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].removeprefix("json").strip() if "```" in text[3:] else text
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in vision response")
    return json.loads(text[start : end + 1])


async def analyze_photo(image_bytes: bytes, content_type: str, photo_type: str) -> dict | None:
    """Return {analysis: dict, model: str, confidence: float, prompt_version: str} or None.

    Routes health/identity types to the ZDR Claude vision model. The caller MUST already have
    checked `exclude_from_cloud_ai` is False before sending bytes here.
    """
    if not settings.openrouter_api_key:
        return None
    if photo_type not in _HEALTH_TYPES:
        return None  # wardrobe/other handled elsewhere (nano-banana) — never here

    guidance = _TYPE_GUIDANCE.get(photo_type, "anything notable that is clearly visible")
    b64 = base64.b64encode(image_bytes).decode()
    mime = content_type if content_type.startswith("image/") else "image/jpeg"
    data_url = f"data:{mime};base64,{b64}"

    body: dict[str, Any] = {
        "model": _model_id(),
        "temperature": 0,
        "max_tokens": 700,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                # Text BEFORE image (OpenRouter parsing recommendation).
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"This is a '{photo_type}' progress photo. Note: {guidance}.\n"
                            'Return JSON exactly like: {"observations": ["..."], '
                            '"attributes": {"<key>": "<short value>"}, '
                            '"confidence": 0.0}. confidence is your 0-1 confidence in the read. '
                            "Keep observations short and factual; relative, never absolute."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }
    if settings.openrouter_zdr:
        # Route ONLY to zero-data-retention endpoints; deny provider-side data collection.
        body["provider"] = {"zdr": True, "data_collection": "deny"}

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://github.com/Princeu3/LifeOS",
        "X-Title": "LifeOS",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions", json=body, headers=headers
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = _extract_json(content)
    except Exception:
        return None  # never block/lose a photo on a vision failure

    conf = parsed.pop("confidence", None)
    try:
        confidence = max(0.0, min(1.0, float(conf))) if conf is not None else None
    except (TypeError, ValueError):
        confidence = None
    return {
        "analysis": parsed,
        "model": _model_id(),
        "confidence": confidence,
        "prompt_version": PROMPT_VERSION,
    }
