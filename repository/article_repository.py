from typing import List, Optional, Dict, Any
import asyncpg
from datetime import datetime
from model.article import Article

class ArticleRepository:
    """Repository for article storage with focus on source URLs"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Create connection pool and tables"""
        self.pool = await asyncpg.create_pool(self.connection_string)

        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    url_hash VARCHAR(32) PRIMARY KEY,
                    source_url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    content TEXT,
                    summary TEXT,
                    author TEXT,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Indexes for efficient queries
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_source_url 
                ON articles(source_url)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_published_at 
                ON articles(published_at DESC)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_provider 
                ON articles(provider)
            ''')

    async def store_articles(self, articles: List[Article]) -> int:
        """Store articles, skipping duplicates. Returns count of new articles."""
        if not articles:
            return 0

        new_count = 0
        async with self.pool.acquire() as conn:
            for article in articles:
                result = await conn.fetchval('''
                    INSERT INTO articles 
                    (url_hash, source_url, title, published_at, provider, 
                     content, summary, author, image_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (url_hash) DO NOTHING
                    RETURNING 1
                ''',
                article.url_hash,
                article.source_url,
                article.title,
                article.published_at,
                article.provider,
                article.content,
                article.summary,
                article.author,
                article.image_url
                )
                if result:
                    new_count += 1

        return new_count

    async def get_unique_source_urls(self) -> List[str]:
        """Get all unique source URLs"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT DISTINCT source_url 
                FROM articles 
                ORDER BY source_url
            ''')
            return [row['source_url'] for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_articles,
                    COUNT(DISTINCT source_url) as unique_urls,
                    COUNT(DISTINCT provider) as providers,
                    MIN(published_at) as earliest_article,
                    MAX(published_at) as latest_article
                FROM articles
            ''')

            provider_counts = await conn.fetch('''
                SELECT provider, COUNT(*) as count
                FROM articles
                GROUP BY provider
                ORDER BY count DESC
            ''')

            return {
                'total_articles': stats['total_articles'],
                'unique_urls': stats['unique_urls'],
                'providers': stats['providers'],
                'earliest_article': stats['earliest_article'],
                'latest_article': stats['latest_article'],
                'articles_by_provider': {
                    row['provider']: row['count']
                    for row in provider_counts
                }
            }

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()