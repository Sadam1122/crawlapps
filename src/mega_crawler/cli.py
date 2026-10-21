"""goldintel commands; standard library argparse keeps installation light."""

import argparse
import asyncio
import importlib.metadata
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

from mega_crawler.adapters.base import APPLICATION_CREDENTIALS, CREDENTIALS
from mega_crawler.analytics.engine import analyze
from mega_crawler.collection.pipeline import Pipeline, read_analysis
from mega_crawler.config import Settings
from mega_crawler.normalization.core import utcnow
from mega_crawler.registries.catalog import capabilities, load_registry
from mega_crawler.reporting.exports import export_bundle
from mega_crawler.schemas.intelligence import PLATFORMS
from mega_crawler.utils.logger import configure_logging
from mega_crawler.utils.safety import atomic_json, redact


def output(value):
    print(json.dumps(value, ensure_ascii=True, indent=2, default=str))


def parser():
    root = argparse.ArgumentParser(
        prog="goldintel",
        description="Gold Competitor Intelligence Indonesia — data teramati yang dapat diaudit",
    )
    root.add_argument("--config-dir", type=Path, default=Path("configs"))
    root.add_argument(
        "--demo-data",
        action="store_true",
        help="Gunakan DB DEMO terpisah untuk normalize/analyze/report/dashboard",
    )
    subs = root.add_subparsers(dest="command", required=True)
    subs.add_parser("doctor", help="Versi paket dan status credential; tidak menampilkan secret")
    checks = subs.add_parser(
        "check-apis", help="Uji akses gratis yang tersedia; token tidak dicetak"
    )
    checks.add_argument("--offline", action="store_true", help="Periksa readiness tanpa network")
    subs.add_parser(
        "verify-registry", help="Validasi struktur registry dan gap bukti; tanpa network"
    )
    discover = subs.add_parser(
        "discover", help="Tampilkan seed registry; bukan verifikasi akun otomatis"
    )
    discover.add_argument("--segment", default="direct")
    collect = subs.add_parser(
        "collect", help="Collect URL allowlist atau YouTube API dengan status per sumber"
    )
    collect.add_argument("--platform", choices=[*PLATFORMS, "all"], required=True)
    collect.add_argument("--days", choices=[30, 90, 180, 365], type=int, default=90)
    collect.add_argument("--end", help="Timestamp aware; default waktu run")
    collect.add_argument("--dry-run", action="store_true")
    collect.add_argument("--resume-run-id")
    imp = subs.add_parser("import", help="Impor CSV+sidecar atau JSON berizin")
    imp.add_argument("--platform", choices=PLATFORMS, required=True)
    imp.add_argument("--file", type=Path, required=True)
    imp.add_argument("--days", type=int, choices=[30, 90, 180, 365], default=90)
    imp.add_argument("--end")
    for command in ("normalize", "analyze", "report"):
        item = subs.add_parser(command)
        item.add_argument("--run-id", required=True)
        if command == "report":
            item.add_argument("--format", choices=["all", "data", "xlsx", "html"], default="all")
    dash = subs.add_parser(
        "dashboard", help="Serve HTML report hanya di 127.0.0.1; Ctrl+C berhenti"
    )
    dash.add_argument("--run-id")
    dash.add_argument("--port", type=int, default=8501)
    subs.add_parser("demo", help="Fixture sintetik end-to-end; tidak ada ranking kompetitor riil")
    purge = subs.add_parser(
        "purge", help="Hapus satu run dan export lokal untuk permintaan deletion"
    )
    purge.add_argument("--run-id", required=True)
    return root


def doctor(settings):
    versions = {}
    for name in (
        "crawl4ai",
        "pydantic",
        "pydantic-settings",
        "pandas",
        "loguru",
        "httpx",
        "pyyaml",
        "pyarrow",
        "openpyxl",
        "ruff",
        "pytest",
    ):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "missing"
    return {
        "versions": versions,
        "credentials": {
            platform: "configured (not remotely validated)"
            if getattr(settings, name).get_secret_value()
            else "missing"
            for platform, name in CREDENTIALS.items()
        },
        "database": "sqlite"
        if settings.database_url.startswith("sqlite:///")
        else "unsupported_backend",
        "application_credentials": {
            platform: "configured; OAuth/permissions not validated"
            if all(
                bool(value.get_secret_value())
                if hasattr(value, "get_secret_value")
                else bool(value)
                for value in (getattr(settings, name) for name in names)
            )
            else "missing_or_incomplete"
            for platform, names in APPLICATION_CREDENTIALS.items()
        },
        "account_ids": {
            name: "configured" if getattr(settings, name) else "missing"
            for name in ("instagram_account_id", "facebook_page_id", "linkedin_organization_id")
        },
        "cost_policy": {
            "allow_paid_providers": settings.allow_paid_providers,
            "max_cost_per_run": settings.max_cost_per_run,
            "unknown_request_price": "blocked",
        },
        "paid_requests": "permanently disabled; free-only build",
        "timezone": settings.timezone,
        "browser_check": "Run uv run crawl4ai-doctor separately; doctor does not crawl",
    }


def demo(settings):
    from datetime import timedelta

    pipeline = Pipeline(settings, demo=True)
    now = utcnow() - timedelta(seconds=2)
    posts = []
    for index in range(12):
        posts.append(
            {
                "post_id": f"synthetic-{index}",
                "canonical_url": f"https://example.org/demo/{index}",
                "published_at_utc": (now - timedelta(days=index + 1)).isoformat(),
                "title": "DEMO / DATA SINTETIS — Livin emas Mandiri tutorial",
                "text": "DATA SINTETIS. Cara nabung emas Mandiri. Cek biaya dan tarik fisik.",
                "format": "shorts",
                "content_type": "video",
                "product_id": "mandiri-tabungan-emas",
                "ownership_type": "owned",
                "metrics": {"likes": 20 + index, "comments": 2, "video_views": (index + 1) * 1000},
            }
        )
    payload = {
        "source": {
            "demo": True,
            "permission_basis": "synthetic fixture authored in repository",
            "provider": "synthetic",
            "source_url": "https://example.org/demo/",
            "observed_at_utc": now.isoformat(),
            "metric_definition_version": "synthetic-v1",
            "enumeration_status": "complete",
        },
        "posts": posts,
        "comments": [
            {
                "comment_id": "synthetic-comment",
                "post_id": "synthetic-0",
                "text": "DEMO gagal beli emas Mandiri, biaya bagaimana?",
                "source_url": "https://example.org/demo/0",
            }
        ],
    }
    path = settings.data_dir / "fixtures/DEMO_import.json"
    atomic_json(path, payload)
    manifest = pipeline.import_file("youtube", path, days=90)
    result = analyze(pipeline.store, manifest, pipeline.registry, manifest["ranking_config"])
    location = export_bundle(pipeline, manifest, result)
    pipeline.store.close()
    return {
        "label": "DEMO / DATA SINTETIS",
        "run_id": manifest["run_id"],
        "exports": str(location),
        "real_rankings": 0,
    }


def dashboard(settings, run_id=None, port=8501):
    retention = Pipeline(settings, demo=settings.data_dir.name == "demo")
    retention.store.close()
    candidates = sorted(
        (settings.data_dir / "runs").glob("*/processed/*report.html"),
        key=lambda p: p.stat().st_mtime,
    )
    if run_id:
        candidates = [p for p in candidates if p.parent.parent.name == run_id]
    if not candidates:
        raise ValueError("No report available; run report or demo first")
    content = candidates[-1].read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in {"/", "/index.html"}:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format, *args):
            pass

    output(
        {"dashboard": f"http://127.0.0.1:{port}/", "report": str(candidates[-1]), "stop": "Ctrl+C"}
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    args = parser().parse_args()
    settings = None
    try:
        settings = Settings(config_dir=args.config_dir)
        use_demo = args.demo_data or args.command == "demo"
        if use_demo:
            settings = settings.model_copy(
                update={
                    "data_dir": settings.data_dir / "demo",
                    "database_url": "sqlite:///"
                    + (settings.data_dir / "demo/goldintel.sqlite").as_posix(),
                }
            )
        configure_logging(settings)
        if args.command == "doctor":
            output(doctor(settings))
        elif args.command == "check-apis":
            from mega_crawler.collection.health import check_apis

            result = asyncio.run(check_apis(settings, live=not args.offline))
            path = settings.data_dir / "health/api-check.json"
            atomic_json(path, result)
            output({**result, "report_path": str(path)})
        elif args.command in {"verify-registry", "discover"}:
            registry = load_registry(settings.config_dir)
            if args.command == "discover":
                output(
                    {
                        "method": "seed registry only; status is not live verification",
                        "records": [r for r in registry if r["segment"] == args.segment],
                    }
                )
            else:
                output(
                    {
                        "schema": "valid",
                        "products": len(registry),
                        "entities": len({r["entity_id"] for r in registry}),
                        "pending_activity": [
                            r["product_id"]
                            for r in registry
                            if r["active_status"] != "verified_active"
                        ],
                        "accounts_approved": sum(
                            len(r["verified_social_accounts"]) for r in registry
                        ),
                        "live_regulatory_verification": "not established; inspect each record",
                    }
                )
        elif args.command == "demo":
            output(demo(settings))
        elif args.command == "dashboard":
            dashboard(settings, args.run_id, args.port)
        elif args.command == "collect" and args.dry_run:
            platforms = list(PLATFORMS) if args.platform == "all" else [args.platform]
            output(
                {
                    "dry_run": True,
                    "network_requests": 0,
                    "platforms": platforms,
                    "estimated_requests": {
                        p: "2 per permitted web URL"
                        if p == "web"
                        else "2 + 2 per uploads page per approved channel"
                        if p == "youtube"
                        else 0
                        for p in platforms
                    },
                    "request_cap": settings.max_requests_per_run,
                    "estimated_cost": 0,
                    "paid_requests": "disabled; unknown price blocks paid sources",
                    "source_capabilities": [
                        c for c in capabilities(settings.config_dir) if c["platform"] in platforms
                    ],
                }
            )
        else:
            pipeline = Pipeline(settings, use_demo)
            try:
                if args.command == "collect":
                    if use_demo:
                        raise ValueError("Live collection disabled in demo database")
                    platforms = list(PLATFORMS) if args.platform == "all" else [args.platform]
                    result = asyncio.run(
                        pipeline.collect(platforms, args.days, args.end, args.resume_run_id)
                    )
                    output(result)
                elif args.command == "import":
                    if use_demo:
                        raise ValueError("Use goldintel demo for synthetic input")
                    output(pipeline.import_file(args.platform, args.file, args.days, args.end))
                elif args.command == "normalize":
                    output(
                        {"normalized_posts": pipeline.normalize(args.run_id), "run_id": args.run_id}
                    )
                elif args.command == "analyze":
                    manifest = pipeline.manifest(args.run_id)
                    result = analyze(
                        pipeline.store, manifest, pipeline.registry, manifest["ranking_config"]
                    )
                    atomic_json(pipeline.directory(args.run_id) / "analysis.json", result)
                    output(
                        {
                            "run_id": args.run_id,
                            "rankings": len(result["rankings"]),
                            "Mandiri": result["mandiri_status"],
                        }
                    )
                elif args.command == "report":
                    manifest = pipeline.manifest(args.run_id)
                    output(
                        {
                            "exports": str(
                                export_bundle(
                                    pipeline,
                                    manifest,
                                    read_analysis(pipeline, args.run_id),
                                    args.format,
                                )
                            )
                        }
                    )
                elif args.command == "purge":
                    from mega_crawler.storage.retention import delete_run

                    delete_run(pipeline, args.run_id)
                    output(
                        {
                            "deleted_run": args.run_id,
                            "scope": "generated local records and exports only",
                        }
                    )
            finally:
                pipeline.store.close()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        # ValidationError includes input data in str(exc); expose neither payload nor secrets.
        message = (
            "Input schema validation failed"
            if isinstance(exc, ValidationError)
            else str(exc)
            if type(exc) is ValueError
            else "Operation failed; inspect documented paths/schema"
        )
        output(
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "message": redact(message, settings.secrets() if settings else ()),
            }
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
