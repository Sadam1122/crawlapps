"""SQLite JSON documents with indexed keys, append-only observations and run lineage."""

import json
import sqlite3
from pathlib import Path

from mega_crawler.normalization.core import utcnow
from mega_crawler.utils.safety import digest

TABLES = (
    "entities",
    "brands",
    "products",
    "relationships",
    "accounts",
    "posts",
    "post_brand_mentions",
    "metric_observations",
    "account_observations",
    "comments_or_mentions",
    "product_facts",
    "price_quotes",
    "news_items",
    "issue_clusters",
    "source_capabilities",
    "collection_runs",
    "collection_events",
    "extraction_errors",
    "ranking_runs",
    "ranking_components",
    "analyst_reviews",
    "post_versions",
    "checkpoints",
)


class Store:
    def __init__(self, settings):
        if not settings.database_url.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL backend unsupported: this release supports SQLite only")
        path = Path(settings.database_url.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY)")
        for table in TABLES:
            self.db.execute(
                f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, run_id TEXT, data TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            self.db.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_run ON {table}(run_id)")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS run_records(run_id TEXT, table_name TEXT, record_id TEXT, PRIMARY KEY(run_id,table_name,record_id))"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS run_record_data(run_id TEXT, table_name TEXT, record_id TEXT, data TEXT NOT NULL, PRIMARY KEY(run_id,table_name,record_id))"
        )
        self.db.execute("INSERT OR IGNORE INTO schema_migrations VALUES(1)")
        self.db.commit()

    def close(self):
        self.db.close()

    def put(self, table, key, data, run_id=None, append=False):
        if table not in TABLES:
            raise ValueError("Unknown table")
        data = data.model_dump(mode="json") if hasattr(data, "model_dump") else data
        if table == "posts":
            old = self.get(table, key)
            if old and old != data:
                self.put(
                    "post_versions",
                    digest([key, old]),
                    {"post_key": key, "previous": old},
                    run_id,
                    append=True,
                )
        verb = "INSERT OR IGNORE" if append else "INSERT OR REPLACE"
        self.db.execute(
            f"{verb} INTO {table} VALUES(?,?,?,?)",
            (key, run_id, json.dumps(data, ensure_ascii=False, default=str), utcnow().isoformat()),
        )
        if run_id:
            self.db.execute("INSERT OR IGNORE INTO run_records VALUES(?,?,?)", (run_id, table, key))
            self.db.execute(
                f"{verb} INTO run_record_data VALUES(?,?,?,?)",
                (run_id, table, key, json.dumps(data, ensure_ascii=False, default=str)),
            )

    def commit(self):
        self.db.commit()

    def get(self, table, key):
        if table not in TABLES:
            raise ValueError("Unknown table")
        row = self.db.execute(f"SELECT data FROM {table} WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def rows(self, table, run_id=None):
        if table not in TABLES:
            raise ValueError("Unknown table")
        if run_id:
            rows = self.db.execute(
                "SELECT data FROM run_record_data WHERE run_id=? AND table_name=? ORDER BY record_id",
                (run_id, table),
            )
        else:
            rows = self.db.execute(f"SELECT data FROM {table} ORDER BY id")
        return [json.loads(r[0]) for r in rows]

    def fact(self, fact, run_id):
        data = fact.model_dump(mode="json")
        same = self.db.execute("SELECT id,data FROM product_facts").fetchall()
        identity = (data["product_id"], data["fact_name"], data["channel"])
        for row in same:
            old = json.loads(row["data"])
            if (old["product_id"], old["fact_name"], old["channel"]) == identity and old[
                "valid_to"
            ] is None:
                if (
                    old["value"] == data["value"]
                    and old["availability_status"] == data["availability_status"]
                ):
                    old["checked_at"] = data["checked_at"]
                    self.put("product_facts", row["id"], old, run_id)
                    return
                old["valid_to"] = data["valid_from"]
                self.put("product_facts", row["id"], old, run_id)
        self.put("product_facts", digest([identity, data["valid_from"]]), data, run_id)

    def seed(self, registry, sources):
        # Remove retired current capability metadata; historical run artifacts remain intact.
        self.db.execute("DELETE FROM source_capabilities WHERE id=?", ("x",))
        for r in registry:
            self.put(
                "entities",
                r["entity_id"],
                {k: r[k] for k in ("entity_id", "legal_name", "parent_group_id")},
            )
            self.put(
                "brands", r["brand_id"], {k: r[k] for k in ("brand_id", "brand_name", "entity_id")}
            )
            self.put("products", r["product_id"], r)
            for a in r["verified_social_accounts"]:
                self.put(
                    "accounts",
                    a["platform"] + ":" + a["platform_id"],
                    {**a, "brand_id": r["brand_id"]},
                )
        for source in sources:
            self.put("source_capabilities", source["platform"], source)
        self.commit()
