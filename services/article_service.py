from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from repository.article_repository import ArticleRepository
from services.client_factory import ApiClientFactory

class ArticleService:
    """Main service for fetching and storing articles"""

    def __init__(self, config_path: str, repository: ArticleRepository):
        self.repository = repository
        self.clients = ApiClientFactory.create_from_config(config_path)
        print(f"Initialized with {len(self.clients)} active API clients")

    async def fetch_articles(self, query: str, from_date: Optional[datetime] = None) -> int:
        """
        Fetch articles from all enabled APIs and store them.
        Returns count of new articles stored.
        """
        # Fetch from all APIs concurrently
        tasks = [client.fetch_articles(query, from_date) for client in self.clients]
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_articles = []
        for articles in results:
            all_articles.extend(articles)

        print(f"Fetched {len(all_articles)} total articles")

        # Store articles (repository handles deduplication)
        new_count = await self.repository.store_articles(all_articles)

        return new_count

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all clients"""
        stats = {}
        for client in self.clients:
            stats[client.provider_name] = client.get_usage_stats()
        return stats

    async def cleanup(self):
        """Clean up resources"""
        for client in self.clients:
            await client.close()