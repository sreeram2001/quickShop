# The pipeline: URL -> cache -> Firecrawl -> deterministic parsing -> validated EvidenceRecord.
# No scoring and no merchant checks here. It never raises: failures become status="unavailable".
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import ValidationError

from quickshop.evidence import page_fields as pf
from quickshop.evidence.cache import DEFAULT_DB_PATH, EvidenceCache, canonicalize_url
from quickshop.evidence.fabric import find_composition_text, parse_composition
from quickshop.evidence.firecrawl_client import FirecrawlClient, RawExtraction
from quickshop.evidence.schema import EvidenceRecord, Price, ReturnPolicy, ReviewSummary

load_dotenv()   # QUICKSHOP_EVIDENCE_* settings come from .env too

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers_on_page(snippet: str, markdown: str) -> bool:
    nums = {n.replace(",", ".") for n in _NUMBER_RE.findall(snippet)}
    page = {n.replace(",", ".") for n in _NUMBER_RE.findall(markdown)}
    return bool(nums) and nums <= page


def build_record(url: str, canonical_url: str, raw: RawExtraction, *, now: datetime | None = None,
                 count_regenerated_as_natural: bool | None = None) -> EvidenceRecord:
    """Turn one raw extraction into a validated record. Pure: no network, no cache."""
    now = now or datetime.now(timezone.utc)
    if not raw.ok:
        return EvidenceRecord.unavailable(url, canonical_url, raw.error_reason or "page unavailable", now)

    f = raw.fields or {}
    notes: list[str] = []
    snippets: dict[str, str] = {}
    if raw.extraction_error:
        notes.append(raw.extraction_error)

    # price
    price = None
    amount = pf.to_float(f.get("price_amount"))
    if amount is None and f.get("price_text"):
        amount = pf.to_float(f.get("price_text"))
    currency = pf.normalize_currency(f.get("price_currency"), f.get("price_text"))
    if amount is not None and currency:
        price = Price(amount=amount, currency=currency)
        if pf.clean_text(f.get("price_text")):
            snippets["price"] = pf.clean_text(f.get("price_text"))
    elif amount is not None:
        notes.append("price found but its currency is unknown")

    # composition: extractor text first, page markdown as fallback; never trust text the page does not contain
    comp_raw = (f.get("composition_text") or "").strip() or None
    from_markdown = False
    force_ambiguous = False
    if comp_raw is None:
        found, blocks = find_composition_text(raw.markdown)
        if found:
            comp_raw, from_markdown = found, True
            notes.append("composition read from page markdown (extractor returned none)")
            if blocks > 1:
                notes.append(f"{blocks} different composition blocks on the page")
                force_ambiguous = True
    elif raw.markdown and not pf.appears_verbatim(comp_raw, raw.markdown):
        if _numbers_on_page(comp_raw, raw.markdown):
            notes.append("composition text is reworded, not verbatim; its numbers do appear on the page")
            force_ambiguous = True
        else:
            notes.append(f"discarded composition not found on the page: {comp_raw[:120]!r}")
            comp_raw = None

    parsed = parse_composition(comp_raw, count_regenerated_as_natural=count_regenerated_as_natural)
    confidence = parsed.confidence
    if force_ambiguous and confidence == "explicit":
        confidence = "ambiguous"
    notes.extend(parsed.notes)
    if comp_raw:
        snippets["composition"] = comp_raw

    # origin, policy, reviews, stock
    origin = pf.parse_origin(f.get("origin_text"))
    if pf.clean_text(f.get("origin_text")):
        snippets["origin_country"] = pf.clean_text(f.get("origin_text"))
        if origin is None:
            notes.append("origin text present but no country could be read from it")

    policy = None
    policy_text = pf.clean_text(f.get("return_policy_text"))
    if policy_text:
        policy = ReturnPolicy(text=policy_text[:300], source_snippet=policy_text[:1000])
        snippets["return_policy"] = policy_text[:1000]

    reviews = None
    rating, count = pf.to_float(f.get("rating")), pf.to_int(f.get("review_count"))
    if rating is not None and not 0 <= rating <= 5:
        notes.append(f"rating {rating} is outside a 0-5 scale and was ignored")
        rating = None
    if rating is not None or count is not None:
        reviews = ReviewSummary(rating=rating, count=count, source=urlsplit(canonical_url).hostname)
        if pf.clean_text(f.get("rating_text")):
            snippets["reviews"] = pf.clean_text(f.get("rating_text"))

    # The page's own wording beats the extractor's true/false guess ("Only 2 left!" means in stock).
    in_stock = pf.to_bool(f.get("in_stock"))
    from_text = pf.stock_from_text(f.get("availability_text"))
    if from_text is not None:
        if in_stock is not None and in_stock != from_text:
            notes.append("stock flag from the extractor contradicted the page text; the page text was used")
        in_stock = from_text
    if pf.clean_text(f.get("availability_text")):
        snippets["in_stock"] = pf.clean_text(f.get("availability_text"))

    title = pf.clean_text(f.get("title"))
    if not (title or price or comp_raw):
        return EvidenceRecord.unavailable(url, canonical_url, "no product data could be read from the page", now)

    problems = []
    if confidence != "explicit":
        problems.append(f"composition {confidence}")
    if price is None:
        problems.append("price missing")
    try:
        return EvidenceRecord(
            url=url, canonical_url=canonical_url, fetched_at=now,
            status="ok" if not problems else "partial",
            error_reason="; ".join(problems) or None,
            title=title, brand=pf.clean_text(f.get("brand")), seller_name=pf.clean_text(f.get("seller_name")),
            price=price, in_stock=in_stock,
            composition=parsed.components, composition_raw=comp_raw if parsed.components or comp_raw else None,
            composition_confidence=confidence, main_part=parsed.main_part,
            natural_fiber_pct=parsed.natural_fiber_pct,
            regenerated_fiber_pct=parsed.regenerated_fiber_pct if parsed.main_part else None,
            synthetic_fiber_pct=parsed.synthetic_fiber_pct if parsed.main_part else None,
            origin_country=origin, care_text=pf.clean_text(f.get("care_text")),
            return_policy=policy, reviews=reviews, source_snippets=snippets, parse_notes=notes,
        )
    except ValidationError as exc:
        return EvidenceRecord.unavailable(url, canonical_url, f"extracted data failed validation: {exc.error_count()} errors", now)


class EvidenceService:
    def __init__(self, client: FirecrawlClient | None = None, cache: EvidenceCache | None = None, *,
                 replay: bool | None = None, clock: Callable[[], datetime] | None = None):
        self.client = client or FirecrawlClient()
        self.cache = cache or EvidenceCache(os.getenv("QUICKSHOP_EVIDENCE_CACHE") or DEFAULT_DB_PATH)
        self.replay = replay if replay is not None else os.getenv("QUICKSHOP_EVIDENCE_REPLAY", "") not in ("", "0")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def get_evidence(self, url: str, *, force_refresh: bool = False) -> EvidenceRecord:
        now = self._clock()
        try:
            canonical = canonicalize_url(url)
        except ValueError as exc:
            return EvidenceRecord.unavailable(str(url), str(url), f"invalid url: {exc}", now)

        cached = self.cache.get(canonical)
        if cached.record is not None and (self.replay or (cached.fresh and not force_refresh)):
            return cached.record
        if self.replay:
            return EvidenceRecord.unavailable(url, canonical, "replay mode: no cached evidence for this url", now)

        raw = self.client.scrape_product(canonical)
        record = build_record(url, canonical, raw, now=now)
        old = cached.record
        if record.status == "unavailable" and old is not None and old.status != "unavailable":
            # A refresh failed. Keep the old data, but say it may be out of date, and do not overwrite it.
            stale = ", ".join(sorted(cached.stale_groups)) or "none"
            return old.model_copy(update={
                "status": "partial",
                "error_reason": f"refresh failed ({record.error_reason}); stale field groups: {stale}",
            })
        if raw.cacheable:
            self.cache.put(record)
        return record

    def usage(self) -> dict:
        """Firecrawl calls/credits and cache hit/miss counters, for the budget hook and evaluation."""
        return {"firecrawl": self.client.usage.snapshot(), "cache": self.cache.stats()}
