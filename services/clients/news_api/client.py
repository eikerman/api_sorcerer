# services/newsapi_client.py
from typing import Optional, override
from datetime import datetime, timedelta
from model.article import Article
from typing import List
import httpx
from urllib.parse import urlencode
from services.base.base_api_client import BaseNewsApiClient
import logging

logger = logging.getLogger(__name__)

class NewsApiClient(BaseNewsApiClient):
    """
    Client for NewsAPI.org Everything endpoint.

    Fetches ALL available articles with automatic pagination.
    """

    @property
    def provider_id(self) -> str:
        return "newsapi.org"

    async def fetch_all_articles(
            self,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None,
            max_results: Optional[int] = None
    ) -> List[Article]:
        """
        Fetch all articles with automatic pagination.

        Args:
            from_date: Start date (defaults to 24 hours ago)
            to_date: End date (defaults to now)
            max_results: Maximum total results to fetch (None = fetch all available)

        Returns:
            List of all articles across all pages
        """
        # Default date range: last 24 hours
        if from_date is None:
            from_date = datetime.now() - timedelta(hours=24)
        if to_date is None:
            to_date = datetime.now()

        all_articles = []
        page = 1
        page_size = 100  # Maximum allowed by NewsAPI

        while True:
            # Check if we should stop due to max_results
            if max_results and len(all_articles) >= max_results:
                logger.info(f"Reached max_results limit: {max_results}")
                break

            # Build URL for current page
            url = self._build_url(
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
                # Make request
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
                page_articles = self._mapper.to_domain_articles(articles_data)
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
        return all_articles[:max_results] if max_results else all_articles

    def _build_url(
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
            language: Language code

        Returns:
            Complete URL with query parameters
        """
        base_url = f"{self._config.base_url}/everything"

        params = {
            'apiKey': self._config.api_key,
            'q': 'a',  # Broad search to get everything
            'from': from_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': to_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'sortBy': 'publishedAt',  # Get newest first
            'pageSize': page_size,
            'page': page
        }

        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def fetch_articles(self) -> List[Article]:
        """
        Implement base class method - delegates to fetch_all_articles.

        Returns:
            All available articles
        """
        # Ignore criteria, just fetch everything from last 24 hours
        return await self.fetch_all_articles()