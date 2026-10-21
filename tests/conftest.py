import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

from mega_crawler.config import Settings
from mega_crawler.normalization.core import utcnow


def pytest_configure(config):
    # A fresh workspace temp root avoids ACL collisions between managed Windows runners.
    if not config.option.basetemp:
        config.option.basetemp = str(
            Path(__file__).resolve().parents[1] / "data" / ("tests-" + uuid.uuid4().hex)
        )


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        config_dir=Path("configs").resolve(),
        data_dir=tmp_path,
        database_url="sqlite:///" + (tmp_path / "test.sqlite").as_posix(),
    )


@pytest.fixture
def payload():
    now = utcnow() - timedelta(minutes=1)
    return {
        "source": {
            "provider": "authorized_test_fixture",
            "permission_basis": "test synthetic local fixture",
            "source_url": "https://example.org/source",
            "observed_at_utc": now.isoformat(),
            "metric_definition_version": "fixture-v1",
            "enumeration_status": "complete",
        },
        "posts": [
            {
                "post_id": "1",
                "canonical_url": "https://example.org/post/1?utm_source=test",
                "text": "Mandiri Livin emas cara nabung",
                "format": "shorts",
                "ownership_type": "owned",
                "published_at_utc": (now - timedelta(days=3)).isoformat(),
                "metrics": {"likes": "1,2 rb", "comments": 0, "video_views": 10000},
            }
        ],
    }


@pytest.fixture
def import_path(tmp_path, payload):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
