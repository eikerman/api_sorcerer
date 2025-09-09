from abc import ABC, abstractmethod
from typing import List, Optional, Any
from datetime import datetime
import httpx
import logging
from typing import List, Dict, Any

class INewsApiClient(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        pass

    @abstractmethod
    async def fetch_articles(self, criteria: 'FetchCriteria') -> List[Article]:
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        pass



class BaseNewsApiClient(INewsApiClient):
    def __init__(self, config: 'ApiClientConfig', mapper: 'BaseMapper'):
        self._config = config
        self._mapper = mapper
        self._logger = logging.getLogger(self.__class__.__name__)
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def is_enabled(self) -> bool:
        return self._config.is_enabled

    @abstractmethod
    async def _build_request_url(self, criteria: 'FetchCriteria') -> str:
        pass

    @abstractmethod
    async def _parse_response(self, response_data: Dict[str, Any]) -> List[Article]:
        pass

    async def fetch_articles(self, criteria: 'FetchCriteria') -> List[Article]:
        if not self.is_enabled:
            self._logger.info(f"{self.provider_id} is disabled, skipping fetch")
            return []

        try:
            url = await self._build_request_url(criteria)
            response = await self._client.get(url)
            response.raise_for_status()

            articles = await self._parse_response(response.json())
            self._logger.info(f"Fetched {len(articles)} articles from {self.provider_id}")
            return articles

        except Exception as e:
            self._logger.error(f"Error fetching from {self.provider_id}: {e}")
            return []