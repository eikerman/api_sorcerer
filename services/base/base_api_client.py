from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
from model.article import Article
from configs.api_config import ApiConfig
from services.base.rate_limiter import RateLimiter
from services.base.base_mapper import BaseMapper
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseNewsApiClient(ABC):
    """Base client for all news APIs"""

    def __init__(self, config: ApiConfig, mapper: BaseMapper):
        self._config = config
        self._mapper = mapper
        self._rate_limiter = RateLimiter(config.provider_id, config)
        self._client = httpx.AsyncClient(timeout=config.timeout)

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _make_request(self, url: str) -> httpx.Response:
        response = await self._client.get(url)
        response.raise_for_status()
        return response

    @abstractmethod
    async def fetch_articles(self, query: str) -> List[Article]:
        pass

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return self._rate_limiter.get_usage_stats()
