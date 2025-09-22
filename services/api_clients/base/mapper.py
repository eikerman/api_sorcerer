from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
from model.entities.article import Article

class BaseMapper(ABC):
    """
    Abstract base class for mapping API responses to domain objects.

    Each API provider will have its own mapper implementation that
    converts their specific response format to our standardized Article objects.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def to_domain_article(self, api_data: Dict[str, Any]) -> Article:
        """
        Convert a single API article response to a domain Article.

        Args:
            api_data: Raw article data from the API

        Returns:
            Article domain object

        Raises:
            ValueError: If required fields are missing or invalid
        """
        pass

    def to_domain_articles(self, api_articles: List[Dict[str, Any]]) -> List[Article]:
        """
        Convert a list of API articles to domain Articles.

        Handles errors gracefully - logs failures but continues processing other articles.

        Args:
            api_articles: List of raw article data from API

        Returns:
            List of successfully mapped Article objects
        """
        articles = []

        for i, api_article in enumerate(api_articles):
            try:
                article = self.to_domain_article(api_article)
                articles.append(article)
            except Exception as e:
                self._logger.warning(
                    f"Failed to map article {i} from {self.provider_name}: {e}"
                )
                # Continue processing other articles
                continue

        self._logger.info(f"Successfully mapped {len(articles)}/{len(api_articles)} articles from {self.provider_name}")
        return articles

    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get a value from dictionary, with optional nested key support."""
        if '.' in key:
            # Handle nested keys like 'source.name'
            keys = key.split('.')
            current = data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            return current
        else:
            return data.get(key, default)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Basic text cleaning
        cleaned = str(text).strip()

        # Remove common API artifacts
        if cleaned.endswith("..."):
            cleaned = cleaned[:-3].strip()

        return cleaned
