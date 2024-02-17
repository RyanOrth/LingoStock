import os
import json
import feedparser
from datetime import datetime
import logging
from typing import Any, Iterator, List, Optional, Sequence

from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.news import NewsURLLoader

from langchain_community.document_loaders import RSSFeedLoader

logger = logging.getLogger(__name__)

class CachingRSSFeedLoader(RSSFeedLoader):
    def __init__(
        self,
        cache_dir: str,
        urls: Optional[Sequence[str]] = None,
        opml: Optional[str] = None,
        continue_on_failure: bool = True,
        show_progress_bar: bool = False,
        **newsloader_kwargs: Any,
    ) -> None:
        super().__init__(
            urls=urls,
            opml=opml,
            continue_on_failure=continue_on_failure,
            show_progress_bar=show_progress_bar,
            **newsloader_kwargs,
        )
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_file_path(self, url: str) -> str:
        # Create a safe filename from the URL
        filename = f"{hash(url)}.json"
        return os.path.join(self.cache_dir, filename)

    def _get_last_update(self, url: str) -> datetime:
        cache_file = self._get_cache_file_path(url)
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return datetime.strptime(data['last_update'], '%Y-%m-%d %H:%M:%S')
        return datetime.min

    def _update_cache(self, url: str, last_update: datetime):
        cache_file = self._get_cache_file_path(url)
        with open(cache_file, 'w') as f:
            json.dump({'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S')}, f)

    def lazy_load(self) -> Iterator[Document]:
        for url in self._get_urls:
            last_update = self._get_last_update(url)
            feed = feedparser.parse(url, agent=self.newsloader_kwargs.get("browser_user_agent", None))
            if getattr(feed, "bozo", False):
                logger.error(f"Error fetching {url}, exception: {feed.bozo_exception}")
                if not self.continue_on_failure:
                    raise ValueError(f"Error fetching {url}, exception: {feed.bozo_exception}")

            new_last_update = last_update
            for entry in feed.entries:
                published = datetime(*entry.published_parsed[:6])
                if published > last_update:
                    try:
                        loader = NewsURLLoader(urls=[entry.link], **self.newsloader_kwargs)
                        article = loader.load()[0]
                        article.metadata["feed"] = url
                        article.metadata["published"] = published.strftime('%Y-%m-%d %H:%M:%S')
                        yield article
                        if published > new_last_update:
                            new_last_update = published
                    except Exception as e:
                        logger.error(f"Error processing entry {entry.link}, exception: {e}")
                        if not self.continue_on_failure:
                            raise e

            if new_last_update > last_update:
                self._update_cache(url, new_last_update)
