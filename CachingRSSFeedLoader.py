import os
import json
import feedparser
import logging
from datetime import datetime
from typing import Any, Iterator, Optional, Sequence

from langchain_core.documents import Document
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

    def _get_cache_file_path(self, article_url: str) -> str:
        # Hash the article URL to create a unique filename
        filename = f"{hash(article_url)}.json"
        return os.path.join(self.cache_dir, filename)

    def _is_article_cached(self, article_url: str) -> bool:
        cache_file = self._get_cache_file_path(article_url)
        return os.path.exists(cache_file)

    def _get_cached_article(self, article_url: str) -> Document:
        cache_file = self._get_cache_file_path(article_url)
        with open(cache_file, 'r') as f:
            data = json.load(f)
            document = Document(content=data['content'], metadata=data['metadata'])
        return document

    def _cache_article(self, article_url: str, article: Document):
        cache_file = self._get_cache_file_path(article_url)
        with open(cache_file, 'w') as f:
            data = {'content': article.content, 'metadata': article.metadata}
            json.dump(data, f)

    def lazy_load(self) -> Iterator[Document]:
        for url in self._get_urls:
            feed = feedparser.parse(url, agent=self.newsloader_kwargs.get("browser_user_agent", None))
            if getattr(feed, "bozo", False):
                logger.error(f"Error fetching {url}, exception: {feed.bozo_exception}")
                if not self.continue_on_failure:
                    raise ValueError(f"Error fetching {url}, exception: {feed.bozo_exception}")

            for entry in feed.entries:
                if self._is_article_cached(entry.link):
                    yield self._get_cached_article(entry.link)
                else:
                    try:
                        loader = NewsURLLoader(urls=[entry.link], **self.newsloader_kwargs)
                        article = loader.load()[0]
                        article.metadata["feed"] = url
                        article.metadata["published"] = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d %H:%M:%S')
                        self._cache_article(entry.link, article)
                        yield article
                    except Exception as e:
                        logger.error(f"Error processing entry {entry.link}, exception: {e}")
                        if not self.continue_on_failure:
                            raise e
