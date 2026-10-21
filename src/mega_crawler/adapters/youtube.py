from mega_crawler.adapters.base import Adapter
from mega_crawler.collection.http import AccessError, SafeHTTP
from mega_crawler.normalization.core import aware, utcnow
from mega_crawler.schemas.intelligence import METRICS, Health, MetricObservation, Post
from mega_crawler.utils.safety import digest, redact

BASE = "https://www.googleapis.com/youtube/v3/"


class YouTubeAdapter(Adapter):
    def __init__(self, settings, transport=None):
        super().__init__("youtube", settings)
        self.http = SafeHTTP(settings, {"www.googleapis.com"}, transport, cost_per_request=0)
        self.quota_units = 0

    async def healthcheck(self):
        ready = bool(self.settings.youtube_api_key.get_secret_value())
        return Health(
            platform="youtube",
            status="READY" if ready else "NOT_CONFIGURED",
            reason="Public uploads/video API implemented; health does not validate token or quota",
        )

    async def request(self, resource, **params):
        key = self.settings.youtube_api_key.get_secret_value()
        if not key:
            raise AccessError("NOT_CONFIGURED")
        self.quota_units += 1
        response = await self.http.get(BASE + resource, params={**params, "key": key})
        return response.json()

    async def discover_accounts(self, accounts=None):
        # Resolve only IDs verified through primary domain links; no guess from similar names.
        output = []
        for account in accounts or []:
            if account.get("reviewer_status") != "approved":
                continue
            result = await self.request(
                "channels", part="snippet,contentDetails,statistics", id=account["platform_id"]
            )
            output.extend(result.get("items", []))
        return output

    async def fetch_posts(self, account, start, end, checkpoint=None, save_checkpoint=None):
        result = await self.request("channels", part="contentDetails", id=account["platform_id"])
        if not result.get("items"):
            raise AccessError("CHANNEL_UNAVAILABLE")
        playlist = result["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        token = checkpoint
        posts, observations = [], []
        while True:
            params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
            if token:
                params["pageToken"] = token
            page = await self.request("playlistItems", **params)
            ids = [i["contentDetails"]["videoId"] for i in page.get("items", [])]
            if ids:
                detail = await self.request(
                    "videos",
                    part="snippet,statistics,contentDetails,liveStreamingDetails",
                    id=",".join(ids),
                )
                for item in detail.get("items", []):
                    snippet = item["snippet"]
                    published = aware(snippet["publishedAt"])
                    if not start <= published < end:
                        continue
                    url = "https://www.youtube.com/watch?v=" + item["id"]
                    evidence = digest(item)
                    live = bool(item.get("liveStreamingDetails"))
                    # Duration alone cannot distinguish Shorts from long video.
                    post = Post(
                        platform="youtube",
                        post_id=item["id"],
                        canonical_url=url,
                        account_id=account["platform_id"],
                        published_at_utc=published,
                        title=redact(snippet["title"]),
                        text=redact(snippet.get("description", "")),
                        content_type="video",
                        format="live" if live else "video_unknown",
                        ownership_type="owned",
                        source_method="official_api",
                        provider="youtube_data_v3",
                        source_url=url,
                        evidence_locator="api-sha256:" + evidence,
                        evidence_hash=evidence,
                        enumeration_status="partial",
                    )
                    posts.append(post)
                    observations.append(self.observation(item))
            token = page.get("nextPageToken")
            # Checkpoint persistence happens in orchestrator after records are durable.
            if save_checkpoint:
                save_checkpoint(token, posts, observations)
                posts, observations = [], []
            if not token:
                break
        return {
            "posts": posts,
            "observations": observations,
            "product_facts": [],
            "comments": [],
            "source": {
                "enumeration_status": "complete available uploads; missing/private/deleted videos not visible",
                "query": playlist,
                "retrieval_order": "uploads API pagination",
                "quota_units": self.quota_units,
            },
        }

    @staticmethod
    def observation(item):
        mapping = {"likes": "likeCount", "comments": "commentCount", "video_views": "viewCount"}
        stats = item.get("statistics", {})
        values = {
            field: int(stats[raw]) if raw in stats else None for field, raw in mapping.items()
        }
        now = utcnow()
        return MetricObservation(
            observation_id=digest([item["id"], now.isoformat()]),
            platform="youtube",
            post_id=item["id"],
            observed_at_utc=now,
            values=values,
            metric_status={
                k: "observed" if values.get(k) is not None else "not_exposed" for k in METRICS
            },
            raw_values={k: stats.get(v) for k, v in mapping.items()},
            count_precision={k: "exact" for k in values if values[k] is not None},
            raw_metric_name=mapping,
            metric_definition_version="youtube-v3-views-short-definition-2025-03-31",
            analytics_permission="blocked",
            source_url="https://www.youtube.com/watch?v=" + item["id"],
            evidence_hash=digest(item),
        )

    async def fetch_metrics(self, post_ids):
        records = []
        for offset in range(0, len(post_ids), 50):
            response = await self.request(
                "videos", part="statistics", id=",".join(post_ids[offset : offset + 50])
            )
            records.extend(self.observation(item) for item in response.get("items", []))
        return records

    async def fetch_comments(self, post_id, max_pages=1):
        rows, token = [], None
        for _ in range(max_pages):
            params = {
                "part": "snippet",
                "videoId": post_id,
                "maxResults": 100,
                "order": "time",
                "textFormat": "plainText",
            }
            if token:
                params["pageToken"] = token
            page = await self.request("commentThreads", **params)
            for item in page.get("items", []):
                comment = item["snippet"]["topLevelComment"]
                rows.append(
                    {
                        "comment_id": digest(["youtube", comment["id"]]),
                        "post_id": post_id,
                        "platform": "youtube",
                        "text": redact(comment["snippet"]["textDisplay"]),
                        "source_url": "https://www.youtube.com/watch?v=" + post_id,
                        "evidence_hash": digest(item),
                        "selection_method": "time ordered top-level; replies excluded",
                        "observed_at_utc": utcnow().isoformat(),
                    }
                )
            token = page.get("nextPageToken")
            if not token:
                break
        return rows
