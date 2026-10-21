from datetime import timedelta

import pytest
from pydantic import ValidationError

from mega_crawler.analytics.content import classify
from mega_crawler.analytics.metrics import (
    age_observation,
    aggregate,
    compare_prices,
    composite_sensitivity,
    engagement,
    interactions,
    percentiles,
    ranks,
    velocity,
)
from mega_crawler.normalization.core import utcnow
from mega_crawler.schemas.intelligence import MetricObservation, PriceQuote


def test_numerator_no_double_count_and_zero_denominator():
    vals = {"likes": 10, "reactions": 20, "comments": 2, "video_views": 100}
    assert interactions(vals) == 12
    assert interactions(vals, "reactions") == 22
    assert engagement(vals) == 12
    assert engagement({**vals, "video_views": 0}) is None
    assert interactions({"likes": None, "comments": 2}) is None
    assert interactions(vals, extended=True) is None


def test_median_vs_pooled():
    rows = [
        {"likes": 10, "comments": 0, "video_views": 100},
        {"likes": 10, "comments": 0, "video_views": 1000},
    ]
    result = aggregate(rows)
    assert result["median_er_pct"] == 5.5
    assert result["pooled_er_pct"] == pytest.approx(20 / 1100 * 100)


def test_tie_and_percentile():
    assert ranks({"b": 10, "a": 10, "c": 5}) == {"a": 1, "b": 1, "c": 3}
    assert percentiles({"a": 1, "b": 2, "c": 2}) == {"a": 0, "b": 75, "c": 75}
    assert percentiles({"a": 1}) == {"a": None}


def test_missing_dimension_blocks_composite_and_sensitivity():
    weights = {"a": 0.6, "b": 0.4}
    assert composite_sensitivity({"x": {"a": 1}}, weights)["status"] == "unavailable"
    result = composite_sensitivity(
        {"x": {"a": 100, "b": 0}, "y": {"a": 0, "b": 100}, "z": {"a": 50, "b": 50}}, weights
    )
    assert result["status"] == "available"
    assert result["rank_ranges"]["x"][0] >= 1


def test_snapshots_correction_age():
    now = utcnow()
    rows = [
        {"observed_at_utc": now.isoformat(), "values": {"video_views": 100}},
        {"observed_at_utc": (now + timedelta(days=1)).isoformat(), "values": {"video_views": 80}},
    ]
    assert velocity(rows, "video_views") == {"status": "correction", "per_day": None}
    assert velocity(rows[:1], "video_views")["status"] == "unavailable"
    assert age_observation(now - timedelta(days=90), rows, 1) is None
    assert age_observation(now - timedelta(days=1), rows, 1) == rows[0]


def test_observation_requires_status():
    base = {
        "observation_id": "1",
        "platform": "youtube",
        "post_id": "p",
        "observed_at_utc": utcnow(),
        "metric_definition_version": "test",
        "source_url": "https://example.org/p",
        "evidence_hash": "hash",
    }
    with pytest.raises(ValidationError):
        MetricObservation(**base, values={"likes": 0}, metric_status={"likes": "request_failed"})
    with pytest.raises(ValidationError):
        MetricObservation(
            **base, values={"likes": float("nan")}, metric_status={"likes": "observed"}
        )
    obs = MetricObservation(**base, values={"likes": 0}, metric_status={"likes": "observed"})
    assert obs.values["shares"] is None


def test_price_perspective_and_time():
    now = utcnow()
    quote = PriceQuote(
        product_id="p",
        customer_buy_price=100,
        customer_sell_price=95,
        purity="9999",
        grams=1,
        channel="app",
        tax_basis="included",
        fees_basis="included",
        quoted_at_utc=now,
        source_url="https://example.org/price",
    )
    assert quote.spread_pct == 5
    assert compare_prices([quote]) == "perspective_unverified"
    quote.perspective_verified = True
    assert compare_prices([quote]) == "comparable"
    stale = quote.model_copy(update={"quoted_at_utc": now + timedelta(minutes=10)})
    assert compare_prices([quote, stale]) == "stale_or_mismatched"


def test_sentiment_aspect_not_mood_or_fraud():
    assert classify("harga emas turun Mandiri")["sentiment"] == "neutral"
    assert (
        classify("Jangan beli emas dari akun palsu atas nama Mandiri")["speech_type"]
        == "impersonation_warning"
    )
    assert classify("aplikasi buruk")["gold_relevant"] is False
    assert classify("gagal beli emas")["validation_status"] == "preliminary_unvalidated"
