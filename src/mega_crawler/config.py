from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)
    app_env: str = "production"
    timezone: str = "Asia/Jakarta"
    database_url: str = "sqlite:///data/goldintel.sqlite"
    data_dir: Path = Path("data")
    config_dir: Path = Path("configs")
    max_concurrent_tasks: int = Field(2, ge=1, le=10)
    per_domain_concurrency: int = Field(1, ge=1, le=2)
    request_timeout_seconds: float = Field(25, gt=0)
    max_retries: int = Field(2, ge=0, le=5)
    max_requests_per_run: int = Field(100, ge=1)
    allow_paid_providers: bool = False
    max_cost_per_run: float = Field(0, ge=0, le=0, allow_inf_nan=False)
    youtube_api_key: SecretStr = SecretStr("")
    meta_access_token: SecretStr = SecretStr("")
    meta_app_id: str = ""
    meta_app_secret: SecretStr = SecretStr("")
    instagram_app_id: str = ""
    instagram_app_secret: SecretStr = SecretStr("")
    instagram_access_token: SecretStr = SecretStr("")
    instagram_account_id: str = ""
    facebook_page_id: str = ""
    threads_access_token: SecretStr = SecretStr("")
    threads_app_id: str = ""
    threads_app_secret: SecretStr = SecretStr("")
    tiktok_client_key: SecretStr = SecretStr("")
    tiktok_client_secret: SecretStr = SecretStr("")
    tiktok_access_token: SecretStr = SecretStr("")
    linkedin_access_token: SecretStr = SecretStr("")
    linkedin_client_id: str = ""
    linkedin_client_secret: SecretStr = SecretStr("")
    linkedin_organization_id: str = ""
    data_provider_name: str = ""
    data_provider_api_key: SecretStr = SecretStr("")
    llm_provider: str = ""
    llm_api_key: SecretStr = SecretStr("")
    retention_days: int = Field(30, ge=1)

    @field_validator("allow_paid_providers")
    @classmethod
    def free_only(cls, value):
        if value:
            raise ValueError("FREE_ONLY: paid providers cannot be enabled")
        return False

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        ZoneInfo(value)
        return value

    def secrets(self):
        return [v.get_secret_value() for v in self.__dict__.values() if isinstance(v, SecretStr)]
