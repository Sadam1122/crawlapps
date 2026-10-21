import subprocess
import uuid
from pathlib import Path

import yaml

from mega_crawler.adapters import get_adapter
from mega_crawler.adapters.imports import load_import
from mega_crawler.adapters.web import WebAdapter
from mega_crawler.collection.budget import RunBudget
from mega_crawler.collection.http import AccessError
from mega_crawler.normalization.core import aware, relevance, utcnow, window
from mega_crawler.registries.catalog import capabilities, load_registry
from mega_crawler.schemas.intelligence import Post
from mega_crawler.storage.database import Store
from mega_crawler.utils.safety import atomic_json, digest


class Pipeline:
    def __init__(self, settings, demo=False):
        self.settings, self.demo = settings, demo
        self.registry = load_registry(settings.config_dir)
        self.store = Store(settings)
        self.store.seed(self.registry, capabilities(settings.config_dir))
        from mega_crawler.storage.retention import enforce_retention

        enforce_retention(self)
        document = yaml.safe_load(
            (settings.config_dir / "competitors.yaml").read_text(encoding="utf-8")
        )
        for r in document.get("relationships", []):
            self.store.put("relationships", digest(r), r)
        self.store.commit()

    def new_run(self, days=90, end=None, platforms=None):
        start, end = window(days, end)
        identifier = ("demo-" if self.demo else "run-") + uuid.uuid4().hex[:16]
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False
            )
            code_version = revision.stdout.strip() if revision.returncode == 0 else "uncommitted"
        except (OSError, subprocess.TimeoutExpired):
            code_version = "unknown"
        hashes = {
            p.name: digest(p.read_text(encoding="utf-8"))
            for p in self.settings.config_dir.glob("*.yaml")
        }
        manifest = {
            "run_id": identifier,
            "demo": self.demo,
            "label": "DEMO / DATA SINTETIS" if self.demo else "DATA TERAMATI",
            "started_at_utc": utcnow().isoformat(),
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "window_interval": "[start,end)",
            "presentation_timezone": self.settings.timezone,
            "config_hash": digest(hashes),
            "code_version": code_version,
            "enabled_sources": platforms or [],
            "retrieval_queries": [],
            "sources": [],
            "status": "running",
            "counts": {},
            "cost": 0,
            "requests": 0,
            "warnings": [
                "Earned population coverage unknown",
                "Mandiri launch active date unverified",
            ],
            "normalization_version": "goldintel-1",
            "ranking_config": yaml.safe_load(
                (self.settings.config_dir / "analysis.yaml").read_text(encoding="utf-8")
            ),
        }
        self.save_manifest(manifest)
        atomic_json(
            self.directory(identifier) / "config_snapshot.json",
            {
                p.name: yaml.safe_load(p.read_text(encoding="utf-8"))
                for p in self.settings.config_dir.glob("*.yaml")
            },
        )
        return manifest

    def directory(self, run_id):
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in run_id):
            raise ValueError("Invalid run ID")
        return self.settings.data_dir / "runs" / run_id

    def save_manifest(self, manifest):
        self.store.put("collection_runs", manifest["run_id"], manifest)
        self.store.commit()
        atomic_json(self.directory(manifest["run_id"]) / "manifest.json", manifest)

    def manifest(self, run_id):
        result = self.store.get("collection_runs", run_id)
        if result is None or result["demo"] != self.demo:
            raise ValueError("Run not found in selected production/demo database")
        return result

    def ingest(self, batch, manifest):
        run_id = manifest["run_id"]
        for post in batch.get("posts", []):
            if post.demo != self.demo:
                raise ValueError("DEMO_PRODUCTION_ISOLATION")
            key = post.platform + ":" + post.post_id
            self.store.put("posts", key, post, run_id)
        for obs in batch.get("observations", []):
            if obs.demo != self.demo:
                raise ValueError("DEMO_PRODUCTION_ISOLATION")
            history = [
                o
                for o in self.store.rows("metric_observations")
                if o["platform"] == obs.platform
                and o["post_id"] == obs.post_id
                and aware(o["observed_at_utc"]) < obs.observed_at_utc
            ]
            if history:
                previous = max(history, key=lambda o: o["observed_at_utc"])
                obs.correction = any(
                    v is not None
                    and previous["values"].get(k) is not None
                    and v < previous["values"][k]
                    for k, v in obs.values.items()
                )
            self.store.put("metric_observations", obs.observation_id, obs, run_id, append=True)
        for fact in batch.get("product_facts", []):
            self.store.fact(fact, run_id)
        for comment in batch.get("comments", []):
            self.store.put("comments_or_mentions", comment["comment_id"], comment, run_id)
        metadata = {
            "source": batch.get("source", {}),
            "evidence_hash": batch.get("evidence_hash"),
            "counts": {
                k: len(batch.get(k, []))
                for k in ("posts", "observations", "product_facts", "comments")
            },
            "demo": self.demo,
            "label": manifest["label"],
            "raw_retained": False,
        }
        self.store.put(
            "collection_events", digest([run_id, metadata]), metadata, run_id, append=True
        )
        self.store.commit()
        atomic_json(self.directory(run_id) / "evidence" / (digest(metadata) + ".json"), metadata)

    def normalize(self, run_id):
        manifest = self.manifest(run_id)
        self.store.db.execute(
            "DELETE FROM run_record_data WHERE run_id=? AND table_name='post_brand_mentions'",
            (run_id,),
        )
        self.store.db.execute(
            "DELETE FROM run_records WHERE run_id=? AND table_name='post_brand_mentions'", (run_id,)
        )
        for row in self.store.rows("posts", run_id):
            post = Post.model_validate(row)
            if post.retrieval_query_id is None and post.query_id:
                post.retrieval_query_id = post.query_id
            if post.platform == "youtube" and post.source_method == "official_api":
                post.access_status = "raw_only_analytics_permission_required"
                self.store.put("posts", post.platform + ":" + post.post_id, post, run_id)
                continue
            matches = {}
            for record in self.registry:
                result = relevance(post.title + " " + post.text, record)
                if result["relevance_score"] >= manifest["ranking_config"]["relevance_threshold"]:
                    matches[record["brand_id"]] = result
            post.relevance_score = 1 if matches else 0
            post.relevance_reason = (
                "brand+gold context"
                if matches
                else "ambiguous/no gold context; manual review needed"
            )
            post.matched_alias = sorted({a for r in matches.values() for a in r["matched_alias"]})
            post.query_id = "registry-relevance-v1"
            if not post.product_id and len(matches) == 1:
                candidates = [
                    r
                    for r in self.registry
                    if r["brand_id"] in matches and r["segment"] == "direct"
                ]
                if len(candidates) == 1:
                    post.product_id = candidates[0]["product_id"]
            self.store.put("posts", post.platform + ":" + post.post_id, post, run_id)
            for brand, result in matches.items():
                mention = {
                    "platform": post.platform,
                    "post_id": post.post_id,
                    "brand_id": brand,
                    "fractional_allocation": 1 / len(matches),
                    "full_allocation": 1,
                    **result,
                }
                self.store.put(
                    "post_brand_mentions",
                    digest([post.platform, post.post_id, brand]),
                    mention,
                    run_id,
                )
        self.store.commit()
        return len(self.store.rows("posts", run_id))

    def finish(self, manifest):
        sources = manifest["sources"]
        successes = sum(s["status"] == "success" for s in sources)
        manifest["status"] = (
            "success"
            if sources and successes == len(sources)
            else "partial"
            if successes or any(s["status"] == "partial" for s in sources)
            else "failed"
        )
        manifest["finished_at_utc"] = utcnow().isoformat()
        manifest["counts"] = {
            name: len(self.store.rows(name, manifest["run_id"]))
            for name in ("posts", "metric_observations", "product_facts", "extraction_errors")
        }
        self.save_manifest(manifest)

    def import_file(self, platform, file, days=90, end=None):
        # Validate whole payload before writing; no partial import on invalid rows.
        batch = load_import(Path(file), platform, self.demo)
        manifest = self.new_run(days, end, [platform])
        self.ingest(batch, manifest)
        manifest["sources"].append(
            {
                "platform": platform,
                "status": "success",
                "access_status": "authorized_import",
                "coverage": batch["source"].get("enumeration_status", "unknown"),
            }
        )
        self.finish(manifest)
        self.normalize(manifest["run_id"])
        return manifest

    async def collect(self, platforms, days=90, end=None, resume_run_id=None):
        manifest = (
            self.manifest(resume_run_id) if resume_run_id else self.new_run(days, end, platforms)
        )
        start, stop = aware(manifest["window_start"]), aware(manifest["window_end"])
        budget = RunBudget(self.settings, spent=manifest["cost"])
        sources = yaml.safe_load(
            (self.settings.config_dir / "web_sources.yaml").read_text(encoding="utf-8")
        )["sources"]
        for platform in platforms:
            remaining = self.settings.max_requests_per_run - manifest["requests"]
            adapter_settings = self.settings.model_copy(
                update={"max_requests_per_run": max(1, remaining)}
            )
            adapter = (
                WebAdapter(adapter_settings, sources)
                if platform == "web"
                else get_adapter(platform, adapter_settings)
            )
            entry = {
                "platform": platform,
                "status": "failed",
                "access_status": "unknown",
                "coverage": "unknown",
            }
            if hasattr(adapter, "http"):
                adapter.http.budget = budget
            try:
                health = await adapter.healthcheck()
                entry["access_status"] = health.status
                if health.status != "READY":
                    entry["reason"] = health.reason
                elif remaining <= 0:
                    entry["access_status"] = "REQUEST_BUDGET_EXHAUSTED"
                elif platform == "web":
                    completed = []
                    for source in sources:
                        try:
                            batch = await adapter.fetch_posts(source, start, stop)
                            self.ingest(batch, manifest)
                            completed.append({"url": source["url"], "status": "success"})
                        except (AccessError, ValueError) as exc:
                            completed.append(
                                {
                                    "url": source["url"],
                                    "status": exc.status
                                    if isinstance(exc, AccessError)
                                    else "VALIDATION_ERROR",
                                }
                            )
                    entry.update(
                        status="success"
                        if completed and all(r["status"] == "success" for r in completed)
                        else "partial"
                        if any(r["status"] == "success" for r in completed)
                        else "failed",
                        results=completed,
                        coverage="allowlisted current pages only; publication unknown",
                    )
                elif platform == "youtube":
                    accounts = [
                        a
                        for a in self.store.rows("accounts")
                        if a["platform"] == "youtube" and a["reviewer_status"] == "approved"
                    ]
                    if not accounts:
                        entry["access_status"] = "NO_VERIFIED_ACCOUNTS"
                    else:
                        completed = []
                        for account in accounts:
                            checkpoint_id = digest(
                                [manifest["run_id"], "youtube", account["platform_id"]]
                            )
                            checkpoint = self.store.get("checkpoints", checkpoint_id)
                            if checkpoint and checkpoint.get("complete"):
                                completed.append(
                                    {
                                        "account_id": account["platform_id"],
                                        "status": "success",
                                        "resumed": True,
                                    }
                                )
                                continue

                            def save_page(token, posts, observations, ck=checkpoint_id):
                                self.ingest(
                                    {"posts": posts, "observations": observations}, manifest
                                )
                                self.store.put(
                                    "checkpoints",
                                    ck,
                                    {"next_page": token, "complete": token is None},
                                    manifest["run_id"],
                                )
                                self.store.commit()

                            try:
                                batch = await adapter.fetch_posts(
                                    account,
                                    start,
                                    stop,
                                    checkpoint=checkpoint.get("next_page") if checkpoint else None,
                                    save_checkpoint=save_page,
                                )
                                self.ingest(batch, manifest)
                                manifest["retrieval_queries"].append(batch["source"])
                                completed.append(
                                    {"account_id": account["platform_id"], "status": "success"}
                                )
                            except AccessError as exc:
                                completed.append(
                                    {"account_id": account["platform_id"], "status": exc.status}
                                )
                        entry.update(
                            status="success"
                            if all(r["status"] == "success" for r in completed)
                            else "partial"
                            if any(r["status"] == "success" for r in completed)
                            else "failed",
                            results=completed,
                            coverage="available uploads; private/deleted excluded; posts conservatively partial",
                        )
                        entry["quota_units_estimate"] = adapter.quota_units
            except AccessError as exc:
                entry.update(access_status=exc.status, http_status=exc.code)
            except Exception as exc:  # noqa: BLE001 -- isolate source failures; never log payload
                # Exception messages may contain credentials/private payloads. Persist type only.
                entry.update(access_status="REQUEST_FAILED", error_type=type(exc).__name__)
            finally:
                if hasattr(adapter, "http"):
                    manifest["requests"] += adapter.http.count
                    manifest["cost"] = float(budget.spent)
                    await adapter.http.close()
            manifest["sources"].append(entry)
            if entry["status"] != "success":
                self.store.put(
                    "extraction_errors",
                    digest([manifest["run_id"], len(manifest["sources"])]),
                    entry,
                    manifest["run_id"],
                )
            self.save_manifest(manifest)
        self.finish(manifest)
        self.normalize(manifest["run_id"])
        return manifest


def read_analysis(pipeline, run_id):
    result = pipeline.store.get("ranking_runs", run_id)
    if result is None:
        raise ValueError("Run goldintel analyze --run-id before report")
    return result


def export_review_sample(store, run_id, target=100):
    from mega_crawler.analytics.content import classify

    rows = store.rows("comments_or_mentions", run_id)
    mentions = store.rows("post_brand_mentions", run_id)
    strata = {}
    for row in rows:
        brands = sorted(
            {
                m["brand_id"]
                for m in mentions
                if m["platform"] == row["platform"] and m["post_id"] == row["post_id"]
            }
        )
        predicted = classify(row["text"])["sentiment"]
        stratum = (row["platform"], "|".join(brands), predicted)
        strata.setdefault(stratum, []).append(
            {**row, "brand_ids": brands, "baseline_label": predicted}
        )
    selected = []
    while strata and len(selected) < target:
        for key in sorted(strata):
            selected.append(strata[key].pop(0))
            if not strata[key]:
                del strata[key]
            if len(selected) >= target:
                break
    return [
        {
            **r,
            "human_label": None,
            "reviewer": None,
            "reviewer_a_label": None,
            "reviewer_b_label": None,
            "review_status": "pending",
        }
        for r in selected
    ]
