from abc import ABC, abstractmethod
from model.entities.article import Article
from services.api_clients.base.usage_tracking import ApiUsageTracker
import httpx
import logging
import time
import asyncio
from collections import deque
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
    async def fetch_articles(self, criteria: 'FetchCriteria') -> List['Article']:
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        pass



class BaseNewsApiClient(INewsApiClient):
    def __init__(self, config: 'ApiClientConfig', mapper: 'BaseMapper'):
        self._config = config
        self._mapper = mapper
        self._request_times = deque()
        self._usage_tracker = ApiUsageTracker(self.provider_id)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._client = httpx.AsyncClient(timeout=config.timeout)

    @property
    def is_enabled(self) -> bool:
        return self._config.is_enabled

    @abstractmethod
    async def _build_request_url(self, criteria: 'FetchCriteria') -> str:
        pass

    @abstractmethod
    async def _parse_response(self, response_data: Dict[str, Any]) -> List[Article]:
        pass

    def _can_make_request(self) -> bool:
        """Check if we can make a request within quota limits."""
        return self._usage_tracker.can_make_request(
            daily_limit=getattr(self._config, 'requests_per_day', None),
            monthly_limit=getattr(self._config, 'requests_per_month', None)
        )

    def _record_burst_call(self):
        self._request_times.append(time.time())

    async def _wait_for_burst_limit(self):
        """Handle per-second burst limiting with in-memory tracking."""
        requests_per_second = getattr(self._config, 'requests_per_second', None)
        if not requests_per_second:
            return

        now = time.time()

        # Remove requests older than 1 second
        while self._request_times and self._request_times[0] < now - 1.0:
            self._request_times.popleft()

        # If we're at the limit, wait
        if len(self._request_times) >= requests_per_second:
            sleep_time = 1.0 - (now - self._request_times[0])
            if sleep_time > 0:
                self._logger.debug(f"Burst limit reached, waiting {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

    async def fetch_articles(self, criteria: 'FetchCriteria') -> List[Article]:
        if not self.is_enabled:
            self._logger.info(f"{self.provider_id} is disabled, skipping fetch")
            return []

        if not self._can_make_request():
            self._logger.warning(f"{self.provider_id} quota exceeded, skipping request")
            return []

        await self._wait_for_burst_limit()

        try:
            url = await self._build_request_url(criteria)
            response = await self._client.get(url)
            response.raise_for_status()

            self._usage_tracker.record_api_call()
            self._record_burst_call()

            articles = await self._parse_response(response.json())
            self._logger.info(f"Fetched {len(articles)} articles from {self.provider_id}")
            return articles

        except Exception as e:
            self._logger.error(f"Error fetching from {self.provider_id}: {e}")
            return []

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this client."""
        stats = self._usage_tracker.get_usage_summary()

        remaining = self._usage_tracker.get_remaining_quota(
            daily_limit=getattr(self._config, 'requests_per_day', None),
            monthly_limit=getattr(self._config, 'requests_per_month', None)
        )
        stats.update(remaining)

        return stats