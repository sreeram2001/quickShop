from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from quickshop.evidence.schema import Component, EvidenceRecord, FiberShare, Price, ReviewSummary

NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


def record(**kw):
    base = dict(url="https://a.test/p", canonical_url="https://a.test/p", fetched_at=NOW, status="ok")
    return EvidenceRecord(**{**base, **kw})


def test_minimal_ok_record_validates_and_defaults_to_unknown():
    r = record()
    assert r.natural_fiber_pct is None and r.price is None and r.in_stock is None
    assert r.composition == [] and r.composition_confidence == "missing"


def test_full_record_roundtrips_through_json():
    comp = Component(part="shell", fibers=[FiberShare(fiber="cotton", percent=60, category="natural_plant", original="60% Cotton")])
    r = record(composition=[comp], composition_raw="60% Cotton", composition_confidence="explicit",
               main_part="shell", natural_fiber_pct=60.0, price=Price(amount=24, currency="usd"),
               reviews=ReviewSummary(rating=4.4, count=210))
    again = EvidenceRecord.model_validate_json(r.model_dump_json())
    assert again == r and again.price.currency == "USD"


@pytest.mark.parametrize("pct", [-1, 100.5, 101])
def test_percent_must_be_0_to_100(pct):
    with pytest.raises(ValidationError):
        FiberShare(fiber="cotton", percent=pct, category="natural_plant", original="x")


@pytest.mark.parametrize("code", ["US", "DOLLAR", "12$", ""])
def test_currency_must_be_a_code(code):
    with pytest.raises(ValidationError):
        Price(amount=1, currency=code)


def test_rating_range_and_negative_count():
    with pytest.raises(ValidationError):
        ReviewSummary(rating=6)
    with pytest.raises(ValidationError):
        ReviewSummary(count=-3)


def test_not_ok_needs_a_reason():
    with pytest.raises(ValidationError):
        record(status="partial")
    with pytest.raises(ValidationError):
        record(status="unavailable")
    assert record(status="partial", error_reason="price missing").status == "partial"


def test_natural_pct_needs_a_composition():
    with pytest.raises(ValidationError):
        record(natural_fiber_pct=50.0)


def test_naive_datetime_becomes_utc():
    r = record(fetched_at=datetime(2026, 1, 1))
    assert r.fetched_at.tzinfo is not None and r.fetched_at.utcoffset().total_seconds() == 0


def test_unavailable_helper_is_valid_and_json_serialisable():
    r = EvidenceRecord.unavailable("u", "u", "blocked", NOW)
    assert r.status == "unavailable" and r.error_reason == "blocked"
    assert r.model_dump(mode="json")["fetched_at"].startswith("2026-11-02")
