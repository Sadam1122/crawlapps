from datetime import timedelta

import pytest

from mega_crawler.normalization.core import age_bucket, aware, parse_count, relevance, window
from mega_crawler.registries.catalog import load_registry
from mega_crawler.utils.safety import canonical_url


@pytest.mark.parametrize(
    "raw,expected,precision",
    [
        ("1,2 rb", 1200, "rounded"),
        ("1.2K", 1200, "rounded"),
        ("2 jt", 2000000, "rounded"),
        ("1M", 1000000, "rounded"),
        ("1.234", 1234, "exact"),
        ("1,234", 1234, "exact"),
        ("1.234.567", 1234567, "exact"),
        ("1,234.5", 1234.5, "exact"),
        ("1.234,5", 1234.5, "exact"),
        ("0", 0, "exact"),
    ],
)
def test_counts(raw, expected, precision):
    parsed = parse_count(raw)
    assert parsed.value == expected
    assert parsed.precision == precision
    assert parsed.raw == raw


@pytest.mark.parametrize("raw", [None, "", "N/A", "-", "hidden", "disembunyikan"])
def test_unavailable_is_not_zero(raw):
    assert parse_count(raw).value is None


@pytest.mark.parametrize("raw", ["NaN", "-3", "garbage", "inf"])
def test_invalid_counts(raw):
    with pytest.raises(ValueError):
        parse_count(raw)


def test_timezone_window_and_age():
    assert aware("2026-10-21T07:00:00+07:00") == aware("2026-10-21T00:00:00Z")
    with pytest.raises(ValueError):
        aware("2026-10-21")
    start, end = window(30, "2026-10-21T00:00:00Z")
    assert end - start == timedelta(days=30)
    assert start <= start + timedelta(seconds=1) < end
    assert end not in (start, start + timedelta(seconds=1))
    assert age_bucket(start, start + timedelta(days=7)) == "7-30d"
    with pytest.raises(ValueError):
        age_bucket(end, start)


def test_relevance_entities(settings):
    registry = load_registry(settings.config_dir)
    mandiri = next(r for r in registry if r["entity_id"] == "mandiri")
    ubs = next(r for r in registry if r["entity_id"] == "ubs")
    treasury = next(r for r in registry if r["entity_id"] == "treasury")
    assert relevance("Mandiri Livin emas", mandiri)["relevance_score"] == 1
    assert relevance("saya mandiri bekerja", mandiri)["relevance_score"] == 0
    assert relevance("UBS bank Swiss gold", ubs)["relevance_score"] == 0
    assert relevance("treasury banking gold", treasury)["relevance_score"] == 0
    assert relevance("MTR tujuan emas Mandiri", mandiri)["relevance_score"] == 0
    assert len({r["entity_id"] for r in registry if "antam" == r["entity_id"]}) == 1
    assert (
        next(r for r in registry if r["entity_id"] == "gopay")["provider_entity_id"] == "treasury"
    )


def test_url_identity():
    assert (
        canonical_url("https://example.org/p?id=1&utm_source=x#anchor")
        == "https://example.org/p?id=1"
    )
    assert canonical_url("https://example.org/p?id=2") != "https://example.org/p?id=1"
