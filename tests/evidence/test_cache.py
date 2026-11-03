from datetime import timedelta

import pytest

from quickshop.evidence.cache import EvidenceCache, canonicalize_url
from quickshop.evidence.schema import EvidenceRecord


@pytest.mark.parametrize("raw,expected", [
    ("https://Example.com/p/1", "https://example.com/p/1"),
    ("https://example.com/p/1/", "https://example.com/p/1"),
    ("https://example.com/p/1#reviews", "https://example.com/p/1"),
    ("https://example.com/p/1?utm_source=x&utm_medium=y", "https://example.com/p/1"),
    ("https://example.com/p/1?color=red&utm_campaign=z", "https://example.com/p/1?color=red"),
    ("https://example.com/p/1?size=m&color=red", "https://example.com/p/1?color=red&size=m"),
    ("https://example.com/p/1?color=red&size=m", "https://example.com/p/1?color=red&size=m"),
    ("https://example.com/p/1?gclid=abc&fbclid=def", "https://example.com/p/1"),
    ("HTTPS://EXAMPLE.COM:443/p/1", "https://example.com/p/1"),
    ("http://example.com:8080/p/1", "http://example.com:8080/p/1"),
    ("https://example.com", "https://example.com"),
    ("https://example.com/", "https://example.com"),
    ("  https://example.com/p/1  ", "https://example.com/p/1"),
])
def test_canonicalize(raw, expected):
    assert canonicalize_url(raw) == expected


def test_variants_of_one_page_share_a_key():
    a = canonicalize_url("https://Shop.test/item/9/?utm_source=ad#top")
    b = canonicalize_url("https://shop.test/item/9")
    assert a == b


@pytest.mark.parametrize("bad", ["", "   ", "not a url", "ftp://x.test/a", "javascript:alert(1)", None])
def test_canonicalize_rejects_non_http(bad):
    with pytest.raises(ValueError):
        canonicalize_url(bad)


def rec(clock, status="ok", url="https://a.test/p"):
    return EvidenceRecord(url=url, canonical_url=url, fetched_at=clock(), status=status,
                          error_reason=None if status == "ok" else "x", title="T")


def test_miss_then_hit_and_counters(clock):
    c = EvidenceCache(":memory:", clock=clock)
    assert not c.get("https://a.test/p").hit
    c.put(rec(clock))
    look = c.get("https://a.test/p")
    assert look.hit and look.fresh and look.record.title == "T"
    assert c.stats() == {"hits": 1, "stale_hits": 0, "misses": 1, "writes": 1, "entries": 1}


def test_ttl_expires_per_field_group(clock):
    c = EvidenceCache(":memory:", clock=clock)
    c.put(rec(clock))
    clock.advance(hours=7)
    assert c.get("https://a.test/p").stale_groups == {"volatile"}        # price/stock: 6h
    clock.advance(days=7)
    assert c.get("https://a.test/p").stale_groups == {"volatile", "reviews"}   # reviews: 7d
    clock.advance(days=30)
    assert c.get("https://a.test/p").stale_groups == {"volatile", "reviews", "static"}   # composition: 30d


def test_within_ttl_nothing_is_stale(clock):
    c = EvidenceCache(":memory:", clock=clock)
    c.put(rec(clock))
    clock.advance(hours=5)
    assert c.get("https://a.test/p").fresh


def test_stale_lookup_counts_as_stale_hit(clock):
    c = EvidenceCache(":memory:", clock=clock)
    c.put(rec(clock))
    clock.advance(hours=7)
    c.get("https://a.test/p")
    assert c.stats()["stale_hits"] == 1 and c.stats()["hits"] == 0


def test_unavailable_is_only_remembered_briefly(clock):
    c = EvidenceCache(":memory:", clock=clock)
    c.put(rec(clock, status="unavailable"))
    clock.advance(minutes=10)
    assert c.get("https://a.test/p").fresh
    clock.advance(minutes=10)
    look = c.get("https://a.test/p")
    assert look.hit and not look.fresh and look.stale_groups      # past the 15 min negative ttl


def test_custom_ttls(clock):
    c = EvidenceCache(":memory:", clock=clock, ttls={"volatile": timedelta(minutes=1)})
    c.put(rec(clock))
    clock.advance(minutes=2)
    assert c.get("https://a.test/p").stale_groups == {"volatile"}


def test_put_overwrites_same_url(clock):
    c = EvidenceCache(":memory:", clock=clock)
    c.put(rec(clock))
    c.put(rec(clock, status="partial"))
    assert c.stats()["entries"] == 1 and c.get("https://a.test/p").record.status == "partial"


def test_disk_persistence_and_snapshot_roundtrip(clock, tmp_path):
    path = tmp_path / "nested" / "e.sqlite3"
    c = EvidenceCache(path, clock=clock)
    c.put(rec(clock))
    c.close()
    assert EvidenceCache(path, clock=clock).get("https://a.test/p").hit
    c2 = EvidenceCache(path, clock=clock)
    snap = tmp_path / "snap.json"
    assert c2.export_json(snap) == 1
    fresh = EvidenceCache(":memory:", clock=clock)
    assert fresh.import_json(snap) == 1 and fresh.get("https://a.test/p").record.title == "T"
