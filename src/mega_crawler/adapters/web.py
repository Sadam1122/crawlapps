import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from mega_crawler.adapters.base import Adapter
from mega_crawler.collection.http import AccessError, SafeHTTP
from mega_crawler.schemas.intelligence import Health, Post
from mega_crawler.utils.safety import digest, redact


def robots_permits(text, url):
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    # RobotFileParser does not implement Google's wildcard syntax. Fail closed for matching PDF.
    if re.search(r"(?im)^disallow:\s*.*\.pdf", text) and ".pdf" in urlsplit(url).path.lower():
        return False
    return parser.can_fetch("GoldIntelResearch", url)


async def extract_public_html(html):
    """Crawl4AI operates on already policy-checked bytes; no browser egress/JS."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(
            url="raw:" + html, config=CrawlerRunConfig(verbose=False, log_console=False)
        )
        if not result.success:
            raise AccessError("EXTRACTION_FAILED")
        return result.markdown.raw_markdown


class WebAdapter(Adapter):
    def __init__(self, settings, sources, transport=None):
        super().__init__("web", settings)
        self.sources = sources
        self.http = SafeHTTP(
            settings, {urlsplit(s["url"]).hostname for s in sources}, transport, cost_per_request=0
        )

    async def healthcheck(self):
        ready = any(s["terms_status"] == "permitted" for s in self.sources)
        return Health(
            platform="web",
            status="READY" if ready else "TERMS_REVIEW_REQUIRED",
            reason="Each URL checks terms assessment and live robots before fetch; readiness is not live success",
        )

    async def discover_accounts(self, *args, **kwargs):
        return self.unsupported(
            "discover_accounts: official links are review candidates, not automatically verified"
        )

    async def fetch_posts(self, source, start=None, end=None):
        if source["terms_status"] != "permitted":
            raise AccessError("TERMS_REVIEW_REQUIRED")
        p = urlsplit(source["url"])
        robots = await self.http.get(f"{p.scheme}://{p.netloc}/robots.txt", allow_not_found=True)
        if robots.status_code != 404 and not robots_permits(robots.text, source["url"]):
            raise AccessError("ROBOTS_DISALLOWED")
        response = await self.http.get(source["url"])
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        # Do not execute embedded JS or load linked media/subresources.
        for node in soup(
            ["script", "style", "iframe", "form", "noscript", "nav", "header", "footer"]
        ):
            node.decompose()
        articles = soup.select(".journal-content-article")
        if articles:
            # Liferay product body: exclude repeated navigation/standard corporate footers.
            body = max(articles, key=lambda n: n.get_text(" ", strip=True).casefold().count("emas"))
        else:
            body = soup.select_one("main") or soup
        markdown = await extract_public_html(str(body))
        evidence_hash = digest(response.text)
        post = Post(
            platform="web",
            post_id=digest(source["url"]),
            canonical_url=source["url"],
            text=redact(markdown),
            title=redact(title),
            content_type="product_page",
            format="web_page",
            product_id=source.get("product_id"),
            ownership_type="owned",
            source_method="public_http_crawl4ai",
            provider=p.hostname,
            source_url=source["url"],
            evidence_locator="sha256:" + evidence_hash,
            evidence_hash=evidence_hash,
            content_hash=digest(markdown),
        )
        return {
            "posts": [post],
            "observations": [],
            "product_facts": [],
            "comments": [],
            "source": {
                "permission_basis": source["assessment"],
                "robots_status": robots.status_code,
                "robots_hash": digest(robots.text),
                "terms_url": source["terms_url"],
                "publication_date": "unknown; page excluded from time-window social rankings",
            },
            "evidence_hash": evidence_hash,
        }
