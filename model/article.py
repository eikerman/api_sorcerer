# models/article.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib


@dataclass
class Article:
    """Article model focused on source URLs with additional metadata"""
    source_url: str
    title: str
    published_at: datetime
    provider: str  # Which API it came from

    # Nice-to-haves
    content: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None

    @property
    def url_hash(self) -> str:
        """Hash for deduplication"""
        return hashlib.md5(self.source_url.encode()).hexdigest()
