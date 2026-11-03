# One real call to Firecrawl. Skipped by default (it spends ~5 credits).
# Run:  FIRECRAWL_API_KEY=... QUICKSHOP_LIVE_URL=https://... pytest --run-live tests/evidence/test_live_smoke.py
import os

import pytest

from quickshop.evidence.cache import EvidenceCache
from quickshop.evidence.firecrawl_client import FirecrawlClient
from quickshop.evidence.schema import EvidenceRecord
from quickshop.evidence.service import EvidenceService

from dotenv import load_dotenv

load_dotenv()          # reads FIRECRAWL_API_KEY (and QUICKSHOP_LIVE_URL) from .env

pytestmark = pytest.mark.live


def test_live_product_page_returns_a_valid_record(tmp_path):
    if not os.getenv("FIRECRAWL_API_KEY"):
        pytest.skip("FIRECRAWL_API_KEY is not set")
    url = os.getenv("QUICKSHOP_LIVE_URL")
    if not url:
        pytest.skip("set QUICKSHOP_LIVE_URL to a clothing product page")
    service = EvidenceService(FirecrawlClient(), EvidenceCache(tmp_path / "live.sqlite3"))
    record = service.get_evidence(url)
    EvidenceRecord.model_validate(record.model_dump(mode="json"))
    print(record.model_dump_json(indent=2))
    assert record.status in {"ok", "partial", "unavailable"}
    if record.status != "unavailable":
        assert record.source_snippets
    assert service.usage()["firecrawl"]["calls"] >= 1
