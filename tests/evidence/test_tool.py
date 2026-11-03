# End to end through fixtures: URL -> cache -> (fake) Firecrawl -> parser -> validated record.
import re

import pytest
from helpers import load_fixture

from quickshop.evidence import tool as evidence_tool
from quickshop.evidence.schema import EvidenceRecord
from quickshop.tools import DEFAULT_TOOLS

URL = "https://Shop.test/p/1?utm_source=ad"


def test_blend_tee_full_record(make_service):
    service, _ = make_service(load_fixture("blend_tee"))
    r = service.get_evidence(URL)
    assert r.status == "ok" and r.error_reason is None
    assert r.url == URL and r.canonical_url == "https://shop.test/p/1"
    assert r.title == "Everyday Crew Tee - Navy" and r.brand == "Example Outfitters"
    assert (r.price.amount, r.price.currency) == (24.0, "USD") and r.in_stock is True
    assert r.composition_raw == "60% Cotton, 40% Polyester"
    assert r.composition_confidence == "explicit" and r.natural_fiber_pct == 60.0
    assert r.synthetic_fiber_pct == 40.0 and r.main_part == "unspecified"
    assert r.origin_country == "Vietnam"
    assert r.return_policy.source_snippet.startswith("Free returns within 30 days")
    assert (r.reviews.rating, r.reviews.count) == (4.4, 210)
    assert r.source_snippets["composition"] == "60% Cotton, 40% Polyester"
    assert r.source_snippets["price"] == "$24.00" and r.source_snippets["origin_country"] == "Made in Vietnam"


def test_shell_lining_uses_the_shell_not_the_lining(make_service):
    r = make_service(load_fixture("shell_lining_jacket"))[0].get_evidence(URL)
    assert r.main_part == "shell" and r.natural_fiber_pct == 100.0
    assert {c.part for c in r.composition} == {"shell", "lining", "trim"}
    assert r.origin_country == "Portugal" and r.reviews is None


def test_euro_price_and_table_layout(make_service):
    r = make_service(load_fixture("wool_sweater"))[0].get_evidence(URL)
    assert (r.price.amount, r.price.currency) == (89.9, "EUR")
    assert r.natural_fiber_pct == 80.0 and r.origin_country == "Italy"


def test_missing_composition_is_partial_and_null_not_zero(make_service):
    r = make_service(load_fixture("missing_composition"))[0].get_evidence(URL)
    assert r.status == "partial" and "composition missing" in r.error_reason
    assert r.composition_confidence == "missing" and r.composition == []
    assert r.natural_fiber_pct is None                       # never silently 0
    assert r.price.amount == 29.99


def test_composition_recovered_from_markdown_when_extractor_misses_it(make_service):
    r = make_service(load_fixture("markdown_fallback"))[0].get_evidence(URL)
    assert r.natural_fiber_pct == 100.0 and r.composition_confidence == "explicit"
    assert any("page markdown" in n for n in r.parse_notes)


def test_composition_the_page_does_not_contain_is_discarded(make_service):
    r = make_service(load_fixture("invented_composition"))[0].get_evidence(URL)
    assert r.composition == [] and r.natural_fiber_pct is None and r.composition_raw is None
    assert any("not found on the page" in n for n in r.parse_notes)


def test_reworded_but_numbers_present_is_ambiguous(make_service):
    doc = load_fixture("blend_tee")
    doc["json"]["composition_text"] = "Cotton 60%, Polyester 40%"
    r = make_service(doc)[0].get_evidence(URL)
    assert r.composition_confidence == "ambiguous" and r.natural_fiber_pct == 60.0
    assert any("reworded" in n for n in r.parse_notes)


@pytest.mark.parametrize("name,reason", [
    ("blocked_page", "403"), ("blocked_page_200", "bot protection"), ("non_product_page", "not a product page")])
def test_failures_are_unavailable_with_reason(make_service, name, reason):
    r = make_service(load_fixture(name))[0].get_evidence(URL)
    assert r.status == "unavailable" and reason in r.error_reason
    assert r.natural_fiber_pct is None and r.composition == []


def test_malformed_extraction_still_yields_a_record_from_markdown(make_service):
    doc = {"markdown": "# Shirt\nFabric: 70% Cotton, 30% Linen\n", "json": "garbage",
           "metadata": {"status_code": 200}}
    r = make_service(doc)[0].get_evidence(URL)
    assert r.natural_fiber_pct == 100.0 and r.status == "partial"        # price is missing


def test_invalid_url_is_unavailable_without_calling_firecrawl(make_service):
    service, scraper = make_service(load_fixture("blend_tee"))
    r = service.get_evidence("not a url")
    assert r.status == "unavailable" and "invalid url" in r.error_reason and scraper.calls == []


# ---------------- real pages captured with Firecrawl (see fixtures/README.md)
def test_real_jacket_uses_the_shell_not_the_lining(make_service):
    r = make_service(load_fixture("live_jacket_shell_lining"))[0].get_evidence("https://www.altitude-sports.com/p/x")
    assert r.status == "ok" and r.composition_confidence == "explicit"
    assert r.main_part == "shell" and r.natural_fiber_pct == 100.0
    parts = {c.part: [(f.fiber, f.percent) for f in c.fibers] for c in r.composition}
    assert parts == {"shell": [("cotton", 100.0)], "lining": [("polyester", 100.0)]}
    assert r.composition_raw == "• Shell: 100% Cotton\n• Lining: 100% Polyester"
    assert r.price.currency == "CAD" and r.source_snippets["composition"] == r.composition_raw


def test_real_cotton_polyester_blend(make_service):
    r = make_service(load_fixture("live_tee_cotton_poly_blend"))[0].get_evidence("https://www.academy.com/p/x")
    assert r.status == "ok" and r.composition_confidence == "explicit"
    assert r.natural_fiber_pct == 50.0 and r.synthetic_fiber_pct == 50.0
    assert r.composition_raw == "Made of 50% cotton and 50% polyester"
    assert (r.price.amount, r.price.currency) == (20.99, "USD")
    # the extractor said in_stock=false but the page says "Hurry! Only 2 left!": the page text wins
    assert r.in_stock is True and any("contradicted" in n for n in r.parse_notes)


@pytest.mark.parametrize("name", ["live_jacket_shell_lining", "live_tee_cotton_poly_blend"])
def test_real_pages_composition_text_is_on_the_page(name):
    from quickshop.evidence.page_fields import appears_verbatim
    doc = load_fixture(name)
    assert appears_verbatim(doc["json"]["composition_text"], doc["markdown"])


# ---------------- cache behaviour through the service
def test_second_call_is_served_from_cache(make_service):
    service, scraper = make_service(load_fixture("blend_tee"))
    a = service.get_evidence(URL)
    b = service.get_evidence("https://shop.test/p/1/#top")             # same page, different spelling
    assert a == b and len(scraper.calls) == 1
    assert service.usage()["cache"]["hits"] == 1 and service.usage()["firecrawl"]["credits_used"] == 5


def test_scrapes_the_canonical_url(make_service):
    service, scraper = make_service(load_fixture("blend_tee"))
    service.get_evidence(URL)
    assert scraper.calls[0]["url"] == "https://shop.test/p/1"


def test_stale_price_triggers_refetch(make_service, clock):
    first, second = load_fixture("blend_tee"), load_fixture("blend_tee")
    second["json"]["price_amount"] = 19.0
    service, scraper = make_service(first, second)
    assert service.get_evidence(URL).price.amount == 24.0
    clock.advance(hours=7)
    assert service.get_evidence(URL).price.amount == 19.0 and len(scraper.calls) == 2


def test_failed_refresh_keeps_old_data_and_says_so(make_service, clock):
    service, _ = make_service(load_fixture("blend_tee"), load_fixture("blocked_page"))
    service.get_evidence(URL)
    clock.advance(hours=7)
    r = service.get_evidence(URL)
    assert r.status == "partial" and "refresh failed" in r.error_reason and "volatile" in r.error_reason
    assert r.natural_fiber_pct == 60.0
    assert service.cache.get("https://shop.test/p/1").record.status == "ok"     # cache not overwritten


def test_unavailable_is_negatively_cached_briefly(make_service, clock):
    service, scraper = make_service(load_fixture("blocked_page"), load_fixture("blend_tee"))
    assert service.get_evidence(URL).status == "unavailable"
    clock.advance(minutes=5)
    assert service.get_evidence(URL).status == "unavailable" and len(scraper.calls) == 1
    clock.advance(minutes=20)
    assert service.get_evidence(URL).status == "ok" and len(scraper.calls) == 2


def test_setup_errors_are_never_cached(make_service, clock):
    class NoKey(Exception):
        status_code = 401
    service, scraper = make_service(NoKey("bad key"), load_fixture("blend_tee"))
    assert "rejected the API key" in service.get_evidence(URL).error_reason
    assert service.get_evidence(URL).status == "ok"          # next call retries at once, no 15 min wait
    assert len(scraper.calls) == 2


def test_force_refresh(make_service):
    service, scraper = make_service(load_fixture("blend_tee"))
    service.get_evidence(URL)
    service.get_evidence(URL, force_refresh=True)
    assert len(scraper.calls) == 2


def test_replay_mode_never_calls_firecrawl(make_service, clock):
    service, scraper = make_service(load_fixture("blend_tee"))
    service.get_evidence(URL)
    service.replay = True
    clock.advance(days=90)                                              # long stale, still served
    assert service.get_evidence(URL).status == "ok"
    miss = service.get_evidence("https://other.test/x")
    assert miss.status == "unavailable" and "replay" in miss.error_reason and len(scraper.calls) == 1


# ---------------- fidelity: every number in `composition` appears in `composition_raw`
@pytest.mark.parametrize("name", ["blend_tee", "shell_lining_jacket", "wool_sweater", "markdown_fallback",
                                  "live_jacket_shell_lining", "live_tee_cotton_poly_blend"])
def test_composition_numbers_come_from_composition_raw(make_service, name):
    r = make_service(load_fixture(name))[0].get_evidence(URL)
    raw_numbers = {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", r.composition_raw)}
    assert r.composition
    for comp in r.composition:
        for f in comp.fibers:
            assert f.percent in raw_numbers


# ---------------- the registered tool
def test_tool_returns_json_serialisable_dict_that_validates(make_service):
    service, _ = make_service(load_fixture("blend_tee"))
    evidence_tool.set_service(service)
    try:
        out = evidence_tool.fetch_product_evidence(URL)
        assert isinstance(out, dict) and EvidenceRecord.model_validate(out).natural_fiber_pct == 60.0
        import json
        json.dumps(out)
    finally:
        evidence_tool.set_service(None)


def test_tool_never_raises_even_if_the_service_explodes():
    class Boom:
        def get_evidence(self, url, **kw):
            raise RuntimeError("kaboom")

    evidence_tool.set_service(Boom())
    try:
        out = evidence_tool.fetch_product_evidence("https://x.test/p")
        assert EvidenceRecord.model_validate(out).status == "unavailable"
        assert "kaboom" in out["error_reason"]
    finally:
        evidence_tool.set_service(None)


def test_tool_failure_cases_still_validate(make_service):
    evidence_tool.set_service(make_service(load_fixture("blocked_page"))[0])
    try:
        out = evidence_tool.fetch_product_evidence(URL)
        assert EvidenceRecord.model_validate(out).status == "unavailable"
    finally:
        evidence_tool.set_service(None)


def test_usage_is_exposed_for_the_budget_hook(make_service):
    service, _ = make_service(load_fixture("blend_tee"))
    evidence_tool.set_service(service)
    try:
        evidence_tool.fetch_product_evidence(URL)
        usage = evidence_tool.get_usage()
        assert usage["firecrawl"]["calls"] == 1 and usage["firecrawl"]["credits_used"] == 5
        assert usage["cache"]["misses"] == 1
    finally:
        evidence_tool.set_service(None)


def test_registered_as_the_agents_evidence_tool():
    assert evidence_tool.fetch_product_evidence in DEFAULT_TOOLS
    assert evidence_tool.fetch_product_evidence.tool_name == "fetch_product_evidence"
    spec = evidence_tool.fetch_product_evidence.tool_spec
    assert "expensive" in spec["description"] and "url" in spec["inputSchema"]["json"]["properties"]
