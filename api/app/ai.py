"""AI capture parsing — "structured default, freeform fallback".

A DSPy signature (run over OpenRouter) routes freeform text/voice into one domain and extracts
structured fields ONLY where confident; anything ambiguous stays in `structured['notes']`, and the
raw input is always retained by the caller. With no OpenRouter key (or on any error) it degrades to
a safe freeform entry at confidence 0.
"""

from __future__ import annotations

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
        )
    )
    _CONFIGURED = True
    return True


class RouteAndExtract(dspy.Signature):
    """Route a freeform life-log into exactly one domain and extract structured fields ONLY where
    confident. Leave anything ambiguous in structured['notes']. Never invent values."""

    text: str = dspy.InputField(desc="freeform text or voice transcript")
    domain_hint: str = dspy.InputField(desc="caller's domain guess, or 'none'")
    domain: Domain = dspy.OutputField()
    structured: dict = dspy.OutputField(desc="fields you are confident about; ambiguous -> 'notes'")
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
        pred = _extract(text=text, domain_hint=domain_hint.value if domain_hint else "none")
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
