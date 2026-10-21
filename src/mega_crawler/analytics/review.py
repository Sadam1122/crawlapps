from collections import Counter


def review_agreement(rows):
    """Observed agreement and Cohen kappa for paired human labels; no invented accuracy."""
    pairs = [
        (r["reviewer_a_label"], r["reviewer_b_label"])
        for r in rows
        if r.get("reviewer_a_label") and r.get("reviewer_b_label")
    ]
    if not pairs:
        return {"status": "unavailable", "n_paired": 0, "agreement": None, "cohen_kappa": None}
    n = len(pairs)
    a, b = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    observed = sum(x == y for x, y in pairs) / n
    expected = sum(a[label] * b[label] for label in set(a) | set(b)) / n**2
    return {
        "status": "observed",
        "n_paired": n,
        "agreement": observed,
        "cohen_kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
        "confusion": dict(Counter(f"{x} -> {y}" for x, y in pairs)),
        "limitation": "agreement on reviewed sample; not whole-internet classification accuracy",
    }
