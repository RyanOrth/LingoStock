import logging
from typing import Any, Iterator, List, Optional, Sequence

from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.news import NewsURLLoader

from langchain_community.document_loaders import RSSFeedLoader

logger = logging.getLogger(__name__)

class AgentRSSFeedLoader(RSSFeedLoader):
    def lazy_load(self) -> Iterator[Document]:
        try:
            import feedparser  # noqa:F401
        except ImportError:
            raise ImportError(
                "feedparser package not found, please install it with "
                "`pip install feedparser`"
            )

        for url in self._get_urls:
            try:
                feed = feedparser.parse(url, agent=self.newsloader_kwargs.get("browser_user_agent", None))
                if getattr(feed, "bozo", False):
                    raise ValueError(
                        f"Error fetching {url}, exception: {feed.bozo_exception}"
                    )
            except Exception as e:
                if self.continue_on_failure:
                    logger.error(f"Error fetching {url}, exception: {e}")
                    continue
                else:
                    raise e
            try:
                for entry in feed.entries:
                    loader = NewsURLLoader(
                        urls=[entry.link],
                        **self.newsloader_kwargs,
                    )
                    article = loader.load()[0]
                    article.metadata["feed"] = url
                    yield article
            except Exception as e:
                if self.continue_on_failure:
                    logger.error(f"Error processing entry {entry.link}, exception: {e}")
                    continue
                else:
                    raise e