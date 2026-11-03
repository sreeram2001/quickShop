import pytest
from helpers import Clock, FakeScraper

from quickshop.evidence.cache import EvidenceCache
from quickshop.evidence.firecrawl_client import FirecrawlClient
from quickshop.evidence.service import EvidenceService


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def make_service(clock):
    def _make(*responses, **kw):
        scraper = FakeScraper(*responses)
        client = FirecrawlClient(scraper=scraper, sleep=lambda s: None)
        cache = EvidenceCache(":memory:", clock=clock)
        service = EvidenceService(client, cache, clock=clock, **kw)
        return service, scraper

    return _make
