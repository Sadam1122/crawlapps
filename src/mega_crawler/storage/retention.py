"""Conservative retention: expired generated runs and their dependent exports are deleted."""

import shutil
from datetime import timedelta

from mega_crawler.normalization.core import aware, utcnow
from mega_crawler.storage.database import TABLES


def expired_runs(pipeline):
    cutoff = utcnow() - timedelta(days=min(pipeline.settings.retention_days, 30))
    expired = []
    for manifest in pipeline.store.rows("collection_runs"):
        run_id = manifest["run_id"]
        posts = pipeline.store.rows("posts", run_id)
        observations = pipeline.store.rows("metric_observations", run_id)
        timestamps = [aware(p["collected_at_utc"]) for p in posts]
        timestamps += [aware(o["observed_at_utc"]) for o in observations]
        if timestamps and min(timestamps) < cutoff:
            expired.append(run_id)
    return expired


def delete_run(pipeline, run_id):
    pipeline.manifest(run_id)
    root = (pipeline.settings.data_dir / "runs").resolve()
    target = pipeline.directory(run_id).resolve()
    if target.parent != root or target == root:
        raise ValueError("Retention target outside generated runs")
    store = pipeline.store
    references = store.db.execute(
        "SELECT table_name,record_id FROM run_records WHERE run_id=?", (run_id,)
    ).fetchall()
    store.db.execute("DELETE FROM run_records WHERE run_id=?", (run_id,))
    store.db.execute("DELETE FROM run_record_data WHERE run_id=?", (run_id,))
    store.db.execute("DELETE FROM collection_runs WHERE id=?", (run_id,))
    for table, key in references:
        if table not in TABLES:
            raise ValueError("Invalid retention table")
        remaining = store.db.execute(
            "SELECT 1 FROM run_records WHERE table_name=? AND record_id=? LIMIT 1", (table, key)
        ).fetchone()
        if not remaining:
            store.db.execute(f"DELETE FROM {table} WHERE id=?", (key,))
    store.commit()
    if target.exists():
        shutil.rmtree(target)


def enforce_retention(pipeline):
    for run_id in expired_runs(pipeline):
        delete_run(pipeline, run_id)
