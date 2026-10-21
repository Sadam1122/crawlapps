import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from mega_crawler.adapters.base import Adapter
from mega_crawler.adapters.imports import load_import
from mega_crawler.adapters.web import WebAdapter, robots_permits
from mega_crawler.adapters.youtube import YouTubeAdapter
from mega_crawler.collection.http import AccessError, SafeHTTP, retry_seconds
from mega_crawler.normalization.core import utcnow
from mega_crawler.schemas.intelligence import UnsupportedCapability


@pytest.mark.parametrize(
    "platform", ["instagram", "tiktok", "threads", "facebook", "linkedin", "rss", "news"]
)
async def test_unsupported_contract(settings, platform):
    adapter = Adapter(platform, settings)
    assert adapter.capabilities()["import_fallback"]
    assert (await adapter.healthcheck()).status != "success"
    for method in ("discover_accounts", "fetch_posts", "fetch_metrics", "fetch_comments"):
        assert isinstance(await getattr(adapter, method)(), UnsupportedCapability)


@pytest.mark.parametrize(
    "platform",
    [
        "youtube",
        "instagram",
        "tiktok",
        "threads",
        "facebook",
        "linkedin",
        "web",
        "rss",
        "news",
    ],
)
def test_import_every_platform(import_path, platform):
    batch = load_import(import_path, platform)
    assert batch["posts"][0].platform == platform
    assert batch["observations"][0].values["likes"] == 1200
    assert batch["observations"][0].values["shares"] is None


def test_csv_sidecar(payload, tmp_path):
    path = tmp_path / "posts.csv"
    path.write_text(
        "post_id,canonical_url,text,likes,comments\n1,https://example.org/1,Mandiri emas,0,\n",
        encoding="utf-8-sig",
    )
    path.with_suffix(".meta.json").write_text(json.dumps(payload["source"]), encoding="utf-8")
    result = load_import(path, "instagram")
    assert result["observations"][0].values["likes"] == 0
    assert result["observations"][0].values["comments"] is None


def test_import_permission_and_demo(payload, tmp_path):
    file = tmp_path / "fixture.json"
    payload["source"]["demo"] = True
    file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="DEMO_PRODUCTION"):
        load_import(file, "youtube")
    payload["source"].pop("permission_basis")
    file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="permission_basis"):
        load_import(file, "youtube", demo=True)


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "AUTH_REQUIRED"),
        (403, "PERMISSION_BLOCKED"),
        (429, "RATE_LIMITED"),
        (500, "SERVER_ERROR"),
    ],
)
async def test_error_classification(settings, status, expected):
    settings.max_retries = 0
    client = SafeHTTP(
        settings,
        {"example.org"},
        httpx.MockTransport(lambda r: httpx.Response(status, text="error")),
        cost_per_request=0,
    )
    with pytest.raises(AccessError) as caught:
        await client.get("https://example.org/p")
    assert caught.value.status == expected
    with pytest.raises(AccessError, match="CIRCUIT_OPEN"):
        await client.get("https://example.org/p")
    await client.close()


async def test_retry_after_budget_and_redirect(settings, monkeypatch):
    calls = []

    async def no_sleep(seconds):
        calls.append(seconds)

    monkeypatch.setattr("mega_crawler.collection.http.asyncio.sleep", no_sleep)
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(200, text="ok")]
    )
    client = SafeHTTP(
        settings,
        {"example.org"},
        httpx.MockTransport(lambda r: next(responses)),
        cost_per_request=0,
    )
    assert (await client.get("https://example.org/")).text == "ok"
    assert calls == [2]
    client.settings.max_requests_per_run = 2
    with pytest.raises(AccessError, match="REQUEST_BUDGET_EXHAUSTED"):
        await client.get("https://example.org/")
    await client.close()
    with pytest.raises(AccessError, match="RETRY_AFTER_EXCEEDS"):
        retry_seconds("999", 0)
    client = SafeHTTP(
        settings,
        {"example.org"},
        httpx.MockTransport(
            lambda r: httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
        ),
        cost_per_request=0,
    )
    with pytest.raises(ValueError, match="TARGET_NOT_ALLOWLISTED"):
        await client.get("https://example.org/")
    await client.close()


async def test_challenge_stops(settings):
    client = SafeHTTP(
        settings,
        {"example.org"},
        httpx.MockTransport(lambda r: httpx.Response(200, text="verify you are human CAPTCHA")),
        cost_per_request=0,
    )
    with pytest.raises(AccessError, match="CHALLENGE_BLOCKED"):
        await client.get("https://example.org/")
    await client.close()


async def test_youtube_missing_key_and_paginated_uploads(settings):
    adapter = YouTubeAdapter(settings, httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert (await adapter.healthcheck()).status == "NOT_CONFIGURED"
    with pytest.raises(AccessError, match="NOT_CONFIGURED"):
        await adapter.fetch_metrics(["1"])
    await adapter.http.close()
    settings.youtube_api_key = SecretStr("fixture-key")
    now = utcnow()
    calls = []

    def respond(request):
        calls.append(request.url)
        if request.url.path.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "uploads-id"}}}]
                },
            )
        if request.url.path.endswith("/playlistItems"):
            second = request.url.params.get("pageToken") == "p2"
            return httpx.Response(
                200,
                json={
                    "items": [{"contentDetails": {"videoId": "b" if second else "a"}}],
                    **({} if second else {"nextPageToken": "p2"}),
                },
            )
        video = request.url.params["id"]
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": video,
                        "snippet": {
                            "publishedAt": (now - timedelta(days=1)).isoformat(),
                            "title": "Mandiri emas",
                        },
                        "statistics": {"viewCount": "10", "commentCount": "0"},
                    }
                ]
            },
        )

    adapter = YouTubeAdapter(settings, httpx.MockTransport(respond))
    result = await adapter.fetch_posts(
        {"platform_id": "approved-id"}, now - timedelta(days=30), now
    )
    assert len(result["posts"]) == 2
    assert result["posts"][0].format == "video_unknown"
    assert result["observations"][0].values["likes"] is None
    assert result["observations"][0].values["comments"] == 0
    assert len(calls) == 5
    await adapter.http.close()


async def test_web_policy_and_fixture_extraction(settings, monkeypatch):
    assert not robots_permits("User-agent: *\nDisallow: /blocked", "https://example.org/blocked")
    assert not robots_permits("User-agent: *\nDisallow: /*.pdf$", "https://example.org/f.pdf")
    assert robots_permits("User-agent: *\nDisallow: /*.pdf$", "https://example.org/product")

    async def extract(html):
        return "Mandiri Livin emas tutorial"

    monkeypatch.setattr("mega_crawler.adapters.web.extract_public_html", extract)
    source = {
        "url": "https://example.org/product",
        "terms_status": "permitted",
        "terms_url": "https://example.org/terms",
        "assessment": "fixture permission",
    }
    client = WebAdapter(
        settings,
        [source],
        httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                text="User-agent: *\nAllow: /"
                if r.url.path == "/robots.txt"
                else "<h1>Mandiri emas</h1>",
            )
        ),
    )
    result = await client.fetch_posts(source)
    assert result["posts"][0].published_at_utc is None
    assert result["observations"] == []
    with pytest.raises(AccessError, match="TERMS_REVIEW_REQUIRED"):
        await client.fetch_posts({**source, "terms_status": "pending"})
    await client.http.close()
