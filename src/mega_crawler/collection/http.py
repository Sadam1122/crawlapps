import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import httpx

from mega_crawler.collection.budget import BudgetError, RunBudget
from mega_crawler.utils.safety import validate_target


class AccessError(Exception):
    def __init__(self, status, code=None):
        super().__init__(status)
        self.status = status
        self.code = code


def retry_seconds(header, attempt):
    if header:
        try:
            seconds = float(header)
        except ValueError:
            try:
                seconds = (
                    parsedate_to_datetime(header).astimezone(UTC) - datetime.now(UTC)
                ).total_seconds()
            except (ValueError, TypeError):
                seconds = 2**attempt
        if seconds > 30:
            raise AccessError("RATE_LIMITED_RETRY_AFTER_EXCEEDS_BOUND", 429)
        return max(0, seconds)
    return min(2**attempt + random.random(), 30)


class SafeHTTP:
    def __init__(
        self,
        settings,
        allowed,
        transport=None,
        *,
        budget=None,
        cost_per_request=None,
        paid_provider=False,
    ):
        self.settings = settings
        self.budget = budget if budget is not None else RunBudget(settings)
        self.cost_per_request = cost_per_request
        self.paid_provider = paid_provider
        self.allowed = set(allowed)
        self.resolve = transport is None
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"User-Agent": "GoldIntelResearch/1.0"},
        )
        self.global_limit = asyncio.Semaphore(settings.max_concurrent_tasks)
        self.domain_limits = {}
        self.count = 0
        self.blocked = set()
        self.failures = {}

    async def close(self):
        await self.client.aclose()

    async def get(self, url, params=None, headers=None, allow_not_found=False):
        host = urlsplit(url).hostname or ""
        if any(
            host == domain or host.endswith("." + domain) for domain in ("x.com", "twitter.com")
        ):
            raise AccessError("SOURCE_REMOVED_FREE_ONLY")
        try:
            self.budget.check(self.cost_per_request, self.paid_provider)
        except BudgetError as exc:
            raise AccessError(str(exc)) from None
        target = validate_target(url, self.allowed, resolve=self.resolve)
        host = urlsplit(target).hostname
        if host in self.blocked:
            raise AccessError("CIRCUIT_OPEN")
        sem = self.domain_limits.setdefault(
            host, asyncio.Semaphore(self.settings.per_domain_concurrency)
        )
        async with self.global_limit, sem:
            for attempt in range(self.settings.max_retries + 1):
                if self.count >= self.settings.max_requests_per_run:
                    raise AccessError("REQUEST_BUDGET_EXHAUSTED")
                try:
                    self.budget.reserve(self.cost_per_request, self.paid_provider)
                except BudgetError as exc:
                    raise AccessError(str(exc)) from None
                self.count += 1
                try:
                    response = await self.client.get(target, params=params, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError):
                    self.failures[host] = self.failures.get(host, 0) + 1
                    if self.failures[host] >= 3:
                        self.blocked.add(host)
                    if attempt == self.settings.max_retries or host in self.blocked:
                        raise AccessError("NETWORK_ERROR") from None
                    await asyncio.sleep(retry_seconds(None, attempt))
                    continue
                if response.is_redirect:
                    # Never forward API keys/authorization to redirects.
                    redirected = urljoin(target, response.headers.get("location", ""))
                    validate_target(redirected, self.allowed, resolve=self.resolve)
                    raise AccessError("REDIRECT_REQUIRES_REVIEW", response.status_code)
                if response.status_code in {401, 403}:
                    self.blocked.add(host)
                    raise AccessError(
                        "AUTH_REQUIRED" if response.status_code == 401 else "PERMISSION_BLOCKED",
                        response.status_code,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.settings.max_retries:
                        await asyncio.sleep(
                            retry_seconds(response.headers.get("retry-after"), attempt)
                        )
                        continue
                    self.blocked.add(host)
                    raise AccessError(
                        "RATE_LIMITED" if response.status_code == 429 else "SERVER_ERROR",
                        response.status_code,
                    )
                if response.status_code == 404 and allow_not_found:
                    return response
                if response.status_code >= 400:
                    raise AccessError("HTTP_ERROR", response.status_code)
                self.failures[host] = 0
                if len(response.content) > 5_000_000:
                    raise AccessError("RESPONSE_TOO_LARGE")
                if (
                    "captcha" in response.text[:10000].lower()
                    or "verify you are human" in response.text[:10000].lower()
                ):
                    self.blocked.add(host)
                    raise AccessError("CHALLENGE_BLOCKED")
                return response
        raise AccessError("REQUEST_FAILED")
