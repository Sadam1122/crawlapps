import yaml
from pydantic import BaseModel, ConfigDict, Field


class Competitor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str
    legal_name: str | None
    brand_id: str
    brand_name: str
    product_id: str
    product_name: str
    segment: str
    priority: int
    active_status: str
    activity_checked_at: str | None
    relationship_to_mandiri: list[str]
    parent_group_id: str | None
    provider_entity_id: str | None
    official_domains: list[str]
    verified_social_accounts: list[dict] = Field(default_factory=list)
    aliases: list[str]
    gold_product_keywords: list[str]
    exclusion_keywords: list[str]
    verification_sources: list[dict]
    regulatory_status: str
    regulatory_checked_at: str | None
    verification_status: str


def load_registry(config_dir):
    document = yaml.safe_load((config_dir / "competitors.yaml").read_text(encoding="utf-8"))
    records = [Competitor.model_validate(r).model_dump() for r in document["competitors"]]
    ids = [r["product_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate product_id")
    for record in records:
        if record["active_status"] not in {
            "verified_active",
            "historical",
            "discontinued",
            "pending_verification",
        }:
            raise ValueError("Invalid activity status")
        for account in record["verified_social_accounts"]:
            required = {
                "url",
                "platform",
                "platform_id",
                "verification_reason",
                "checked_at",
                "confidence",
                "reviewer_status",
                "evidence_url",
            }
            if not required <= account.keys():
                raise ValueError("Account verification evidence incomplete")
    return records


def capabilities(config_dir):
    return yaml.safe_load((config_dir / "source_capabilities.yaml").read_text(encoding="utf-8"))[
        "sources"
    ]
