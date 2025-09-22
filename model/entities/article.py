# domain/entities/article.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from model.value_objects.article_id import ArticleId
from model.value_objects.url import Url
from model.value_objects.publish_date import PublishedDate

@dataclass(frozen=True)
class Article:
    id: ArticleId
    title: str
    content: str
    summary: Optional[str]
    source_url: Url
    author_name: Optional[str]
    published_at: PublishedDate
    source: 'Source'
    categories: List['Category']
    image_url: Optional[str] = None

    @classmethod
    def create(cls,
               title: str,
               content: str,
               source_url: str,
               published_at: datetime,
               source: 'Source',
               **kwargs) -> 'Article':
        return cls(
            id=ArticleId.generate(),
            title=title,
            content=content,
            summary=kwargs.get('summary'),
            source_url=Url(source_url),
            author_name=kwargs.get('author_name'),
            published_at=PublishedDate(published_at),
            source=source,
            categories=kwargs.get('categories', []),
            image_url=kwargs.get('image_url')
        )