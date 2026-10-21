from datetime import timedelta

import pytest

from mega_crawler.collection.pipeline import Pipeline
from mega_crawler.normalization.core import utcnow
from mega_crawler.schemas.intelligence import Post
from mega_crawler.storage.retention import delete_run, enforce_retention, expired_runs


def test_retention_removes_run_records_exports_and_references(settings):
    pipe = Pipeline(settings)
    manifest = pipe.new_run()
    post = Post(
        platform="web",
        post_id="old",
        canonical_url="https://example.org/old",
        collected_at_utc=utcnow() - timedelta(days=31),
        source_method="fixture",
        provider="fixture",
        source_url="https://example.org/old",
        evidence_locator="test",
        evidence_hash="hash",
    )
    pipe.ingest({"posts": [post]}, manifest)
    target = pipe.directory(manifest["run_id"]) / "processed/report.html"
    target.parent.mkdir(parents=True)
    target.write_text("expired fixture", encoding="utf-8")
    assert expired_runs(pipe) == [manifest["run_id"]]
    enforce_retention(pipe)
    assert not target.exists()
    assert not pipe.store.rows("posts")
    assert not pipe.store.rows("collection_runs")
    assert not pipe.store.db.execute("SELECT * FROM run_record_data").fetchall()
    pipe.store.close()


def test_purge_path_validation_and_shared_snapshot(settings, import_path):
    pipe = Pipeline(settings)
    one = pipe.import_file("instagram", import_path)
    two = pipe.import_file("instagram", import_path)
    with pytest.raises(ValueError):
        delete_run(pipe, "../../outside")
    delete_run(pipe, one["run_id"])
    assert len(pipe.store.rows("metric_observations", two["run_id"])) == 1
    assert len(pipe.store.rows("metric_observations")) == 1
    delete_run(pipe, two["run_id"])
    assert not pipe.store.rows("metric_observations")
    pipe.store.close()
