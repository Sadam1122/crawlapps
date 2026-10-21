import math
from statistics import median

from mega_crawler.normalization.core import aware


def interactions(values, reaction_field="likes", extended=False):
    fields = [reaction_field, "comments"]
    if extended:
        fields += ["shares", "reposts", "quotes"]
    if any(values.get(field) is None for field in fields):
        return None
    return sum(values[field] for field in fields)


def engagement(values, denominator="video_views", reaction_field="likes"):
    numerator = interactions(values, reaction_field)
    count = values.get(denominator)
    return (
        numerator / count * 100
        if numerator is not None and count is not None and count > 0
        else None
    )


def aggregate(values, denominator="video_views", reaction_field="likes"):
    eligible = [v for v in values if engagement(v, denominator, reaction_field) is not None]
    return {
        "median_er_pct": median([engagement(v, denominator, reaction_field) for v in eligible])
        if eligible
        else None,
        "pooled_er_pct": sum(interactions(v, reaction_field) for v in eligible)
        / sum(v[denominator] for v in eligible)
        * 100
        if eligible
        else None,
        "n_observed": len(eligible),
    }


def percentiles(values):
    """Average tied ascending rank: 100*(rank-1)/(n-1), n>=2."""
    n = len(values)
    if n < 2:
        return {k: None for k in values}
    return {
        k: 100
        * (
            sum(x < value for x in values.values())
            + (sum(x == value for x in values.values()) - 1) / 2
        )
        / (n - 1)
        for k, value in values.items()
    }


def ranks(values):
    return {k: 1 + sum(v > value for v in values.values()) for k, value in sorted(values.items())}


def composite_sensitivity(dimensions, weights):
    """All participants require all dimensions. Global perturbation, never per-brand reweight."""
    if len(dimensions) < 3 or any(
        set(v) != set(weights) or any(x is None for x in v.values()) for v in dimensions.values()
    ):
        return {
            "status": "unavailable",
            "reason": "common complete dimensions and >=3 brands required",
        }
    total = sum(weights.values())
    if total <= 0 or any(v < 0 for v in weights.values()):
        raise ValueError("Invalid weights")
    variants = [weights]
    for key in weights:
        for factor in (0.8, 1.2):
            variant = {k: w * (factor if k == key else 1) for k, w in weights.items()}
            variants.append(variant)
    outputs = []
    for variant in variants:
        norm = sum(variant.values())
        outputs.append(
            ranks(
                {
                    brand: sum(fields[k] * w / norm for k, w in variant.items())
                    for brand, fields in dimensions.items()
                }
            )
        )
    return {
        "status": "available",
        "baseline": outputs[0],
        "rank_ranges": {
            b: [min(r[b] for r in outputs), max(r[b] for r in outputs)] for b in dimensions
        },
    }


def velocity(observations, metric):
    rows = sorted(
        (o for o in observations if o["values"].get(metric) is not None),
        key=lambda o: aware(o["observed_at_utc"]),
    )
    if len(rows) < 2:
        return {"status": "unavailable", "per_day": None}
    first, last = rows[0], rows[-1]
    elapsed = (
        aware(last["observed_at_utc"]) - aware(first["observed_at_utc"])
    ).total_seconds() / 86400
    if elapsed <= 0:
        return {"status": "unavailable", "per_day": None}
    change = last["values"][metric] - first["values"][metric]
    return {
        "status": "correction" if change < 0 else "observed",
        "per_day": change / elapsed if change >= 0 else None,
    }


def age_observation(published, observations, age_days, tolerance_hours=12):
    candidates = [
        (
            abs(
                (aware(o["observed_at_utc"]) - aware(published)).total_seconds() / 3600
                - age_days * 24
            ),
            o,
        )
        for o in observations
    ]
    candidates = [c for c in candidates if c[0] <= tolerance_hours]
    return min(candidates, key=lambda c: c[0])[1] if candidates else None


def compare_prices(quotes, tolerance_minutes=5):
    if not quotes or not all(q.perspective_verified for q in quotes):
        return "perspective_unverified"
    keys = {
        (q.purity, q.grams, q.channel, q.tax_basis, q.fees_basis, q.currency, q.unit)
        for q in quotes
    }
    elapsed = (
        max(q.quoted_at_utc for q in quotes) - min(q.quoted_at_utc for q in quotes)
    ).total_seconds()
    return (
        "comparable"
        if len(keys) == 1 and elapsed <= tolerance_minutes * 60
        else "stale_or_mismatched"
    )


def log_exposure(values):
    return median(math.log1p(v["video_views"]) for v in values if v.get("video_views") is not None)
