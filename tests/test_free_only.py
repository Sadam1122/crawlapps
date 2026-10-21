import pytest
from pydantic import ValidationError

from mega_crawler.adapters import get_adapter
from mega_crawler.cli import doctor, parser
from mega_crawler.collection.health import check_apis
from mega_crawler.collection.http import AccessError, SafeHTTP
from mega_crawler.config import Settings
from mega_crawler.registries.catalog import capabilities
from mega_crawler.schemas.intelligence import PLATFORMS


def test_removed_platform_rejected_everywhere(settings, import_path):
    from mega_crawler.adapters.imports import load_import

    assert "x" not in PLATFORMS
    assert "x_bearer_token" not in Settings.model_fields
    assert not any(c["platform"] == "x" for c in capabilities(settings.config_dir))
    assert "x" not in doctor(settings)["credentials"]
    with pytest.raises(ValueError):
        get_adapter("x", settings)
    with pytest.raises(ValidationError):
        load_import(import_path, "x")
    with pytest.raises(SystemExit):
        parser().parse_args(["collect", "--platform", "x"])


@pytest.mark.parametrize(
    "url", ["https://api.x.com/2/tweets/search/recent", "https://api.twitter.com/2/tweets"]
)
async def test_retired_api_blocked_even_if_declared_free(settings, url):
    client = SafeHTTP(settings, {"api.x.com", "api.twitter.com"}, cost_per_request=0)
    try:
        with pytest.raises(AccessError, match="SOURCE_REMOVED_FREE_ONLY"):
            await client.get(url)
        assert client.count == 0
    finally:
        await client.close()


async def test_check_apis_offline_never_dispatches(settings, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("No network permitted in offline check")

    monkeypatch.setattr(SafeHTTP, "get", forbidden)
    result = await check_apis(settings, live=False)
    assert result["free_only"] and result["requests"] == 0 and result["monetary_cost"] == 0
    assert {row["platform"] for row in result["sources"]} == set(PLATFORMS)
    assert all(not row["live_verified"] for row in result["sources"])


async def test_unimplemented_apis_are_not_probed_with_app_secrets(settings, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Must not send an app secret as an access token")

    monkeypatch.setattr(SafeHTTP, "get", forbidden)
    result = await check_apis(settings)
    for row in result["sources"]:
        if row["platform"] not in {"web", "youtube"}:
            assert not row["live_verified"] and row["requests"] == 0
