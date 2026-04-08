from typing import Dict, Any, List, Optional
from datetime import datetime
from model.article import Article
from services.base.base_mapper import BaseMapper

class NewsApiMapper(BaseMapper):
    """Mapper for newsapi.org responses"""

    def get_items_from_response(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return raw_data.get('articles', [])

    def map_to_article(self, raw_data: Dict[str, Any], provider: str) -> Optional[Article]:
        # Skip if no URL
        if not raw_data.get('url'):
            return None

        # Parse published date
        published_str = raw_data.get('publishedAt', '')
        if published_str:
            published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
        else:
            published_at = datetime.now()

        return Article(
            source_url=raw_data['url'],
            title=raw_data.get('title', ''),
            published_at=published_at,
            provider=provider,
            content=raw_data.get('content'),
            summary=raw_data.get('description'),
            author=raw_data.get('author'),
            image_url=raw_data.get('urlToImage')
        )