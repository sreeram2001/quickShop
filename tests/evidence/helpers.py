import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeScraper:
    """Stands in for Firecrawl. `responses` is a list of documents or exceptions, used in order
    (the last one repeats). Records every call."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def scrape(self, url, *, formats, timeout):
        self.calls.append({"url": url, "formats": formats, "timeout": timeout})
        r = self.responses[min(len(self.calls), len(self.responses)) - 1]
        if isinstance(r, Exception):
            raise r
        return r


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)
