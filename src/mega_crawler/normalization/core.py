import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel


def utcnow():
    return datetime.now(UTC)


def aware(value):
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        raise ValueError("Timestamp requires explicit timezone, e.g. +07:00 or Z")
    return dt.astimezone(UTC)


def window(days=90, end=None):
    end = aware(end) if end else utcnow()
    return end - timedelta(days=days), end


class ParsedCount(BaseModel):
    raw: str | None
    value: float | None
    precision: str
    status: str
    unit: str = "count"


def parse_count(raw, locale=None):
    text = "" if raw is None else str(raw).strip().lower()
    if text in {"", "n/a", "na", "none", "null", "-", "hidden", "disembunyikan"}:
        return ParsedCount(
            raw=None if raw is None else str(raw),
            value=None,
            precision="unknown",
            status="hidden" if "hidden" in text or "disembunyikan" in text else "not_collected",
        )
    match = re.fullmatch(r"([\d.,\s]+)\s*(rb|ribu|k|jt|juta|m|b)?", text)
    if not match:
        raise ValueError("Invalid count")
    number, suffix = match.groups()
    number = number.replace(" ", "")
    if "," in number and "." in number:
        decimal = "," if number.rfind(",") > number.rfind(".") else "."
        number = number.replace("." if decimal == "," else ",", "").replace(decimal, ".")
    elif "," in number or "." in number:
        sep = "," if "," in number else "."
        parts = number.split(sep)
        thousands = len(parts) > 2 or (len(parts[-1]) == 3 and not suffix)
        if locale == "id" and sep == "." and not suffix:
            thousands = True
        number = "".join(parts) if thousands else number.replace(sep, ".")
    factor = {
        None: 1,
        "rb": 1000,
        "ribu": 1000,
        "k": 1000,
        "jt": 1000000,
        "juta": 1000000,
        "m": 1000000,
        "b": 1000000000,
    }[suffix]
    return ParsedCount(
        raw=str(raw),
        value=float(Decimal(number) * factor),
        precision="rounded" if suffix else "exact",
        status="observed",
    )


def age_bucket(published, observed):
    age = (aware(observed) - aware(published)).total_seconds() / 86400
    if age < 0:
        raise ValueError("Observation precedes publication")
    return "0-7d" if age < 7 else "7-30d" if age < 30 else "30-90d" if age < 90 else "90d+"


def relevance(text, record):
    text = text.casefold()
    matched = []
    for alias in record["aliases"]:
        for match in re.finditer(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", text):
            context = text[max(0, match.start() - 100) : match.end() + 100]
            gold = any(k.casefold() in context for k in record["gold_product_keywords"])
            excluded = any(k.casefold() in context for k in record["exclusion_keywords"])
            if gold and not excluded:
                matched.append(alias)
                break
    score = 1.0 if matched else 0.0
    return {
        "relevance_score": score,
        "relevance_reason": "brand+gold context" if score else "ambiguous/excluded/no gold context",
        "matched_alias": matched,
        "query_id": "registry-relevance-v1",
    }
