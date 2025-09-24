# services/api_client.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime
from model.article import Article
from configs.api_config import ApiConfig
from services.base.rate_limiter import RateLimiter
from services.base.base_mapper import BaseMapper


class BaseNewsApiClient(ABC):
    """Base client for all news APIs"""

    def __init__(self, config: ApiConfig, mapper: BaseMapper):
        self.config = config
        self.mapper = mapper
        self.rate_limiter = RateLimiter(config.provider_id, config)
        self._client = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def build_request_url(self, query: str, from_date: Optional[datetime]) -> str:
        """Build the API request URL"""
        pass

    async def fetch_articles(self, query: str, from_date: Optional[datetime] = None) -> List[Article]:
        """Fetch articles from the API with rate limiting"""
        if not self.config.enabled:
            return []

        # Check rate limits
        can_proceed = await self.rate_limiter.check_and_wait()
        if not can_proceed:
            print(f"Skipping {self.provider_name} due to rate limits")
            return []

        try:
            url = await self.build_request_url(query, from_date)

            # Make request
            if not self._client:
                self._client = httpx.AsyncClient(timeout=self.config.timeout)

            response = await self._client.get(url)
            response.raise_for_status()

            # Record successful request
            self.rate_limiter.record_request()

            # Map response to articles
            articles = self.mapper.map_to_articles(
                response.json(),
                self.provider_name
            )

            print(f"Fetched {len(articles)} articles from {self.provider_name}")
            return articles

        except Exception as e:
            print(f"Error fetching from {self.provider_name}: {e}")
            return []

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return self.rate_limiter.get_usage_stats()
