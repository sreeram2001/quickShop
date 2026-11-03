# Small deterministic helpers that clean the non-composition fields the extractor returns.
# Each returns None (never a guess) when the value cannot be read safely.
from __future__ import annotations

import re

_CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}
_ORIGIN_PATTERNS = [
    re.compile(r"(?:made|manufactured|produced|assembled)\s+in\s+(?P<c>[^\n,.;()|]+)", re.I),
    re.compile(r"country\s+of\s+(?:origin|manufacture)\s*[:\-]?\s*(?P<c>[^\n,.;()|]+)", re.I),
    re.compile(r"product\s+of\s+(?P<c>[^\n,.;()|]+)", re.I),
    re.compile(r"imported\s+from\s+(?P<c>[^\n,.;()|]+)", re.I),
]


def clean_text(value) -> str | None:
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


def to_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d+(?:[.,]\d+)?", str(value).replace(" ", ""))
    return float(m.group().replace(",", ".")) if m else None


def to_int(value) -> int | None:
    f = to_float(value)
    if f is None or f < 0:
        return None
    return int(round(f))


def to_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "in stock", "available"}:
            return True
        if v in {"false", "no", "out of stock", "sold out", "unavailable"}:
            return False
    return None


_OUT_RE = re.compile(r"out of stock|sold out|no longer available|currently unavailable|unavailable|not available|"
                     r"discontinued|notify me when|back in stock soon", re.I)
_IN_RE = re.compile(r"\bin stock\b|only \d+ left|\d+ left in stock|low stock|few left|ready to ship|"
                    r"add to (?:cart|bag|basket)|available now", re.I)


def stock_from_text(text) -> bool | None:
    """Read stock from the page's own wording. None when absent or contradictory (e.g. per-variant text)."""
    t = clean_text(text)
    if not t:
        return None
    out, in_ = bool(_OUT_RE.search(t)), bool(_IN_RE.search(re.sub(_OUT_RE, " ", t)))
    if out == in_:
        return None
    return in_


def normalize_currency(code, price_text=None) -> str | None:
    """3-letter code if given; else from a $, £ or € symbol in the price text; else None."""
    if isinstance(code, str):
        c = code.strip()
        if c in _CURRENCY_SYMBOLS:
            return _CURRENCY_SYMBOLS[c]
        if len(c) == 3 and c.isalpha():
            return c.upper()
    if isinstance(price_text, str):
        for sym, iso in _CURRENCY_SYMBOLS.items():
            if sym in price_text:
                return iso
    return None


_NOT_A_COUNTRY = {"imported", "import", "domestic", "unknown", "n/a", "na", "none", "various", "multiple",
                  "see label", "see tag", "not specified", "other", "global", "worldwide"}


def parse_origin(text) -> str | None:
    """'Made in Portugal' -> 'Portugal'. A bare short country-like string is accepted as is."""
    t = clean_text(text)
    if not t:
        return None
    for pat in _ORIGIN_PATTERNS:
        m = pat.search(t)
        if m:
            country = m.group("c").strip(" .:-")
            return country if 2 <= len(country) <= 40 else None
    if t.strip(" .").lower() not in _NOT_A_COUNTRY and re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,38}", t):
        return t.strip(" .")
    return None


def _squash(s: str) -> str:
    return re.sub(r"[\s*_`|\\]+", " ", s).strip().lower()


def appears_verbatim(snippet: str | None, page_markdown: str | None) -> bool:
    """True if the snippet is really on the page (ignoring whitespace and markdown decoration)."""
    if not snippet or not page_markdown:
        return False
    return _squash(snippet) in _squash(page_markdown)
