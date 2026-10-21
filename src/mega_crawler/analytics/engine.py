from collections import defaultdict
from statistics import median

from mega_crawler.analytics.content import classify
from mega_crawler.analytics.metrics import (
    aggregate,
    engagement,
    log_exposure,
    percentiles,
    ranks,
    velocity,
)
from mega_crawler.normalization.core import age_bucket, aware
from mega_crawler.utils.safety import digest


def analyze(store, manifest, registry, config):
    run_id = manifest["run_id"]
    posts = store.rows("posts", run_id)
    observations = store.rows("metric_observations", run_id)
    mentions = store.rows("post_brand_mentions", run_id)
    latest = {}
    for observation in observations:
        key = (observation["platform"], observation["post_id"])
        if key not in latest or aware(observation["observed_at_utc"]) > aware(
            latest[key]["observed_at_utc"]
        ):
            latest[key] = observation
    catalog = {r["product_id"]: r for r in registry}
    by_post = defaultdict(list)
    for mention in mentions:
        by_post[(mention["platform"], mention["post_id"])].append(mention)
    cohorts = defaultdict(lambda: defaultdict(list))
    availability_rows = []
    content = []
    conversation = defaultdict(float)
    full_conversation = defaultdict(int)
    start, end = aware(manifest["window_start"]), aware(manifest["window_end"])
    definitions = defaultdict(set)
    for observation in observations:
        definitions[observation["platform"]].add(observation["metric_definition_version"])
    for post in posts:
        key = (post["platform"], post["post_id"])
        observation = latest.get(key)
        if observation and observation.get("analytics_permission") == "blocked":
            availability_rows.append(
                {
                    "platform": post["platform"],
                    "post_id": post["post_id"],
                    "source_url": post["canonical_url"],
                    "metric_status": observation["metric_status"],
                    "analytics_status": "permission_required_for_derived_metrics",
                }
            )
            continue
        parsed = classify(post["title"] + " " + post["text"])
        content.append(
            {
                "platform": post["platform"],
                "post_id": post["post_id"],
                "source_url": post["canonical_url"],
                "brand_product_id": post["product_id"],
                "format": post["format"],
                "hook_type": post.get("hook_type"),
                "cta_type": post.get("cta_type"),
                "campaign_theme": post.get("campaign_theme"),
                "kol_handle": post.get("kol_handle"),
                **parsed,
            }
        )
        availability_rows.append(
            {
                "platform": post["platform"],
                "post_id": post["post_id"],
                "source_url": post["canonical_url"],
                "metric_status": observation["metric_status"]
                if observation
                else {"all": "not_collected"},
                "enumeration_status": post["enumeration_status"],
                "population_coverage": "unknown",
            }
        )
        published = post["published_at_utc"]
        if (
            not published
            or not start <= aware(published) < end
            or post["relevance_score"] < config["relevance_threshold"]
        ):
            continue
        matched = by_post[key]
        if post["ownership_type"] == "earned":
            for mention in matched:
                conversation[(post["platform"], mention["brand_id"])] += mention[
                    "fractional_allocation"
                ]
                full_conversation[(post["platform"], mention["brand_id"])] += 1
        product = catalog.get(post["product_id"])
        if not product or post["format"] in {"unknown", "video_unknown", "web_page"}:
            continue
        if observation is None:
            versions = definitions[post["platform"]]
            observation = {
                "values": {},
                "observed_at_utc": post["collected_at_utc"],
                "metric_definition_version": next(iter(versions))
                if len(versions) == 1
                else "unknown",
            }
        # Separate age, segment, format, ownership, definitions and enumeration quality.
        cohort = (
            post["platform"],
            post["format"],
            post["ownership_type"],
            product["segment"],
            age_bucket(published, observation["observed_at_utc"]),
            observation["metric_definition_version"],
            post["enumeration_status"],
        )
        cohorts[cohort][product["brand_id"]].append((post, observation))
    rankings, gates = [], []
    for cohort, grouped in cohorts.items():
        # A single identical numerator across all members of the cohort.
        reaction_field = "likes"
        if all(
            o["values"].get("reactions") is not None for pairs in grouped.values() for _, o in pairs
        ):
            reaction_field = "reactions"
        eligible = {}
        for brand, pairs in grouped.items():
            vals = [o["values"] for _, o in pairs]
            observed = [v for v in vals if engagement(v, reaction_field=reaction_field) is not None]
            availability = len(observed) / len(vals)
            reasons = []
            if len(vals) < config["min_posts"]:
                reasons.append("insufficient_posts")
            if availability < config["min_availability"]:
                reasons.append("insufficient_metric_availability")
            if any(
                catalog[p["product_id"]]["active_status"] != "verified_active" for p, _ in pairs
            ):
                reasons.append("activity_not_verified")
            row = {
                "cohort": list(cohort),
                "brand_id": brand,
                "n_posts": len(vals),
                "availability": availability,
                "numerator": reaction_field + "+comments",
                "gate_reasons": reasons,
                "assumption": "exploratory gate; sample not necessarily representative",
            }
            gates.append(row)
            if not reasons:
                eligible[brand] = {
                    **row,
                    **aggregate(vals, reaction_field=reaction_field),
                    "observed_exposure_log1p": log_exposure(observed),
                    "median_video_views": median(v["video_views"] for v in observed),
                    "evidence_urls": [p["canonical_url"] for p, _ in pairs],
                    "outlier_rule": "no deletion; median/log1p; compare leave-largest-view-out median",
                    "median_er_without_largest_view": median(
                        engagement(v, reaction_field=reaction_field)
                        for v in sorted(observed, key=lambda v: v["video_views"])[:-1]
                    )
                    if len(observed) > 1
                    else None,
                }
        if manifest["demo"] or len(eligible) < config["min_brands"]:
            for row in gates:
                if row["cohort"] == list(cohort):
                    row["gate_reasons"] = sorted(
                        set(
                            row["gate_reasons"]
                            + [
                                "demo_no_real_ranking"
                                if manifest["demo"]
                                else "insufficient_brands"
                            ]
                        )
                    )
            continue
        efficiency = {b: r["median_er_pct"] for b, r in eligible.items()}
        exposure = {b: r["observed_exposure_log1p"] for b, r in eligible.items()}
        er_ranks, view_ranks = ranks(efficiency), ranks(exposure)
        er_percentiles = percentiles(efficiency)
        outlier_ranks = ranks({b: r["median_er_without_largest_view"] for b, r in eligible.items()})
        for brand, row in eligible.items():
            row.update(
                platform=cohort[0],
                format=cohort[1],
                ownership_type=cohort[2],
                segment=cohort[3],
                age_bucket=cohort[4],
                n_brands_eligible=len(eligible),
                efficiency_rank=er_ranks[brand],
                exposure_rank=view_ranks[brand],
                percentile_exploratory=round(er_percentiles[brand]),
                outlier_rank=outlier_ranks[brand],
                rank_unstable=outlier_ranks[brand] != er_ranks[brand],
                composite=None,
                composite_status="unavailable: earned and consistent complete account enumeration dimensions missing",
            )
            rankings.append(row)
    shares = []
    for (platform, brand), allocation in conversation.items():
        denominator = sum(v for (p, _), v in conversation.items() if p == platform)
        full_den = sum(v for (p, _), v in full_conversation.items() if p == platform)
        shares.append(
            {
                "platform": platform,
                "brand_id": brand,
                "allocation": allocation,
                "denominator": denominator,
                "observed_share_pct": allocation / denominator * 100,
                "full_count_share_pct": full_conversation[(platform, brand)] / full_den * 100,
                "method": "fractional 1/k per relevant post; eligible brand mentions in observed earned corpus only",
                "population_coverage": "unknown; retrieval bias",
            }
        )
    issues = []
    relevant_comments = []
    for comment in store.rows("comments_or_mentions", run_id):
        parsed = classify(comment["text"])
        if parsed["gold_relevant"]:
            relevant_comments.append({**comment, **parsed})
    counts = defaultdict(list)
    for comment in relevant_comments:
        for aspect in comment["aspects"]:
            counts[(comment["platform"], aspect)].append(comment)
    for (platform, aspect), rows in counts.items():
        denominator = sum(c["platform"] == platform for c in relevant_comments)
        complaints = sum(c["speech_type"] == "complaint" for c in rows)
        issues.append(
            {
                "platform": platform,
                "aspect": aspect,
                "n_observed": len(rows),
                "n_complaints": complaints,
                "relevant_comment_denominator": denominator,
                "observed_complaint_rate": complaints / denominator if denominator else None,
                "validation_status": "preliminary_unvalidated",
                "severity": "requires_human_review",
                "source_urls": sorted({c["source_url"] for c in rows}),
                "limitation": "selected comments; not customer incidence or inferential sentiment ranking",
            }
        )
    trends = []
    history = store.rows("metric_observations")
    for post in posts:
        rows = [
            o
            for o in history
            if (o["platform"], o["post_id"]) == (post["platform"], post["post_id"])
            and o.get("analytics_permission") != "blocked"
        ]
        trend = velocity(rows, "video_views")
        if trend["status"] != "unavailable":
            trends.append({"platform": post["platform"], "post_id": post["post_id"], **trend})
    mandiri = "Belum dapat diberi peringkat: data/cohort eligible belum memadai atau format/tanggal aktif belum terverifikasi."
    mandiri_rows = [r for r in rankings if r["brand_id"] == "mandiri"]
    if mandiri_rows:
        mandiri = "Lihat peringkat dimensi per cohort; tanggal aktif produk Mandiri belum terverifikasi, sehingga perbandingan utama sejak aktif belum tersedia."
    analysis = {
        "run_id": run_id,
        "demo": manifest["demo"],
        "label": "DEMO / DATA SINTETIS" if manifest["demo"] else "DATA TERAMATI",
        "window_start": manifest["window_start"],
        "window_end": manifest["window_end"],
        "mandiri_status": mandiri,
        "raw_availability": availability_rows,
        "rankings": rankings,
        "ranking_gates": gates,
        "observed_conversation": shares,
        "issues": issues,
        "content_analysis": content,
        "trends": trends,
        "recommendations": [],
        "composite_status": "unavailable; complete common dimensions not established",
        "weight_sensitivity": "unavailable because composite unavailable",
        "limitations": [
            "Sampel teramati; bukan peringkat pasar nasional atau market share.",
            "Tanggal aktif Mandiri belum diverifikasi; rilis bukan otomatis tanggal aktif.",
            "Sentimen preliminary/unvalidated; belum ada akurasi atau agreement review manusia.",
            "Views bukan unique reach; engagement bukan nasabah, AUM, ROAS atau conversion.",
            "Tidak ada rekomendasi campaign 30/60/90 sampai bukti memadai.",
        ],
    }
    store.put("ranking_runs", run_id, analysis, run_id)
    for row in rankings + gates:
        store.put("ranking_components", digest([run_id, row]), row, run_id)
    for row in issues:
        store.put("issue_clusters", digest([run_id, row]), row, run_id)
    store.commit()
    return analysis
