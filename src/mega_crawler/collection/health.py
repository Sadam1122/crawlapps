"""Minimal read-only checks: only implemented zero-cost routes; never exchange app secrets."""

import yaml

from mega_crawler.adapters import get_adapter
from mega_crawler.adapters.base import APPLICATION_CREDENTIALS, CREDENTIALS
from mega_crawler.adapters.web import WebAdapter
from mega_crawler.collection.http import AccessError
from mega_crawler.normalization.core import utcnow
from mega_crawler.schemas.intelligence import PLATFORMS


async def check_apis(settings, live=True):
    sources = yaml.safe_load(
        (settings.config_dir / "web_sources.yaml").read_text(encoding="utf-8")
    )["sources"]
    results = []
    request_count = 0
    request_limit = min(settings.max_requests_per_run, 3)
    for platform in PLATFORMS:
        remaining = request_limit - request_count
        local = settings.model_copy(
            update={
                "max_retries": 0,
                "max_requests_per_run": max(1, min(2 if platform == "web" else 1, remaining)),
            }
        )
        adapter = WebAdapter(local, sources) if platform == "web" else get_adapter(platform, local)
        app_fields = APPLICATION_CREDENTIALS.get(platform, ())
        application_configured = bool(app_fields) and all(
            bool(v.get_secret_value()) if hasattr(v, "get_secret_value") else bool(v)
            for v in (getattr(settings, field) for field in app_fields)
        )
        token_field = CREDENTIALS.get(platform)
        token_configured = (
            bool(getattr(settings, token_field).get_secret_value()) if token_field else False
        )
        record = {
            "platform": platform,
            "application_configured": application_configured,
            "access_credential_configured": token_configured,
            "live_verified": False,
            "requests": 0,
            "monetary_cost": 0,
            "import_available": True,
        }
        try:
            health = await adapter.healthcheck()
            record.update(
                status=health.status,
                reason=health.reason,
                docs_status=adapter.capabilities()["docs_status"],
            )
            if not live:
                record["probe"] = "offline_only"
            elif platform not in {"web", "youtube"}:
                record["probe"] = (
                    "not_sent: API adapter unavailable; OAuth token/permission missing or unverified"
                )
                if token_configured:
                    record["status"] = "API_NOT_IMPLEMENTED"
            elif health.status != "READY":
                record["probe"] = "not_sent: credential/terms missing"
            elif remaining <= 0:
                record["status"] = "CHECK_REQUEST_LIMIT_REACHED"
            elif platform == "web":
                source = next(s for s in sources if s["terms_status"] == "permitted")
                batch = await adapter.fetch_posts(source)
                record.update(
                    status="LIVE_OK",
                    live_verified=True,
                    probe="robots + first permitted product page",
                    source_url=source["url"],
                    observed_pages=len(batch["posts"]),
                )
            else:
                response = await adapter.request("i18nRegions", part="snippet", hl="id")
                valid = response.get("kind") == "youtube#i18nRegionListResponse"
                record.update(
                    status="LIVE_OK" if valid else "UNEXPECTED_RESPONSE",
                    live_verified=valid,
                    probe="i18nRegions.list only; no competitor collection",
                    quota_units_estimate=1,
                    docs_url="https://developers.google.com/youtube/data/reference/rest/v3/i18nRegions/list",
                )
        except AccessError as exc:
            record.update(status=exc.status, http_status=exc.code)
        except Exception as exc:  # noqa: BLE001 -- isolate providers and do not disclose payloads
            record.update(status="CHECK_FAILED", error_type=type(exc).__name__)
        finally:
            if hasattr(adapter, "http"):
                record["requests"] = adapter.http.count
                request_count += adapter.http.count
                await adapter.http.close()
        results.append(record)
    return {
        "checked_at_utc": utcnow().isoformat(),
        "free_only": True,
        "live_requested": live,
        "requests": request_count,
        "request_limit": request_limit,
        "monetary_cost": 0,
        "sources": results,
        "limitations": [
            "Live OK only validates the named probe, not all platform methods.",
            "App credentials are not access tokens; no automatic OAuth or paid requests.",
        ],
    }
