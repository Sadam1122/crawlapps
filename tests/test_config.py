import json
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values
from pydantic import SecretStr, ValidationError

from mega_crawler.adapters.base import APPLICATION_CREDENTIALS, CREDENTIALS, Adapter
from mega_crawler.cli import doctor
from mega_crawler.collection.budget import BudgetError, RunBudget
from mega_crawler.collection.http import AccessError, SafeHTTP
from mega_crawler.config import Settings


def test_empty_optional_credentials_start_with_safe_defaults(tmp_path):
    path = tmp_path / ".env"
    path.write_text(Path(".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    settings = Settings(_env_file=path)
    assert settings.database_url == "sqlite:///data/goldintel.sqlite"
    assert settings.timezone == "Asia/Jakarta"
    assert not settings.allow_paid_providers and settings.max_cost_per_run == 0
    assert all(not getattr(settings, name).get_secret_value() for name in CREDENTIALS.values())


def test_app_ids_secrets_are_separate_from_accounts_and_tokens(tmp_path):
    path = tmp_path / ".env"
    pairs = {
        "YOUTUBE_API_KEY": "fixture-youtube-key",
        "INSTAGRAM_APP_ID": "ig-app",
        "INSTAGRAM_APP_SECRET": "fixture-ig-secret",
        "META_APP_ID": "fb-app",
        "META_APP_SECRET": "fixture-fb-secret",
        "THREADS_APP_ID": "threads-app",
        "THREADS_APP_SECRET": "fixture-threads-secret",
        "TIKTOK_CLIENT_KEY": "fixture-tiktok-key",
        "TIKTOK_CLIENT_SECRET": "fixture-tiktok-secret",
        "LINKEDIN_CLIENT_ID": "li-client",
        "LINKEDIN_CLIENT_SECRET": "fixture-linkedin-secret==",
    }
    path.write_text("".join(f'{k}="{v}"\n' for k, v in pairs.items()), encoding="utf-8")
    settings = Settings(_env_file=path)
    for platform, names in APPLICATION_CREDENTIALS.items():
        for name in names:
            value = getattr(settings, name)
            assert (value.get_secret_value() if isinstance(value, SecretStr) else value) == pairs[
                name.upper()
            ]
        assert not getattr(settings, CREDENTIALS[platform]).get_secret_value()
    assert not settings.instagram_account_id and not settings.facebook_page_id
    assert not settings.linkedin_organization_id
    rendered = repr(settings) + json.dumps(doctor(settings))
    assert all(
        value not in rendered
        for key, value in pairs.items()
        if "SECRET" in key or key == "YOUTUBE_API_KEY"
    )
    assert all(
        secret in settings.secrets() for secret in (pairs[k] for k in pairs if "SECRET" in k)
    )


def test_example_contains_only_empty_credentials_and_safe_cost_defaults():
    values = dotenv_values(".env.example")
    assert set(values) <= {name.upper() for name in Settings.model_fields}
    for key, value in values.items():
        assert value == (
            "false" if key == "ALLOW_PAID_PROVIDERS" else "0" if key == "MAX_COST_PER_RUN" else ""
        )


async def test_app_credentials_do_not_make_adapter_ready(settings):
    settings.instagram_app_id = "fixture-app"
    settings.instagram_app_secret = SecretStr("fixture-secret")
    assert (await Adapter("instagram", settings).healthcheck()).status == "NOT_CONFIGURED"
    assert CREDENTIALS["instagram"] == "instagram_access_token"


@pytest.mark.parametrize(
    "paid,price,expected",
    [
        (True, 0, "PAID_PROVIDERS_DISABLED"),
        (False, "0.01", "PAID_PROVIDERS_DISABLED"),
        (False, None, "REQUEST_PRICE_UNKNOWN"),
    ],
)
async def test_cost_policy_blocks_before_dispatch(settings, paid, price, expected):
    calls = []
    client = SafeHTTP(
        settings,
        {"example.org"},
        httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200)),
        paid_provider=paid,
        cost_per_request=price,
    )
    try:
        with pytest.raises(AccessError, match=expected):
            await client.get("https://example.org/")
        assert not calls and client.count == 0 and client.budget.spent == 0
    finally:
        await client.close()


def test_paid_settings_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allow_paid_providers=True)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_cost_per_run=1)


def test_zero_budget_blocks_paid_even_if_enabled(settings):
    # Runtime policy still holds if code deliberately bypasses Pydantic validation.
    settings.allow_paid_providers = True
    settings.max_cost_per_run = 100
    budget = RunBudget(settings)
    assert budget.limit == 0 and not budget.allow_paid
    with pytest.raises(BudgetError, match="PAID_PROVIDERS_DISABLED"):
        budget.reserve("0.01", True)
    with pytest.raises(BudgetError, match="PAID_PROVIDERS_DISABLED"):
        budget.reserve(None, True)
    budget.reserve(0)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf")])
def test_invalid_cost_setting_rejected(cost):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_cost_per_run=cost)
