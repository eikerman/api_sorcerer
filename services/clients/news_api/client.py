# services/newsapi_client.py
from datetime import datetime, timedelta
from model.article import Article
from typing import List
import httpx
from urllib.parse import urlencode
from services.base.base_api_client import BaseNewsApiClient
from services.base.base_mapper import BaseMapper
from services.base.time_service import now
from configs.api_config import ApiConfig
import logging

logger = logging.getLogger(__name__)

class NewsApiClient(BaseNewsApiClient):
    """
    Client for NewsAPI.org Everything endpoint.

    Fetches ALL available articles with automatic pagination.
    """

    def __init__(self, config: ApiConfig, mapper: BaseMapper):
        super().__init__(config, mapper)
        self._client = httpx.AsyncClient(timeout=self._config.timeout)

    @property
    def provider_id(self) -> str:
        return "newsapi.org"

    async def fetch_articles(self, query: str) -> List[Article]:
        """
        Fetch all articles with automatic pagination.

        Args:

        Returns:
            List of all articles across all pages
        """
        # Default date range: last 24 hours
        from_date = now() - timedelta(hours=24)
        to_date = now()

        all_articles = []
        page = 1
        page_size = 100  # Maximum allowed by NewsAPI

        while True:
            url = self._build_request_url(
                page=page,
                page_size=page_size,
                from_date=from_date,
                to_date=to_date,
            )

            # Check rate limits and wait if necessary
            can_proceed = await self._rate_limiter.check_and_wait()
            if not can_proceed:
                logger.warning(f"Rate limit reached, stopping pagination at page {page}")
                break

            try:
                response = await self._client.get(url)
                response.raise_for_status()
                response_data = response.json()

                # Record the API call
                self._rate_limiter.record_request()

                # Parse response
                articles_data = response_data.get('articles', [])
                total_results = response_data.get('totalResults', 0)

                if not articles_data:
                    logger.info(f"No more articles on page {page}")
                    break

                # Convert to domain objects
                page_articles = self._mapper.map_to_articles(articles_data, provider=self.provider_id)
                all_articles.extend(page_articles)

                logger.info(
                    f"Page {page}: fetched {len(page_articles)} articles "
                    f"(total so far: {len(all_articles)}/{total_results})"
                )

                # Check if we've fetched all available articles
                if len(all_articles) >= total_results:
                    logger.info(f"Fetched all {total_results} available articles")
                    break

                # Check if there are more pages
                # NewsAPI returns empty array when no more results
                if len(articles_data) < page_size:
                    logger.info(f"Received partial page, no more results available")
                    break

                # Move to next page
                page += 1

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    def _build_request_url(
            self,
            page: int,
            page_size: int,
            from_date: datetime,
            to_date: datetime
    ) -> str:
        """
        Build NewsAPI URL for fetching everything.

        Args:
            page: Page number (1-indexed)
            page_size: Results per page (max 100)
            from_date: Start date
            to_date: End date

        Returns:
            Complete URL with query parameters
        """
        base_url = f"{self._config.base_url}/everything"

        params = {
            'apiKey': self._config.api_key,
            'q': 'a',
            'from': from_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': to_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'sortBy': 'publishedAt',  # Get newest first
            'pageSize': page_size,
            'page': page
        }

        query_string = urlencode(params)
        return f"{base_url}?{query_string}"
