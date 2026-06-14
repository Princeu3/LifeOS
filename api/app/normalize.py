"""Normalize a parsed capture's freeform `structured` dict into a typed domain-table row.

"Structured default, freeform fallback": this is a lenient, never-crash projection. The FULL parse
is always retained losslessly on `timeline_events.structured`, so these models use `extra="ignore"`
— the domain row is just the typed subset that powers trends/insights/doctor-PDF later. Anything the
model couldn't bucket stays in `structured['notes']` on the event (and `notes` here when present).

Returns `(ref_table, orm_row)` for capture.py to link via `event.ref_table/ref_id`, or `None` when
nothing structured was extracted (the event still stands on its own).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from .models import (
    BristolLog,
    CareRoutineRun,
    Domain,
    FoodLog,
    MoodLog,
    SleepLog,
    UrineLog,
)

# --- coercion helpers (lenient: bad input -> None, never raise) ---


def _coerce_int(v: Any) -> int | None:
    if v is None or isinstance(v, bool):
        return int(v) if isinstance(v, bool) else None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+", v)
        return int(m.group()) if m else None
    return None


def _ranged(lo: int, hi: int):
    def f(v: Any) -> int | None:
        i = _coerce_int(v)
        return None if i is None else max(lo, min(hi, i))

    return f


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+(?:\.\d+)?", v)
        return float(m.group()) if m else None
    return None


def _coerce_bool(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "yes", "y", "1"}:
            return True
        if s in {"false", "no", "n", "0"}:
            return False
    return None


def _coerce_dt(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _coerce_str(v: Any) -> str | None:
    if v is None:
        return None
    s = v if isinstance(v, str) else str(v)
    s = s.strip()
    return s or None


def _coerce_list(v: Any) -> list | None:
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [p.strip() for p in v.split(",") if p.strip()]
    return None


def _coerce_dict(v: Any) -> dict | None:
    return v if isinstance(v, dict) else None


Int15 = Annotated[int | None, BeforeValidator(_ranged(1, 5))]
Int17 = Annotated[int | None, BeforeValidator(_ranged(1, 7))]
Int18 = Annotated[int | None, BeforeValidator(_ranged(1, 8))]
IntN = Annotated[int | None, BeforeValidator(_coerce_int)]
Flt = Annotated[float | None, BeforeValidator(_coerce_float)]
Bln = Annotated[bool | None, BeforeValidator(_coerce_bool)]
Dtm = Annotated[datetime | None, BeforeValidator(_coerce_dt)]
Str = Annotated[str | None, BeforeValidator(_coerce_str)]
Lst = Annotated[list | None, BeforeValidator(_coerce_list)]
Dct = Annotated[dict | None, BeforeValidator(_coerce_dict)]


def _a(*names: str):
    return Field(default=None, validation_alias=AliasChoices(*names))


# --- per-domain typed projections (every field optional; aliases absorb key variance) ---


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SleepIn(_Base):
    bed_at: Dtm = _a("bed_at", "bedtime", "sleep_at", "slept_at", "start")
    wake_at: Dtm = _a("wake_at", "wake_time", "woke_at", "woke_up", "end")
    quality: Int15 = _a("quality", "sleep_quality", "rating")
    awakenings: IntN = _a("awakenings", "wakeups", "times_woke", "awakenings_count")
    notes: Str = _a("notes", "note", "comment")


class FoodIn(_Base):
    meal_type: Str = _a("meal_type", "type")
    dish_text: Str = _a("dish_text", "dish", "food", "meal_name", "item", "description")
    ingredients: Lst = _a("ingredients", "items")
    macros: Dct = _a("macros", "macro")  # NOT "nutrition" — that's the domain wrapper key
    caffeine_mg: Flt = _a("caffeine_mg", "caffeine")
    alcohol_units: Flt = _a("alcohol_units", "alcohol", "drinks")
    notes: Str = _a("notes", "note")


class MoodIn(_Base):
    mood: Int15 = _a("mood", "mood_score")
    energy: Int15 = _a("energy", "energy_level")
    stress: Int15 = _a("stress", "stress_level")
    journal: Str = _a("journal", "notes", "note", "text")


class BristolIn(_Base):
    bristol_type: Int17 = _a("bristol_type", "bristol", "stool_type", "type")
    color: Str = _a("color", "colour", "stool_color")
    straining: Bln = _a("straining", "strain")
    blood: Bln = _a("blood")
    pain: Bln = _a("pain", "painful")
    notes: Str = _a("notes", "note")


class UrineIn(_Base):
    color_scale: Int18 = _a("color_scale", "urine_color", "hydration_scale", "scale")
    notes: Str = _a("notes", "note")


class CareIn(_Base):
    completed: Bln = Field(default=True, validation_alias=AliasChoices("completed", "done", "complete"))
    exceptions: Lst = _a("exceptions", "skipped", "missed")
    notes: Str = _a("notes", "note", "routine", "routine_name")


# LLMs sometimes nest the extracted fields under a top-level domain-named key,
# e.g. {"sleep": {...}} or {"nutrition": {macros, dish_text, ...}}. Flatten those wrappers
# up so the typed projections find the fields (don't trust the LLM's nesting — grounded lesson).
_WRAPPERS: dict[Domain, set[str]] = {
    Domain.sleep: {"sleep"},
    Domain.nutrition: {"nutrition", "food", "meal", "diet"},
    Domain.mood: {"mood", "mental"},
    Domain.egestion: {"egestion", "bristol", "stool", "urine", "urination", "bowel"},
    Domain.care: {"care", "routine", "skincare", "hygiene"},
}


def flatten(domain: Domain, s: dict | None) -> dict:
    """Hoist a domain-named wrapper dict ({'sleep': {...}}) to the top level. Used both to
    normalize into the domain row AND to store a clean `structured` on the event."""
    if not isinstance(s, dict):
        return {}
    wrappers = _WRAPPERS.get(domain, set())
    out: dict = {}
    for k, v in s.items():
        if isinstance(v, dict) and k.lower() in wrappers:
            out.update(v)  # hoist a domain-named wrapper dict to the top level
        else:
            out.setdefault(k, v)
    return out


def _validate(model: type[_Base], structured: dict) -> _Base | None:
    try:
        return model.model_validate(structured)
    except ValidationError:
        return None


def _nonempty(m: _Base) -> bool:
    return bool(m.model_dump(exclude_none=True, exclude_defaults=True))


def _normalize_egestion(s: dict) -> tuple[str, Any] | None:
    keys = {k.lower() for k in s}
    looks_urine = bool(keys & {"color_scale", "urine_color", "hydration_scale"}) and not (
        keys & {"bristol_type", "bristol", "stool_type", "stool_color"}
    )
    if looks_urine:
        m = _validate(UrineIn, s)
        if not m or not _nonempty(m):
            return None
        return "urine_logs", UrineLog(color_scale=m.color_scale, notes=m.notes)
    m = _validate(BristolIn, s)
    if not m or not _nonempty(m):
        return None
    return "bristol_logs", BristolLog(
        bristol_type=m.bristol_type, color=m.color, straining=m.straining,
        blood=m.blood, pain=m.pain, notes=m.notes,
    )


def normalize(domain: Domain, structured: dict | None) -> tuple[str, Any] | None:
    """Project a parsed capture into a typed domain-table row, or None (event-only)."""
    s = structured or {}
    if not isinstance(s, dict):
        return None
    s = flatten(domain, s)

    if domain == Domain.egestion:
        return _normalize_egestion(s)

    if domain == Domain.sleep:
        m = _validate(SleepIn, s)
        if not m or not _nonempty(m):
            return None
        return "sleep_logs", SleepLog(
            bed_at=m.bed_at, wake_at=m.wake_at, quality=m.quality,
            awakenings=m.awakenings, notes=m.notes,
        )

    if domain == Domain.nutrition:
        m = _validate(FoodIn, s)
        if not m or not _nonempty(m):
            return None
        return "food_logs", FoodLog(
            meal_type=m.meal_type, dish_text=m.dish_text, ingredients=m.ingredients,
            macros=m.macros, caffeine_mg=m.caffeine_mg, alcohol_units=m.alcohol_units, notes=m.notes,
        )

    if domain == Domain.mood:
        m = _validate(MoodIn, s)
        if not m or not _nonempty(m):
            return None
        return "mood_logs", MoodLog(mood=m.mood, energy=m.energy, stress=m.stress, journal=m.journal)

    if domain == Domain.care:
        # A care capture inherently means a routine ran — always log it (even if only `completed`).
        m = _validate(CareIn, s) or CareIn()
        return "care_routine_runs", CareRoutineRun(
            completed=m.completed if m.completed is not None else True,
            exceptions=m.exceptions, notes=m.notes,
        )

    return None  # hydration/work/body_metric/etc. — event-only for now
