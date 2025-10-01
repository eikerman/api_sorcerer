from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from model.article import Article
import logging

logger = logging.getLogger(__name__)

class BaseMapper(ABC):
    """Base mapper for converting API responses to domain models"""

    @abstractmethod
    def map_to_article(self, raw_data: Dict[str, Any], provider: str) -> Optional[Article]:
        """Map a single API response item to an Article"""
        pass

    def map_to_articles(self, raw_data: Dict[str, Any], provider: str) -> List[Article]:
        """Map API response to list of Articles"""
        articles = []
        items = self.get_items_from_response(raw_data)

        for item in items:
            try:
                article = self.map_to_article(item, provider)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error mapping article: {e}")
                continue

        return articles

    @abstractmethod
    def get_items_from_response(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract article items from API response"""
        pass