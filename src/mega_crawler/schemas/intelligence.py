import math
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mega_crawler.normalization.core import aware, utcnow
from mega_crawler.utils.safety import canonical_url

PLATFORMS = (
    "web",
    "youtube",
    "instagram",
    "tiktok",
    "threads",
    "facebook",
    "linkedin",
    "rss",
    "news",
)
METRICS = (
    "likes",
    "reactions",
    "comments",
    "shares",
    "reposts",
    "quotes",
    "saves",
    "video_views",
    "impressions",
    "reach",
    "clicks",
)


class MetricStatus(StrEnum):
    OBSERVED = "observed"
    NOT_EXPOSED = "not_exposed"
    HIDDEN = "hidden"
    REQUIRES_PERMISSION = "requires_permission"
    UNSUPPORTED = "unsupported"
    REQUEST_FAILED = "request_failed"
    NOT_COLLECTED = "not_collected"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UnsupportedCapability(Model):
    status: Literal["unsupported"] = "unsupported"
    platform: str
    capability: str
    reason: str


class Health(Model):
    platform: str
    status: str
    reason: str
    live_verified: bool = False


class Post(Model):
    platform: str
    post_id: str
    canonical_url: str
    account_id: str | None = None
    published_at_utc: datetime | None = None
    collected_at_utc: datetime = Field(default_factory=utcnow)
    text: str = ""
    title: str = ""
    language: str | None = None
    content_type: str = "unknown"
    format: str = "unknown"
    product_id: str | None = None
    ownership_type: Literal[
        "owned", "earned", "paid_disclosed", "partnership_disclosed", "paid_unknown"
    ] = "paid_unknown"
    commercial_disclosure: str = "unknown"
    campaign_id: str | None = None
    creative_cluster: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    hook_type: str | None = None
    cta_type: str | None = None
    campaign_theme: str | None = None
    audience_intended: str | None = None
    kol_handle: str | None = None
    promo_terms: str | None = None
    promo_end_at_utc: datetime | None = None
    visual_description: str | None = None
    visual_access_status: str = "not_collected"
    indonesia_relevance_reason: str | None = None
    retrieval_query_id: str | None = None
    retrieval_position: int | None = Field(None, ge=0)
    relevance_score: float = Field(0, ge=0, le=1)
    relevance_reason: str = "unreviewed"
    matched_alias: list[str] = Field(default_factory=list)
    query_id: str | None = None
    source_method: str
    provider: str
    source_url: str
    evidence_locator: str
    evidence_hash: str
    extractor_version: str = "goldintel-1"
    content_hash: str = ""
    access_status: str = "observed"
    enumeration_status: Literal["complete", "partial", "unknown"] = "unknown"
    demo: bool = False

    _utc = field_validator(
        "published_at_utc", "collected_at_utc", "promo_end_at_utc", mode="before"
    )(lambda v: aware(v) if v else v)
    _url = field_validator("canonical_url", "source_url")(canonical_url)

    @field_validator("platform")
    @classmethod
    def platform_known(cls, value):
        if value not in PLATFORMS:
            raise ValueError("Unknown platform")
        return value


class MetricObservation(Model):
    observation_id: str
    platform: str
    post_id: str
    observed_at_utc: datetime
    source_reported_at: datetime | None = None
    values: dict[str, float | None] = Field(default_factory=dict)
    metric_status: dict[str, MetricStatus] = Field(default_factory=dict)
    raw_values: dict[str, str | None] = Field(default_factory=dict)
    count_precision: dict[str, str] = Field(default_factory=dict)
    raw_metric_name: dict[str, str] = Field(default_factory=dict)
    metric_definition_version: str
    source_url: str
    evidence_hash: str
    correction: bool = False
    demo: bool = False
    analytics_permission: Literal["blocked", "approved", "not_applicable"] = "not_applicable"

    _utc = field_validator("observed_at_utc", "source_reported_at", mode="before")(
        lambda v: aware(v) if v else v
    )
    _url = field_validator("source_url")(canonical_url)

    @model_validator(mode="after")
    def consistency(self):
        if set(self.values) - set(METRICS) or set(self.metric_status) - set(METRICS):
            raise ValueError("Unknown metric")
        for key in METRICS:
            value = self.values.setdefault(key, None)
            status = self.metric_status.setdefault(key, MetricStatus.NOT_COLLECTED)
            if value is not None and (
                not math.isfinite(value) or value < 0 or status != MetricStatus.OBSERVED
            ):
                raise ValueError("Numeric metrics must be nonnegative and observed")
            if value is None and status == MetricStatus.OBSERVED:
                raise ValueError("Observed requires a number; unavailable is null")
        return self


class ProductFact(Model):
    product_id: str
    fact_name: str
    value: str
    unit: str | None = None
    channel: str
    official_source_url: str
    evidence_locator: str
    evidence_hash: str
    published_at: datetime | None = None
    effective_at: datetime | None = None
    checked_at: datetime
    availability_status: Literal["live", "planned", "unknown"] = "unknown"
    verification_status: str = "pending_review"
    valid_from: datetime
    valid_to: datetime | None = None

    _utc = field_validator(
        "published_at", "effective_at", "checked_at", "valid_from", "valid_to", mode="before"
    )(lambda v: aware(v) if v else v)
    _url = field_validator("official_source_url")(canonical_url)


class PriceQuote(Model):
    product_id: str
    customer_buy_price: float = Field(gt=0)
    customer_sell_price: float = Field(ge=0)
    currency: str = "IDR"
    unit: str = "per_gram"
    purity: str
    grams: float = Field(gt=0)
    channel: str
    tax_basis: str
    fees_basis: str
    quoted_at_utc: datetime
    source_url: str
    perspective_verified: bool = False

    _utc = field_validator("quoted_at_utc", mode="before")(aware)
    _url = field_validator("source_url")(canonical_url)

    @property
    def spread_pct(self):
        return (self.customer_buy_price - self.customer_sell_price) / self.customer_buy_price * 100
