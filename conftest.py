# Tests marked @pytest.mark.live call the real Firecrawl API and spend credits.
# They are skipped unless you run: pytest --run-live
import pytest


def pytest_addoption(parser):
    parser.addoption("--run-live", action="store_true", default=False,
                     help="run tests that call the real Firecrawl API (needs FIRECRAWL_API_KEY)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip = pytest.mark.skip(reason="live API test: pass --run-live to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
