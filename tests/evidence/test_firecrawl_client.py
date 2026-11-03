# The client must never raise, whatever the scraper does.
import pytest

from quickshop.evidence.firecrawl_client import ESTIMATED_CREDITS_PER_SCRAPE, FirecrawlClient

from helpers import FakeScraper, load_fixture

URL = "https://shop.test/p/1"


class RateLimitError(Exception):
    status_code = 429


class PaymentRequiredError(Exception):
    status_code = 402


class InternalServerError(Exception):
    status_code = 500


def client(*responses, **kw):
    scraper = FakeScraper(*responses)
    sleeps = []
    c = FirecrawlClient(scraper=scraper, sleep=sleeps.append, backoff_s=1.0, **kw)
    return c, scraper, sleeps


def test_success_returns_markdown_fields_and_credits():
    c, scraper, _ = client(load_fixture("blend_tee"))
    r = c.scrape_product(URL)
    assert r.ok and r.fields["composition_text"] == "60% Cotton, 40% Polyester" and "Everyday Crew" in r.markdown
    assert r.credits_used == 5 and c.usage.snapshot()["credits_used"] == 5
    assert scraper.calls[0]["formats"][0] == "markdown" and scraper.calls[0]["formats"][1]["type"] == "json"
    assert scraper.calls[0]["formats"][1]["schema"]["properties"]["composition_text"]


def test_credits_are_estimated_when_api_does_not_report_them():
    doc = load_fixture("blend_tee")
    del doc["metadata"]["credits_used"]
    c, *_ = client(doc)
    assert c.scrape_product(URL).credits_used == ESTIMATED_CREDITS_PER_SCRAPE


def test_no_api_key_is_unavailable_not_an_exception(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    r = FirecrawlClient().scrape_product(URL)
    assert not r.ok and "FIRECRAWL_API_KEY" in r.error_reason and r.cacheable is False


def test_timeout_is_retried_then_succeeds():
    c, scraper, sleeps = client(TimeoutError("slow"), load_fixture("blend_tee"))
    assert c.scrape_product(URL).ok
    assert len(scraper.calls) == 2 and sleeps == [1.0]
    assert c.usage.snapshot()["retries"] == 1


def test_timeout_every_time_gives_up_with_reason():
    c, scraper, sleeps = client(TimeoutError("slow"), max_retries=2)
    r = c.scrape_product(URL)
    assert not r.ok and "timeout" in r.error_reason and len(scraper.calls) == 3
    assert sleeps == [1.0, 2.0]                      # exponential backoff, bounded


def test_rate_limit_retries_with_backoff():
    c, scraper, sleeps = client(RateLimitError("429"), RateLimitError("429"), load_fixture("blend_tee"))
    assert c.scrape_product(URL).ok and sleeps == [1.0, 2.0]


def test_rate_limit_forever_is_unavailable():
    c, *_ = client(RateLimitError("429"), max_retries=1)
    r = c.scrape_product(URL)
    assert not r.ok and "rate limited" in r.error_reason


def test_server_error_is_retried():
    c, scraper, _ = client(InternalServerError("boom"), load_fixture("blend_tee"))
    assert c.scrape_product(URL).ok and len(scraper.calls) == 2


def test_out_of_credits_is_not_retried():
    c, scraper, sleeps = client(PaymentRequiredError("402"))
    r = c.scrape_product(URL)
    assert not r.ok and "credits exhausted" in r.error_reason and len(scraper.calls) == 1 and sleeps == []
    assert r.cacheable is False


def test_ordinary_failures_stay_cacheable():
    assert client(load_fixture("blocked_page"))[0].scrape_product(URL).cacheable is True


def test_unknown_exception_is_unavailable():
    c, *_ = client(ValueError("weird"))
    r = c.scrape_product(URL)
    assert not r.ok and "ValueError" in r.error_reason


def test_blocked_http_status():
    r = client(load_fixture("blocked_page"))[0].scrape_product(URL)
    assert not r.ok and "403" in r.error_reason and "blocked" in r.error_reason


def test_blocked_page_with_200_status_is_detected():
    r = client(load_fixture("blocked_page_200"))[0].scrape_product(URL)
    assert not r.ok and "bot protection" in r.error_reason


def test_empty_page():
    r = client({"markdown": "", "json": {}, "metadata": {"status_code": 200}})[0].scrape_product(URL)
    assert not r.ok and "empty" in r.error_reason


def test_none_document_is_empty_not_a_crash():
    r = client(None)[0].scrape_product(URL)
    assert not r.ok


def test_non_product_page():
    r = client(load_fixture("non_product_page"))[0].scrape_product(URL)
    assert not r.ok and "not a product page" in r.error_reason


def test_malformed_json_keeps_markdown_for_fallback():
    doc = {"markdown": "# Linen Shirt\n$58\nMaterial: 55% Linen, 45% Cotton", "json": "garbage {",
           "metadata": {"status_code": 200}}
    r = client(doc)[0].scrape_product(URL)
    assert r.ok and r.fields == {} and r.extraction_error and "55% Linen" in r.markdown


@pytest.mark.parametrize("weird", [object(), 42, "text", [], {"json": 5}])
def test_weird_scraper_output_never_raises(weird):
    r = client(weird)[0].scrape_product(URL)
    assert r.ok is False or isinstance(r.fields, dict)


def test_usage_counts_calls_and_failures():
    c, *_ = client(load_fixture("blend_tee"))
    c.scrape_product(URL)
    c.scrape_product(URL)
    assert c.usage.snapshot() == {"calls": 2, "successes": 2, "failures": 0, "retries": 0, "credits_used": 10}
