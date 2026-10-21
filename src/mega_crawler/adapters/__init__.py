from mega_crawler.adapters.base import Adapter
from mega_crawler.adapters.youtube import YouTubeAdapter


def get_adapter(platform, settings):
    return YouTubeAdapter(settings) if platform == "youtube" else Adapter(platform, settings)
