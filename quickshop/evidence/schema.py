# The validated shape of what we learn from one product page.
# Rules: unknown is None (never a silent 0), percentages are 0-100, currency is a 3-letter code.
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Status = Literal["ok", "partial", "unavailable"]
Confidence = Literal["explicit", "ambiguous", "missing"]
FiberCategory = Literal["natural_plant", "natural_animal", "regenerated", "synthetic", "unknown"]
PartName = Literal["shell", "lining", "trim", "filling", "sleeve", "unspecified"]


class FiberShare(BaseModel):
    fiber: str                      # normalized name, e.g. "cotton" (organic cotton -> cotton)
    percent: float = Field(ge=0, le=100)
    category: FiberCategory
    original: str                   # the exact source text, e.g. "60% Organic Cotton"


class Component(BaseModel):
    part: PartName
    fibers: list[FiberShare]

    @property
    def total_percent(self) -> float:
        return round(sum(f.percent for f in self.fibers), 2)


class Price(BaseModel):
    amount: float = Field(ge=0)
    currency: str

    @field_validator("currency")
    @classmethod
    def _currency_code(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter code such as USD")
        return v


class ReviewSummary(BaseModel):
    rating: float | None = Field(default=None, ge=0, le=5)
    count: int | None = Field(default=None, ge=0)
    source: str | None = None


class ReturnPolicy(BaseModel):
    text: str                       # short form (trimmed, never paraphrased)
    source_snippet: str             # the exact text from the page


class EvidenceRecord(BaseModel):
    url: str
    canonical_url: str
    fetched_at: datetime
    status: Status
    error_reason: str | None = None

    title: str | None = None
    brand: str | None = None
    seller_name: str | None = None
    price: Price | None = None
    in_stock: bool | None = None

    composition: list[Component] = []
    composition_raw: str | None = None
    composition_confidence: Confidence = "missing"
    main_part: PartName | None = None            # which part natural_fiber_pct was computed from
    natural_fiber_pct: float | None = Field(default=None, ge=0, le=100)
    regenerated_fiber_pct: float | None = Field(default=None, ge=0, le=100)
    synthetic_fiber_pct: float | None = Field(default=None, ge=0, le=100)

    origin_country: str | None = None
    care_text: str | None = None
    return_policy: ReturnPolicy | None = None
    reviews: ReviewSummary | None = None

    source_snippets: dict[str, str] = {}         # field name -> exact text it came from
    parse_notes: list[str] = []                  # why a value is missing or ambiguous

    @field_validator("fetched_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self):
        if self.status != "ok" and not self.error_reason:
            raise ValueError("error_reason is required when status is not 'ok'")
        if self.natural_fiber_pct is not None and (not self.composition or self.main_part is None):
            raise ValueError("natural_fiber_pct needs a parsed composition and a main part")
        if self.composition_confidence == "missing" and self.natural_fiber_pct is not None:
            raise ValueError("natural_fiber_pct must be None when composition is missing")
        return self

    @classmethod
    def unavailable(cls, url: str, canonical_url: str, reason: str, now: datetime | None = None):
        return cls(
            url=url,
            canonical_url=canonical_url,
            fetched_at=now or datetime.now(timezone.utc),
            status="unavailable",
            error_reason=reason,
        )
