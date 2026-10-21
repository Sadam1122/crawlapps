from mega_crawler.registries.catalog import capabilities
from mega_crawler.schemas.intelligence import PLATFORMS, Health, UnsupportedCapability

CREDENTIALS = {
    "youtube": "youtube_api_key",
    "instagram": "instagram_access_token",
    "facebook": "meta_access_token",
    "threads": "threads_access_token",
    "tiktok": "tiktok_access_token",
    "linkedin": "linkedin_access_token",
}

APPLICATION_CREDENTIALS = {
    "instagram": ("instagram_app_id", "instagram_app_secret"),
    "facebook": ("meta_app_id", "meta_app_secret"),
    "threads": ("threads_app_id", "threads_app_secret"),
    "tiktok": ("tiktok_client_key", "tiktok_client_secret"),
    "linkedin": ("linkedin_client_id", "linkedin_client_secret"),
}


class Adapter:
    def __init__(self, platform, settings):
        if platform not in PLATFORMS:
            raise ValueError("Unsupported platform in free-only build")
        self.platform, self.settings = platform, settings

    def capabilities(self):
        return next(
            c for c in capabilities(self.settings.config_dir) if c["platform"] == self.platform
        )

    def unsupported(self, method):
        return UnsupportedCapability(
            platform=self.platform,
            capability=method,
            reason="Use authorized CSV/JSON import; competitor API path/permission not verified",
        )

    async def healthcheck(self):
        credential = CREDENTIALS.get(self.platform)
        configured = (
            bool(getattr(self.settings, credential).get_secret_value()) if credential else False
        )
        caps = self.capabilities()
        status = (
            "NOT_CONFIGURED"
            if credential and not configured
            else "DOCS_UNVERIFIED"
            if caps["docs_status"] == "docs_unverified"
            else "PERMISSION_REQUIRED"
        )
        return Health(platform=self.platform, status=status, reason=caps["limitations"])

    async def discover_accounts(self, *args, **kwargs):
        return self.unsupported("discover_accounts")

    async def fetch_posts(self, *args, **kwargs):
        return self.unsupported("fetch_posts")

    async def fetch_metrics(self, *args, **kwargs):
        return self.unsupported("fetch_metrics")

    async def fetch_comments(self, *args, **kwargs):
        return self.unsupported("fetch_comments")
