from datetime import timedelta

from mega_crawler.analytics.engine import analyze
from mega_crawler.analytics.review import review_agreement
from mega_crawler.collection.pipeline import Pipeline
from mega_crawler.normalization.core import utcnow
from mega_crawler.schemas.intelligence import MetricObservation, Post


def seed_cohort(settings, missing_brand=None, count=10, demo=False, vary_format=False):
    pipe = Pipeline(settings, demo=demo)
    manifest = pipe.new_run()
    now = utcnow()
    for b, brand in enumerate(("mandiri", "pegadaian", "bsi")):
        product = next(
            r for r in pipe.registry if r["brand_id"] == brand and r["segment"] == "direct"
        )
        for i in range(count):
            post_id = f"{brand}-{i}"
            post = Post(
                platform="instagram",
                post_id=post_id,
                canonical_url="https://example.org/" + post_id,
                product_id=product["product_id"],
                published_at_utc=now - timedelta(days=3),
                title=f"{brand} emas tutorial",
                format="photo" if vary_format and brand == "bsi" else "reels",
                ownership_type="owned",
                enumeration_status="complete",
                source_method="authorized_import",
                provider="fixture",
                source_url="https://example.org",
                evidence_locator="fixture",
                evidence_hash="test",
                demo=demo,
            )
            values = {"likes": 10 + b * 10, "comments": 0, "video_views": 1000}
            if missing_brand == brand:
                values["likes"] = None
            obs = MetricObservation(
                observation_id=post_id,
                platform="instagram",
                post_id=post_id,
                observed_at_utc=now,
                values=values,
                metric_status={
                    k: "observed" if v is not None else "request_failed" for k, v in values.items()
                },
                metric_definition_version="fixture",
                source_url=post.canonical_url,
                evidence_hash="test",
                demo=demo,
            )
            pipe.ingest({"posts": [post], "observations": [obs]}, manifest)
    pipe.normalize(manifest["run_id"])
    return pipe, manifest


def test_eligible_rank_and_raw_availability(settings):
    pipe, manifest = seed_cohort(settings)
    result = analyze(pipe.store, manifest, pipe.registry, manifest["ranking_config"])
    assert len(result["rankings"]) == 3
    mandiri = next(r for r in result["rankings"] if r["brand_id"] == "mandiri")
    assert mandiri["efficiency_rank"] == 3
    assert mandiri["n_brands_eligible"] == 3 and mandiri["n_posts"] == 10
    assert mandiri["composite"] is None
    assert len(result["raw_availability"]) == 30
    pipe.store.close()


def test_failed_metric_not_zero_and_not_last_rank(settings):
    pipe, manifest = seed_cohort(settings, missing_brand="mandiri")
    result = analyze(pipe.store, manifest, pipe.registry, manifest["ranking_config"])
    assert result["rankings"] == []
    gate = next(r for r in result["ranking_gates"] if r["brand_id"] == "mandiri")
    assert "insufficient_metric_availability" in gate["gate_reasons"]
    assert gate["availability"] == 0
    pipe.store.close()


def test_format_intersection_and_demo_gate(settings):
    pipe, manifest = seed_cohort(settings, vary_format=True)
    result = analyze(pipe.store, manifest, pipe.registry, manifest["ranking_config"])
    assert not result["rankings"]
    pipe.store.close()
    # Separate database fixture; no demo ranking even with all exploratory gates met.
    settings.database_url = "sqlite:///" + (settings.data_dir / "demo.sqlite").as_posix()
    pipe, manifest = seed_cohort(settings, demo=True)
    assert (
        analyze(pipe.store, manifest, pipe.registry, manifest["ranking_config"])["rankings"] == []
    )
    pipe.store.close()


def test_human_review_no_fabricated_agreement():
    assert review_agreement([])["agreement"] is None
    result = review_agreement(
        [
            {"reviewer_a_label": "positive", "reviewer_b_label": "positive"},
            {"reviewer_a_label": "negative", "reviewer_b_label": "positive"},
        ]
    )
    assert result["agreement"] == 0.5
    assert result["n_paired"] == 2


def test_absent_snapshot_counts_against_availability(settings):
    pipe, manifest = seed_cohort(settings)
    key = manifest["run_id"]
    for post_id in ("mandiri-0", "mandiri-1", "mandiri-2"):
        pipe.store.db.execute(
            "DELETE FROM run_record_data WHERE run_id=? AND table_name='metric_observations' AND record_id=?",
            (key, post_id),
        )
    result = analyze(pipe.store, manifest, pipe.registry, manifest["ranking_config"])
    row = next(r for r in result["ranking_gates"] if r["brand_id"] == "mandiri")
    assert row["n_posts"] == 10
    assert row["availability"] == 0.7
    assert not result["rankings"]
    pipe.store.close()
