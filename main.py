import asyncio
import os
from datetime import datetime, timedelta
from services.article_service import ArticleService
from repository.article_repository import ArticleRepository

async def main():
    # Initialize repository
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'newsdb')
    db_user = os.environ.get('DB_USER', 'user')
    db_password = os.environ.get('DB_PASSWORD', 'password')

    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    repo = ArticleRepository(connection_string)

    await repo.initialize()

    # Initialize service
    service = ArticleService('config.yaml', repo)

    # Fetch articles from last 7 days
    from_date = datetime.now() - timedelta(days=7)
    new_count = await service.fetch_articles("technology", from_date)
    print(f"\nStored {new_count} new articles")

    # Get statistics
    stats = await repo.get_stats()
    print(f"\nRepository Statistics:")
    print(f"  Total articles: {stats['total_articles']}")
    print(f"  Unique URLs: {stats['unique_urls']}")
    print(f"  Articles by provider: {stats['articles_by_provider']}")

    usage_stats = await service.get_usage_stats()
    print(f"\nAPI Usage Statistics:")
    for provider, usage in usage_stats.items():
        print(f"  {provider}:")
        print(f"    Daily: {usage.get('daily_count')} / {usage.get('daily_remaining', 'unlimited')}")
        print(f"    Monthly: {usage.get('monthly_count')} / {usage.get('monthly_remaining', 'unlimited')}")

    # Export source URLs
    sources = await repo.get_unique_source_urls()
    with open('source_urls.txt', 'w') as f:
        for url in sources:
            f.write(url + '\n')
    print(f"\nExported {len(sources)} unique source URLs to source_urls.txt")

    # Cleanup
    await service.cleanup()
    await repo.close()

if __name__ == "__main__":
    asyncio.run(main())