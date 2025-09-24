# services/newsapi_client.py
from typing import Optional
from datetime import datetime
from services.base.base_api_client import BaseNewsApiClient


class NewsApiOrgClient(BaseNewsApiClient):
    """Client for newsapi.org"""

    @property
    def provider_name(self) -> str:
        return "newsapi.org"

    async def build_request_url(self, query: str, from_date: Optional[datetime]) -> str:
        url = f"{self.config.base_url}/everything"
        params = {
            'q': query,
            'apiKey': self.config.api_key,
            'sortBy': 'publishedAt'
        }

        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')

        # Build query string
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{url}?{query_string}"