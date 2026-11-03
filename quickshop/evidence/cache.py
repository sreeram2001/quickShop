# URL-keyed evidence cache (SQLite). Freshness is judged per field group, not per URL:
# slow fields live long, price and stock expire fast, and failures are only remembered briefly.
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from quickshop.evidence.schema import EvidenceRecord

DEFAULT_DB_PATH = ".cache/evidence.sqlite3"

FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "static": ("title", "brand", "seller_name", "composition", "origin_country", "care_text", "return_policy"),
    "reviews": ("reviews",),
    "volatile": ("price", "in_stock"),
}
TTLS: dict[str, timedelta] = {
    "static": timedelta(days=30),
    "reviews": timedelta(days=7),
    "volatile": timedelta(hours=6),
}
NEGATIVE_TTL = timedelta(minutes=15)   # how long an "unavailable" result is remembered

_TRACKING_PARAMS = {"gclid", "fbclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid",
                    "srsltid", "yclid", "ttclid", "_ga"}


def canonicalize_url(url: str) -> str:
    """One stable key per product page: no tracking params or fragment, lowercase host, no trailing slash."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("empty url")
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError(f"not an http(s) url: {url!r}")
    host = parts.hostname.lower()
    default_port = {"http": 80, "https": 443}[parts.scheme.lower()]
    netloc = host if parts.port in (None, default_port) else f"{host}:{parts.port}"
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    )
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


@dataclass
class CacheLookup:
    record: EvidenceRecord | None
    stale_groups: frozenset[str] = field(default_factory=frozenset)

    @property
    def hit(self) -> bool:
        return self.record is not None

    @property
    def fresh(self) -> bool:
        return self.record is not None and not self.stale_groups


class EvidenceCache:
    def __init__(self, path: str | Path = DEFAULT_DB_PATH, *, ttls: dict[str, timedelta] | None = None,
                 negative_ttl: timedelta = NEGATIVE_TTL,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.ttls = {**TTLS, **(ttls or {})}
        self.negative_ttl = negative_ttl
        self._clock = clock
        self._lock = threading.Lock()
        self.counters = {"hits": 0, "stale_hits": 0, "misses": 0, "writes": 0}
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS evidence ("
            "canonical_url TEXT PRIMARY KEY, status TEXT NOT NULL, "
            "fetched_at TEXT NOT NULL, record_json TEXT NOT NULL)"
        )
        self._db.commit()

    # -- reads / writes
    def get(self, canonical_url: str) -> CacheLookup:
        with self._lock:
            row = self._db.execute(
                "SELECT record_json FROM evidence WHERE canonical_url = ?", (canonical_url,)
            ).fetchone()
            if row is None:
                self.counters["misses"] += 1
                return CacheLookup(None)
            record = EvidenceRecord.model_validate_json(row[0])
            stale = self.stale_groups(record)
            self.counters["stale_hits" if stale else "hits"] += 1
            return CacheLookup(record, stale)

    def put(self, record: EvidenceRecord) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?)",
                (record.canonical_url, record.status, record.fetched_at.isoformat(),
                 record.model_dump_json()),
            )
            self._db.commit()
            self.counters["writes"] += 1

    def stale_groups(self, record: EvidenceRecord) -> frozenset[str]:
        age = self._clock() - record.fetched_at
        if record.status == "unavailable":
            return frozenset(FIELD_GROUPS) if age > self.negative_ttl else frozenset()
        return frozenset(g for g in FIELD_GROUPS if age > self.ttls[g])

    # -- observability and snapshots
    def stats(self) -> dict:
        with self._lock:
            n = self._db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        return {**self.counters, "entries": n}

    def export_json(self, path: str | Path) -> int:
        """Freeze the cache as a JSON snapshot (for reproducible evaluation runs)."""
        with self._lock:
            rows = self._db.execute("SELECT record_json FROM evidence").fetchall()
        Path(path).write_text(json.dumps([json.loads(r[0]) for r in rows], indent=2))
        return len(rows)

    def import_json(self, path: str | Path) -> int:
        items = json.loads(Path(path).read_text())
        for item in items:
            self.put(EvidenceRecord.model_validate(item))
        return len(items)

    def close(self) -> None:
        self._db.close()
