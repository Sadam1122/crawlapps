"""Authorized import, shared by every platform. Missing metrics stay null."""

import csv
import json
from pathlib import Path

from mega_crawler.normalization.core import aware, parse_count, utcnow
from mega_crawler.schemas.intelligence import METRICS, MetricObservation, Post, ProductFact
from mega_crawler.utils.safety import digest, redact


def load_import(path: Path, platform: str, demo=False):
    if path.suffix.lower() == ".csv":
        meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8-sig"))
        with path.open(encoding="utf-8-sig", newline="") as handle:
            data = {"source": meta, "posts": list(csv.DictReader(handle))}
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        raise ValueError("Import supports .csv or .json")
    source = data["source"]
    for field in (
        "permission_basis",
        "provider",
        "source_url",
        "observed_at_utc",
        "metric_definition_version",
    ):
        if not source.get(field):
            raise ValueError(f"Import source.{field} required")
    if bool(source.get("demo", False)) != demo:
        raise ValueError("DEMO_PRODUCTION_ISOLATION: demo only via goldintel demo")
    observed = aware(source["observed_at_utc"])
    if observed > utcnow():
        raise ValueError("Observation timestamp is in the future")
    evidence_hash = digest(data)
    locator = "import-sha256:" + evidence_hash
    posts, observations = [], []
    for index, row in enumerate(data.get("posts", [])):
        if row.get("platform", platform) != platform:
            raise ValueError("Platform mismatch")
        metrics = row.get("metrics", {})
        values, statuses, raw, precision = {}, {}, {}, {}
        for field in METRICS:
            parsed = parse_count(metrics.get(field, row.get(field)), source.get("locale"))
            values[field], raw[field], precision[field] = parsed.value, parsed.raw, parsed.precision
            statuses[field] = row.get("metric_status", {}).get(field, parsed.status)
        post_data = {k: v for k, v in row.items() if k in Post.model_fields and v != ""}
        post_data.update(
            platform=platform,
            source_method="authorized_import",
            provider=source["provider"],
            source_url=source["source_url"],
            evidence_locator=f"{locator}#posts/{index}",
            evidence_hash=evidence_hash,
            demo=demo,
            collected_at_utc=observed,
            enumeration_status=source.get("enumeration_status", "unknown"),
        )
        for field in ("text", "title", "promo_terms", "visual_description", "audience_intended"):
            if field not in {"text", "title"} and post_data.get(field) is None:
                continue
            post_data[field] = redact(str(post_data.get(field, "")))
        if isinstance(post_data.get("topic_tags"), str):
            post_data["topic_tags"] = post_data["topic_tags"].split("|")
        post = Post.model_validate(post_data)
        if post.published_at_utc and post.published_at_utc > observed:
            raise ValueError("Post published after observation")
        post.content_hash = digest([post.text, post.title])
        posts.append(post)
        observations.append(
            MetricObservation(
                observation_id=digest(
                    [platform, post.post_id, observed.isoformat(), source["provider"]]
                ),
                platform=platform,
                post_id=post.post_id,
                observed_at_utc=observed,
                values=values,
                metric_status=statuses,
                raw_values=raw,
                count_precision=precision,
                raw_metric_name=source.get("raw_metric_name", {}),
                metric_definition_version=source["metric_definition_version"],
                analytics_permission="blocked"
                if platform == "youtube" and not demo
                else "not_applicable",
                source_url=post.canonical_url,
                evidence_hash=evidence_hash,
                demo=demo,
            )
        )
    facts = [ProductFact.model_validate(f) for f in data.get("product_facts", [])]
    comments = []
    for c in data.get("comments", []):
        # Never retain personal handles or raw external author IDs.
        comments.append(
            {
                "comment_id": digest([platform, source["provider"], c["comment_id"]]),
                "post_id": str(c["post_id"]),
                "platform": platform,
                "text": redact(c["text"]),
                "source_url": c["source_url"],
                "observed_at_utc": observed.isoformat(),
                "evidence_hash": evidence_hash,
                "selection_method": source.get("comment_selection_method", "unknown"),
                "demo": demo,
            }
        )
    return {
        "posts": posts,
        "observations": observations,
        "product_facts": facts,
        "comments": comments,
        "source": source,
        "evidence_hash": evidence_hash,
        "evidence_locator": locator,
    }
