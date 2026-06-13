"""AI capture parsing — "structured default, freeform fallback".

A DSPy signature (run over OpenRouter) routes freeform text/voice into one domain and extracts
structured fields ONLY where confident; anything ambiguous stays in `structured['notes']`, and the
raw input is always retained by the caller. With no OpenRouter key (or on any error) it degrades to
a safe freeform entry at confidence 0.
"""

from __future__ import annotations

from datetime import datetime

import dspy

from .config import settings
from .models import Domain
from .schemas import ParsedEntry

_CONFIGURED = False


def _ensure_lm() -> bool:
    """Lazily configure DSPy to use the OpenRouter capture model. Returns False if no key."""
    global _CONFIGURED
    if _CONFIGURED:
        return True
    if not settings.openrouter_api_key:
        return False
    dspy.configure(
        lm=dspy.LM(
            settings.capture_model,  # e.g. openrouter/anthropic/claude-haiku-4.5
            api_key=settings.openrouter_api_key,
            api_base=settings.openrouter_base_url,
            temperature=0.0,
        ),
        adapter=dspy.JSONAdapter(),  # hardens structured-dict output (grounded: schema-mode is provider-flaky)
    )
    _CONFIGURED = True
    return True


# Per-domain key hints so the parser emits predictable keys for normalize.py to map.
_STRUCTURED_HINT = (
    "Fields you are confident about, keyed per domain — use these exact keys when they apply: "
    "sleep{bed_at,wake_at,quality(1-5),awakenings}; "
    "nutrition{meal_type,dish_text,ingredients[],macros{kcal,protein_g,carbs_g,fat_g},caffeine_mg,alcohol_units}; "
    "mood{mood(1-5),energy(1-5),stress(1-5),journal}; "
    "egestion{bristol_type(1-7),color,straining,blood,pain} OR {color_scale(1-8)} for urine; "
    "care{completed,exceptions[]}. Use ISO 8601 for any datetime, resolving relative times against `now`. "
    "Put anything you can't confidently bucket into 'notes'. Never invent values."
)


class RouteAndExtract(dspy.Signature):
    """Route a freeform life-log into exactly one domain and extract structured fields ONLY where
    confident. Resolve relative times against `now` and emit ISO 8601. Leave anything ambiguous in
    structured['notes']. Never invent values."""

    text: str = dspy.InputField(desc="freeform text or voice transcript")
    now: str = dspy.InputField(desc="current local datetime (ISO 8601) for resolving relative times")
    domain_hint: str = dspy.InputField(desc="caller's domain guess, or 'none'")
    domain: Domain = dspy.OutputField()
    structured: dict = dspy.OutputField(desc=_STRUCTURED_HINT)
    summary: str = dspy.OutputField(desc="one-line, embeddable summary")
    confidence: float = dspy.OutputField(desc="0-1 confidence in the routing + extraction")


_extract = dspy.Predict(RouteAndExtract)


def _fallback(text: str, domain_hint: Domain | None) -> ParsedEntry:
    return ParsedEntry(
        domain=domain_hint or Domain.media,
        structured={"notes": text},
        summary=text[:120],
        confidence=0.0,
        needs_confirmation=True,
    )


def parse_capture(text: str, domain_hint: Domain | None = None) -> ParsedEntry:
    if not text.strip() or not _ensure_lm():
        return _fallback(text, domain_hint)
    try:
        now = datetime.now().astimezone().isoformat()
        pred = _extract(
            text=text, now=now, domain_hint=domain_hint.value if domain_hint else "none"
        )
        dom = pred.domain if isinstance(pred.domain, Domain) else Domain(str(pred.domain))
        conf = float(pred.confidence)
        return ParsedEntry(
            domain=dom,
            structured=dict(pred.structured or {}),
            summary=pred.summary or text[:120],
            confidence=conf,
            needs_confirmation=conf < 0.6,
        )
    except Exception:
        # Never lose a log to a parsing failure — keep the raw input.
        return _fallback(text, domain_hint)
