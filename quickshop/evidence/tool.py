# The agent-facing tool. Name, argument and return type match the old stub, so it drops into the registry.
from __future__ import annotations

import threading
from datetime import datetime, timezone

from strands import tool

from quickshop.evidence.schema import EvidenceRecord
from quickshop.evidence.service import EvidenceService

_service: EvidenceService | None = None
_lock = threading.Lock()


def get_service() -> EvidenceService:
    global _service
    with _lock:
        if _service is None:
            _service = EvidenceService()
        return _service


def set_service(service: EvidenceService | None) -> None:
    """Swap the service (tests, or evaluation with a frozen cache). None resets to the default."""
    global _service
    with _lock:
        _service = service


def get_usage() -> dict:
    """Firecrawl calls/credits and cache counters, for Part A's budget logic and for evaluation."""
    return get_service().usage()


@tool
def fetch_product_evidence(url: str) -> dict:
    """Read a product page for fabric, origin, price, return policy and review details.
    This is expensive: a fresh page read costs about 5 page-reading credits. Saved results are
    reused and cost nothing.

    Args:
        url: The product page url from a listing.

    Returns:
        An evidence record. status is "ok", "partial" or "unavailable" (with error_reason).
        composition_raw is the exact fabric text from the page. natural_fiber_pct is the share of
        natural fiber in the main fabric, or null if the fabric is unknown. Unknown fields are null,
        never guessed.
    """
    try:
        return get_service().get_evidence(url).model_dump(mode="json")
    except Exception as exc:  # the agent loop must never see an exception from this tool
        now = datetime.now(timezone.utc)
        return EvidenceRecord.unavailable(
            str(url), str(url), f"unexpected error: {type(exc).__name__}: {str(exc)[:200]}", now
        ).model_dump(mode="json")
